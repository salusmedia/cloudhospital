"""平台 AI 能力接口：处方审方（rx-review）、AI 分诊（triage）。

优先调用 Claude API（需 PLATFORM_AI_ANTHROPIC_API_KEY 环境变量）；
未配置 API Key 时自动降级到规则引擎（演示可用）。
"""

from __future__ import annotations

import json
import os

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from py_common import AuthUser, audit_action, get_current_user

from app.config import settings

router = APIRouter(prefix="/api/platform-ai", tags=["platform-ai"])

# ---- 规则引擎（无 AI Key 时的兜底）--------------------------------------

_NSAID_DRUGS = ("布洛芬", "双氯芬酸", "吲哚美辛", "阿司匹林")
_ANTIBIOTIC_DRUGS = ("青霉素", "阿莫西林", "头孢", "左氧氟沙星", "甲硝唑")

_PRIORITY_KEYWORDS = {
    "P1": ("胸痛", "呼吸困难", "意识不清", "大出血", "晕厥", "剧烈腹痛"),
    "P2": ("发热", "头痛", "咳嗽", "腹痛", "恶心", "呕吐", "腹泻"),
    "P3": ("复诊", "随访", "调药", "换药", "慢病"),
}


def _rule_rx_review(drug_name: str, usage: str | None, patient_context: str | None) -> dict:
    """基于规则的处方审方：NSAID 相互作用 + 青霉素过敏提示。"""
    drug_upper = (drug_name or "").upper()
    context_upper = (patient_context or "").upper()

    if any(k in drug_name for k in _NSAID_DRUGS):
        if "抗凝" in context_upper or "华法林" in context_upper or "血小板" in context_upper:
            return {"result": "warn", "note": "NSAID 与抗凝/抗血小板药物合用增加出血风险，请复核"}
        return {"result": "passed", "note": None}

    if any(k in drug_name for k in _ANTIBIOTIC_DRUGS):
        if "青霉素过敏" in context_upper or "β-内酰胺过敏" in context_upper:
            return {"result": "rejected", "note": "患者有青霉素/β-内酰胺过敏史，禁止使用"}
        return {"result": "passed", "note": "抗生素使用须明确感染指征，遵医嘱足疗程"}

    return {"result": "passed", "note": None}


def _rule_triage(chief_complaint: str, dept_code: str | None) -> dict:
    for priority, kws in _PRIORITY_KEYWORDS.items():
        if any(k in chief_complaint for k in kws):
            return {"priority": priority, "note": f"主诉含 '{[k for k in kws if k in chief_complaint][0]}'，分诊优先级 {priority}"}
    return {"priority": "P3", "note": "常规复诊，优先级 P3"}


# ---- Claude API 调用（可选）----------------------------------------------

def _get_anthropic_client():
    """延迟导入 anthropic SDK；未安装/无 Key 时返回 None。"""
    api_key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None
    try:
        import anthropic  # type: ignore[import]
        return anthropic.Anthropic(api_key=api_key)
    except ImportError:
        return None


def _claude_rx_review(drug_name: str, usage: str | None, patient_context: str | None) -> dict:
    client = _get_anthropic_client()
    if client is None:
        return _rule_rx_review(drug_name, usage, patient_context)

    prompt = (
        f"请审核以下电子处方，评估用药安全性：\n"
        f"- 药品：{drug_name}\n"
        f"- 用法用量：{usage or '未填写'}\n"
        f"- 患者情况：{patient_context or '无'}\n\n"
        "请以 JSON 格式回复，字段：result（passed/warn/rejected）、note（简短审核意见，不超过50字，无问题则 null）。"
        "只输出 JSON，不要其他文字。"
    )
    try:
        msg = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=256,
            system="你是一名临床药师 AI，专门进行电子处方合理性审核。严格按格式输出 JSON，不要解释。",
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        parsed = json.loads(raw)
        return {
            "result": parsed.get("result", "passed"),
            "note": parsed.get("note"),
        }
    except Exception:
        return _rule_rx_review(drug_name, usage, patient_context)


def _claude_triage(chief_complaint: str, dept_code: str | None) -> dict:
    client = _get_anthropic_client()
    if client is None:
        return _rule_triage(chief_complaint, dept_code)

    prompt = (
        f"患者主诉：{chief_complaint}\n"
        f"预约科室：{dept_code or '未定'}\n\n"
        "请以 JSON 格式回复分诊结果，字段：priority（P1/P2/P3）、note（分诊提示，不超过30字）。"
        "只输出 JSON。"
    )
    try:
        msg = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=128,
            system="你是急诊分诊 AI，P1=危急，P2=急诊，P3=常规。严格按格式输出 JSON。",
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        parsed = json.loads(raw)
        return {"priority": parsed.get("priority", "P3"), "note": parsed.get("note")}
    except Exception:
        return _rule_triage(chief_complaint, dept_code)


# ---- 接口定义 ----------------------------------------------------------

class RxReviewIn(BaseModel):
    drug_name: str
    usage: str | None = None
    patient_context: str | None = None  # 患者当前诊断/用药情况（脱敏后传入）


class RxReviewOut(BaseModel):
    result: str       # passed | warn | rejected
    note: str | None  # 审核意见
    engine: str       # claude | rule（方便路演说明）


@router.post("/rx-review", response_model=RxReviewOut)
def rx_review(
    payload: RxReviewIn,
    user: AuthUser = Depends(get_current_user),
) -> RxReviewOut:
    """处方 AI 审方。"""
    api_key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    engine = "claude" if api_key else "rule"
    res = _claude_rx_review(payload.drug_name, payload.usage, payload.patient_context)
    audit_action(
        user,
        action="rx_review",
        scenario="platform-ai",
        result=res["result"],
        extra={"drug": payload.drug_name, "engine": engine},
    )
    return RxReviewOut(result=res["result"], note=res.get("note"), engine=engine)


class TriageIn(BaseModel):
    chief_complaint: str
    dept_code: str | None = None


class TriageOut(BaseModel):
    priority: str     # P1 | P2 | P3
    note: str | None
    engine: str


@router.post("/triage", response_model=TriageOut)
def triage(
    payload: TriageIn,
    user: AuthUser = Depends(get_current_user),
) -> TriageOut:
    """AI 分诊：根据主诉给出就诊优先级。"""
    api_key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    engine = "claude" if api_key else "rule"
    res = _claude_triage(payload.chief_complaint, payload.dept_code)
    audit_action(
        user,
        action="triage",
        scenario="platform-ai",
        result=res["priority"],
    )
    return TriageOut(priority=res["priority"], note=res.get("note"), engine=engine)
