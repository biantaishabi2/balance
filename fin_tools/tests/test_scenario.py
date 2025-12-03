# -*- coding: utf-8 -*-
"""
场景管理器测试
"""

import unittest
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fin_tools.models import ScenarioManager


class TestScenarioManager(unittest.TestCase):
    """场景管理器测试"""

    def setUp(self):
        """测试准备"""
        self.base_data = {
            "company": "测试公司",
            "period": "2025Q3",
            "last_revenue": 100000000,
            "last_cost": 75000000,
            "closing_cash": 10000000,
            "closing_debt": 5000000,
            "closing_equity": 20000000,
            "closing_receivable": 8000000,
            "closing_payable": 6000000,
            "closing_inventory": 5000000,
            "fixed_asset_gross": 15000000,
            "accum_depreciation": 3000000,
            "fixed_asset_life": 10
        }

        self.base_assumptions = {
            "growth_rate": 0.10,
            "gross_margin": 0.25,
            "opex_ratio": 0.10,
            "capex_ratio": 0.05,
            "ar_days": 30,
            "ap_days": 30,
            "inv_days": 25,
            "interest_rate": 0.05,
            "tax_rate": 0.25,
            "dividend_ratio": 0.30
        }

        self.bull_assumptions = self.base_assumptions.copy()
        self.bull_assumptions["growth_rate"] = 0.15
        self.bull_assumptions["gross_margin"] = 0.30

        self.bear_assumptions = self.base_assumptions.copy()
        self.bear_assumptions["growth_rate"] = 0.05
        self.bear_assumptions["gross_margin"] = 0.20

    def test_add_scenario(self):
        """测试添加场景"""
        sm = ScenarioManager(self.base_data)
        sm.add_scenario("base_case", self.base_assumptions, "基准情景")

        scenario = sm.get_scenario("base_case")
        self.assertIsNotNone(scenario)
        self.assertEqual(scenario["name"], "base_case")
        self.assertEqual(scenario["description"], "基准情景")

    def test_run_scenario(self):
        """测试运行单个场景"""
        sm = ScenarioManager(self.base_data)
        sm.add_scenario("base_case", self.base_assumptions)

        result = sm.run_scenario("base_case")

        # 检查结果结构
        self.assertIn("income_statement", result)
        self.assertIn("balance_sheet", result)
        self.assertIn("_scenario", result)

        # 检查收入计算
        expected_revenue = self.base_data["last_revenue"] * 1.10
        actual_revenue = result["income_statement"]["revenue"]["value"]
        self.assertAlmostEqual(actual_revenue, expected_revenue, places=0)

    def test_run_scenario_cache(self):
        """测试场景结果缓存"""
        sm = ScenarioManager(self.base_data)
        sm.add_scenario("base_case", self.base_assumptions)

        # 第一次运行
        result1 = sm.run_scenario("base_case")

        # 第二次运行应该使用缓存
        result2 = sm.run_scenario("base_case", use_cache=True)

        self.assertIs(result1, result2)

    def test_update_assumption(self):
        """测试更新假设后清除缓存"""
        sm = ScenarioManager(self.base_data)
        sm.add_scenario("base_case", self.base_assumptions)

        # 运行一次以创建缓存
        sm.run_scenario("base_case")
        self.assertIn("base_case", sm.results)

        # 更新假设
        sm.update_assumption("base_case", "growth_rate", 0.20)

        # 缓存应被清除
        self.assertNotIn("base_case", sm.results)

        # 新假设应该生效
        scenario = sm.get_scenario("base_case")
        self.assertEqual(scenario["assumptions"]["growth_rate"], 0.20)

    def test_compare_scenarios(self):
        """测试场景对比"""
        sm = ScenarioManager(self.base_data)
        sm.add_scenario("base_case", self.base_assumptions, "基准")
        sm.add_scenario("bull_case", self.bull_assumptions, "乐观")
        sm.add_scenario("bear_case", self.bear_assumptions, "悲观")

        comparison = sm.compare_scenarios()

        # 检查结构
        self.assertIn("headers", comparison)
        self.assertIn("rows", comparison)

        # 检查有所有场景
        headers = comparison["headers"]
        self.assertIn("base_case", headers)
        self.assertIn("bull_case", headers)
        self.assertIn("bear_case", headers)

        # 检查排序验证
        self.assertIn("validation", comparison)
        self.assertTrue(comparison["validation"]["is_valid"])

    def test_sensitivity_1d(self):
        """测试单参数敏感性分析"""
        sm = ScenarioManager(self.base_data)
        sm.add_scenario("base_case", self.base_assumptions)

        result = sm.sensitivity_1d(
            param="growth_rate",
            values=[0.05, 0.10, 0.15, 0.20],
            output_metric="net_income"
        )

        # 检查结构
        self.assertEqual(result["param"], "growth_rate")
        self.assertEqual(len(result["data"]), 4)

        # 净利润应随增长率增加
        values = [row["net_income"] for row in result["data"]]
        self.assertEqual(values, sorted(values))

    def test_sensitivity_2d(self):
        """测试双参数敏感性分析"""
        sm = ScenarioManager(self.base_data)
        sm.add_scenario("base_case", self.base_assumptions)

        result = sm.sensitivity_2d(
            param1="growth_rate",
            values1=[0.05, 0.10, 0.15],
            param2="gross_margin",
            values2=[0.20, 0.25, 0.30],
            output_metric="net_income"
        )

        # 检查结构
        self.assertEqual(result["headers"]["rows"], "growth_rate")
        self.assertEqual(result["headers"]["columns"], "gross_margin")
        self.assertEqual(len(result["data"]), 3)  # 3行

    def test_nonexistent_scenario(self):
        """测试运行不存在的场景"""
        sm = ScenarioManager(self.base_data)

        with self.assertRaises(ValueError):
            sm.run_scenario("nonexistent")


if __name__ == '__main__':
    unittest.main()
