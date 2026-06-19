"""平台服务 · 数据授权/知情同意。V10「数据授权管理·全程留痕·随时撤回」。

- 查看：患者本人或临床角色。
- 授予/撤回：患者本人（自主管理）或管理员。每次操作落审计 + evidence_hash 留痕。
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from py_common import AuthUser, audit_action, get_current_user

app = FastAPI(title="平台服务 · 数据授权")

_CLINICAL_ROLES = {"doctor", "nurse", "admin", "regulator"}


def _can_view(user: AuthUser, pid: str) -> bool:
    return user.patient_id == pid or any(r in _CLINICAL_ROLES for r in user.roles)


def _can_manage(user: AuthUser, pid: str) -> None:
    if user.patient_id == pid or "admin" in user.roles:
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, detail="只能管理本人的数据授权")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "platform-consent"}


class ConsentOut(BaseModel):
    id: str
    grantee: str
    grantee_name: str | None
    purpose: str
    scope: str | None
    status: str
    granted_at: datetime
    revoked_at: datetime | None


@app.get(f"{settings.api_prefix}/patients/{{pid}}/consents", response_model=list[ConsentOut])
def list_consents(pid: str, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ConsentOut]:
    if not _can_view(user, pid):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="无权查看该患者授权")
    rows = db.execute(
        text("""SELECT id,grantee,grantee_name,purpose,scope,status,granted_at,revoked_at
                FROM platform_consent.consent_record WHERE patient_id=:p ORDER BY granted_at DESC"""),
        {"p": pid},
    ).mappings().all()
    audit_action(user, action="list_consents", scenario="platform-consent", patient_id=pid)
    return [ConsentOut(id=str(x["id"]), **{k: x[k] for k in ("grantee", "grantee_name", "purpose", "scope", "status", "granted_at", "revoked_at")}) for x in rows]


class GrantIn(BaseModel):
    patient_id: str
    grantee: str
    grantee_name: str | None = None
    purpose: str
    scope: str | None = None


@app.post(f"{settings.api_prefix}/consents", response_model=ConsentOut, status_code=status.HTTP_201_CREATED)
def grant(payload: GrantIn, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> ConsentOut:
    _can_manage(user, payload.patient_id)
    now = datetime.now(timezone.utc)
    ev = hashlib.sha256(f"{payload.patient_id}{payload.grantee}{now.isoformat()}".encode()).hexdigest()
    row = db.execute(
        text("""INSERT INTO platform_consent.consent_record(patient_id,grantee,grantee_name,purpose,scope,status,granted_at,evidence_hash,updated_by)
                VALUES(:p,:g,:gn,:pu,:sc,'granted',:t,:ev,:by) RETURNING id"""),
        {"p": payload.patient_id, "g": payload.grantee, "gn": payload.grantee_name, "pu": payload.purpose, "sc": payload.scope, "t": now, "ev": ev, "by": user.user_id},
    ).mappings().first()
    assert row is not None
    audit_action(user, action="grant_consent", scenario="platform-consent", patient_id=payload.patient_id, target=payload.grantee)
    return ConsentOut(id=str(row["id"]), grantee=payload.grantee, grantee_name=payload.grantee_name, purpose=payload.purpose, scope=payload.scope, status="granted", granted_at=now, revoked_at=None)


@app.post(f"{settings.api_prefix}/consents/{{cid}}/revoke")
def revoke(cid: str, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    row = db.execute(text("SELECT patient_id,status FROM platform_consent.consent_record WHERE id=:i"), {"i": cid}).mappings().first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="授权记录不存在")
    _can_manage(user, row["patient_id"])
    db.execute(
        text("UPDATE platform_consent.consent_record SET status='revoked', revoked_at=:t, updated_by=:by WHERE id=:i"),
        {"t": datetime.now(timezone.utc), "by": user.user_id, "i": cid},
    )
    audit_action(user, action="revoke_consent", scenario="platform-consent", patient_id=row["patient_id"], target=cid)
    return {"id": cid, "status": "revoked"}
