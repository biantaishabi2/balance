# -*- coding: utf-8 -*-
"""
财务比率分析工具测试
"""

import pytest
from financial_model.tools.ratio_tools import (
    calc_profitability,
    calc_liquidity,
    calc_solvency,
    calc_efficiency,
    calc_valuation,
    calc_dupont,
    calc_all_ratios,
)


# 测试数据（基于设计文档的示例）
SAMPLE_INCOME = {
    "revenue": 150_000_000_000,
    "cost_of_revenue": 45_000_000_000,
    "gross_profit": 105_000_000_000,
    "operating_expenses": 30_000_000_000,
    "operating_income": 75_000_000_000,
    "interest_expense": 500_000_000,
    "ebit": 75_500_000_000,
    "ebitda": 82_000_000_000,
    "ebt": 75_000_000_000,  # 税前利润
    "net_income": 62_000_000_000
}

SAMPLE_BALANCE = {
    "cash": 50_000_000_000,
    "accounts_receivable": 12_000_000_000,
    "inventory": 8_000_000_000,
    "current_assets": 75_000_000_000,
    "total_assets": 200_000_000_000,
    "accounts_payable": 15_000_000_000,
    "short_term_debt": 5_000_000_000,
    "current_liabilities": 25_000_000_000,
    "long_term_debt": 30_000_000_000,
    "total_liabilities": 60_000_000_000,
    "total_equity": 140_000_000_000
}

SAMPLE_MARKET = {
    "stock_price": 150.00,
    "shares_outstanding": 1_000_000_000,
    "market_cap": 150_000_000_000
}


class TestProfitability:
    """盈利能力测试"""

    def test_gross_margin(self):
        """测试毛利率计算"""
        result = calc_profitability(
            revenue=SAMPLE_INCOME["revenue"],
            gross_profit=SAMPLE_INCOME["gross_profit"]
        )
        assert result["type"] == "profitability"
        assert round(result["ratios"]["gross_margin"]["value"], 2) == 0.70

    def test_net_margin(self):
        """测试净利率计算"""
        result = calc_profitability(
            revenue=SAMPLE_INCOME["revenue"],
            net_income=SAMPLE_INCOME["net_income"]
        )
        assert round(result["ratios"]["net_margin"]["value"], 4) == 0.4133

    def test_roe(self):
        """测试ROE计算"""
        result = calc_profitability(
            revenue=SAMPLE_INCOME["revenue"],
            net_income=SAMPLE_INCOME["net_income"],
            total_equity=SAMPLE_BALANCE["total_equity"]
        )
        assert round(result["ratios"]["roe"]["value"], 4) == 0.4429

    def test_roa(self):
        """测试ROA计算"""
        result = calc_profitability(
            revenue=SAMPLE_INCOME["revenue"],
            net_income=SAMPLE_INCOME["net_income"],
            total_assets=SAMPLE_BALANCE["total_assets"]
        )
        assert result["ratios"]["roa"]["value"] == 0.31

    def test_all_profitability_ratios(self):
        """测试所有盈利能力比率"""
        result = calc_profitability(
            revenue=SAMPLE_INCOME["revenue"],
            gross_profit=SAMPLE_INCOME["gross_profit"],
            operating_income=SAMPLE_INCOME["operating_income"],
            net_income=SAMPLE_INCOME["net_income"],
            ebitda=SAMPLE_INCOME["ebitda"],
            total_assets=SAMPLE_BALANCE["total_assets"],
            total_equity=SAMPLE_BALANCE["total_equity"]
        )
        assert "gross_margin" in result["ratios"]
        assert "operating_margin" in result["ratios"]
        assert "net_margin" in result["ratios"]
        assert "ebitda_margin" in result["ratios"]
        assert "roa" in result["ratios"]
        assert "roe" in result["ratios"]


class TestLiquidity:
    """流动性测试"""

    def test_current_ratio(self):
        """测试流动比率计算"""
        result = calc_liquidity(
            current_assets=SAMPLE_BALANCE["current_assets"],
            current_liabilities=SAMPLE_BALANCE["current_liabilities"]
        )
        assert result["type"] == "liquidity"
        assert result["ratios"]["current_ratio"]["value"] == 3.0

    def test_quick_ratio(self):
        """测试速动比率计算"""
        result = calc_liquidity(
            current_assets=SAMPLE_BALANCE["current_assets"],
            inventory=SAMPLE_BALANCE["inventory"],
            current_liabilities=SAMPLE_BALANCE["current_liabilities"]
        )
        assert round(result["ratios"]["quick_ratio"]["value"], 2) == 2.68

    def test_cash_ratio(self):
        """测试现金比率计算"""
        result = calc_liquidity(
            cash=SAMPLE_BALANCE["cash"],
            current_liabilities=SAMPLE_BALANCE["current_liabilities"]
        )
        assert result["ratios"]["cash_ratio"]["value"] == 2.0

    def test_missing_current_liabilities(self):
        """测试缺少流动负债时的处理"""
        result = calc_liquidity(
            cash=SAMPLE_BALANCE["cash"],
            current_liabilities=None
        )
        assert "error" in result


class TestSolvency:
    """偿债能力测试"""

    def test_debt_to_equity(self):
        """测试负债权益比计算"""
        total_debt = SAMPLE_BALANCE["short_term_debt"] + SAMPLE_BALANCE["long_term_debt"]
        result = calc_solvency(
            total_debt=total_debt,
            total_equity=SAMPLE_BALANCE["total_equity"]
        )
        assert result["type"] == "solvency"
        assert round(result["ratios"]["debt_to_equity"]["value"], 2) == 0.25

    def test_interest_coverage(self):
        """测试利息覆盖倍数计算"""
        result = calc_solvency(
            ebit=SAMPLE_INCOME["ebit"],
            interest_expense=SAMPLE_INCOME["interest_expense"]
        )
        assert result["ratios"]["interest_coverage"]["value"] == 151.0

    def test_equity_multiplier(self):
        """测试权益乘数计算"""
        result = calc_solvency(
            total_assets=SAMPLE_BALANCE["total_assets"],
            total_equity=SAMPLE_BALANCE["total_equity"]
        )
        assert round(result["ratios"]["equity_multiplier"]["value"], 4) == 1.4286


class TestEfficiency:
    """运营效率测试"""

    def test_asset_turnover(self):
        """测试资产周转率计算"""
        result = calc_efficiency(
            revenue=SAMPLE_INCOME["revenue"],
            total_assets=SAMPLE_BALANCE["total_assets"]
        )
        assert result["type"] == "efficiency"
        assert result["ratios"]["asset_turnover"]["value"] == 0.75

    def test_inventory_turnover(self):
        """测试存货周转率计算"""
        result = calc_efficiency(
            cost_of_revenue=SAMPLE_INCOME["cost_of_revenue"],
            inventory=SAMPLE_BALANCE["inventory"]
        )
        assert round(result["ratios"]["inventory_turnover"]["value"], 3) == 5.625

    def test_receivable_turnover(self):
        """测试应收账款周转率计算"""
        result = calc_efficiency(
            revenue=SAMPLE_INCOME["revenue"],
            accounts_receivable=SAMPLE_BALANCE["accounts_receivable"]
        )
        assert result["ratios"]["receivable_turnover"]["value"] == 12.5

    def test_cash_conversion_cycle(self):
        """测试现金转换周期计算"""
        result = calc_efficiency(
            revenue=SAMPLE_INCOME["revenue"],
            cost_of_revenue=SAMPLE_INCOME["cost_of_revenue"],
            total_assets=SAMPLE_BALANCE["total_assets"],
            inventory=SAMPLE_BALANCE["inventory"],
            accounts_receivable=SAMPLE_BALANCE["accounts_receivable"],
            accounts_payable=SAMPLE_BALANCE["accounts_payable"]
        )
        assert "cash_conversion_cycle" in result["ratios"]
        # CCC = 库存天数 + 应收天数 - 应付天数
        # 约 64.89 + 29.2 - 121.67 = -27.58
        assert result["ratios"]["cash_conversion_cycle"]["value"] < 0


class TestValuation:
    """估值测试"""

    def test_pe_ratio(self):
        """测试市盈率计算"""
        result = calc_valuation(
            market_cap=SAMPLE_MARKET["market_cap"],
            net_income=SAMPLE_INCOME["net_income"]
        )
        assert result["type"] == "valuation"
        assert round(result["ratios"]["pe_ratio"]["value"], 2) == 2.42

    def test_pb_ratio(self):
        """测试市净率计算"""
        result = calc_valuation(
            market_cap=SAMPLE_MARKET["market_cap"],
            total_equity=SAMPLE_BALANCE["total_equity"]
        )
        assert round(result["ratios"]["pb_ratio"]["value"], 2) == 1.07

    def test_ev_ebitda(self):
        """测试EV/EBITDA计算"""
        total_debt = SAMPLE_BALANCE["short_term_debt"] + SAMPLE_BALANCE["long_term_debt"]
        result = calc_valuation(
            market_cap=SAMPLE_MARKET["market_cap"],
            ebitda=SAMPLE_INCOME["ebitda"],
            total_debt=total_debt,
            cash=SAMPLE_BALANCE["cash"]
        )
        # EV = 150B + 35B - 50B = 135B
        # EV/EBITDA = 135B / 82B ≈ 1.65
        assert round(result["ratios"]["ev_ebitda"]["value"], 2) == 1.65

    def test_market_cap_from_price(self):
        """测试从股价计算市值"""
        result = calc_valuation(
            stock_price=SAMPLE_MARKET["stock_price"],
            shares_outstanding=SAMPLE_MARKET["shares_outstanding"],
            net_income=SAMPLE_INCOME["net_income"]
        )
        assert "pe_ratio" in result["ratios"]


class TestDupont:
    """杜邦分析测试"""

    def test_dupont_3_factor(self):
        """测试3因素杜邦分析"""
        result = calc_dupont(
            net_income=SAMPLE_INCOME["net_income"],
            revenue=SAMPLE_INCOME["revenue"],
            total_assets=SAMPLE_BALANCE["total_assets"],
            total_equity=SAMPLE_BALANCE["total_equity"],
            levels=3
        )
        assert result["model"] == "dupont_3_factor"
        assert round(result["roe"], 4) == 0.4429
        assert "net_margin" in result["decomposition"]
        assert "asset_turnover" in result["decomposition"]
        assert "equity_multiplier" in result["decomposition"]
        assert "verification" in result

    def test_dupont_5_factor(self):
        """测试5因素杜邦分析"""
        result = calc_dupont(
            net_income=SAMPLE_INCOME["net_income"],
            revenue=SAMPLE_INCOME["revenue"],
            total_assets=SAMPLE_BALANCE["total_assets"],
            total_equity=SAMPLE_BALANCE["total_equity"],
            ebit=SAMPLE_INCOME["ebit"],
            ebt=SAMPLE_INCOME["ebt"],
            levels=5
        )
        assert result["model"] == "dupont_5_factor"
        assert "tax_burden" in result["decomposition"]
        assert "interest_burden" in result["decomposition"]
        assert "operating_margin" in result["decomposition"]
        assert "insights" in result

    def test_dupont_5_missing_params(self):
        """测试5因素缺少参数时的处理"""
        result = calc_dupont(
            net_income=SAMPLE_INCOME["net_income"],
            revenue=SAMPLE_INCOME["revenue"],
            total_assets=SAMPLE_BALANCE["total_assets"],
            total_equity=SAMPLE_BALANCE["total_equity"],
            levels=5
        )
        assert "error" in result


class TestAllRatios:
    """综合计算测试"""

    def test_calc_all_ratios(self):
        """测试计算所有比率"""
        result = calc_all_ratios(
            income_statement=SAMPLE_INCOME,
            balance_sheet=SAMPLE_BALANCE,
            market_data=SAMPLE_MARKET
        )
        assert "_meta" in result
        assert result["_meta"]["model_type"] == "ratio_analysis"
        assert "profitability" in result
        assert "liquidity" in result
        assert "solvency" in result
        assert "efficiency" in result
        assert "valuation" in result
        assert "dupont_3" in result
        assert "dupont_5" in result

    def test_partial_data(self):
        """测试部分数据输入"""
        result = calc_all_ratios(
            income_statement={
                "revenue": 100_000_000,
                "net_income": 10_000_000
            },
            balance_sheet={
                "total_assets": 80_000_000,
                "total_equity": 50_000_000
            }
        )
        assert "profitability" in result
        # 没有流动负债，不应有流动性分析
        assert "liquidity" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
