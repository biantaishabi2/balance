# -*- coding: utf-8 -*-
"""
LBO 原子工具测试

测试每个原子工具的独立功能和组合使用
"""

import pytest
from fin_tools.tools import (
    calc_purchase_price,
    calc_sources_uses,
    project_operations,
    calc_debt_schedule,
    calc_exit_value,
    calc_equity_proceeds,
    calc_irr,
    calc_moic,
    lbo_quick_build,
)


class TestCalcPurchasePrice:
    """收购价格计算测试"""

    def test_basic_calculation(self):
        """基础计算"""
        result = calc_purchase_price(100_000_000, 8.0)

        assert result["value"] == 800_000_000
        assert result["formula"] == "EBITDA × Entry Multiple"
        assert result["inputs"]["ebitda"] == 100_000_000
        assert result["inputs"]["multiple"] == 8.0
        assert result["source"] == "tool"

    def test_custom_source(self):
        """自定义来源标记"""
        result = calc_purchase_price(100_000_000, 8.0, source="llm_override")
        assert result["source"] == "llm_override"

    def test_different_multiples(self):
        """不同倍数测试"""
        ebitda = 50_000_000

        # 低倍数
        result_low = calc_purchase_price(ebitda, 5.0)
        assert result_low["value"] == 250_000_000

        # 高倍数
        result_high = calc_purchase_price(ebitda, 12.0)
        assert result_high["value"] == 600_000_000


class TestCalcSourcesUses:
    """资金来源与用途测试"""

    def test_basic_calculation(self):
        """基础计算"""
        result = calc_sources_uses(
            purchase_price=800_000_000,
            debt_amounts={"senior": 320_000_000, "sub": 160_000_000}
        )

        # 验证用途
        uses = result["uses"]
        assert uses["purchase_price"] == 800_000_000
        assert uses["transaction_fees"] == 16_000_000  # 2%
        assert uses["financing_fees"] == 4_800_000  # 1% of 480M debt

        # 验证来源
        sources = result["sources"]
        assert sources["total_debt"] == 480_000_000
        assert sources["equity"] == result["equity_required"]

        # 验证平衡
        assert sources["total_sources"] == uses["total_uses"]

    def test_with_existing_cash(self):
        """有现有现金"""
        result = calc_sources_uses(
            purchase_price=800_000_000,
            debt_amounts={"senior": 320_000_000},
            existing_cash=50_000_000
        )

        # 现金减少股权需求
        equity_without_cash = calc_sources_uses(
            purchase_price=800_000_000,
            debt_amounts={"senior": 320_000_000}
        )["equity_required"]

        assert result["equity_required"] == equity_without_cash - 50_000_000

    def test_custom_fee_rates(self):
        """自定义费用率"""
        result = calc_sources_uses(
            purchase_price=1_000_000_000,
            debt_amounts={"senior": 500_000_000},
            transaction_fee_rate=0.03,  # 3%
            financing_fee_rate=0.02     # 2%
        )

        assert result["uses"]["transaction_fees"] == 30_000_000
        assert result["uses"]["financing_fees"] == 10_000_000


class TestProjectOperations:
    """运营预测测试"""

    def test_basic_projection(self):
        """基础预测"""
        result = project_operations(
            base_revenue=500_000_000,
            years=5,
            revenue_growth=0.05,
            ebitda_margin=0.20
        )

        assert len(result["projections"]) == 5
        assert result["summary"]["entry_revenue"] == 500_000_000

        # 验证第一年
        year1 = result["projections"][0]
        assert year1["year"] == 1
        assert year1["revenue"] == 525_000_000  # 500M * 1.05
        assert year1["ebitda"] == 105_000_000   # 525M * 0.20

    def test_list_inputs(self):
        """列表输入"""
        result = project_operations(
            base_revenue=500_000_000,
            years=3,
            revenue_growth=[0.05, 0.06, 0.07],
            ebitda_margin=[0.20, 0.21, 0.22]
        )

        projections = result["projections"]

        # 第一年: 5% 增长, 20% margin
        assert projections[0]["revenue"] == pytest.approx(525_000_000)
        assert projections[0]["ebitda"] == pytest.approx(105_000_000)

        # 第二年: 6% 增长, 21% margin
        assert projections[1]["revenue"] == pytest.approx(556_500_000)
        assert projections[1]["ebitda"] == pytest.approx(116_865_000)

    def test_ufcf_calculation(self):
        """UFCF计算"""
        result = project_operations(
            base_revenue=1_000_000_000,
            years=1,
            revenue_growth=0.0,
            ebitda_margin=0.25,
            capex_percent=0.05,
            nwc_percent=0.10
        )

        year1 = result["projections"][0]
        # UFCF = EBITDA - Capex - ΔNWC
        # = 250M - 50M - 0 (第一年NWC变化为0因为base已有NWC)
        # 实际上 delta_nwc = 1000M*0.1 - 1000M*0.1 = 0
        assert year1["ufcf"] == year1["ebitda"] - year1["capex"] - year1["delta_nwc"]


class TestCalcDebtSchedule:
    """债务计划表测试"""

    def test_basic_schedule(self):
        """基础债务计划"""
        tranches = [
            {"name": "senior", "amount": 100_000_000, "interest_rate": 0.06}
        ]
        operations = [
            {"year": 1, "ufcf": 30_000_000, "ebit": 25_000_000, "tax_rate": 0.25},
            {"year": 2, "ufcf": 32_000_000, "ebit": 27_000_000, "tax_rate": 0.25},
        ]

        result = calc_debt_schedule(tranches, operations)

        assert "senior" in result["schedule"]
        assert len(result["schedule"]["senior"]) == 2
        assert result["final_debt"] > 0

    def test_with_amortization(self):
        """有强制还本"""
        tranches = [
            {"name": "senior", "amount": 100_000_000, "interest_rate": 0.06, "amortization_rate": 0.10}
        ]
        operations = [
            {"year": 1, "ufcf": 50_000_000, "ebit": 40_000_000, "tax_rate": 0.25}
        ]

        result = calc_debt_schedule(tranches, operations)

        senior_y1 = result["schedule"]["senior"][0]
        assert senior_y1["mandatory_amort"] == 10_000_000  # 10% of 100M

    def test_with_pik_interest(self):
        """PIK利息"""
        tranches = [
            {"name": "mezzanine", "amount": 50_000_000, "interest_rate": 0.08, "pik_rate": 0.04}
        ]
        operations = [
            {"year": 1, "ufcf": 20_000_000, "ebit": 15_000_000, "tax_rate": 0.25}
        ]

        result = calc_debt_schedule(tranches, operations, sweep_percent=0)

        mezz_y1 = result["schedule"]["mezzanine"][0]
        # PIK利息加到本金
        assert mezz_y1["pik_interest"] == 2_000_000  # 4% of 50M
        # 期末余额增加（因为sweep=0且无摊销）
        assert mezz_y1["closing_balance"] == 52_000_000

    def test_cash_sweep(self):
        """现金扫荡还款"""
        tranches = [
            {"name": "senior", "amount": 100_000_000, "interest_rate": 0.05}
        ]
        operations = [
            {"year": 1, "ufcf": 50_000_000, "ebit": 45_000_000, "tax_rate": 0.25}
        ]

        result = calc_debt_schedule(tranches, operations, sweep_percent=0.75)

        # 验证有现金扫荡发生
        assert result["annual_summary"][0]["cash_sweep"] > 0


class TestCalcExitValue:
    """退出价值测试"""

    def test_basic_calculation(self):
        """基础计算"""
        result = calc_exit_value(130_000_000, 8.0)

        assert result["value"] == 1_040_000_000
        assert result["formula"] == "Exit EBITDA × Exit Multiple"

    def test_multiple_expansion(self):
        """倍数扩张"""
        entry = calc_purchase_price(100_000_000, 8.0)
        exit_val = calc_exit_value(100_000_000, 10.0)  # 倍数从8x到10x

        assert exit_val["value"] > entry["value"]


class TestCalcEquityProceeds:
    """股权所得测试"""

    def test_basic_calculation(self):
        """基础计算"""
        result = calc_equity_proceeds(1_040_000_000, 180_000_000, 20_000_000)

        # Net Debt = 180M - 20M = 160M
        # Equity Proceeds = 1040M - 160M = 880M
        assert result["value"] == 880_000_000
        assert result["net_debt"] == 160_000_000

    def test_no_cash(self):
        """无现金"""
        result = calc_equity_proceeds(1_000_000_000, 300_000_000)

        assert result["value"] == 700_000_000
        assert result["net_debt"] == 300_000_000

    def test_underwater(self):
        """资不抵债"""
        result = calc_equity_proceeds(500_000_000, 600_000_000)

        # 退出价值低于债务
        assert result["value"] < 0


class TestCalcIRR:
    """IRR计算测试"""

    def test_basic_irr(self):
        """基础IRR"""
        # 投入100，5年后拿回200，IRR约14.9%
        cash_flows = [-100, 0, 0, 0, 0, 200]
        result = calc_irr(cash_flows)

        assert result["value"] == pytest.approx(0.1487, rel=0.01)

    def test_high_return(self):
        """高回报"""
        # 投入100，5年后拿回300，IRR约24.6%
        cash_flows = [-100, 0, 0, 0, 0, 300]
        result = calc_irr(cash_flows)

        assert result["value"] == pytest.approx(0.246, rel=0.01)

    def test_with_interim_cashflows(self):
        """有期间现金流"""
        # 投入100，每年分红20，5年后拿回100
        cash_flows = [-100, 20, 20, 20, 20, 120]
        result = calc_irr(cash_flows)

        assert result["value"] > 0.20  # 应该超过20%


class TestCalcMOIC:
    """MOIC计算测试"""

    def test_basic_moic(self):
        """基础MOIC"""
        result = calc_moic(344_000_000, 880_000_000)

        assert result["value"] == pytest.approx(2.56, rel=0.01)

    def test_with_distributions(self):
        """有期间分红"""
        result = calc_moic(100_000_000, 200_000_000, interim_distributions=50_000_000)

        # (200M + 50M) / 100M = 2.5x
        assert result["value"] == 2.5

    def test_loss(self):
        """亏损"""
        result = calc_moic(100_000_000, 50_000_000)

        assert result["value"] == 0.5


class TestLBOQuickBuild:
    """快捷构建测试"""

    @pytest.fixture
    def standard_inputs(self):
        """标准输入"""
        return {
            "entry_ebitda": 100_000_000,
            "entry_multiple": 8.0,
            "exit_multiple": 8.0,
            "holding_period": 5,
            "revenue_growth": 0.05,
            "ebitda_margin": 0.20,
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
            }
        }

    def test_quick_build_structure(self, standard_inputs):
        """验证输出结构"""
        result = lbo_quick_build(standard_inputs)

        assert "_meta" in result
        assert "transaction" in result
        assert "operating_model" in result
        assert "debt_schedule" in result
        assert "exit_analysis" in result
        assert "returns" in result
        assert "credit_stats" in result

    def test_quick_build_returns(self, standard_inputs):
        """验证回报计算"""
        result = lbo_quick_build(standard_inputs)

        irr = result["returns"]["irr"]["value"]
        moic = result["returns"]["moic"]["value"]

        # 合理范围检查
        assert 0.10 < irr < 0.30  # IRR应在10%-30%之间
        assert 1.5 < moic < 3.0   # MOIC应在1.5x-3.0x之间

    def test_quick_build_vs_individual_tools(self, standard_inputs):
        """与单独调用原子工具对比"""
        # 使用快捷构建
        quick_result = lbo_quick_build(standard_inputs)

        # 单独调用原子工具
        purchase = calc_purchase_price(
            standard_inputs["entry_ebitda"],
            standard_inputs["entry_multiple"]
        )

        # 验证一致性
        assert quick_result["transaction"]["purchase_price"]["value"] == purchase["value"]


class TestAtomicToolsComposition:
    """原子工具组合测试 - 模拟LLM灵活调用场景"""

    def test_custom_purchase_price(self):
        """LLM自定义收购价格（跳过calc_purchase_price）"""
        # 场景：用户要求用净资产+30%溢价定价
        custom_price = 750_000_000  # LLM自己算的

        # 后续工具正常使用
        sources = calc_sources_uses(
            purchase_price=custom_price,
            debt_amounts={"senior": 300_000_000, "sub": 150_000_000}
        )

        # 验证追溯
        assert sources["inputs"]["purchase_price"] == custom_price

    def test_alternative_exit_valuation(self):
        """替代退出估值方法"""
        # 场景：用DCF方法得到退出价值
        dcf_exit_value = 950_000_000  # LLM用DCF算的

        # 直接使用这个值计算股权所得
        proceeds = calc_equity_proceeds(
            exit_value=dcf_exit_value,
            ending_debt=200_000_000
        )

        assert proceeds["inputs"]["exit_value"] == dcf_exit_value

    def test_partial_workflow(self):
        """部分流程执行"""
        # 场景：只需要计算资金结构

        # 1. 计算收购价
        purchase = calc_purchase_price(100_000_000, 8.0)

        # 2. 计算资金来源
        sources = calc_sources_uses(
            purchase_price=purchase["value"],
            debt_amounts={"term_loan": 400_000_000}
        )

        # 不需要运营预测，直接返回
        assert sources["equity_required"] > 0

    def test_override_with_traceability(self):
        """覆盖并保留追溯"""
        # 场景：LLM修改了某个计算

        # 用户自定义收购价
        custom_result = {
            "value": 700_000_000,
            "formula": "用户自定义",
            "inputs": {
                "source": "llm_calculated",
                "method": "净资产 × 1.2",
                "note": "用户要求用净资产+20%溢价"
            },
            "source": "llm_override"
        }

        # 后续计算可以使用这个值
        sources = calc_sources_uses(
            purchase_price=custom_result["value"],
            debt_amounts={"senior": 350_000_000}
        )

        # 追溯链完整
        assert sources["inputs"]["purchase_price"] == 700_000_000


class TestEdgeCases:
    """边界情况测试"""

    def test_zero_ebitda(self):
        """EBITDA为零"""
        result = calc_purchase_price(0, 8.0)
        assert result["value"] == 0

    def test_negative_ebitda(self):
        """负EBITDA"""
        result = calc_purchase_price(-50_000_000, 8.0)
        assert result["value"] == -400_000_000

    def test_no_debt(self):
        """无债务（全股权收购）"""
        result = calc_sources_uses(
            purchase_price=500_000_000,
            debt_amounts={}
        )

        # 全部用股权
        assert result["sources"]["total_debt"] == 0
        assert result["equity_required"] > 500_000_000  # 加费用

    def test_single_year(self):
        """单年持有期"""
        inputs = {
            "entry_ebitda": 100_000_000,
            "entry_multiple": 8.0,
            "exit_multiple": 8.5,
            "holding_period": 1,
            "revenue_growth": 0.05,
            "ebitda_margin": 0.20,
            "debt_structure": {
                "senior": {"amount_percent": 0.50, "interest_rate": 0.05}
            }
        }

        result = lbo_quick_build(inputs)

        assert len(result["operating_model"]["projections"]) == 1
        assert len(result["returns"]["cash_flows"]) == 2  # 入+出
