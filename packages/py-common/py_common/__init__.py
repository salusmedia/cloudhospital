"""AI 云医院后端共享库。

各场景后端统一从这里取鉴权、审计、脱敏、日志、DB 基类、公共字段、数据权限与清分，
不要各自重复实现（尤其是合规相关的脱敏、审计与数据权限）。
"""

from py_common.audit import audit_action
from py_common.auth import (
    AuthUser,
    get_current_user,
    require_cap,
    require_roles,
)
from py_common.authz import has_global_scope, scope_filter
from py_common.clearing import RateCard, Split, split_income
from py_common.desensitize import mask_id_card, mask_name, mask_phone
from py_common.logging import get_logger
from py_common.models import CommonColumns, uuid7
from py_common.tokens import TokenError, create_token, decode_token

__all__ = [
    # 鉴权
    "AuthUser",
    "get_current_user",
    "require_roles",
    "require_cap",
    # 数据权限
    "scope_filter",
    "has_global_scope",
    # 审计 / 脱敏 / 日志
    "audit_action",
    "mask_id_card",
    "mask_name",
    "mask_phone",
    "get_logger",
    # 令牌
    "create_token",
    "decode_token",
    "TokenError",
    # 模型 / 公共字段
    "CommonColumns",
    "uuid7",
    # 清分 / 差异化收入
    "RateCard",
    "Split",
    "split_income",
]
