# -*- coding: utf-8 -*-
"""
tax_tools 测试用例
"""

import pytest
from fin_tools.tools.tax_tools import (
    vat_calc,
    cit_calc,
    iit_calc,
    bonus_optimize,
    rd_deduction,
    tax_burden
)


class TestVatCalc:
    """增值税计算测试"""

    def test_general_taxpayer(self):
        """一般纳税人"""
        result = vat_calc(
            sales=[{"amount": 113000, "rate": 0.13}],
            purchases=[{"amount": 56500, "rate": 0.13}],
            taxpayer_type="general"
        )

        # 销项 = 113000/1.13 * 0.13 = 13000
        # 进项 = 56500/1.13 * 0.13 = 6500
        # 应纳 = 13000 - 6500 = 6500
        assert result["output_tax"] == pytest.approx(13000, rel=0.01)
        assert result["input_tax"] == pytest.approx(6500, rel=0.01)
        assert result["tax_payable"] == pytest.approx(6500, rel=0.01)

    def test_small_scale_taxpayer(self):
        """小规模纳税人"""
        result = vat_calc(
            sales=[{"amount": 103000, "rate": 0.03}],
            purchases=[{"amount": 50000, "rate": 0.13}],
            taxpayer_type="small_scale"
        )

        # 小规模3%，不能抵扣进项
        assert result["output_tax"] == pytest.approx(3000, rel=0.01)
        assert result["input_tax"] == 0
        assert result["tax_payable"] == pytest.approx(3000, rel=0.01)

    def test_multiple_rates(self):
        """多税率混合"""
        result = vat_calc(
            sales=[
                {"amount": 113000, "rate": 0.13},  # 货物
                {"amount": 106000, "rate": 0.06}   # 服务
            ],
            purchases=[{"amount": 56500, "rate": 0.13}]
        )

        # 销项 = 13000 + 6000 = 19000
        assert result["output_tax"] == pytest.approx(19000, rel=0.01)

    def test_tax_burden_rate(self):
        """税负率计算"""
        result = vat_calc(
            sales=[{"amount": 113000, "rate": 0.13}],
            purchases=[{"amount": 56500, "rate": 0.13}]
        )

        # 税负率 = 6500 / 100000 = 6.5%
        assert result["tax_burden_rate"] == pytest.approx(0.065, rel=0.01)


class TestCitCalc:
    """企业所得税计算测试"""

    def test_standard_rate(self):
        """标准25%税率"""
        result = cit_calc(
            accounting_profit=1000000,
            preference="standard"
        )

        assert result["tax_rate"] == 0.25
        assert result["tax_payable"] == 250000

    def test_high_tech_rate(self):
        """高新技术企业15%"""
        result = cit_calc(
            accounting_profit=1000000,
            preference="high_tech"
        )

        assert result["tax_rate"] == 0.15
        assert result["tax_payable"] == 150000

    def test_small_low_profit(self):
        """小型微利企业"""
        result = cit_calc(
            accounting_profit=2000000,
            preference="small_low_profit"
        )

        # 300万以下实际税负5%
        assert result["tax_rate"] == 0.05
        assert result["tax_payable"] == 100000

    def test_adjustments(self):
        """纳税调整"""
        result = cit_calc(
            accounting_profit=1000000,
            adjustments={
                "add": {"业务招待费超支": 20000},
                "subtract": {"研发加计扣除": 100000}
            }
        )

        # 应纳税所得额 = 1000000 + 20000 - 100000 = 920000
        assert result["taxable_income"] == 920000
        assert result["tax_payable"] == 230000

    def test_prior_year_loss(self):
        """亏损弥补"""
        result = cit_calc(
            accounting_profit=1000000,
            prior_year_loss=300000
        )

        # 应纳税所得额 = 1000000 - 300000 = 700000
        assert result["taxable_income"] == 700000
        assert result["tax_payable"] == 175000


class TestIitCalc:
    """个人所得税计算测试"""

    def test_low_income(self):
        """低收入（3%档）"""
        result = iit_calc(
            annual_salary=100000,
            special_deductions=12000
        )

        # 应纳税所得额 = 100000 - 60000 - 12000 = 28000
        # 28000 * 3% = 840
        assert result["taxable_income"] == 28000
        assert result["tax_rate"] == 0.03
        assert result["tax_payable"] == pytest.approx(840, rel=0.01)

    def test_medium_income(self):
        """中等收入（10%档）"""
        result = iit_calc(
            annual_salary=200000,
            social_insurance=20000,
            housing_fund=20000,
            special_deductions=24000
        )

        # 应纳税所得额 = 200000 - 60000 - 20000 - 20000 - 24000 = 76000
        # 76000 * 10% - 2520 = 5080
        assert result["taxable_income"] == 76000
        assert result["tax_rate"] == 0.10
        assert result["tax_payable"] == pytest.approx(5080, rel=0.01)

    def test_high_income(self):
        """高收入（30%档）"""
        result = iit_calc(annual_salary=800000)

        # 应纳税所得额 = 800000 - 60000 = 740000
        # 740000 * 35% - 85920 = 173080
        assert result["taxable_income"] == 740000
        assert result["tax_rate"] == 0.35

    def test_no_tax(self):
        """免税情况"""
        result = iit_calc(
            annual_salary=60000,  # 正好等于基本扣除
            special_deductions=0
        )

        assert result["taxable_income"] == 0
        assert result["tax_payable"] == 0


class TestBonusOptimize:
    """年终奖优化测试"""

    def test_basic_optimization(self):
        """基本优化"""
        result = bonus_optimize(
            annual_salary=200000,
            total_bonus=100000,
            special_deductions=24000
        )

        assert "scenarios" in result
        assert len(result["scenarios"]) >= 2
        assert "optimal" in result
        assert "tax_saved" in result

    def test_low_bonus(self):
        """低年终奖"""
        result = bonus_optimize(
            annual_salary=150000,
            total_bonus=36000
        )

        # 36000是临界点，应有优化建议
        assert result["optimal"]["total_tax"] >= 0

    def test_high_bonus(self):
        """高年终奖"""
        result = bonus_optimize(
            annual_salary=300000,
            total_bonus=500000
        )

        assert result["optimal"]["total_tax"] > 0
        assert result["tax_saved"] >= 0

    def test_recommendation(self):
        """推荐方案"""
        result = bonus_optimize(
            annual_salary=200000,
            total_bonus=100000
        )

        assert result["recommendation"] in [
            "年终奖单独计税",
            "年终奖并入综合所得",
            "最优拆分"
        ]


class TestRdDeduction:
    """研发加计扣除测试"""

    def test_manufacturing(self):
        """制造业100%加计"""
        result = rd_deduction(
            rd_expenses={
                "personnel": 500000,
                "materials": 200000,
                "depreciation": 100000
            },
            industry="manufacturing"
        )

        assert result["total_rd_expense"] == 800000
        assert result["deduction_rate"] == 1.0
        assert result["additional_deduction"] == 800000
        assert result["tax_saving_25"] == 200000

    def test_other_limit(self):
        """其他费用限额"""
        result = rd_deduction(
            rd_expenses={
                "personnel": 500000,
                "materials": 200000,
                "other": 200000  # 超过10%限额
            }
        )

        # 其他费用限额 = (500000+200000) * 10% / 90% ≈ 77778
        assert result["eligible_expense"] < result["total_rd_expense"]

    def test_tax_saving(self):
        """节税计算"""
        result = rd_deduction(
            rd_expenses={"personnel": 1000000}
        )

        # 加计100万，25%税率节税25万
        assert result["tax_saving_25"] == 250000
        # 15%税率节税15万
        assert result["tax_saving_15"] == 150000


class TestTaxBurden:
    """综合税负分析测试"""

    def test_basic_burden(self):
        """基本税负计算"""
        result = tax_burden(
            revenue=10000000,
            vat_payable=300000,
            cit_payable=200000
        )

        assert result["total_tax"] > 500000  # 含附加税
        assert result["burden_rate"] > 0.05
        assert "breakdown" in result

    def test_with_other_taxes(self):
        """含其他税费"""
        result = tax_burden(
            revenue=10000000,
            vat_payable=300000,
            cit_payable=200000,
            other_taxes={
                "stamp_tax": 5000,
                "property_tax": 10000
            }
        )

        assert result["breakdown"]["印花税"] == 5000
        assert result["breakdown"]["房产税"] == 10000

    def test_low_burden(self):
        """低税负"""
        result = tax_burden(
            revenue=10000000,
            vat_payable=100000,
            cit_payable=50000
        )

        assert "合规风险" in result["analysis"]

    def test_high_burden(self):
        """高税负"""
        result = tax_burden(
            revenue=10000000,
            vat_payable=500000,
            cit_payable=400000
        )

        assert "税务筹划" in result["analysis"] or "策略" in result["analysis"]

    def test_composition(self):
        """税种构成"""
        result = tax_burden(
            revenue=10000000,
            vat_payable=300000,
            cit_payable=200000
        )

        # 确保有构成比例
        assert "composition" in result
        total_composition = sum(result["composition"].values())
        assert total_composition == pytest.approx(1.0, rel=0.01)
