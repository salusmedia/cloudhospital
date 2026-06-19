"""统一鉴权。

身份由网关校验后通过请求头下发（X-User-*），后端不重复解析 token，
只取身份做"数据权限/最小权限"校验。各接口用 Depends(get_current_user) 注入。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import unquote

from fastapi import Depends, Header, HTTPException, status


@dataclass
class AuthUser:
    user_id: str
    name: str
    roles: list[str] = field(default_factory=list)
    scopes: list[str] = field(default_factory=list)  # 可访问的科室代码，用于数据权限
    caps: list[str] = field(default_factory=list)  # 场景能力点，如 teleclinic:prescribe
    patient_id: str | None = None  # 居民/患者身份绑定的患者主数据 id（仅患者端登录时有）

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes

    def has_cap(self, cap: str) -> bool:
        return cap in self.caps


def get_current_user(
    x_user_id: str | None = Header(default=None),
    x_user_name: str | None = Header(default=None),
    x_user_roles: str | None = Header(default=None),
    x_user_scopes: str | None = Header(default=None),
    x_user_caps: str | None = Header(default=None),
    x_user_patient_id: str | None = Header(default=None),
) -> AuthUser:
    """从网关注入的请求头构造当前用户。缺失则 401。

    约定（重要）：HTTP 头只能是 ASCII。
    - roles/scopes/caps 用 ASCII 代码（如 doctor / card / teleclinic:prescribe），不要用中文名。
    - caps 是场景能力点（由 platform-auth 按 staff_scenario_enrollment 展开），用于场景级最小权限。
    - name 等可能含中文的字段由网关 URL-encode 后下发，这里 unquote 还原。
    """
    if not x_user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="未认证")
    return AuthUser(
        user_id=x_user_id,
        name=unquote(x_user_name) if x_user_name else "",
        roles=[r for r in (x_user_roles or "").split(",") if r],
        scopes=[s for s in (x_user_scopes or "").split(",") if s],
        caps=[c for c in (x_user_caps or "").split(",") if c],
        patient_id=x_user_patient_id or None,
    )


def require_roles(*required: str):
    """依赖工厂：要求用户具备指定角色之一。用法 Depends(require_roles("doctor"))。"""

    def checker(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if not any(r in user.roles for r in required):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="权限不足")
        return user

    return checker


def require_cap(*required: str):
    """依赖工厂：要求用户在场景里具备指定能力点之一（场景级最小权限）。

    能力点由 platform-auth 按 staff_scenario_enrollment + enrollment_capability 展开下发。
    用法 Depends(require_cap("teleclinic:prescribe"))。
    注意：这是"能不能做这个动作"的功能授权，数据可见性仍需 authz.scope_filter 把关。
    """

    def checker(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if not any(c in user.caps for c in required):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="未授权该场景能力")
        return user

    return checker
