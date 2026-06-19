"""平台服务 · 健康档案（跨院汇聚，只读）。

合规：临床内容是访问受控真源——治疗医护(按角色)或患者本人可读，落审计；禁止入日志。
访问控制：患者本人（user.patient_id==pid）或临床角色(doctor/nurse/admin/regulator)。
"""

from __future__ import annotations

from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from py_common import AuthUser, audit_action, get_current_user

app = FastAPI(title="平台服务 · 健康档案")

_CLINICAL_ROLES = {"doctor", "nurse", "admin", "regulator"}


def _authz(user: AuthUser, pid: str) -> None:
    if user.patient_id == pid:
        return
    if any(r in _CLINICAL_ROLES for r in user.roles):
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, detail="无权访问该患者档案")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "platform-archive"}


class Summary(BaseModel):
    encounters: int
    orgs: int
    reports: int
    diagnoses: int


@app.get(f"{settings.api_prefix}/patients/{{pid}}/summary", response_model=Summary)
def summary(pid: str, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> Summary:
    """档案概览：贯通机构数 / 就诊数 / 报告数 / 诊断数。"""
    _authz(user, pid)
    row = db.execute(
        text("""
          SELECT
            (SELECT count(*) FROM platform_archive.encounter WHERE patient_id=:p) AS encounters,
            (SELECT count(DISTINCT org_id) FROM platform_archive.encounter WHERE patient_id=:p) AS orgs,
            (SELECT count(*) FROM platform_archive.report WHERE patient_id=:p) AS reports,
            (SELECT count(*) FROM platform_archive.diagnosis WHERE patient_id=:p) AS diagnoses
        """),
        {"p": pid},
    ).mappings().first()
    audit_action(user, action="view_archive_summary", scenario="platform-archive", patient_id=pid)
    return Summary(**dict(row)) if row else Summary(encounters=0, orgs=0, reports=0, diagnoses=0)


class EncounterOut(BaseModel):
    encounter_id: str
    org_name: str | None
    dept_code: str
    type: str
    visit_time: datetime
    chief_complaint: str | None


@app.get(f"{settings.api_prefix}/patients/{{pid}}/encounters", response_model=list[EncounterOut])
def encounters(pid: str, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[EncounterOut]:
    _authz(user, pid)
    rows = db.execute(
        text("""
          SELECT e.encounter_id, o.name AS org_name, e.dept_code, e.type, e.visit_time, e.chief_complaint
          FROM platform_archive.encounter e
          LEFT JOIN platform_identity.organization o ON o.org_id=e.org_id
          WHERE e.patient_id=:p ORDER BY e.visit_time DESC
        """),
        {"p": pid},
    ).mappings().all()
    audit_action(user, action="view_archive_encounters", scenario="platform-archive", patient_id=pid)
    return [EncounterOut(**dict(x)) for x in rows]


class DiagnosisOut(BaseModel):
    name: str
    icd_code: str | None
    is_chronic: bool
    diagnosed_at: datetime


@app.get(f"{settings.api_prefix}/patients/{{pid}}/diagnoses", response_model=list[DiagnosisOut])
def diagnoses(pid: str, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[DiagnosisOut]:
    _authz(user, pid)
    rows = db.execute(
        text("SELECT name,icd_code,is_chronic,diagnosed_at FROM platform_archive.diagnosis WHERE patient_id=:p ORDER BY diagnosed_at DESC"),
        {"p": pid},
    ).mappings().all()
    audit_action(user, action="view_archive_diagnoses", scenario="platform-archive", patient_id=pid)
    return [DiagnosisOut(**dict(x)) for x in rows]


class ReportOut(BaseModel):
    report_id: str
    category: str
    item_name: str
    conclusion: str | None
    report_time: datetime
    org_name: str | None


@app.get(f"{settings.api_prefix}/patients/{{pid}}/reports", response_model=list[ReportOut])
def reports(pid: str, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ReportOut]:
    _authz(user, pid)
    rows = db.execute(
        text("""
          SELECT r.report_id, r.category, r.item_name, r.conclusion, r.report_time, o.name AS org_name
          FROM platform_archive.report r
          LEFT JOIN platform_identity.organization o ON o.org_id=r.org_id
          WHERE r.patient_id=:p ORDER BY r.report_time DESC
        """),
        {"p": pid},
    ).mappings().all()
    audit_action(user, action="view_archive_reports", scenario="platform-archive", patient_id=pid)
    return [ReportOut(**dict(x)) for x in rows]


class RxItem(BaseModel):
    drug_name: str
    usage: str | None
    course: str | None


class RxOut(BaseModel):
    rx_id: str
    status: str
    created_at: datetime
    items: list[RxItem]


@app.get(f"{settings.api_prefix}/patients/{{pid}}/prescriptions", response_model=list[RxOut])
def prescriptions(pid: str, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[RxOut]:
    _authz(user, pid)
    rxs = db.execute(
        text("SELECT rx_id,status,created_at FROM platform_archive.prescription WHERE patient_id=:p ORDER BY created_at DESC"),
        {"p": pid},
    ).mappings().all()
    out: list[RxOut] = []
    for rx in rxs:
        items = db.execute(
            text("SELECT drug_name,usage,course FROM platform_archive.prescription_item WHERE rx_id=:r"),
            {"r": rx["rx_id"]},
        ).mappings().all()
        out.append(RxOut(rx_id=rx["rx_id"], status=rx["status"], created_at=rx["created_at"], items=[RxItem(**dict(i)) for i in items]))
    audit_action(user, action="view_archive_prescriptions", scenario="platform-archive", patient_id=pid)
    return out
