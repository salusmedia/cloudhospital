"""把请求转发到上游服务。单独成模块，便于测试时 monkeypatch。"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

# 逐跳头：不应原样透传。
_HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "content-length", "host",
}


@dataclass
class UpstreamResponse:
    status_code: int
    content: bytes
    headers: dict[str, str]


async def forward(
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes,
    *,
    timeout: float = 30.0,
) -> UpstreamResponse:
    send_headers = {k: v for k, v in headers.items() if k.lower() not in _HOP_BY_HOP}
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.request(method, url, headers=send_headers, content=body)
    resp_headers = {k: v for k, v in resp.headers.items() if k.lower() not in _HOP_BY_HOP}
    return UpstreamResponse(resp.status_code, resp.content, resp_headers)
