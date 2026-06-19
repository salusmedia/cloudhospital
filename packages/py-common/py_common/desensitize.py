"""敏感字段脱敏工具。日志/对外输出涉及敏感信息时必须先脱敏。

合规要求（见根 CLAUDE.md）：身份证、手机号、姓名等禁止以明文进入日志。
"""

from __future__ import annotations


def mask_phone(phone: str | None) -> str:
    """手机号脱敏：138****8000"""
    if not phone or len(phone) < 7:
        return "***"
    return f"{phone[:3]}****{phone[-4:]}"


def mask_id_card(id_card: str | None) -> str:
    """身份证脱敏：保留前 6 后 4。"""
    if not id_card or len(id_card) < 10:
        return "***"
    return f"{id_card[:6]}********{id_card[-4:]}"


def mask_name(name: str | None) -> str:
    """姓名脱敏：张三 -> 张*；张三丰 -> 张*丰。"""
    if not name:
        return "***"
    if len(name) == 1:
        return name
    if len(name) == 2:
        return name[0] + "*"
    return name[0] + "*" * (len(name) - 2) + name[-1]
