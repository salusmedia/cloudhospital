"""轻量 HS256 令牌（JWT 风格），零外部依赖，便于私有化与离线测试。

platform-auth 用 create_token 签发；gateway 用 decode_token 校验。
两者共享同一 secret（由环境注入，绝不写死/不进仓库）。

生产可平滑替换为标准 PyJWT/JWKS，接口保持一致即可。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time


class TokenError(Exception):
    """令牌无效/过期/被篡改。"""


def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _sign(signing_input: str, secret: str) -> str:
    sig = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    return _b64e(sig)


def create_token(claims: dict, secret: str, expires_in: int = 3600) -> str:
    """签发令牌。claims 至少应含 sub(用户ID)。自动加 exp。"""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {**claims, "exp": int(time.time()) + expires_in}
    seg = f"{_b64e(_dump(header))}.{_b64e(_dump(payload))}"
    return f"{seg}.{_sign(seg, secret)}"


def decode_token(token: str, secret: str) -> dict:
    """校验签名与过期，返回 payload。失败抛 TokenError。"""
    try:
        h, p, s = token.split(".")
    except ValueError as e:
        raise TokenError("令牌格式错误") from e
    if not hmac.compare_digest(_sign(f"{h}.{p}", secret), s):
        raise TokenError("签名校验失败")
    try:
        payload = json.loads(_b64d(p))
    except Exception as e:  # noqa: BLE001
        raise TokenError("载荷解析失败") from e
    if int(payload.get("exp", 0)) < int(time.time()):
        raise TokenError("令牌已过期")
    return payload


def _dump(obj: dict) -> bytes:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode()
