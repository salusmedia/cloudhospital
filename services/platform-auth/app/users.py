"""数据库认证：对接 platform_identity（替代硬编码演示账号）。

- 账号/密码：app_user（password_hash，演示用 sha256；生产请 bcrypt/argon2 + 盐）。
- 角色：user_role。
- 数据权限 scopes：user_data_scope（scope_type=all → 'all'，否则取 dept_code）。
- 场景能力 caps：staff_scenario_enrollment + enrollment_capability。
- 患者绑定 patient_id：patient_guardian（relation='本人'，患者端登录用）。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass
class User:
    user_id: str
    name: str
    roles: list[str] = field(default_factory=list)
    scopes: list[str] = field(default_factory=list)
    caps: list[str] = field(default_factory=list)
    patient_id: str | None = None


def _resolve_scopes(db: Session, uid: str) -> list[str]:
    out: list[str] = []
    for scope_type, dept in db.execute(
        text("SELECT scope_type,dept_code FROM platform_identity.user_data_scope WHERE user_id=:u"),
        {"u": uid},
    ).all():
        if scope_type == "all":
            out.append("all")
        elif dept:
            out.append(dept)
    return out


def _assemble(db: Session, uid: str, name: str) -> User:
    """从身份库装配完整身份（角色/scopes/caps/patient_id）。"""
    roles = [r[0] for r in db.execute(
        text("SELECT role_code FROM platform_identity.user_role WHERE user_id=:u"), {"u": uid}
    ).all()]
    caps = [r[0] for r in db.execute(
        text("""SELECT ec.cap_code FROM platform_identity.staff_scenario_enrollment e
                JOIN platform_identity.enrollment_capability ec ON ec.enrollment_id=e.enrollment_id
                WHERE e.user_id=:u AND e.status='active' AND ec.granted"""),
        {"u": uid},
    ).all()]
    patient_id = db.scalar(
        text("SELECT patient_id FROM platform_identity.patient_guardian WHERE guardian_user_id=:u AND relation='本人' LIMIT 1"),
        {"u": uid},
    )
    return User(user_id=uid, name=name, roles=roles, scopes=_resolve_scopes(db, uid), caps=caps, patient_id=patient_id)


def authenticate(db: Session, username: str, password: str) -> User | None:
    """校验账号密码，命中则装配身份。"""
    row = db.execute(
        text("SELECT user_id,name,password_hash,status FROM platform_identity.app_user WHERE username=:u"),
        {"u": username},
    ).mappings().first()
    if row is None or row["status"] != "active" or not row["password_hash"]:
        return None
    if hashlib.sha256(password.encode()).hexdigest() != row["password_hash"]:
        return None
    return _assemble(db, row["user_id"], row["name"])


def load_user(db: Session, user_id: str) -> User | None:
    """按 user_id 重新装配身份（令牌刷新用，不校验密码）。"""
    row = db.execute(
        text("SELECT name,status FROM platform_identity.app_user WHERE user_id=:u"), {"u": user_id}
    ).mappings().first()
    if row is None or row["status"] != "active":
        return None
    return _assemble(db, user_id, row["name"])
