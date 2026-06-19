"""路由解析：把请求路径匹配到上游服务。

路由 = 平台服务内置路由 + 场景路由(routes.json，脚手架维护)。
按前缀最长匹配；boundary 严格（/api/scenario-001 不会误匹配 /api/scenario-0011）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Route:
    prefix: str
    service: str  # docker 服务名 = 主机名
    port: int
    public: bool = False  # True 表示无需令牌（如登录）


# 平台服务内置路由。端口约定：平台服务 81xx。
PLATFORM_ROUTES: list[Route] = [
    Route("/api/platform-auth/login", "platform-auth", 8101, public=True),
    Route("/api/platform-auth/refresh", "platform-auth", 8101, public=True),
    Route("/api/platform-auth/logout", "platform-auth", 8101, public=True),
    Route("/api/platform-auth", "platform-auth", 8101),
    Route("/api/platform-patient", "platform-patient", 8102),
    Route("/api/platform-ai", "platform-ai", 8103),
    Route("/api/platform-file", "platform-file", 8104),
    Route("/api/platform-archive", "platform-archive", 8105),
    Route("/api/platform-iot", "platform-iot", 8106),
    Route("/api/platform-consent", "platform-consent", 8107),
]


def load_routes(routes_file: str | Path) -> list[Route]:
    """合并平台路由与场景路由，按前缀长度降序（最长匹配优先）。"""
    routes = list(PLATFORM_ROUTES)
    p = Path(routes_file)
    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))
        for r in data.get("routes", []):
            routes.append(Route(prefix=r["prefix"], service=r["service"], port=int(r["port"])))
    routes.sort(key=lambda r: len(r.prefix), reverse=True)
    return routes


def _matches(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix + "/")


def resolve_route(path: str, routes: list[Route]) -> Route | None:
    for r in routes:  # 已按长度降序，首个命中即最长匹配
        if _matches(path, r.prefix):
            return r
    return None


def upstream_url(route: Route, path: str, query: str, *, use_localhost: bool) -> str:
    host = "localhost" if use_localhost else route.service
    url = f"http://{host}:{route.port}{path}"
    return f"{url}?{query}" if query else url
