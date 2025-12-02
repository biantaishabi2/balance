# -*- coding: utf-8 -*-
"""
DCF估值工具测试
"""

import unittest
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from financial_model.models import DCFModel


class TestDCFModel(unittest.TestCase):
    """DCF模型测试"""

    def setUp(self):
        """测试准备"""
        self.dcf = DCFModel()

    def test_calc_capm(self):
        """测试CAPM计算"""
        result = self.dcf.calc_capm(
            risk_free_rate=0.03,
            beta=1.2,
            market_risk_premium=0.05
        )

        expected = 0.03 + 1.2 * 0.05
        self.assertAlmostEqual(result.value, expected, places=4)
        self.assertEqual(result.formula, "Rf + β × MRP")

    def test_calc_wacc(self):
        """测试WACC计算"""
        result = self.dcf.calc_wacc(
            cost_of_equity=0.09,
            cost_of_debt=0.04,
            tax_rate=0.25,
            debt_ratio=0.30
        )

        # WACC = 0.7 * 0.09 + 0.3 * 0.04 * 0.75 = 0.063 + 0.009 = 0.072
        expected = 0.7 * 0.09 + 0.3 * 0.04 * 0.75
        self.assertAlmostEqual(result.value, expected, places=4)

    def test_calc_terminal_value_perpetual(self):
        """测试永续增长终值"""
        result = self.dcf.calc_terminal_value_perpetual(
            final_fcf=1000000,
            wacc=0.10,
            terminal_growth=0.02
        )

        # TV = 1000000 * 1.02 / (0.10 - 0.02) = 12750000
        expected = 1000000 * 1.02 / 0.08
        self.assertAlmostEqual(result.value, expected, places=2)

    def test_calc_terminal_value_error(self):
        """测试永续增长率超过WACC时报错"""
        with self.assertRaises(ValueError):
            self.dcf.calc_terminal_value_perpetual(
                final_fcf=1000000,
                wacc=0.05,
                terminal_growth=0.06  # 大于WACC
            )

    def test_calc_fcff(self):
        """测试FCFF计算"""
        result = self.dcf.calc_fcff(
            ebit=10000000,
            tax_rate=0.25,
            depreciation=1000000,
            capex=2000000,
            delta_nwc=500000
        )

        # FCFF = 10000000 * 0.75 + 1000000 - 2000000 - 500000 = 6000000
        expected = 10000000 * 0.75 + 1000000 - 2000000 - 500000
        self.assertEqual(result.value, expected)

    def test_calc_enterprise_value(self):
        """测试企业价值计算"""
        fcf_list = [1000000, 1100000, 1210000]
        wacc = 0.10
        terminal_value = 15000000

        result = self.dcf.calc_enterprise_value(fcf_list, wacc, terminal_value)

        # 检查结构
        self.assertIn("pv_of_fcf", result.inputs)
        self.assertIn("pv_of_terminal", result.inputs)
        self.assertGreater(result.value, 0)

    def test_calc_equity_value(self):
        """测试股权价值计算"""
        result = self.dcf.calc_equity_value(
            enterprise_value=100000000,
            debt=20000000,
            cash=10000000
        )

        # Equity = 100000000 - 20000000 + 10000000 = 90000000
        self.assertEqual(result.value, 90000000)

    def test_calc_per_share_value(self):
        """测试每股价值计算"""
        result = self.dcf.calc_per_share_value(
            equity_value=90000000,
            shares_outstanding=1000000
        )

        self.assertEqual(result.value, 90)

    def test_sensitivity_analysis(self):
        """测试敏感性分析"""
        fcf_list = [1000000, 1100000, 1210000, 1331000, 1464100]
        wacc_range = [0.08, 0.09, 0.10]
        growth_range = [0.01, 0.02, 0.03]

        result = self.dcf.sensitivity_analysis(
            fcf_list=fcf_list,
            wacc_range=wacc_range,
            growth_range=growth_range,
            debt=5000000,
            cash=10000000,
            shares=1000000
        )

        # 检查矩阵结构
        self.assertIn("headers", result)
        self.assertIn("data", result)
        self.assertEqual(len(result["data"]), 3)  # 3行WACC

    def test_valuate(self):
        """测试完整估值"""
        inputs = {
            "fcf_projections": {
                "year_1": 1000000,
                "year_2": 1100000,
                "year_3": 1210000,
                "year_4": 1331000,
                "year_5": 1464100
            },
            "wacc_inputs": {
                "risk_free_rate": 0.03,
                "beta": 1.2,
                "market_risk_premium": 0.05,
                "cost_of_debt": 0.04,
                "tax_rate": 0.25,
                "debt_ratio": 0.30
            },
            "terminal_inputs": {
                "method": "perpetual_growth",
                "terminal_growth": 0.02
            },
            "balance_sheet_adjustments": {
                "cash": 5000000,
                "debt": 3000000,
                "shares_outstanding": 1000000
            }
        }

        result = self.dcf.valuate(inputs)

        # 检查结构
        self.assertIn("cost_of_equity", result)
        self.assertIn("wacc", result)
        self.assertIn("terminal_value", result)
        self.assertIn("enterprise_value", result)
        self.assertIn("equity_value", result)
        self.assertIn("per_share_value", result)

        # 每个都应该有追溯信息
        self.assertIn("value", result["per_share_value"])
        self.assertIn("formula", result["per_share_value"])


if __name__ == '__main__':
    unittest.main()
