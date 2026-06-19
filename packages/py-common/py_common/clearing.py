"""阳光收入·空中清分：把一次计酬服务拆成机构/科室/个人多方分账。

见 docs/08-数据库设计.md 第 5 节。差异化收入的核心：
**个人到账 = 单价 × 个人分成 × 综合绩效系数，并夹在 [保底, 封顶] 之间**；
机构/科室按固定比例分；平台/清算方吸收绩效调节带来的差额（保证各方金额加总 = 毛收入）。

纯函数，无 DB 依赖，便于单测。金额一律用 Decimal，分位四舍五入。
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


def _money(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class RateCard:
    """计价规则（service_rate_card 的运行时投影）。比例之和应为 1。"""

    individual_ratio: Decimal
    dept_ratio: Decimal
    org_ratio: Decimal
    platform_ratio: Decimal
    floor_price: Decimal | None = None  # 个人到账保底（如转诊积分单价保底）
    cap_price: Decimal | None = None  # 个人到账封顶


@dataclass(frozen=True)
class Split:
    """一条分账明细（对应 income_split 一行）。"""

    payee_type: str  # individual / dept / org / platform
    amount: Decimal


def split_income(
    gross_amount: Decimal | str | int | float,
    rate: RateCard,
    *,
    perf_coef: Decimal | str | int | float = 1,
) -> list[Split]:
    """把一笔毛收入按规则拆分为四方分账。

    个人 = clamp(gross × individual_ratio × perf_coef, floor, cap)；
    科室/机构按固定比例；平台 = 毛收入 − 个人 − 科室 − 机构（吸收绩效调节差额，可正可负）。
    """
    gross = Decimal(str(gross_amount))
    coef = Decimal(str(perf_coef))

    individual = gross * rate.individual_ratio * coef
    if rate.floor_price is not None and individual < rate.floor_price:
        individual = rate.floor_price
    if rate.cap_price is not None and individual > rate.cap_price:
        individual = rate.cap_price
    individual = _money(individual)

    dept = _money(gross * rate.dept_ratio)
    org = _money(gross * rate.org_ratio)
    platform = _money(gross - individual - dept - org)

    return [
        Split("individual", individual),
        Split("dept", dept),
        Split("org", org),
        Split("platform", platform),
    ]
