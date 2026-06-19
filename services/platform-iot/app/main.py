"""平台服务 · 体征监测（设备/护士/自报实时回传，带异常判定）。

访问控制：患者本人(自报/查看)或临床角色(doctor/nurse/admin/regulator)。
异常判定：按 vital_threshold 的 low/high 区间，越界即 abnormal_flag=true。
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from py_common import AuthUser, audit_action, get_current_user

app = FastAPI(title="平台服务 · 体征监测")

_CLINICAL_ROLES = {"doctor", "nurse", "admin", "regulator"}


def _authz(user: AuthUser, pid: str) -> None:
    if user.patient_id == pid or any(r in _CLINICAL_ROLES for r in user.roles):
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, detail="无权访问该患者体征")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "platform-iot"}


class VitalIn(BaseModel):
    patient_id: str
    metric: str  # bp/glucose/spo2/hr/temp/weight
    value_num: float | None = None
    value_text: str | None = None
    unit: str | None = None
    source: str = "device"
    org_id: str | None = None
    dept_code: str | None = None


class VitalOut(BaseModel):
    metric: str
    value_num: float | None
    value_text: str | None
    unit: str | None
    measured_at: datetime
    source: str
    abnormal_flag: bool


@app.post(f"{settings.api_prefix}/vitals", response_model=VitalOut, status_code=status.HTTP_201_CREATED)
def record(v: VitalIn, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> VitalOut:
    """回传一条体征，按阈值判定异常。"""
    _authz(user, v.patient_id)
    th = db.execute(
        text("SELECT low_num,high_num,unit FROM platform_iot.vital_threshold WHERE metric=:m"),
        {"m": v.metric},
    ).mappings().first()
    abnormal = False
    if v.value_num is not None and th is not None:
        if th["low_num"] is not None and v.value_num < float(th["low_num"]):
            abnormal = True
        if th["high_num"] is not None and v.value_num > float(th["high_num"]):
            abnormal = True
    now = datetime.now(timezone.utc)
    db.execute(
        text("""INSERT INTO platform_iot.vital_sign
                 (patient_id,metric,value_num,value_text,unit,measured_at,source,abnormal_flag,org_id,dept_code)
                VALUES(:p,:m,:vn,:vt,:u,:t,:s,:a,:o,:d)"""),
        {
            "p": v.patient_id, "m": v.metric, "vn": v.value_num, "vt": v.value_text,
            "u": v.unit or (th["unit"] if th else None), "t": now, "s": v.source,
            "a": abnormal, "o": v.org_id, "d": v.dept_code,
        },
    )
    audit_action(user, action="record_vital", scenario="platform-iot", patient_id=v.patient_id, extra={"metric": v.metric, "abnormal": abnormal})
    return VitalOut(metric=v.metric, value_num=v.value_num, value_text=v.value_text, unit=v.unit, measured_at=now, source=v.source, abnormal_flag=abnormal)


_SELECT_COLS = "metric,value_num,value_text,unit,measured_at,source,abnormal_flag"


@app.get(f"{settings.api_prefix}/patients/{{pid}}/vitals", response_model=list[VitalOut])
def list_vitals(
    pid: str,
    metric: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[VitalOut]:
    _authz(user, pid)
    sql = f"SELECT {_SELECT_COLS} FROM platform_iot.vital_sign WHERE patient_id=:p"
    params: dict = {"p": pid, "l": limit}
    if metric:
        sql += " AND metric=:m"
        params["m"] = metric
    sql += " ORDER BY measured_at DESC LIMIT :l"
    rows = db.execute(text(sql), params).mappings().all()
    return [VitalOut(**dict(x)) for x in rows]


@app.get(f"{settings.api_prefix}/patients/{{pid}}/vitals/latest", response_model=list[VitalOut])
def latest(pid: str, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[VitalOut]:
    """每个指标的最新一条。"""
    _authz(user, pid)
    rows = db.execute(
        text(f"""SELECT DISTINCT ON (metric) {_SELECT_COLS}
                 FROM platform_iot.vital_sign WHERE patient_id=:p
                 ORDER BY metric, measured_at DESC"""),
        {"p": pid},
    ).mappings().all()
    return [VitalOut(**dict(x)) for x in rows]


@app.get(f"{settings.api_prefix}/patients/{{pid}}/alerts", response_model=list[VitalOut])
def alerts(pid: str, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[VitalOut]:
    """异常体征（预警）。"""
    _authz(user, pid)
    rows = db.execute(
        text(f"SELECT {_SELECT_COLS} FROM platform_iot.vital_sign WHERE patient_id=:p AND abnormal_flag ORDER BY measured_at DESC LIMIT 50"),
        {"p": pid},
    ).mappings().all()
    return [VitalOut(**dict(x)) for x in rows]
