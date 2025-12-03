# -*- coding: utf-8 -*-
"""
risk_tools 测试用例
"""

import pytest
from datetime import date, timedelta
from fin_tools.tools.risk_tools import (
    credit_score,
    ar_aging,
    bad_debt_provision,
    fx_exposure
)


class TestCreditScore:
    """客户信用评分测试"""

    def test_excellent_customer(self):
        """优质客户"""
        result = credit_score({
            "customer_name": "优质公司",
            "payment_history": {
                "on_time_rate": 0.98,
                "avg_days_late": 1,
                "max_days_late": 5
            },
            "credit_utilization": {
                "credit_limit": 100000,
                "current_ar": 50000
            },
            "relationship": {"years": 8},
            "order_frequency": {"orders_per_year": 24},
            "financial_health": {
                "current_ratio": 2.5,
                "debt_ratio": 0.3,
                "profitable": True
            }
        })

        assert result["score"] >= 85
        assert result["grade"] in ["AAA", "AA"]
        assert len(result["risk_factors"]) == 0

    def test_risky_customer(self):
        """风险客户"""
        result = credit_score({
            "customer_name": "风险公司",
            "payment_history": {
                "on_time_rate": 0.5,
                "avg_days_late": 30,
                "max_days_late": 90
            },
            "credit_utilization": {
                "credit_limit": 100000,
                "current_ar": 95000
            },
            "relationship": {"years": 0.5},
            "financial_health": {
                "current_ratio": 0.8,
                "debt_ratio": 0.8,
                "profitable": False
            }
        })

        assert result["score"] < 60
        assert result["grade"] in ["BB", "B", "C"]
        assert len(result["risk_factors"]) > 0

    def test_new_customer(self):
        """新客户"""
        result = credit_score({
            "customer_name": "新客户",
            "payment_history": {"on_time_rate": 1.0},
            "relationship": {"years": 0}
        })

        # 新客户应有相应提示
        assert any("新客户" in f for f in result["risk_factors"])

    def test_custom_weights(self):
        """自定义权重"""
        data = {
            "customer_name": "测试",
            "payment_history": {"on_time_rate": 1.0},
            "relationship": {"years": 5}
        }

        # 默认权重
        result1 = credit_score(data)

        # 只看付款历史
        result2 = credit_score(data, weights={
            "payment_history": 1.0,
            "credit_utilization": 0,
            "relationship_length": 0,
            "order_frequency": 0,
            "financial_health": 0
        })

        assert result2["score"] == 100  # 付款历史满分

    def test_minimal_data(self):
        """最少数据"""
        result = credit_score({"customer_name": "简单客户"})

        assert "score" in result
        assert "grade" in result
        assert 0 <= result["score"] <= 100

    def test_high_overdue(self):
        """高逾期风险"""
        result = credit_score({
            "customer_name": "逾期客户",
            "payment_history": {
                "on_time_rate": 0.6,
                "avg_days_late": 45,
                "max_days_late": 120
            }
        })

        assert any("逾期" in f for f in result["risk_factors"])


class TestArAging:
    """应收账款账龄分析测试"""

    def test_basic_aging(self):
        """基本账龄分析"""
        today = date.today()
        result = ar_aging(
            receivables=[
                {
                    "invoice_id": "INV001",
                    "customer_name": "客户A",
                    "invoice_date": (today - timedelta(days=15)).isoformat(),
                    "due_date": (today - timedelta(days=5)).isoformat(),
                    "amount": 10000
                },
                {
                    "invoice_id": "INV002",
                    "customer_name": "客户B",
                    "invoice_date": (today - timedelta(days=45)).isoformat(),
                    "due_date": (today - timedelta(days=15)).isoformat(),
                    "amount": 20000
                }
            ],
            as_of_date=today.isoformat()
        )

        assert result["total_ar"] == 30000
        assert result["invoice_count"] == 2
        assert "aging_summary" in result
        assert "by_customer" in result

    def test_overdue_calculation(self):
        """逾期计算"""
        today = date.today()
        result = ar_aging(
            receivables=[
                {
                    "invoice_id": "INV001",
                    "customer_name": "客户A",
                    "invoice_date": (today - timedelta(days=60)).isoformat(),
                    "due_date": (today - timedelta(days=30)).isoformat(),
                    "amount": 10000
                }
            ],
            as_of_date=today.isoformat()
        )

        assert result["overdue_summary"]["total_overdue"] == 10000
        assert result["overdue_summary"]["overdue_rate"] == 1.0
        assert result["overdue_summary"]["avg_days_overdue"] == 30

    def test_empty_receivables(self):
        """空应收"""
        result = ar_aging(receivables=[])

        assert result["total_ar"] == 0
        assert result["invoice_count"] == 0

    def test_partial_payment(self):
        """部分收款"""
        today = date.today()
        result = ar_aging(
            receivables=[
                {
                    "invoice_id": "INV001",
                    "customer_name": "客户A",
                    "invoice_date": (today - timedelta(days=10)).isoformat(),
                    "amount": 10000,
                    "paid_amount": 3000
                }
            ]
        )

        # 只计算未收金额
        assert result["total_ar"] == 7000

    def test_fully_paid(self):
        """完全收款"""
        today = date.today()
        result = ar_aging(
            receivables=[
                {
                    "invoice_id": "INV001",
                    "customer_name": "客户A",
                    "invoice_date": (today - timedelta(days=10)).isoformat(),
                    "amount": 10000,
                    "paid_amount": 10000  # 已结清
                }
            ]
        )

        assert result["total_ar"] == 0
        assert result["invoice_count"] == 0

    def test_multiple_customers(self):
        """多客户汇总"""
        today = date.today()
        result = ar_aging(
            receivables=[
                {"customer_name": "客户A", "invoice_date": today.isoformat(), "amount": 10000},
                {"customer_name": "客户A", "invoice_date": today.isoformat(), "amount": 5000},
                {"customer_name": "客户B", "invoice_date": today.isoformat(), "amount": 20000}
            ]
        )

        assert len(result["by_customer"]) == 2
        # 客户B金额最大应排第一
        assert result["by_customer"][0]["customer_name"] == "客户B"
        assert result["by_customer"][0]["total"] == 20000

    def test_aging_buckets(self):
        """账龄区间分布"""
        today = date.today()
        result = ar_aging(
            receivables=[
                {"invoice_date": (today - timedelta(days=10)).isoformat(), "amount": 1000},
                {"invoice_date": (today - timedelta(days=40)).isoformat(), "amount": 2000},
                {"invoice_date": (today - timedelta(days=100)).isoformat(), "amount": 3000},
            ]
        )

        assert result["aging_summary"]["0-30天"]["amount"] == 1000
        assert result["aging_summary"]["31-60天"]["amount"] == 2000
        assert result["aging_summary"]["91-180天"]["amount"] == 3000


class TestBadDebtProvision:
    """坏账准备计算测试"""

    def test_basic_provision(self):
        """基本计提"""
        result = bad_debt_provision({
            "aging_summary": {
                "0-30天": {"amount": 100000},
                "31-60天": {"amount": 50000},
                "61-90天": {"amount": 20000}
            }
        })

        assert result["total_ar"] == 170000
        # 100000*1% + 50000*3% + 20000*5% = 1000+1500+1000 = 3500
        assert result["general_provision"] == pytest.approx(3500, rel=0.01)

    def test_simplified_format(self):
        """简化格式输入"""
        result = bad_debt_provision({
            "0-30天": 100000,
            "31-60天": 50000
        })

        assert result["total_ar"] == 150000
        assert result["general_provision"] > 0

    def test_custom_rates(self):
        """自定义计提比例"""
        result = bad_debt_provision(
            aging_data={"0-30天": {"amount": 100000}},
            provision_rates={"0-30天": 0.05}  # 5%
        )

        assert result["general_provision"] == 5000

    def test_specific_provision(self):
        """专项计提"""
        result = bad_debt_provision(
            aging_data={"0-30天": {"amount": 100000}},
            specific_provisions=[
                {"customer_name": "问题客户", "amount": 50000, "rate": 1.0, "reason": "破产"}
            ]
        )

        assert result["specific_provision"] == 50000
        assert result["total_provision"] == result["general_provision"] + 50000

    def test_empty_aging(self):
        """空账龄数据"""
        result = bad_debt_provision({"aging_summary": {}})

        assert result["total_ar"] == 0
        assert result["total_provision"] == 0

    def test_high_aging(self):
        """高账龄"""
        result = bad_debt_provision({
            "1年以上": 100000
        })

        # 1年以上计提50%
        assert result["general_provision"] == 50000

    def test_provision_rate_calculation(self):
        """综合计提比例"""
        result = bad_debt_provision({
            "0-30天": 90000,   # 1% = 900
            "1年以上": 10000   # 50% = 5000
        })

        # 总额100000，坏账5900，比例5.9%
        assert result["provision_rate"] == pytest.approx(0.059, rel=0.01)


class TestFxExposure:
    """汇率风险敞口测试"""

    def test_basic_exposure(self):
        """基本敞口计算"""
        result = fx_exposure(
            assets=[
                {"currency": "USD", "amount": 100000}
            ],
            liabilities=[
                {"currency": "USD", "amount": 30000}
            ],
            exchange_rates={"USD": 7.2}
        )

        assert "USD" in result["by_currency"]
        usd = result["by_currency"]["USD"]
        assert usd["assets"] == 100000
        assert usd["liabilities"] == 30000
        assert usd["net_exposure"] == 70000
        assert usd["exposure_type"] == "long"
        assert usd["base_value"] == 70000 * 7.2

    def test_short_position(self):
        """空头头寸"""
        result = fx_exposure(
            assets=[{"currency": "USD", "amount": 30000}],
            liabilities=[{"currency": "USD", "amount": 100000}],
            exchange_rates={"USD": 7.2}
        )

        usd = result["by_currency"]["USD"]
        assert usd["net_exposure"] == -70000
        assert usd["exposure_type"] == "short"

    def test_multiple_currencies(self):
        """多币种"""
        result = fx_exposure(
            assets=[
                {"currency": "USD", "amount": 100000},
                {"currency": "EUR", "amount": 50000}
            ],
            liabilities=[
                {"currency": "USD", "amount": 30000}
            ],
            exchange_rates={"USD": 7.2, "EUR": 7.8}
        )

        assert "USD" in result["by_currency"]
        assert "EUR" in result["by_currency"]

    def test_no_exposure(self):
        """无敞口"""
        result = fx_exposure(
            assets=[],
            liabilities=[]
        )

        assert result["total_exposure"]["gross"] == 0

    def test_balanced_position(self):
        """平衡头寸"""
        result = fx_exposure(
            assets=[{"currency": "USD", "amount": 50000}],
            liabilities=[{"currency": "USD", "amount": 50000}],
            exchange_rates={"USD": 7.2}
        )

        usd = result["by_currency"]["USD"]
        assert usd["net_exposure"] == 0
        assert usd["exposure_type"] == "balanced"

    def test_sensitivity_analysis(self):
        """敏感性分析"""
        result = fx_exposure(
            assets=[{"currency": "USD", "amount": 100000}],
            liabilities=[],
            exchange_rates={"USD": 7.2}
        )

        usd = result["by_currency"]["USD"]
        base_value = 100000 * 7.2

        assert usd["sensitivity"]["1%"] == pytest.approx(base_value * 0.01, rel=0.01)
        assert usd["sensitivity"]["5%"] == pytest.approx(base_value * 0.05, rel=0.01)
        assert usd["sensitivity"]["10%"] == pytest.approx(base_value * 0.10, rel=0.01)

    def test_risk_assessment(self):
        """风险评估"""
        result = fx_exposure(
            assets=[{"currency": "USD", "amount": 1000000}],
            liabilities=[],
            exchange_rates={"USD": 7.2}
        )

        assert "risk_level" in result["risk_assessment"]
        assert "recommendations" in result["risk_assessment"]

    def test_custom_base_currency(self):
        """自定义本位币"""
        result = fx_exposure(
            assets=[{"currency": "CNY", "amount": 100000}],
            liabilities=[],
            base_currency="USD"
        )

        # CNY对USD应有敞口
        assert result["base_currency"] == "USD"


# ============================================================
# 边界情况测试
# ============================================================

class TestCreditScoreEdgeCases:
    """信用评分边界测试"""

    def test_zero_credit_limit(self):
        """零信用额度"""
        result = credit_score({
            "credit_utilization": {
                "credit_limit": 0,
                "current_ar": 10000
            }
        })

        # 应正常处理
        assert "score" in result

    def test_100_percent_on_time(self):
        """100%准时付款"""
        result = credit_score({
            "payment_history": {"on_time_rate": 1.0}
        })

        assert result["dimension_scores"]["payment_history"] == 100

    def test_0_percent_on_time(self):
        """0%准时付款"""
        result = credit_score({
            "payment_history": {"on_time_rate": 0}
        })

        assert result["dimension_scores"]["payment_history"] == 0

    def test_low_credit_utilization(self):
        """低信用使用率（0-30%）"""
        result = credit_score({
            "credit_utilization": {
                "credit_limit": 100000,
                "current_ar": 20000  # 20%
            }
        })

        # 低使用率应得高分
        assert result["dimension_scores"]["credit_utilization"] >= 90

    def test_medium_relationship(self):
        """中等合作时长（3-5年）"""
        result = credit_score({
            "relationship": {"years": 4}
        })

        # 3-5年应在80-100之间
        score = result["dimension_scores"]["relationship_length"]
        assert 80 <= score <= 100

    def test_short_relationship(self):
        """较短合作时长（1-3年）"""
        result = credit_score({
            "relationship": {"years": 2}
        })

        # 1-3年应在60-80之间
        score = result["dimension_scores"]["relationship_length"]
        assert 60 <= score <= 80

    def test_medium_order_frequency(self):
        """中等订单频率（6-12次/年）"""
        result = credit_score({
            "order_frequency": {"orders_per_year": 8}
        })

        # 6-12次应在70-100之间
        score = result["dimension_scores"]["order_frequency"]
        assert 70 <= score <= 100

    def test_low_order_frequency(self):
        """低订单频率（1-6次/年）"""
        result = credit_score({
            "order_frequency": {"orders_per_year": 3}
        })

        # 1-6次应在40-70之间
        score = result["dimension_scores"]["order_frequency"]
        assert 40 <= score <= 70

    def test_medium_financial_ratios(self):
        """中等财务指标"""
        result = credit_score({
            "financial_health": {
                "current_ratio": 1.7,   # 1.5-2之间
                "debt_ratio": 0.5,      # 0.4-0.6之间
                "profitable": True
            }
        })

        # 中等财务状况应得中等偏上分数
        score = result["dimension_scores"]["financial_health"]
        assert 70 <= score <= 90

    def test_borderline_financial_ratios(self):
        """边界财务指标"""
        result = credit_score({
            "financial_health": {
                "current_ratio": 1.2,   # 1-1.5之间
                "debt_ratio": 0.65,     # 0.6-0.7之间
                "profitable": True
            }
        })

        score = result["dimension_scores"]["financial_health"]
        assert 60 <= score <= 80

    def test_grade_a_customer(self):
        """A级客户（正常）"""
        result = credit_score({
            "customer_name": "普通客户",
            "payment_history": {"on_time_rate": 0.85},
            "relationship": {"years": 2},
            "order_frequency": {"orders_per_year": 6}
        })

        # A级客户应有维持当前政策建议
        if result["grade"] == "A" and not any("风险" in r for r in result["risk_factors"]):
            assert any("维持" in r for r in result["recommendations"])


class TestArAgingEdgeCases:
    """账龄分析边界测试"""

    def test_missing_dates(self):
        """缺少日期"""
        result = ar_aging([
            {"customer_name": "客户A", "amount": 10000}  # 无日期
        ])

        assert result["total_ar"] == 10000

    def test_future_invoice_date(self):
        """未来发票日期"""
        future = (date.today() + timedelta(days=30)).isoformat()
        result = ar_aging([
            {"invoice_date": future, "amount": 10000}
        ])

        # 账龄为负数，应归入0-30天或特殊处理
        assert result["total_ar"] == 10000


class TestBadDebtProvisionEdgeCases:
    """坏账准备边界测试"""

    def test_zero_amounts(self):
        """全零金额"""
        result = bad_debt_provision({
            "0-30天": 0,
            "31-60天": 0
        })

        assert result["total_ar"] == 0
        assert result["total_provision"] == 0

    def test_unknown_bucket(self):
        """未知账龄区间"""
        result = bad_debt_provision({
            "自定义区间": 100000
        })

        # 应使用默认比例
        assert result["general_provision"] > 0


class TestFxExposureEdgeCases:
    """汇率风险边界测试"""

    def test_base_currency_in_list(self):
        """资产中包含本位币"""
        result = fx_exposure(
            assets=[
                {"currency": "CNY", "amount": 100000},
                {"currency": "USD", "amount": 50000}
            ],
            liabilities=[],
            base_currency="CNY"
        )

        # 本位币不应出现在敞口中
        assert "CNY" not in result["by_currency"]
        assert "USD" in result["by_currency"]

    def test_missing_exchange_rate(self):
        """缺少汇率"""
        result = fx_exposure(
            assets=[{"currency": "XYZ", "amount": 100000}],  # 不存在的货币
            liabilities=[]
        )

        # 应使用默认汇率1.0
        assert "XYZ" in result["by_currency"]

    def test_zero_amount(self):
        """零金额"""
        result = fx_exposure(
            assets=[{"currency": "USD", "amount": 0}],
            liabilities=[]
        )

        if "USD" in result["by_currency"]:
            assert result["by_currency"]["USD"]["net_exposure"] == 0
