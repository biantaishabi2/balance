# -*- coding: utf-8 -*-
"""
三表模型原子工具测试
"""

import pytest
from financial_model.tools.three_statement_tools import (
    forecast_revenue,
    forecast_cost,
    forecast_opex,
    calc_income_statement,
    calc_working_capital,
    calc_depreciation,
    calc_capex,
    calc_operating_cash_flow,
    calc_cash_flow_statement,
    check_balance,
    three_statement_quick_build,
)


class TestForecastRevenue:
    """测试 forecast_revenue: 收入预测"""

    def test_basic_growth(self):
        """基础增长"""
        result = forecast_revenue(500_000_000, 0.09)
        assert result["value"] == 545_000_000
        assert result["formula"] == "last_revenue × (1 + growth_rate)"

    def test_zero_growth(self):
        """零增长"""
        result = forecast_revenue(500_000_000, 0)
        assert result["value"] == 500_000_000

    def test_negative_growth(self):
        """负增长"""
        result = forecast_revenue(500_000_000, -0.10)
        assert result["value"] == 450_000_000

    def test_high_growth(self):
        """高增长"""
        result = forecast_revenue(100_000_000, 1.0)  # 100%增长
        assert result["value"] == 200_000_000


class TestForecastCost:
    """测试 forecast_cost: 成本预测"""

    def test_basic_cost(self):
        """基础成本计算"""
        result = forecast_cost(545_000_000, 0.25)
        assert result["value"] == 408_750_000

    def test_high_margin(self):
        """高毛利率"""
        result = forecast_cost(100_000_000, 0.50)
        assert result["value"] == 50_000_000

    def test_low_margin(self):
        """低毛利率"""
        result = forecast_cost(100_000_000, 0.10)
        assert result["value"] == 90_000_000

    def test_zero_margin(self):
        """零毛利率"""
        result = forecast_cost(100_000_000, 0)
        assert result["value"] == 100_000_000


class TestForecastOpex:
    """测试 forecast_opex: 费用预测"""

    def test_basic_opex(self):
        """基础费用计算"""
        result = forecast_opex(545_000_000, 0.12)
        assert result["value"] == 65_400_000

    def test_high_opex_ratio(self):
        """高费用率"""
        result = forecast_opex(100_000_000, 0.30)
        assert result["value"] == 30_000_000

    def test_zero_opex(self):
        """零费用"""
        result = forecast_opex(100_000_000, 0)
        assert result["value"] == 0


class TestCalcIncomeStatement:
    """测试 calc_income_statement: 完整利润表"""

    def test_profitable_company(self):
        """盈利公司"""
        result = calc_income_statement(
            revenue=545_000_000,
            cost=408_750_000,
            opex=65_400_000,
            interest=5_000_000,
            tax_rate=0.25
        )

        assert result["gross_profit"] == 136_250_000
        assert result["ebit"] == 70_850_000
        assert result["ebt"] == 65_850_000
        assert result["tax"] == 65_850_000 * 0.25
        assert result["net_income"] > 0

    def test_loss_making_company(self):
        """亏损公司"""
        result = calc_income_statement(
            revenue=100_000_000,
            cost=90_000_000,
            opex=20_000_000,
            interest=5_000_000,
            tax_rate=0.25
        )

        assert result["ebt"] < 0
        assert result["tax"] == 0  # 亏损不交税
        assert result["net_income"] == result["ebt"]

    def test_margin_calculations(self):
        """利润率计算"""
        result = calc_income_statement(
            revenue=1_000_000_000,
            cost=700_000_000,
            opex=150_000_000,
            interest=10_000_000,
            tax_rate=0.25
        )

        assert result["details"]["gross_margin"]["value"] == 0.30
        assert round(result["details"]["ebit_margin"]["value"], 2) == 0.15


class TestCalcWorkingCapital:
    """测试 calc_working_capital: 营运资本"""

    def test_basic_working_capital(self):
        """基础营运资本计算"""
        result = calc_working_capital(
            revenue=545_000_000,
            cost=408_750_000,
            ar_days=60,
            ap_days=45,
            inv_days=30
        )

        # AR = 545M / 365 × 60 ≈ 89.59M
        assert round(result["receivable"], 0) == round(545_000_000 / 365 * 60, 0)
        # AP = 408.75M / 365 × 45 ≈ 50.38M
        assert round(result["payable"], 0) == round(408_750_000 / 365 * 45, 0)
        # Inv = 408.75M / 365 × 30 ≈ 33.60M
        assert round(result["inventory"], 0) == round(408_750_000 / 365 * 30, 0)

    def test_nwc_calculation(self):
        """净营运资本计算"""
        result = calc_working_capital(
            revenue=365_000_000,  # 简化计算
            cost=365_000_000,
            ar_days=30,
            ap_days=30,
            inv_days=30
        )

        # AR = 365M / 365 × 30 = 30M
        # AP = 365M / 365 × 30 = 30M
        # Inv = 365M / 365 × 30 = 30M
        # NWC = 30M + 30M - 30M = 30M
        assert round(result["net_working_capital"], 0) == 30_000_000


class TestCalcDepreciation:
    """测试 calc_depreciation: 折旧计算"""

    def test_basic_depreciation(self):
        """基础折旧计算"""
        result = calc_depreciation(100_000_000, 10)
        assert result["value"] == 10_000_000

    def test_with_salvage(self):
        """有残值"""
        result = calc_depreciation(100_000_000, 10, 10_000_000)
        assert result["value"] == 9_000_000

    def test_short_life(self):
        """短使用年限"""
        result = calc_depreciation(50_000_000, 2)
        assert result["value"] == 25_000_000

    def test_zero_life(self):
        """零年限（边界情况）"""
        result = calc_depreciation(100_000_000, 0)
        assert result["value"] == 0


class TestCalcCapex:
    """测试 calc_capex: 资本支出"""

    def test_basic_capex(self):
        """基础资本支出"""
        result = calc_capex(545_000_000, 0.05)
        assert result["value"] == 27_250_000

    def test_high_capex(self):
        """高资本支出率（重资产行业）"""
        result = calc_capex(100_000_000, 0.20)
        assert result["value"] == 20_000_000

    def test_zero_capex(self):
        """零资本支出"""
        result = calc_capex(100_000_000, 0)
        assert result["value"] == 0


class TestCalcOperatingCashFlow:
    """测试 calc_operating_cash_flow: 经营现金流"""

    def test_basic_ocf(self):
        """基础经营现金流"""
        result = calc_operating_cash_flow(
            net_income=49_387_500,
            depreciation=10_000_000,
            delta_ar=5_000_000,
            delta_inv=2_000_000,
            delta_ap=3_000_000
        )

        # OCF = 49.3875M + 10M - (5M + 2M - 3M) = 59.3875M - 4M = 55.3875M
        expected = 49_387_500 + 10_000_000 - (5_000_000 + 2_000_000 - 3_000_000)
        assert result["value"] == expected
        assert result["inputs"]["delta_nwc"] == 4_000_000

    def test_nwc_decrease(self):
        """营运资本下降（释放现金）"""
        result = calc_operating_cash_flow(
            net_income=50_000_000,
            depreciation=10_000_000,
            delta_ar=-5_000_000,  # AR下降
            delta_inv=-3_000_000,  # Inv下降
            delta_ap=-2_000_000   # AP下降
        )

        # ΔNWC = -5 - 3 + 2 = -6M（释放6M现金）
        # OCF = 50M + 10M - (-6M) = 66M
        assert result["value"] == 66_000_000


class TestCalcCashFlowStatement:
    """测试 calc_cash_flow_statement: 完整现金流量表"""

    def test_complete_cash_flow(self):
        """完整现金流量表（间接法，利息已在净利润中扣除）"""
        result = calc_cash_flow_statement(
            net_income=49_387_500,
            depreciation=10_000_000,
            delta_ar=5_000_000,
            delta_inv=2_000_000,
            delta_ap=3_000_000,
            capex=27_250_000,
            dividend=15_000_000
        )

        # OCF = 49.3875M + 10M - 4M = 55.3875M
        # ICF = -27.25M
        # FCF = -15M + 0 = -15M（利息已在净利润中扣除，不再重复扣除）
        # Net = 55.3875M - 27.25M - 15M = 13.1375M
        assert result["operating_cf"] == 55_387_500
        assert result["investing_cf"] == -27_250_000
        assert result["financing_cf"] == -15_000_000

    def test_with_debt_change(self):
        """包含债务变动"""
        result = calc_cash_flow_statement(
            net_income=50_000_000,
            depreciation=10_000_000,
            delta_ar=0,
            delta_inv=0,
            delta_ap=0,
            capex=20_000_000,
            dividend=10_000_000,
            delta_debt=30_000_000  # 新增借款
        )

        # FCF = -10M + 30M = 20M（利息已在净利润中扣除）
        assert result["financing_cf"] == 20_000_000


class TestCheckBalance:
    """测试 check_balance: 配平检验"""

    def test_balanced(self):
        """配平"""
        result = check_balance(500_000_000, 200_000_000, 300_000_000)
        assert result["is_balanced"] is True
        assert result["difference"] == 0

    def test_unbalanced(self):
        """不配平"""
        result = check_balance(500_000_000, 200_000_000, 290_000_000)
        assert result["is_balanced"] is False
        assert result["difference"] == 10_000_000

    def test_small_difference(self):
        """小误差（在允许范围内）"""
        result = check_balance(500_000_000.005, 200_000_000, 300_000_000)
        assert result["is_balanced"] is True


class TestThreeStatementQuickBuild:
    """测试 three_statement_quick_build: 快捷构建"""

    @pytest.fixture
    def base_data(self):
        """基期数据 - 确保配平: 资产310M = 负债150M + 权益160M"""
        return {
            "company": "测试公司",
            "period": "2024Q3",
            "last_revenue": 500_000_000,
            "closing_cash": 100_000_000,
            "closing_receivable": 80_000_000,
            "closing_inventory": 30_000_000,
            "closing_payable": 50_000_000,
            "closing_debt": 100_000_000,
            "closing_equity": 160_000_000,  # 310M - 150M = 160M
            "fixed_asset_gross": 150_000_000,
            "fixed_asset_life": 10,
            "accum_depreciation": 50_000_000
            # 资产: 100M + 80M + 30M + (150M-50M) = 310M
            # 负债: 50M + 100M = 150M
            # 权益: 160M
        }

    @pytest.fixture
    def assumptions(self):
        """预测假设"""
        return {
            "growth_rate": 0.09,
            "gross_margin": 0.25,
            "opex_ratio": 0.12,
            "ar_days": 60,
            "ap_days": 45,
            "inv_days": 30,
            "capex_ratio": 0.05,
            "interest_rate": 0.05,
            "tax_rate": 0.25,
            "dividend_ratio": 0.30
        }

    def test_basic_build(self, base_data, assumptions):
        """基础构建"""
        result = three_statement_quick_build(base_data, assumptions)

        assert result["_meta"]["model_type"] == "three_statement"
        assert result["_meta"]["built_with"] == "atomic_tools"
        assert result["_meta"]["company"] == "测试公司"

    def test_income_statement(self, base_data, assumptions):
        """利润表计算验证"""
        result = three_statement_quick_build(base_data, assumptions)

        # 收入增长9%
        expected_revenue = 500_000_000 * 1.09
        assert result["income_statement"]["revenue"]["value"] == expected_revenue

        # 毛利率25%
        gross_profit = expected_revenue * 0.25
        assert result["income_statement"]["gross_profit"]["value"] == gross_profit

        # 净利润应该为正
        assert result["income_statement"]["net_income"]["value"] > 0

    def test_balance_sheet_balanced(self, base_data, assumptions):
        """资产负债表配平"""
        result = three_statement_quick_build(base_data, assumptions)

        assert result["validation"]["is_balanced"] is True

    def test_cash_flow_reconciliation(self, base_data, assumptions):
        """现金流勾稽"""
        result = three_statement_quick_build(base_data, assumptions)

        # 期末现金 = 期初现金 + 净现金变动
        opening_cash = base_data["closing_cash"]
        net_change = result["cash_flow"]["net_change"]["value"]
        closing_cash = result["cash_flow"]["closing_cash"]["value"]

        assert round(closing_cash, 2) == round(opening_cash + net_change, 2)

    def test_working_capital_changes(self, base_data, assumptions):
        """营运资本变动"""
        result = three_statement_quick_build(base_data, assumptions)

        wc = result["working_capital"]
        assert "delta_ar" in wc
        assert "delta_inv" in wc
        assert "delta_ap" in wc
        assert "delta_nwc" in wc

    def test_fixed_asset_tracking(self, base_data, assumptions):
        """固定资产追踪"""
        result = three_statement_quick_build(base_data, assumptions)

        fa = result["fixed_assets"]
        assert fa["opening_gross"] == base_data["fixed_asset_gross"]
        assert fa["closing_gross"] == fa["opening_gross"] + fa["capex"]["value"]
        assert fa["closing_accum_dep"] == base_data["accum_depreciation"] + fa["depreciation"]["value"]

    def test_zero_debt(self, base_data, assumptions):
        """零负债情况"""
        # 当债务从100M变为0时，需要调整权益以保持期初配平
        # 原来: 资产310M = 负债150M(50M应付+100M债务) + 权益160M
        # 现在: 资产310M = 负债50M(只有应付) + 权益260M
        base_data["closing_debt"] = 0
        base_data["closing_equity"] = 260_000_000  # 310M - 50M = 260M
        result = three_statement_quick_build(base_data, assumptions)

        assert result["income_statement"]["interest"]["value"] == 0
        assert result["validation"]["is_balanced"] is True


class TestIntegration:
    """集成测试"""

    def test_full_workflow(self):
        """完整工作流程：模拟LLM调用"""
        # 用户提供基期数据
        # 资产: 200M + 150M + 80M + (500M-200M) = 730M
        # 负债: 100M + 300M = 400M
        # 权益: 330M => 730M = 400M + 330M
        base = {
            "last_revenue": 1_000_000_000,
            "closing_cash": 200_000_000,
            "closing_receivable": 150_000_000,
            "closing_inventory": 80_000_000,
            "closing_payable": 100_000_000,
            "closing_debt": 300_000_000,
            "closing_equity": 330_000_000,  # 730M - 400M = 330M
            "fixed_asset_gross": 500_000_000,
            "fixed_asset_life": 10,
            "accum_depreciation": 200_000_000
        }

        assumptions = {
            "growth_rate": 0.10,
            "gross_margin": 0.30,
            "opex_ratio": 0.15,
            "ar_days": 55,
            "ap_days": 40,
            "inv_days": 25,
            "capex_ratio": 0.08,
            "interest_rate": 0.06,
            "tax_rate": 0.25,
            "dividend_ratio": 0.25
        }

        result = three_statement_quick_build(base, assumptions)

        # 验证关键指标
        assert result["income_statement"]["revenue"]["value"] == 1_100_000_000
        assert result["income_statement"]["net_income"]["value"] > 0
        assert result["validation"]["is_balanced"] is True

    def test_llm_override_scenario(self):
        """LLM覆盖场景：用户自己提供收入"""
        # 用户想要直接使用800M收入，不用公式计算
        revenue = 800_000_000  # 用户直接提供

        # LLM可以跳过forecast_revenue，直接用后续工具
        cost = forecast_cost(revenue, 0.25)
        opex = forecast_opex(revenue, 0.12)

        income = calc_income_statement(
            revenue=revenue,
            cost=cost["value"],
            opex=opex["value"],
            interest=5_000_000,
            tax_rate=0.25
        )

        assert income["gross_profit"] == revenue * 0.25
        assert income["net_income"] > 0

    def test_partial_tool_usage(self):
        """部分工具使用"""
        # 只用部分工具计算营运资本和现金流
        revenue = 500_000_000
        cost = 375_000_000

        wc = calc_working_capital(revenue, cost, 60, 45, 30)
        ocf = calc_operating_cash_flow(
            net_income=30_000_000,
            depreciation=10_000_000,
            delta_ar=5_000_000,
            delta_inv=2_000_000,
            delta_ap=3_000_000
        )

        assert wc["receivable"] > 0
        assert ocf["value"] > 0
