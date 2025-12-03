# -*- coding: utf-8 -*-
"""
核心模块测试
"""

import unittest
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fin_tools.core import ModelCell, ModelResult, FinancialModel


class TestModelResult(unittest.TestCase):
    """ModelResult 测试"""

    def test_create(self):
        """测试创建 ModelResult"""
        result = ModelResult(
            value=100.0,
            formula="a + b",
            inputs={"a": 60.0, "b": 40.0}
        )
        self.assertEqual(result.value, 100.0)
        self.assertEqual(result.formula, "a + b")
        self.assertEqual(result.inputs["a"], 60.0)

    def test_to_dict(self):
        """测试转换为字典"""
        result = ModelResult(
            value=100.0,
            formula="a + b",
            inputs={"a": 60.0, "b": 40.0}
        )
        d = result.to_dict()
        self.assertEqual(d["value"], 100.0)
        self.assertEqual(d["formula"], "a + b")


class TestModelCell(unittest.TestCase):
    """ModelCell 测试"""

    def test_create(self):
        """测试创建 ModelCell"""
        cell = ModelCell(
            name="revenue",
            value=30000000.0,
            formula="last_revenue × (1 + growth_rate)",
            inputs={"last_revenue": 28000000.0, "growth_rate": 0.09}
        )
        self.assertEqual(cell.name, "revenue")
        self.assertEqual(cell.value, 30000000.0)

    def test_explain(self):
        """测试解释功能"""
        cell = ModelCell(
            name="revenue",
            value=30000000.0,
            formula="last_revenue × (1 + growth_rate)",
            inputs={"last_revenue": 28000000.0, "growth_rate": 0.09},
            source="forecast"
        )
        explanation = cell.explain()
        self.assertIn("revenue", explanation)
        self.assertIn("last_revenue", explanation)

    def test_from_result(self):
        """测试从 ModelResult 创建"""
        result = ModelResult(
            value=100.0,
            formula="a + b",
            inputs={"a": 60.0, "b": 40.0}
        )
        cell = ModelCell.from_result("test", result, source="test")
        self.assertEqual(cell.name, "test")
        self.assertEqual(cell.value, 100.0)


class TestFinancialModel(unittest.TestCase):
    """FinancialModel 测试"""

    def test_create(self):
        """测试创建模型"""
        model = FinancialModel(name="测试模型", scenario="base_case")
        self.assertEqual(model.name, "测试模型")
        self.assertEqual(model.scenario, "base_case")

    def test_assumptions(self):
        """测试假设管理"""
        model = FinancialModel(name="测试模型")
        model.set_assumption("growth_rate", 0.09, label="增长率")

        value = model.get_assumption("growth_rate")
        self.assertEqual(value, 0.09)

    def test_cells(self):
        """测试单元格管理"""
        model = FinancialModel(name="测试模型")
        cell = ModelCell(
            name="revenue",
            value=30000000.0,
            formula="test"
        )
        model.add_cell(cell)

        retrieved = model.get_cell("revenue")
        self.assertEqual(retrieved.value, 30000000.0)

    def test_to_json(self):
        """测试JSON导出"""
        model = FinancialModel(name="测试模型")
        model.set_assumption("growth_rate", 0.09)

        json_str = model.to_json()
        self.assertIn("测试模型", json_str)
        self.assertIn("growth_rate", json_str)


if __name__ == '__main__':
    unittest.main()
