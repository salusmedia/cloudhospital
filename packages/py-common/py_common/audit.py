"""审计日志。患者数据的增删改查等关键操作必须落审计（满足等保/合规追溯）。

记录：谁(user)、何时(ts)、对哪个患者(patient_id)、做了什么(action)、结果。
审计内容本身也要避免明文敏感信息——传 patient_id 等引用，不传姓名/身份证明文。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from py_common.auth import AuthUser
from py_common.logging import get_logger

_audit_logger = get_logger("audit")


def audit_action(
    user: AuthUser,
    action: str,
    *,
    scenario: str,
    patient_id: str | None = None,
    target: str | None = None,
    result: str = "ok",
    extra: dict | None = None,
) -> None:
    """记录一条审计。生产环境应改为写独立审计库/审计服务，此处先落结构化日志。"""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "user_id": user.user_id,
        "roles": user.roles,
        "scenario": scenario,
        "action": action,
        "patient_id": patient_id,
        "target": target,
        "result": result,
        "extra": extra or {},
    }
    _audit_logger.info("AUDIT %s", json.dumps(entry, ensure_ascii=False))
