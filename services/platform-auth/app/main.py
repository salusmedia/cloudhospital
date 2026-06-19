"""统一登录鉴权：签发访问令牌 + 刷新令牌，支持刷新与登出（吊销）。

- 访问令牌（短 TTL）：含 sub/name/roles/scopes/caps/patient_id，网关校验后下发身份。
- 刷新令牌（长 TTL）：仅含 sub + jti，用于换新访问令牌；登出即把 jti 加入吊销集。
  演示用内存吊销集；生产应用 Redis/DB（多实例共享）。
"""

from __future__ import annotations

import uuid

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.users import User, authenticate, load_user
from py_common import TokenError, create_token, decode_token

app = FastAPI(title="平台服务 · 统一登录鉴权")

# 已吊销的刷新令牌 jti（演示内存集合；生产用 Redis/DB）。
_REVOKED: set[str] = set()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenPair(BaseModel):
    token: str
    refresh_token: str
    user_id: str
    name: str
    roles: list[str]
    scopes: list[str]
    caps: list[str]
    patient_id: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessOut(BaseModel):
    token: str


def _issue_access(user: User) -> str:
    return create_token(
        {
            "sub": user.user_id, "name": user.name, "roles": user.roles,
            "scopes": user.scopes, "caps": user.caps, "patient_id": user.patient_id, "typ": "access",
        },
        secret=settings.jwt_secret,
        expires_in=settings.token_ttl_seconds,
    )


def _issue_refresh(user: User) -> str:
    return create_token(
        {"sub": user.user_id, "typ": "refresh", "jti": uuid.uuid4().hex},
        secret=settings.jwt_secret,
        expires_in=settings.refresh_ttl_seconds,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "platform-auth"}


@app.post(f"{settings.api_prefix}/login", response_model=TokenPair)
async def login(req: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    """登录：校验身份库账号 → 签发 访问令牌 + 刷新令牌。网关侧 public。"""
    user = authenticate(db, req.username, req.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    return TokenPair(
        token=_issue_access(user), refresh_token=_issue_refresh(user),
        user_id=user.user_id, name=user.name, roles=user.roles,
        scopes=user.scopes, caps=user.caps, patient_id=user.patient_id,
    )


@app.post(f"{settings.api_prefix}/refresh", response_model=AccessOut)
async def refresh(req: RefreshRequest, db: Session = Depends(get_db)) -> AccessOut:
    """用刷新令牌换新的访问令牌（重新从身份库装配身份）。网关侧 public。"""
    try:
        payload = decode_token(req.refresh_token, settings.jwt_secret)
    except TokenError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e
    if payload.get("typ") != "refresh" or payload.get("jti") in _REVOKED:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="刷新令牌无效或已登出")
    user = load_user(db, str(payload.get("sub", "")))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="用户不可用")
    return AccessOut(token=_issue_access(user))


@app.post(f"{settings.api_prefix}/logout")
async def logout(req: RefreshRequest) -> dict[str, str]:
    """登出：吊销刷新令牌（其 jti 加入吊销集，后续不可再刷新）。网关侧 public。"""
    try:
        payload = decode_token(req.refresh_token, settings.jwt_secret)
        jti = payload.get("jti")
        if jti:
            _REVOKED.add(str(jti))
    except TokenError:
        pass  # 令牌已无效也视为登出成功
    return {"status": "ok"}
