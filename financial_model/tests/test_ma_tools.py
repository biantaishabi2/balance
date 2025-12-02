# -*- coding: utf-8 -*-
"""
M&A 原子工具测试

测试场景覆盖:
1. 基础功能测试 - 各工具的正常计算
2. 增厚/稀释测试 - 不同支付方式的影响
3. 商誉测试 - 正商誉、负商誉（廉价收购）
4. 协同效应测试 - 成本协同、收入协同、整合成本
5. 边界情况测试 - 异常输入处理
"""

import pytest
from financial_model.tools.ma_tools import (
    calc_offer_price,
    calc_funding_mix,
    calc_goodwill,
    calc_pro_forma,
    calc_accretion_dilution,
    calc_synergies,
    calc_breakeven,
    ma_quick_build,
)


class TestCalcOfferPrice:
    """收购报价计算测试"""

    def test_basic_offer_with_premium(self):
        """基础测试：带溢价的收购报价"""
        result = calc_offer_price(
            target_share_price=50,
            target_shares=200_000_000,
            premium_percent=0.30
        )

        assert result["offer_price_per_share"] == 65.0
        assert result["total_purchase_price"] == 13_000_000_000
        assert result["premium"]["percent"] == 0.30
        assert result["premium"]["value"] == 3_000_000_000

    def test_offer_without_premium(self):
        """无溢价收购"""
        result = calc_offer_price(
            target_share_price=50,
            target_shares=200_000_000,
            premium_percent=0
        )

        assert result["offer_price_per_share"] == 50.0
        assert result["total_purchase_price"] == 10_000_000_000
        assert result["premium"]["value"] == 0

    def test_high_premium(self):
        """高溢价收购（50%溢价）"""
        result = calc_offer_price(
            target_share_price=100,
            target_shares=100_000_000,
            premium_percent=0.50
        )

        assert result["offer_price_per_share"] == 150.0
        assert result["total_purchase_price"] == 15_000_000_000

    def test_output_structure(self):
        """验证输出结构"""
        result = calc_offer_price(50, 200_000_000, 0.30)

        assert "offer_price_per_share" in result
        assert "total_purchase_price" in result
        assert "premium" in result
        assert "formula" in result
        assert "inputs" in result
        assert "source" in result


class TestCalcFundingMix:
    """融资结构计算测试"""

    def test_cash_only(self):
        """全现金收购"""
        result = calc_funding_mix(
            total_purchase_price=10_000_000_000,
            cash_percent=1.0,
            stock_percent=0,
            acquirer_share_price=100
        )

        assert result["cash_amount"] == 10_000_000_000
        assert result["stock_amount"] == 0
        assert result["new_shares_issued"] == 0

    def test_stock_only(self):
        """全股票收购"""
        result = calc_funding_mix(
            total_purchase_price=10_000_000_000,
            cash_percent=0,
            stock_percent=1.0,
            acquirer_share_price=100
        )

        assert result["cash_amount"] == 0
        assert result["stock_amount"] == 10_000_000_000
        assert result["new_shares_issued"] == 100_000_000

    def test_mixed_funding(self):
        """混合支付（60%现金+40%股票）"""
        result = calc_funding_mix(
            total_purchase_price=13_000_000_000,
            cash_percent=0.60,
            stock_percent=0.40,
            acquirer_share_price=100
        )

        assert result["cash_amount"] == 7_800_000_000
        assert result["stock_amount"] == 5_200_000_000
        assert result["new_shares_issued"] == 52_000_000

    def test_funding_with_debt(self):
        """包含债务融资"""
        result = calc_funding_mix(
            total_purchase_price=10_000_000_000,
            cash_percent=0.40,
            stock_percent=0.30,
            acquirer_share_price=100,
            new_debt=3_000_000_000
        )

        assert result["cash_amount"] == 4_000_000_000
        assert result["stock_amount"] == 3_000_000_000
        assert result["new_debt"] == 3_000_000_000


class TestCalcGoodwill:
    """商誉计算测试"""

    def test_positive_goodwill(self):
        """正商誉（收购溢价）"""
        result = calc_goodwill(
            purchase_price=15_000_000_000,
            target_book_value=10_000_000_000
        )

        assert result["goodwill"] == 5_000_000_000
        assert result["is_bargain_purchase"] is False

    def test_goodwill_with_fv_adjustments(self):
        """含公允价值调整的商誉"""
        result = calc_goodwill(
            purchase_price=13_000_000_000,
            target_book_value=20_000_000_000,
            fair_value_adjustments={
                "intangible_assets": 5_000_000_000,
                "fixed_assets_step_up": 1_000_000_000,
                "deferred_tax_liability": 1_500_000_000
            }
        )

        # 调整后净资产 = 20B + 5B + 1B - 1.5B = 24.5B
        # 商誉 = 13B - 24.5B = -11.5B
        assert result["adjusted_net_assets"] == 24_500_000_000
        assert result["goodwill"] == -11_500_000_000
        assert result["is_bargain_purchase"] is True

    def test_bargain_purchase(self):
        """廉价收购（负商誉）"""
        result = calc_goodwill(
            purchase_price=8_000_000_000,
            target_book_value=10_000_000_000
        )

        assert result["goodwill"] == -2_000_000_000
        assert result["is_bargain_purchase"] is True
        assert "负商誉" in result["note"]

    def test_zero_goodwill(self):
        """零商誉（收购价=净资产）"""
        result = calc_goodwill(
            purchase_price=10_000_000_000,
            target_book_value=10_000_000_000
        )

        assert result["goodwill"] == 0
        assert result["is_bargain_purchase"] is False


class TestCalcAccretionDilution:
    """增厚/稀释分析测试"""

    def test_dilutive_deal(self):
        """稀释型交易"""
        result = calc_accretion_dilution(
            acquirer_net_income=50_000_000_000,
            acquirer_shares=1_000_000_000,
            target_net_income=2_000_000_000,
            purchase_price=13_000_000_000,
            cash_percent=0.60,
            stock_percent=0.40,
            acquirer_share_price=100
        )

        assert result["accretion_dilution"]["status"] == "Dilutive"
        assert result["pro_forma"]["eps"] < result["standalone"]["eps"]

    def test_accretive_deal_low_pe_target(self):
        """增厚型交易（目标PE低于收购方）"""
        # 收购方PE = 100/5 = 20x
        # 目标PE = 50/5 = 10x (更便宜)
        result = calc_accretion_dilution(
            acquirer_net_income=5_000_000_000,   # EPS = 5
            acquirer_shares=1_000_000_000,
            target_net_income=1_000_000_000,     # 目标盈利更高相对于收购价
            purchase_price=5_000_000_000,        # 低PE收购
            cash_percent=0,
            stock_percent=1.0,                   # 全股票
            acquirer_share_price=100
        )

        assert result["accretion_dilution"]["status"] == "Accretive"

    def test_with_synergies(self):
        """含协同效应的分析"""
        result = calc_accretion_dilution(
            acquirer_net_income=50_000_000_000,
            acquirer_shares=1_000_000_000,
            target_net_income=2_000_000_000,
            purchase_price=13_000_000_000,
            cash_percent=0.60,
            stock_percent=0.40,
            acquirer_share_price=100,
            synergies=2_000_000_000  # 20亿协同
        )

        # 有协同时稀释应该减少
        result_no_syn = calc_accretion_dilution(
            acquirer_net_income=50_000_000_000,
            acquirer_shares=1_000_000_000,
            target_net_income=2_000_000_000,
            purchase_price=13_000_000_000,
            cash_percent=0.60,
            stock_percent=0.40,
            acquirer_share_price=100,
            synergies=0
        )

        assert result["pro_forma"]["eps"] > result_no_syn["pro_forma"]["eps"]

    def test_cash_vs_stock_impact(self):
        """现金vs股票支付的影响"""
        # 全现金
        result_cash = calc_accretion_dilution(
            acquirer_net_income=10_000_000_000,
            acquirer_shares=1_000_000_000,
            target_net_income=500_000_000,
            purchase_price=5_000_000_000,
            cash_percent=1.0,
            stock_percent=0,
            acquirer_share_price=100
        )

        # 全股票
        result_stock = calc_accretion_dilution(
            acquirer_net_income=10_000_000_000,
            acquirer_shares=1_000_000_000,
            target_net_income=500_000_000,
            purchase_price=5_000_000_000,
            cash_percent=0,
            stock_percent=1.0,
            acquirer_share_price=100
        )

        # 全现金不稀释股数，但损失利息
        # 全股票稀释股数，但不损失利息
        assert result_cash["pro_forma"]["combined_shares"] == 1_000_000_000
        assert result_stock["pro_forma"]["combined_shares"] == 1_050_000_000


class TestCalcSynergies:
    """协同效应计算测试"""

    def test_cost_synergies_only(self):
        """仅成本协同"""
        result = calc_synergies(
            cost_synergies=1_000_000_000,
            revenue_synergies=0,
            integration_costs=0,
            years=5,
            discount_rate=0.10,
            tax_rate=0.25
        )

        assert result["total_synergies_pv"] > 0
        assert len(result["yearly_details"]) == 5

    def test_synergies_with_ramp_up(self):
        """协同效应逐年递增"""
        result = calc_synergies(
            cost_synergies=[500_000_000, 800_000_000, 1_000_000_000, 1_000_000_000, 1_000_000_000],
            revenue_synergies=[0, 200_000_000, 500_000_000, 500_000_000, 500_000_000],
            integration_costs=[300_000_000, 100_000_000, 0, 0, 0],
            years=5,
            discount_rate=0.10
        )

        # 第一年协同较低（有整合成本）
        assert result["yearly_details"][0]["net_synergy"] < result["yearly_details"][2]["net_synergy"]

    def test_integration_costs_impact(self):
        """整合成本的影响"""
        # 有整合成本
        result_with_integ = calc_synergies(
            cost_synergies=1_000_000_000,
            integration_costs=500_000_000,
            years=3,
            discount_rate=0.10
        )

        # 无整合成本
        result_no_integ = calc_synergies(
            cost_synergies=1_000_000_000,
            integration_costs=0,
            years=3,
            discount_rate=0.10
        )

        assert result_with_integ["total_synergies_pv"] < result_no_integ["total_synergies_pv"]

    def test_terminal_value(self):
        """终值计算"""
        result = calc_synergies(
            cost_synergies=1_000_000_000,
            years=5,
            discount_rate=0.10,
            tax_rate=0.25
        )

        assert "terminal_value" in result
        assert result["terminal_value"]["value"] > 0
        assert result["total_synergies_pv_with_terminal"] > result["total_synergies_pv"]


class TestCalcBreakeven:
    """盈亏平衡分析测试"""

    def test_synergies_needed_for_dilutive_deal(self):
        """稀释交易需要协同"""
        result = calc_breakeven(
            acquirer_net_income=50_000_000_000,
            acquirer_shares=1_000_000_000,
            target_net_income=2_000_000_000,
            purchase_price=13_000_000_000,
            cash_percent=0.60,
            stock_percent=0.40,
            acquirer_share_price=100
        )

        assert result["synergies_needed"] > 0
        assert result["current_dilution"]["status"] == "Dilutive"

    def test_no_synergies_needed_for_accretive_deal(self):
        """增厚交易不需要协同"""
        result = calc_breakeven(
            acquirer_net_income=5_000_000_000,
            acquirer_shares=1_000_000_000,
            target_net_income=1_000_000_000,
            purchase_price=5_000_000_000,
            cash_percent=0,
            stock_percent=1.0,
            acquirer_share_price=100
        )

        # synergies_needed 应该为0（或负值，表示已增厚）
        assert result["synergies_needed"] == 0
        assert "已经增厚" in result["interpretation"]


class TestCalcProForma:
    """合并报表测试"""

    def test_basic_combination(self):
        """基础合并"""
        result = calc_pro_forma(
            acquirer_financials={
                "total_assets": 500_000_000_000,
                "cash": 100_000_000_000,
                "goodwill": 10_000_000_000,
                "intangible_assets": 5_000_000_000,
                "total_liabilities": 200_000_000_000,
                "total_equity": 300_000_000_000
            },
            target_financials={
                "total_assets": 30_000_000_000,
                "cash": 5_000_000_000,
                "goodwill": 0,
                "intangible_assets": 1_000_000_000,
                "total_liabilities": 10_000_000_000,
                "total_equity": 20_000_000_000
            },
            deal_adjustments={
                "cash_used": 7_800_000_000,
                "new_debt": 0,
                "new_equity_issued": 5_200_000_000,
                "goodwill_created": 5_000_000_000,
                "intangible_assets_created": 3_000_000_000,
                "fixed_assets_step_up": 1_000_000_000,
                "deferred_tax_liability": 500_000_000
            }
        )

        # 验证现金调整
        pro_forma_cash = result["pro_forma_balance_sheet"]["assets"]["cash"]["pro_forma"]
        expected_cash = 100_000_000_000 + 5_000_000_000 - 7_800_000_000
        assert pro_forma_cash == expected_cash

        # 验证商誉
        pro_forma_goodwill = result["pro_forma_balance_sheet"]["assets"]["goodwill"]["pro_forma"]
        expected_goodwill = 10_000_000_000 + 0 + 5_000_000_000
        assert pro_forma_goodwill == expected_goodwill


class TestMAQuickBuild:
    """快捷构建测试"""

    def test_basic_ma_analysis(self):
        """基础M&A分析"""
        inputs = {
            "acquirer": {
                "share_price": 100,
                "shares_outstanding": 1_000_000_000,
                "net_income": 50_000_000_000,
                "total_assets": 500_000_000_000,
                "total_liabilities": 200_000_000_000,
                "total_equity": 300_000_000_000,
                "cash": 100_000_000_000,
                "goodwill": 10_000_000_000
            },
            "target": {
                "share_price": 50,
                "shares_outstanding": 200_000_000,
                "net_income": 2_000_000_000,
                "total_assets": 30_000_000_000,
                "total_liabilities": 10_000_000_000,
                "total_equity": 20_000_000_000,
                "cash": 5_000_000_000,
                "goodwill": 0
            },
            "deal_terms": {
                "premium_percent": 0.30,
                "cash_percent": 0.60,
                "stock_percent": 0.40
            }
        }

        result = ma_quick_build(inputs)

        # 验证结构
        assert "_meta" in result
        assert result["_meta"]["model_type"] == "ma"
        assert "deal_summary" in result
        assert "purchase_price_allocation" in result
        assert "accretion_dilution" in result
        assert "breakeven" in result

        # 验证收购价
        assert result["deal_summary"]["purchase_price"] == 13_000_000_000

    def test_ma_with_synergies(self):
        """含协同效应的M&A分析"""
        inputs = {
            "acquirer": {
                "share_price": 100,
                "shares_outstanding": 1_000_000_000,
                "net_income": 50_000_000_000,
                "total_assets": 500_000_000_000,
                "total_liabilities": 200_000_000_000,
                "total_equity": 300_000_000_000,
                "cash": 100_000_000_000,
                "goodwill": 10_000_000_000
            },
            "target": {
                "share_price": 50,
                "shares_outstanding": 200_000_000,
                "net_income": 2_000_000_000,
                "total_assets": 30_000_000_000,
                "total_liabilities": 10_000_000_000,
                "total_equity": 20_000_000_000,
                "cash": 5_000_000_000,
                "goodwill": 0
            },
            "deal_terms": {
                "premium_percent": 0.30,
                "cash_percent": 0.60,
                "stock_percent": 0.40
            },
            "synergies": {
                "cost_synergies": [500_000_000, 800_000_000, 1_000_000_000],
                "revenue_synergies": [0, 200_000_000, 500_000_000],
                "integration_costs": [300_000_000, 100_000_000, 0]
            },
            "ppa": {
                "intangible_assets": 5_000_000_000,
                "intangible_amortization_years": 10,
                "fixed_assets_step_up": 1_000_000_000,
                "deferred_tax_liability": 1_500_000_000
            }
        }

        result = ma_quick_build(inputs)

        # 验证协同效应分析
        assert result["synergies"] is not None
        assert result["synergies"]["total_synergies_pv"] > 0

        # 验证协同效应覆盖率
        assert result["synergy_coverage"] is not None
        assert result["synergy_coverage"]["coverage_ratio"] > 0

        # 验证有无协同的增厚/稀释对比
        assert result["accretion_dilution"]["with_synergies"] is not None
        eps_with_syn = result["accretion_dilution"]["with_synergies"]["pro_forma"]["eps"]
        eps_without_syn = result["accretion_dilution"]["without_synergies"]["pro_forma"]["eps"]
        assert eps_with_syn > eps_without_syn

    def test_ma_with_ppa(self):
        """含PPA的M&A分析"""
        inputs = {
            "acquirer": {
                "share_price": 100,
                "shares_outstanding": 1_000_000_000,
                "net_income": 50_000_000_000,
                "total_assets": 500_000_000_000,
                "total_liabilities": 200_000_000_000,
                "total_equity": 300_000_000_000,
                "cash": 100_000_000_000,
                "goodwill": 10_000_000_000
            },
            "target": {
                "share_price": 50,
                "shares_outstanding": 200_000_000,
                "net_income": 2_000_000_000,
                "total_assets": 30_000_000_000,
                "total_liabilities": 10_000_000_000,
                "total_equity": 20_000_000_000,
                "cash": 5_000_000_000,
                "goodwill": 0
            },
            "deal_terms": {
                "premium_percent": 0.30,
                "cash_percent": 0.60,
                "stock_percent": 0.40
            },
            "ppa": {
                "intangible_assets": 5_000_000_000,
                "intangible_amortization_years": 10
            }
        }

        result = ma_quick_build(inputs)

        # 验证无形资产摊销
        assert result["intangible_amortization"]["annual_amortization"] == 500_000_000
        assert result["intangible_amortization"]["years"] == 10


class TestEdgeCases:
    """边界情况测试"""

    def test_zero_shares(self):
        """零股数处理"""
        result = calc_funding_mix(
            total_purchase_price=10_000_000_000,
            cash_percent=1.0,
            stock_percent=0,
            acquirer_share_price=0  # 可能导致除零
        )
        assert result["new_shares_issued"] == 0

    def test_funding_auto_debt_fill(self):
        """现金+股票不足100%时自动填补债务"""
        result = calc_funding_mix(
            total_purchase_price=10_000_000_000,
            cash_percent=0.40,
            stock_percent=0.30,  # 总计70%，差30%
            acquirer_share_price=100,
            new_debt=0  # 未指定债务，应自动填补
        )
        # 应自动填补30%的债务（使用近似比较避免浮点误差）
        assert abs(result["new_debt"] - 3_000_000_000) < 1

    def test_zero_purchase_price(self):
        """零收购价"""
        result = calc_offer_price(
            target_share_price=0,
            target_shares=100_000_000,
            premium_percent=0.30
        )
        assert result["total_purchase_price"] == 0

    def test_negative_net_income(self):
        """目标公司亏损"""
        result = calc_accretion_dilution(
            acquirer_net_income=10_000_000_000,
            acquirer_shares=1_000_000_000,
            target_net_income=-500_000_000,  # 亏损
            purchase_price=5_000_000_000,
            cash_percent=0.50,
            stock_percent=0.50,
            acquirer_share_price=100
        )

        # 亏损公司拖累合并利润
        assert result["pro_forma"]["combined_net_income"] < result["standalone"]["net_income"]

    def test_large_premium(self):
        """超高溢价（100%）"""
        result = calc_offer_price(
            target_share_price=50,
            target_shares=100_000_000,
            premium_percent=1.0  # 100%溢价
        )

        assert result["offer_price_per_share"] == 100.0


class TestConsistency:
    """一致性测试"""

    def test_sources_equals_uses(self):
        """资金来源=资金用途"""
        result = calc_funding_mix(
            total_purchase_price=10_000_000_000,
            cash_percent=0.50,
            stock_percent=0.30,
            acquirer_share_price=100,
            new_debt=2_000_000_000
        )

        total_sources = result["cash_amount"] + result["stock_amount"] + result["new_debt"]
        assert total_sources == 10_000_000_000

    def test_eps_calculation_consistency(self):
        """EPS计算一致性"""
        result = calc_accretion_dilution(
            acquirer_net_income=10_000_000_000,
            acquirer_shares=1_000_000_000,
            target_net_income=1_000_000_000,
            purchase_price=5_000_000_000,
            cash_percent=0.50,
            stock_percent=0.50,
            acquirer_share_price=100
        )

        # 验证EPS计算
        standalone_eps = result["standalone"]["net_income"] / result["standalone"]["shares"]
        assert abs(result["standalone"]["eps"] - standalone_eps) < 0.01

        pro_forma_eps = result["pro_forma"]["combined_net_income"] / result["pro_forma"]["combined_shares"]
        assert abs(result["pro_forma"]["eps"] - pro_forma_eps) < 0.01


class TestTracability:
    """追溯性测试"""

    def test_source_tracking(self):
        """来源追踪"""
        result = calc_offer_price(50, 100_000_000, 0.30, source="llm_override")
        assert result["source"] == "llm_override"

    def test_formula_documentation(self):
        """公式文档"""
        result = calc_goodwill(15_000_000_000, 10_000_000_000)
        assert "formula" in result
        assert "Goodwill" in result["formula"]

    def test_inputs_preserved(self):
        """输入参数保留"""
        result = calc_synergies(
            cost_synergies=[1_000_000_000, 1_200_000_000],
            revenue_synergies=[500_000_000, 600_000_000],
            discount_rate=0.12,
            years=2
        )

        # 列表输入会被保留
        assert result["inputs"]["cost_synergies"] == [1_000_000_000, 1_200_000_000]
        assert result["inputs"]["revenue_synergies"] == [500_000_000, 600_000_000]
        assert result["inputs"]["discount_rate"] == 0.12


# ============================================
# MAModel 类测试
# ============================================

from financial_model.models.ma import MAModel


class TestMAModelClass:
    """MAModel类测试"""

    @pytest.fixture
    def ma_model(self):
        return MAModel()

    @pytest.fixture
    def base_inputs(self):
        return {
            "acquirer": {
                "share_price": 100,
                "shares_outstanding": 1_000_000_000,
                "net_income": 50_000_000_000,
                "total_assets": 500_000_000_000,
                "total_liabilities": 200_000_000_000,
                "total_equity": 300_000_000_000,
                "cash": 100_000_000_000,
                "goodwill": 10_000_000_000
            },
            "target": {
                "share_price": 50,
                "shares_outstanding": 200_000_000,
                "net_income": 2_000_000_000,
                "total_assets": 30_000_000_000,
                "total_liabilities": 10_000_000_000,
                "total_equity": 20_000_000_000,
                "cash": 5_000_000_000,
                "goodwill": 0
            },
            "deal_terms": {
                "premium_percent": 0.30,
                "cash_percent": 0.60,
                "stock_percent": 0.40
            }
        }

    def test_model_init(self, ma_model):
        """模型初始化"""
        assert ma_model.name == "M&A模型"

    def test_calc_offer_price_method(self, ma_model):
        """calc_offer_price方法"""
        result = ma_model.calc_offer_price(
            target_share_price=50,
            target_shares=200_000_000,
            premium_percent=0.30
        )
        assert result.value == 13_000_000_000

    def test_calc_funding_mix_method(self, ma_model):
        """calc_funding_mix方法"""
        result = ma_model.calc_funding_mix(
            total_purchase_price=10_000_000_000,
            cash_percent=0.60,
            stock_percent=0.40,
            acquirer_share_price=100
        )
        assert result.value == 40_000_000  # new_shares_issued

    def test_calc_goodwill_method(self, ma_model):
        """calc_goodwill方法"""
        result = ma_model.calc_goodwill(
            purchase_price=15_000_000_000,
            target_book_value=10_000_000_000
        )
        assert result.value == 5_000_000_000

    def test_analyze_accretion_dilution_method(self, ma_model):
        """analyze_accretion_dilution方法"""
        result = ma_model.analyze_accretion_dilution(
            acquirer_net_income=50_000_000_000,
            acquirer_shares=1_000_000_000,
            target_net_income=2_000_000_000,
            purchase_price=13_000_000_000,
            cash_percent=0.60,
            stock_percent=0.40,
            acquirer_share_price=100
        )
        assert result.value < 0  # 稀释

    def test_analyze_synergies_method(self, ma_model):
        """analyze_synergies方法"""
        result = ma_model.analyze_synergies(
            cost_synergies=1_000_000_000,
            revenue_synergies=500_000_000,
            years=5,
            discount_rate=0.10
        )
        assert result.value > 0

    def test_calc_breakeven_synergies_method(self, ma_model):
        """calc_breakeven_synergies方法"""
        result = ma_model.calc_breakeven_synergies(
            acquirer_net_income=50_000_000_000,
            acquirer_shares=1_000_000_000,
            target_net_income=2_000_000_000,
            purchase_price=13_000_000_000,
            cash_percent=0.60,
            stock_percent=0.40,
            acquirer_share_price=100
        )
        assert result.value > 0

    def test_build_method(self, ma_model, base_inputs):
        """build方法"""
        result = ma_model.build(base_inputs)
        assert result["_meta"]["model_type"] == "ma"
        assert result["_meta"]["model_name"] == "M&A模型"
        assert "deal_summary" in result
        assert "accretion_dilution" in result

    def test_sensitivity_payment_mix(self, ma_model, base_inputs):
        """支付方式敏感性分析"""
        result = ma_model.sensitivity_payment_mix(
            base_inputs,
            cash_range=[0.0, 0.50, 1.0]
        )
        assert "data" in result
        assert len(result["data"]) == 3

    def test_sensitivity_premium(self, ma_model, base_inputs):
        """溢价敏感性分析"""
        result = ma_model.sensitivity_premium(
            base_inputs,
            premium_range=[0.20, 0.30, 0.40]
        )
        assert "data" in result
        assert len(result["data"]) == 3

    def test_to_excel(self, ma_model, base_inputs, tmp_path):
        """Excel导出"""
        # 添加协同效应
        base_inputs["synergies"] = {
            "cost_synergies": 500_000_000,
            "revenue_synergies": 200_000_000
        }

        result = ma_model.build(base_inputs)
        filepath = str(tmp_path / "ma_test.xlsx")
        output = ma_model.to_excel(result, filepath)

        assert output == filepath
        import os
        assert os.path.exists(filepath)
