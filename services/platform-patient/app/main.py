"""平台服务 · 患者主数据（唯一真源）。

合规要点（见根 CLAUDE.md）：
- 敏感字段（姓名/身份证/手机号）用 pgcrypto 加密落盘，明文绝不入库。
- 读取统一脱敏（py_common.desensitize），明文不外泄、不入日志。
- 患者数据增删改查落审计。
- 加密密钥运行时注入，绝不写死。
"""

from __future__ import annotations

import hashlib

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from py_common import (
    AuthUser,
    audit_action,
    get_current_user,
    mask_id_card,
    mask_name,
    mask_phone,
)

app = FastAPI(title="平台服务 · 患者主数据")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "platform-patient"}


class PatientIn(BaseModel):
    patient_id: str
    name: str
    id_card: str | None = None
    phone: str | None = None
    gender: str | None = None
    org_id: str


class PatientOut(BaseModel):
    patient_id: str
    name: str  # 已脱敏
    id_card: str  # 已脱敏
    phone: str  # 已脱敏
    gender: str | None
    org_id: str
    # 参保信息（来自外部医保局数据，LEFT JOIN，可能为空）
    insurance_type: str | None = None
    filed: bool | None = None
    annual_reimbursed: float | None = None
    cap_line: float | None = None


_INSERT = text(
    """
    INSERT INTO platform_patient.patient
      (patient_id, name_enc, id_card_enc, id_card_hash, phone_enc, gender, org_id)
    VALUES
      (:pid,
       pgp_sym_encrypt(CAST(:name AS text), CAST(:k AS text)),
       CASE WHEN CAST(:idc AS text) IS NULL THEN NULL
            ELSE pgp_sym_encrypt(CAST(:idc AS text), CAST(:k AS text)) END,
       :idh,
       CASE WHEN CAST(:phone AS text) IS NULL THEN NULL
            ELSE pgp_sym_encrypt(CAST(:phone AS text), CAST(:k AS text)) END,
       :gender, :org)
    """
)

_SELECT = text(
    """
    SELECT p.patient_id,
           pgp_sym_decrypt(p.name_enc, CAST(:k AS text)) AS name,
           pgp_sym_decrypt(p.id_card_enc, CAST(:k AS text)) AS id_card,
           pgp_sym_decrypt(p.phone_enc, CAST(:k AS text)) AS phone,
           p.gender, p.org_id,
           i.insurance_type, i.filed, i.annual_reimbursed, i.cap_line
    FROM platform_patient.patient p
    LEFT JOIN platform_insurance.patient_insurance i ON i.patient_id = p.patient_id
    WHERE p.patient_id = :pid
    """
)


@app.post(f"{settings.api_prefix}/patients", status_code=status.HTTP_201_CREATED)
def create_patient(
    p: PatientIn,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """登记患者。敏感字段入库即加密；身份证另存不可逆哈希用于查重。"""
    idh = hashlib.sha256(p.id_card.encode()).hexdigest() if p.id_card else None
    db.execute(
        _INSERT,
        {
            "pid": p.patient_id, "name": p.name, "idc": p.id_card, "idh": idh,
            "phone": p.phone, "gender": p.gender, "org": p.org_id, "k": settings.pii_key,
        },
    )
    audit_action(
        user, action="create_patient", scenario="platform-patient", patient_id=p.patient_id
    )
    return {"patient_id": p.patient_id}


@app.get(f"{settings.api_prefix}/patients/{{patient_id}}", response_model=PatientOut)
def get_patient(
    patient_id: str,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PatientOut:
    """读取患者：解密后**统一脱敏**返回，明文不外泄。"""
    row = db.execute(_SELECT, {"pid": patient_id, "k": settings.pii_key}).mappings().first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="患者不存在")
    audit_action(
        user, action="get_patient", scenario="platform-patient", patient_id=patient_id
    )
    return PatientOut(
        patient_id=row["patient_id"],
        name=mask_name(row["name"]),
        id_card=mask_id_card(row["id_card"]),
        phone=mask_phone(row["phone"]),
        gender=row["gender"],
        org_id=row["org_id"],
        insurance_type=row["insurance_type"],
        filed=row["filed"],
        annual_reimbursed=float(row["annual_reimbursed"]) if row["annual_reimbursed"] is not None else None,
        cap_line=float(row["cap_line"]) if row["cap_line"] is not None else None,
    )
