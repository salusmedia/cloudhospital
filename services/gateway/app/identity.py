"""身份头处理。安全关键：

1. strip_client_identity —— 必须先剥离客户端伪造的 X-User-* 头，防止越权伪装。
2. build_identity_headers —— 只有网关校验令牌后，才注入可信身份头给下游。
   头只能 ASCII：name 用 URL-encode（下游 py_common.auth 会 unquote 还原）。
"""

from __future__ import annotations

from urllib.parse import quote

_IDENTITY_HEADERS = (
    "x-user-id",
    "x-user-name",
    "x-user-roles",
    "x-user-scopes",
    "x-user-caps",
    "x-user-patient-id",
)


def strip_client_identity(headers: dict[str, str]) -> dict[str, str]:
    """去掉客户端自带的身份头与 Authorization（下游不需要原始令牌）。"""
    return {
        k: v
        for k, v in headers.items()
        if k.lower() not in _IDENTITY_HEADERS and k.lower() != "authorization"
    }


def build_identity_headers(claims: dict) -> dict[str, str]:
    return {
        "X-User-Id": str(claims.get("sub", "")),
        "X-User-Name": quote(str(claims.get("name", ""))),
        "X-User-Roles": ",".join(claims.get("roles", []) or []),
        "X-User-Scopes": ",".join(claims.get("scopes", []) or []),
        "X-User-Caps": ",".join(claims.get("caps", []) or []),
        "X-User-Patient-Id": str(claims.get("patient_id", "") or ""),
    }


def extract_bearer(headers: dict[str, str]) -> str | None:
    for k, v in headers.items():
        if k.lower() == "authorization" and v.lower().startswith("bearer "):
            return v[7:].strip()
    return None
