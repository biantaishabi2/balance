# -*- coding: utf-8 -*-
"""
财务模型基类

提供模型的基础结构和通用方法
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional

from .cell import ModelCell


class FinancialModel:
    """
    财务模型基类

    提供:
    - 单元格管理
    - 假设参数管理
    - JSON导出
    - 追溯查询
    """

    def __init__(self, name: str, scenario: str = "base_case"):
        """
        初始化模型

        Args:
            name: 模型名称
            scenario: 情景名称
        """
        self.name = name
        self.scenario = scenario
        self.cells: Dict[str, ModelCell] = {}
        self.assumptions: Dict[str, Any] = {}
        self.created_at = datetime.now()

    def set_assumption(self, key: str, value: float,
                       label: str = "", source: str = "用户输入"):
        """
        设置假设参数

        Args:
            key: 参数名
            value: 参数值
            label: 参数标签（中文）
            source: 数据来源
        """
        self.assumptions[key] = {
            "value": value,
            "label": label or key,
            "source": source,
            "editable": True
        }

    def get_assumption(self, key: str) -> Optional[float]:
        """获取假设参数值"""
        if key in self.assumptions:
            return self.assumptions[key]["value"]
        return None

    def add_cell(self, cell: ModelCell):
        """添加计算单元"""
        self.cells[cell.name] = cell

    def get_cell(self, name: str) -> Optional[ModelCell]:
        """获取单元格"""
        return self.cells.get(name)

    def get_value(self, name: str) -> Optional[float]:
        """获取单元格的值"""
        cell = self.get_cell(name)
        return cell.value if cell else None

    def explain(self, cell_name: str) -> str:
        """解释某个单元格的计算过程"""
        cell = self.get_cell(cell_name)
        if cell:
            return cell.explain()
        return f"未找到: {cell_name}"

    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            "_meta": {
                "model_name": self.name,
                "scenario": self.scenario,
                "created_at": self.created_at.isoformat()
            },
            "assumptions": self.assumptions,
            "cells": {
                name: cell.to_dict()
                for name, cell in self.cells.items()
            }
        }

    def to_json(self, indent: int = 2) -> str:
        """导出为JSON字符串"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def summary(self) -> str:
        """生成模型摘要"""
        lines = [
            f"模型: {self.name}",
            f"情景: {self.scenario}",
            f"创建时间: {self.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"",
            f"假设参数: {len(self.assumptions)} 个",
            f"计算单元: {len(self.cells)} 个",
        ]
        return "\n".join(lines)
