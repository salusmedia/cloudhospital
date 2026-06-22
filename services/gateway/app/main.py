"""统一网关：鉴权 → 注入身份 → 路由转发。

主链路：
  客户端(Bearer 令牌) → 网关校验令牌 → 剥离伪造身份头 → 注入可信 X-User-* → 转发到上游场景/平台服务
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import FastAPI, Request, Response

from app import proxy
from app.config import settings
from app.identity import build_identity_headers, extract_bearer, strip_client_identity
from app.routing import load_routes, resolve_route, upstream_url
from py_common import TokenError, decode_token

app = FastAPI(title="统一网关")
ROUTES = load_routes(settings.routes_file)

_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "gateway", "routes": str(len(ROUTES))}


def _serve_static(path: str) -> Response:
    """同源托管 web_root 下的静态资源。

    web_root 聚合多个前端：portal 在根，各 Next 静态导出在子目录
    （/scenario-XXX、/patient、/regulator）。
    - 目录 → 补 index.html（每个 app 一个 index.html）。
    - 未命中文件 → 回落到该 app（首段路径）的 index.html；无则回根（portal SPA）。
    """
    root = Path(settings.web_root).resolve()
    rel = path.lstrip("/")
    candidate = (root / rel).resolve()

    # 防目录穿越：必须在 root 之内（或就是 root）
    if candidate != root and root not in candidate.parents:
        candidate = root

    # 目录 → index.html
    if candidate.is_dir():
        candidate = candidate / "index.html"

    if not candidate.is_file():
        # 回落：首段是某个已部署 app 目录则回该 app 的 index.html，否则回根。
        seg = rel.split("/", 1)[0] if rel else ""
        app_index = root / seg / "index.html"
        candidate = app_index if seg and app_index.is_file() else root / "index.html"

    if not candidate.is_file():
        return _json_error(404, "NO_UI", "未配置前端")
    ctype = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
    return Response(content=candidate.read_bytes(), media_type=ctype)


def _json_error(status_code: int, code: str, message: str) -> Response:
    import json

    return Response(
        content=json.dumps({"code": code, "message": message}, ensure_ascii=False),
        status_code=status_code,
        media_type="application/json",
    )


@app.api_route("/{full_path:path}", methods=_METHODS)
async def gateway(full_path: str, request: Request) -> Response:
    path = "/" + full_path
    # 非 /api 路径：若配置了前端目录，同源托管之（API 与页面同源，免跨域）。
    if settings.web_root and not path.startswith("/api"):
        return _serve_static(path)
    route = resolve_route(path, ROUTES)
    if route is None:
        return _json_error(404, "NO_ROUTE", f"无匹配路由: {path}")

    headers = strip_client_identity(dict(request.headers))

    if not route.public:
        token = extract_bearer(dict(request.headers))
        if not token:
            return _json_error(401, "NO_TOKEN", "缺少令牌")
        try:
            claims = decode_token(token, settings.jwt_secret)
        except TokenError as e:
            return _json_error(401, "BAD_TOKEN", str(e))
        headers.update(build_identity_headers(claims))

    body = await request.body()
    url = upstream_url(route, path, request.url.query, use_localhost=settings.use_localhost)
    up = await proxy.forward(
        request.method, url, headers, body, timeout=settings.request_timeout
    )
    return Response(content=up.content, status_code=up.status_code, headers=up.headers)
