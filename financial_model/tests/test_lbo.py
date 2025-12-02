# -*- coding: utf-8 -*-
"""
LBO模型测试

测试场景:
1. 基础功能测试 - 标准交易、零杠杆、高杠杆
2. 债务还款测试 - 现金扫荡、PIK利息
3. 回报计算测试 - IRR、MOIC
4. 边界情况测试
"""

import pytest
from ..models.lbo import LBOModel, DebtTranche


class TestDebtTranche:
    """债务层级测试"""

    def test_basic_interest(self):
        """测试基础利息计算"""
        tranche = DebtTranche(
            name="senior",
            initial_amount=100_000_000,
            interest_rate=0.06,
            amortization_rate=0.05
        )

        period = tranche.calc_period(cash_sweep=0)

        assert period["opening_balance"] == 100_000_000
        assert period["cash_interest"] == 6_000_000  # 6%利息
        assert period["mandatory_amort"] == 5_000_000  # 5%强制还本
        assert period["closing_balance"] == 95_000_000

    def test_pik_interest(self):
        """测试PIK利息（加到本金）"""
        tranche = DebtTranche(
            name="mezzanine",
            initial_amount=50_000_000,
            interest_rate=0.08,
            pik_rate=0.02
        )

        period = tranche.calc_period()

        assert period["cash_interest"] == 4_000_000  # 8%现金利息
        assert period["pik_interest"] == 1_000_000  # 2%PIK
        # 期末余额 = 期初 + PIK（无强制还本）
        assert period["closing_balance"] == 51_000_000

    def test_cash_sweep(self):
        """测试现金扫荡还款"""
        tranche = DebtTranche(
            name="senior",
            initial_amount=100_000_000,
            interest_rate=0.06,
            amortization_rate=0.05
        )

        # 额外还款2000万
        period = tranche.calc_period(cash_sweep=20_000_000)

        assert period["mandatory_amort"] == 5_000_000
        assert period["cash_sweep"] == 20_000_000
        assert period["total_principal_payment"] == 25_000_000
        assert period["closing_balance"] == 75_000_000


class TestLBOModel:
    """LBO模型测试"""

    @pytest.fixture
    def standard_inputs(self):
        """标准LBO输入参数"""
        return {
            "entry_ebitda": 100_000_000,  # 1亿EBITDA
            "entry_multiple": 8.0,
            "exit_multiple": 8.0,
            "holding_period": 5,
            "revenue_growth": [0.05, 0.06, 0.07, 0.06, 0.05],
            "ebitda_margin": [0.20, 0.21, 0.22, 0.22, 0.22],
            "capex_percent": 0.03,
            "nwc_percent": 0.10,
            "tax_rate": 0.25,
            "transaction_fee_rate": 0.02,
            "financing_fee_rate": 0.01,
            "debt_structure": {
                "senior": {
                    "amount_percent": 0.40,
                    "interest_rate": 0.06,
                    "amortization_rate": 0.05,
                    "priority": 1
                },
                "subordinated": {
                    "amount_percent": 0.20,
                    "interest_rate": 0.10,
                    "pik_rate": 0.02,
                    "priority": 2
                }
            },
            "sweep_percent": 0.75
        }

    def test_purchase_price(self):
        """测试收购价格计算"""
        lbo = LBOModel()
        result = lbo.calc_purchase_price(100_000_000, 8.0)

        assert result.value == 800_000_000
        assert "EBITDA" in result.formula

    def test_sources_uses(self):
        """测试资金来源与用途"""
        lbo = LBOModel()
        result = lbo.calc_sources_uses(
            purchase_price=800_000_000,
            transaction_fee_rate=0.02,
            financing_fee_rate=0.01,
            debt_amounts={"senior": 320_000_000, "sub": 160_000_000}
        )

        sources = result.inputs["sources"]
        uses = result.inputs["uses"]

        # 验证用途
        assert uses["purchase_price"] == 800_000_000
        assert uses["transaction_fees"] == 16_000_000  # 2%
        assert uses["financing_fees"] == 4_800_000  # 1% of debt

        # 验证来源平衡
        assert sources["total_sources"] == uses["total_uses"]

        # 股权 = 总用途 - 债务
        expected_equity = 820_800_000 - 480_000_000
        assert result.value == expected_equity

    def test_standard_lbo(self, standard_inputs):
        """测试标准LBO交易"""
        lbo = LBOModel()
        result = lbo.build(standard_inputs)

        # 验证结构完整
        assert "transaction" in result
        assert "operating_model" in result
        assert "debt_schedule" in result
        assert "exit_analysis" in result
        assert "returns" in result

        # 验证收购价格
        assert result["transaction"]["purchase_price"]["value"] == 800_000_000

        # 验证持有期
        assert len(result["operating_model"]) == 5

        # 验证IRR在合理范围（15%-25%）
        irr = result["returns"]["irr"]["value"]
        assert 0.10 < irr < 0.30, f"IRR {irr:.1%} out of expected range"

        # 验证MOIC在合理范围（1.5x-3x）
        moic = result["returns"]["moic"]["value"]
        assert 1.5 < moic < 3.5, f"MOIC {moic:.2f}x out of expected range"

    def test_zero_leverage(self, standard_inputs):
        """测试零杠杆（100%股权）"""
        inputs = standard_inputs.copy()
        inputs["debt_structure"] = {}  # 无债务

        lbo = LBOModel()
        result = lbo.build(inputs)

        # 股权投入 = 收购价 + 费用
        equity = result["transaction"]["equity_invested"]
        purchase = result["transaction"]["purchase_price"]["value"]
        assert equity > purchase  # 还要加费用

        # 零杠杆下IRR应该较低
        irr = result["returns"]["irr"]["value"]
        assert irr < 0.15, f"Zero leverage IRR {irr:.1%} too high"

    def test_high_leverage(self, standard_inputs):
        """测试高杠杆（70%债务）"""
        inputs = standard_inputs.copy()
        inputs["debt_structure"] = {
            "senior": {
                "amount_percent": 0.50,
                "interest_rate": 0.06,
                "amortization_rate": 0.05,
                "priority": 1
            },
            "subordinated": {
                "amount_percent": 0.20,
                "interest_rate": 0.10,
                "priority": 2
            }
        }

        lbo = LBOModel()
        result = lbo.build(inputs)

        # 高杠杆应该提升IRR
        irr = result["returns"]["irr"]["value"]
        assert irr > 0.15, f"High leverage IRR {irr:.1%} too low"

    def test_multiple_expansion(self, standard_inputs):
        """测试估值提升（入场8x，退出10x）"""
        inputs = standard_inputs.copy()
        inputs["exit_multiple"] = 10.0

        lbo = LBOModel()
        result = lbo.build(inputs)

        # 估值提升应显著提高回报
        irr = result["returns"]["irr"]["value"]
        moic = result["returns"]["moic"]["value"]

        assert irr > 0.25, f"Multiple expansion IRR {irr:.1%} lower than expected"
        assert moic > 2.5, f"MOIC {moic:.2f}x lower than expected"

    def test_multiple_compression(self, standard_inputs):
        """测试估值下降（入场8x，退出6x）"""
        inputs = standard_inputs.copy()
        inputs["exit_multiple"] = 6.0

        lbo = LBOModel()
        result = lbo.build(inputs)

        # 估值下降会降低回报，甚至可能亏损
        irr = result["returns"]["irr"]["value"]
        moic = result["returns"]["moic"]["value"]

        assert irr < 0.15, f"Multiple compression IRR {irr:.1%} higher than expected"

    def test_debt_paydown(self, standard_inputs):
        """测试债务逐年下降"""
        lbo = LBOModel()
        result = lbo.build(standard_inputs)

        debt_schedule = result["debt_schedule"]["annual_summary"]

        # 债务应该逐年下降
        debts = [s["ending_debt"] for s in debt_schedule]
        for i in range(1, len(debts)):
            assert debts[i] <= debts[i-1], f"Debt increased in year {i+1}"

    def test_irr_calculation(self):
        """测试IRR计算准确性"""
        lbo = LBOModel()

        # 简单案例：投入100，5年后拿回200
        # MOIC = 2x，IRR ≈ 14.87%
        cash_flows = [-100, 0, 0, 0, 0, 200]
        result = lbo.calc_irr(cash_flows)

        expected_irr = 0.1487  # (200/100)^(1/5) - 1
        assert abs(result.value - expected_irr) < 0.01

    def test_moic_calculation(self):
        """测试MOIC计算"""
        lbo = LBOModel()

        result = lbo.calc_moic(
            equity_invested=100_000_000,
            equity_proceeds=220_000_000,
            interim_distributions=10_000_000
        )

        # MOIC = (220 + 10) / 100 = 2.3x
        assert result.value == 2.3

    def test_credit_stats(self, standard_inputs):
        """测试信用指标"""
        lbo = LBOModel()
        result = lbo.build(standard_inputs)

        credit_stats = result["credit_stats"]

        # 应有5年的信用指标
        assert len(credit_stats) == 5

        # Debt/EBITDA应逐年下降
        ratios = [s["debt_to_ebitda"] for s in credit_stats]
        for i in range(1, len(ratios)):
            assert ratios[i] <= ratios[i-1], f"Leverage increased in year {i+1}"


class TestEdgeCases:
    """边界情况测试"""

    def test_single_year_holding(self):
        """测试1年持有期"""
        lbo = LBOModel()
        inputs = {
            "entry_ebitda": 100_000_000,
            "entry_multiple": 8.0,
            "exit_multiple": 8.0,
            "holding_period": 1,
            "revenue_growth": [0.05],
            "ebitda_margin": [0.20],
            "capex_percent": 0.03,
            "nwc_percent": 0.10,
            "tax_rate": 0.25,
            "transaction_fee_rate": 0.02,
            "financing_fee_rate": 0.01,
            "debt_structure": {
                "senior": {
                    "amount_percent": 0.50,
                    "interest_rate": 0.06,
                    "priority": 1
                }
            },
            "sweep_percent": 0.75
        }

        result = lbo.build(inputs)
        assert len(result["operating_model"]) == 1

    def test_no_growth(self):
        """测试零增长场景"""
        lbo = LBOModel()
        inputs = {
            "entry_ebitda": 100_000_000,
            "entry_multiple": 8.0,
            "exit_multiple": 8.0,
            "holding_period": 5,
            "revenue_growth": [0, 0, 0, 0, 0],
            "ebitda_margin": [0.20] * 5,
            "capex_percent": 0.03,
            "nwc_percent": 0.10,
            "tax_rate": 0.25,
            "debt_structure": {
                "senior": {
                    "amount_percent": 0.50,
                    "interest_rate": 0.06,
                    "amortization_rate": 0.05,
                    "priority": 1
                }
            },
            "sweep_percent": 0.75
        }

        result = lbo.build(inputs)

        # 零增长仍应能计算
        assert result["returns"]["irr"]["value"] > 0
        assert result["returns"]["moic"]["value"] > 1

    def test_high_amortization(self):
        """测试快速还债"""
        lbo = LBOModel()
        inputs = {
            "entry_ebitda": 100_000_000,
            "entry_multiple": 6.0,  # 较低倍数
            "exit_multiple": 6.0,
            "holding_period": 5,
            "revenue_growth": [0.05] * 5,
            "ebitda_margin": [0.25] * 5,  # 较高margin
            "capex_percent": 0.02,
            "nwc_percent": 0.05,
            "tax_rate": 0.25,
            "debt_structure": {
                "senior": {
                    "amount_percent": 0.40,
                    "interest_rate": 0.05,
                    "amortization_rate": 0.15,  # 高摊销
                    "priority": 1
                }
            },
            "sweep_percent": 1.0  # 全部多余现金还债
        }

        result = lbo.build(inputs)

        # 债务应该大幅下降
        ending_debt = result["debt_schedule"]["final_debt"]
        initial_debt = 600_000_000 * 0.40  # 240M
        assert ending_debt < initial_debt * 0.5, "Debt should be less than 50% of initial"
