"""平台服务 · 文件对象元数据。原件走对象存储(MinIO/S3)，此处管理元数据 + 访问控制。

- 登记：临床角色（上传报告/影像/签署件元数据）。
- 查看/列举：临床角色或患者本人。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from py_common import AuthUser, audit_action, get_current_user

app = FastAPI(title="平台服务 · 文件")

_CLINICAL_ROLES = {"doctor", "nurse", "admin", "regulator"}


def _is_clinical(user: AuthUser) -> bool:
    return any(r in _CLINICAL_ROLES for r in user.roles)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "platform-file"}


class FileIn(BaseModel):
    filename: str
    mime: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None
    patient_id: str | None = None
    dept_code: str | None = None
    scenario: str | None = None


class FileOut(BaseModel):
    file_id: str
    filename: str
    mime: str | None
    size_bytes: int | None
    patient_id: str | None
    scenario: str | None
    storage_uri: str
    created_at: datetime


@app.post(f"{settings.api_prefix}/files", response_model=FileOut, status_code=status.HTTP_201_CREATED)
def register(payload: FileIn, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> FileOut:
    if not _is_clinical(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="无登记权限")
    fid = "F-" + uuid.uuid4().hex[:12]
    uri = f"minio://{settings.bucket}/{fid}"
    row = db.execute(
        text("""INSERT INTO platform_file.file_object(file_id,filename,mime,size_bytes,sha256,storage_uri,owner_user_id,patient_id,dept_code,scenario)
                VALUES(:fid,:fn,:mi,:sz,:sh,:uri,:own,:pid,:dept,:scn) RETURNING created_at"""),
        {"fid": fid, "fn": payload.filename, "mi": payload.mime, "sz": payload.size_bytes, "sh": payload.sha256, "uri": uri, "own": user.user_id, "pid": payload.patient_id, "dept": payload.dept_code, "scn": payload.scenario},
    ).mappings().first()
    assert row is not None
    audit_action(user, action="register_file", scenario="platform-file", patient_id=payload.patient_id, target=fid)
    return FileOut(file_id=fid, filename=payload.filename, mime=payload.mime, size_bytes=payload.size_bytes, patient_id=payload.patient_id, scenario=payload.scenario, storage_uri=uri, created_at=row["created_at"])


def _to_out(x: dict) -> FileOut:
    return FileOut(file_id=x["file_id"], filename=x["filename"], mime=x["mime"], size_bytes=x["size_bytes"], patient_id=x["patient_id"], scenario=x["scenario"], storage_uri=x["storage_uri"], created_at=x["created_at"])


@app.get(f"{settings.api_prefix}/files/{{fid}}", response_model=FileOut)
def get_file(fid: str, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> FileOut:
    x = db.execute(text("SELECT * FROM platform_file.file_object WHERE file_id=:f"), {"f": fid}).mappings().first()
    if x is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="文件不存在")
    if not (_is_clinical(user) or user.patient_id == x["patient_id"]):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="无权访问该文件")
    audit_action(user, action="get_file", scenario="platform-file", patient_id=x["patient_id"], target=fid)
    return _to_out(dict(x))


@app.get(f"{settings.api_prefix}/patients/{{pid}}/files", response_model=list[FileOut])
def list_files(pid: str, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[FileOut]:
    if not (_is_clinical(user) or user.patient_id == pid):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="无权访问")
    rows = db.execute(text("SELECT * FROM platform_file.file_object WHERE patient_id=:p ORDER BY created_at DESC"), {"p": pid}).mappings().all()
    return [_to_out(dict(x)) for x in rows]
