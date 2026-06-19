"""场景 001 · 在线随访 —— 对外接口。

这是给团队抄的"样板接口"，演示如何正确使用共享层与合规要求：
- 鉴权：Depends(get_current_user)，由网关注入身份；越权返回 403。
- 数据权限：按 user.scopes 过滤，只返回有权科室的记录（最小权限）。
- 审计：查询患者数据落 audit_action。
- 脱敏：响应里的患者姓名脱敏，敏感明文不外泄、不入日志。
- 患者主数据不自存：这里只持有 patient_id 引用（真实场景调 platform-patient）。
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.config import settings
from py_common import AuthUser, audit_action, get_current_user, mask_name

router = APIRouter(prefix=settings.api_prefix, tags=["scenario-001"])


# ---- 契约模型（FastAPI 自动产出 OpenAPI → 前端 gen:types 同步） ----
class FollowupRecord(BaseModel):
    id: str
    patient_id: str
    patient_name: str  # 输出前脱敏
    dept_code: str  # 科室代码（数据权限按它判定）
    dept: str  # 科室显示名
    visit_date: date
    note: str


class FollowupPage(BaseModel):
    items: list[FollowupRecord]
    total: int
    page: int
    page_size: int


# ---- 演示数据（真实场景来自本场景库 + platform-patient） ----
_DEMO: list[dict] = [
    {"id": "f1", "patient_id": "p1001", "patient_name": "张三",
     "dept_code": "card", "dept": "心内科",
     "visit_date": date(2026, 6, 1), "note": "血压平稳"},
    {"id": "f2", "patient_id": "p1002", "patient_name": "欧阳娜娜",
     "dept_code": "endo", "dept": "内分泌科",
     "visit_date": date(2026, 6, 3), "note": "血糖偏高，调整用药"},
]


@router.get("/followups", response_model=FollowupPage)
async def list_followups(
    on: date | None = Query(default=None, description="按随访日期过滤"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: AuthUser = Depends(get_current_user),
) -> FollowupPage:
    """按日期查询随访记录（仅返回当前用户有权科室的数据）。"""
    rows = [r for r in _DEMO if user.has_scope(r["dept_code"])]
    if on:
        rows = [r for r in rows if r["visit_date"] == on]

    total = len(rows)
    start = (page - 1) * page_size
    page_rows = rows[start : start + page_size]

    audit_action(
        user,
        action="list_followups",
        scenario=settings.scenario_id,
        result="ok",
        extra={"count": len(page_rows), "on": on.isoformat() if on else None},
    )

    return FollowupPage(
        items=[
            FollowupRecord(**{**r, "patient_name": mask_name(r["patient_name"])})
            for r in page_rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/followups/{record_id}", response_model=FollowupRecord)
async def get_followup(
    record_id: str,
    user: AuthUser = Depends(get_current_user),
) -> FollowupRecord:
    row = next((r for r in _DEMO if r["id"] == record_id), None)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="记录不存在")
    if not user.has_scope(row["dept_code"]):  # 数据权限：越权访问
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="无权访问该患者记录")

    audit_action(
        user, action="get_followup", scenario=settings.scenario_id,
        patient_id=row["patient_id"], target=record_id,
    )
    return FollowupRecord(**{**row, "patient_name": mask_name(row["patient_name"])})
