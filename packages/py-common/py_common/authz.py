"""数据权限过滤 + 跨机构记录授权（见 docs/08-数据库设计.md 第 4 节）。

场景查询统一走这里，**不要**在各场景里裸写 `WHERE dept_code`，避免漏判导致越权。

- scope_filter：按 AuthUser.scopes（科室代码）过滤业务表，并默认排除软删除行。
- 跨机构可见性（转诊/MDT/会诊）：通过 record_grant 授予的资源 id 放行——
  一张转诊单同时属于转出/接收机构，单靠 dept_code 看不全，传入 extra_visible_ids 即可 OR 放行。
"""

from __future__ import annotations

from typing import Any, TypeVar

from sqlalchemy import Select

from py_common.auth import AuthUser

ALL_SCOPE = "all"
ADMIN_ROLE = "admin"
# 无任何 scope 时用的哨兵：使 IN 条件恒不命中（看不到任何数据），语义清晰且避免空 IN 警告
_NO_MATCH = "__none__"

_S = TypeVar("_S", bound=Select[Any])


def has_global_scope(user: AuthUser) -> bool:
    """全局可见：平台管理员或显式持有 all scope。"""
    return ALL_SCOPE in user.scopes or ADMIN_ROLE in user.roles


def scope_filter(
    stmt: _S,
    model: Any,
    user: AuthUser,
    *,
    extra_visible_ids: list[Any] | None = None,
    include_deleted: bool = False,
) -> _S:
    """给查询语句叠加数据权限与软删除过滤。

    参数：
      model            业务 ORM 模型（须含 dept_code；建议继承 CommonColumns）。
      user             当前用户（网关注入身份）。
      extra_visible_ids 跨机构授权放行的资源 id（来自 record_grant 命中）。
      include_deleted  是否包含软删除行（默认排除）。
    """
    if not has_global_scope(user):
        scopes = user.scopes or [_NO_MATCH]
        cond = model.dept_code.in_(scopes)
        if extra_visible_ids:
            cond = cond | model.id.in_(extra_visible_ids)
        stmt = stmt.where(cond)

    if not include_deleted and hasattr(model, "is_deleted"):
        stmt = stmt.where(model.is_deleted.is_(False))

    return stmt
