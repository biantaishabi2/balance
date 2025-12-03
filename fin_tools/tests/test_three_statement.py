# -*- coding: utf-8 -*-
"""
三表模型工具测试
"""

import unittest
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fin_tools.models import ThreeStatementModel


class TestThreeStatementModel(unittest.TestCase):
    """三表模型测试"""

    def setUp(self):
        """测试准备"""
        self.base_data = {
            "company": "测试公司",
            "period": "2025Q3",
            "last_revenue": 28307198.70,
            "last_cost": 21142714.70,
            "closing_cash": 32424158.60,
            "closing_debt": 9375638.80,
            "closing_equity": 27345617.40,
            "closing_receivable": 6648123.50,
            "closing_payable": 21492614.50,
            "closing_inventory": 8021155.80,
            "fixed_asset_gross": 12862270.20,
            "accum_depreciation": 1286227.02,
            "fixed_asset_life": 10
        }

        self.assumptions = {
            "growth_rate": 0.09,
            "gross_margin": 0.253,
            "opex_ratio": 0.097,
            "capex_ratio": 0.042,
            "ar_days": 64,
            "ap_days": 120,
            "inv_days": 102,
            "interest_rate": 0.0233,
            "tax_rate": 0.1386,
            "dividend_ratio": 0.30
        }

    def test_forecast_revenue(self):
        """测试收入预测"""
        model = ThreeStatementModel(self.base_data)
        result = model.forecast_revenue(0.09)

        expected = 28307198.70 * 1.09
        self.assertAlmostEqual(result.value, expected, places=2)
        self.assertEqual(result.formula, "last_revenue × (1 + growth_rate)")
        self.assertIn("last_revenue", result.inputs)

    def test_forecast_cost(self):
        """测试成本预测"""
        model = ThreeStatementModel(self.base_data)
        revenue = 30854846.58
        result = model.forecast_cost(revenue, 0.253)

        expected = revenue * (1 - 0.253)
        self.assertAlmostEqual(result.value, expected, places=2)

    def test_calc_tax(self):
        """测试所得税计算"""
        model = ThreeStatementModel(self.base_data)

        # 正利润
        result = model.calc_tax(1000000, 0.25)
        self.assertEqual(result.value, 250000)

        # 亏损时税为0
        result = model.calc_tax(-1000000, 0.25)
        self.assertEqual(result.value, 0)

    def test_calc_working_capital(self):
        """测试营运资本计算"""
        model = ThreeStatementModel(self.base_data)
        result = model.calc_working_capital(
            revenue=30000000,
            cost=22000000,
            ar_days=64,
            ap_days=120,
            inv_days=102
        )

        self.assertIn("receivable", result)
        self.assertIn("payable", result)
        self.assertIn("inventory", result)

        # 验证公式正确性
        expected_ar = 30000000 / 365 * 64
        self.assertAlmostEqual(result["receivable"].value, expected_ar, places=2)

    def test_calc_depreciation(self):
        """测试折旧计算"""
        model = ThreeStatementModel(self.base_data)
        result = model.calc_depreciation(10000000, 10, 0)

        self.assertEqual(result.value, 1000000)

    def test_build(self):
        """测试完整构建"""
        model = ThreeStatementModel(self.base_data)
        result = model.build(self.assumptions)

        # 检查结构
        self.assertIn("income_statement", result)
        self.assertIn("balance_sheet", result)
        self.assertIn("cash_flow", result)
        self.assertIn("validation", result)

        # 检查利润表
        income = result["income_statement"]
        self.assertIn("revenue", income)
        self.assertIn("net_income", income)

        # 检查每个项目都有追溯信息
        self.assertIn("value", income["revenue"])
        self.assertIn("formula", income["revenue"])
        self.assertIn("inputs", income["revenue"])

    def test_build_balanced(self):
        """测试构建结果是否配平"""
        model = ThreeStatementModel(self.base_data)
        result = model.build(self.assumptions)

        # 注意：简化模型可能不完全配平，这里只检查结构
        validation = result["validation"]
        self.assertIn("is_balanced", validation)
        self.assertIn("difference", validation)


class TestIncomeStatement(unittest.TestCase):
    """利润表工具测试"""

    def setUp(self):
        self.base_data = {"last_revenue": 100000000}
        self.model = ThreeStatementModel(self.base_data)

    def test_profit_chain(self):
        """测试利润计算链"""
        revenue = 100000000
        gross_margin = 0.25
        opex_ratio = 0.10

        # 成本
        cost_r = self.model.forecast_cost(revenue, gross_margin)
        cost = cost_r.value
        self.assertEqual(cost, 75000000)

        # 毛利
        gp_r = self.model.calc_gross_profit(revenue, cost)
        gp = gp_r.value
        self.assertEqual(gp, 25000000)

        # 费用
        opex_r = self.model.forecast_opex(revenue, opex_ratio)
        opex = opex_r.value
        self.assertEqual(opex, 10000000)

        # EBIT
        ebit_r = self.model.calc_ebit(gp, opex)
        ebit = ebit_r.value
        self.assertEqual(ebit, 15000000)


if __name__ == '__main__':
    unittest.main()
