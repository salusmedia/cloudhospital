from decimal import Decimal

from py_common.clearing import RateCard, split_income

# 院外多点执业档：个人 70% / 科室 0 / 机构 20% / 平台 10%
EXTERNAL = RateCard(
    individual_ratio=Decimal("0.70"),
    dept_ratio=Decimal("0"),
    org_ratio=Decimal("0.20"),
    platform_ratio=Decimal("0.10"),
)
# 院内 MDT 档：个人 60% / 科室 20% / 机构 20%
MDT = RateCard(
    individual_ratio=Decimal("0.60"),
    dept_ratio=Decimal("0.20"),
    org_ratio=Decimal("0.20"),
    platform_ratio=Decimal("0"),
)


def _by_type(splits):
    return {s.payee_type: s.amount for s in splits}


def test_splits_sum_to_gross():
    splits = split_income(Decimal("200"), MDT)
    total = sum(s.amount for s in splits)
    assert total == Decimal("200.00")


def test_individual_share_with_perf_coef():
    # 报告解读 ¥15，个人 70%，评价系数 1.02 → 15*0.7*1.02 = 10.71
    splits = _by_type(split_income(Decimal("15"), EXTERNAL, perf_coef="1.02"))
    assert splits["individual"] == Decimal("10.71")


def test_mdt_individual_120():
    # MDT ¥200 个人 60% → 120
    splits = _by_type(split_income(Decimal("200"), MDT))
    assert splits["individual"] == Decimal("120.00")


def test_platform_absorbs_perf_variance():
    # 绩效系数 >1 时个人多拿，平台吸收差额（各方加总仍 = 毛收入）
    splits = split_income(Decimal("100"), EXTERNAL, perf_coef="1.5")
    by = _by_type(splits)
    assert by["individual"] == Decimal("105.00")  # 100*0.7*1.5
    assert sum(s.amount for s in splits) == Decimal("100.00")
    assert by["platform"] < 0  # 平台让利


def test_floor_and_cap_clamp_individual():
    rated = RateCard(
        individual_ratio=Decimal("1"),
        dept_ratio=Decimal("0"),
        org_ratio=Decimal("0"),
        platform_ratio=Decimal("0"),
        floor_price=Decimal("1.5"),
        cap_price=Decimal("3.5"),
    )
    # 低于保底 → 抬到 1.5（转诊积分单价保底）
    assert _by_type(split_income(Decimal("1"), rated))["individual"] == Decimal("1.50")
    # 高于封顶 → 压到 3.5
    assert _by_type(split_income(Decimal("9"), rated))["individual"] == Decimal("3.50")
