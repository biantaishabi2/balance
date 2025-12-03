# -*- coding: utf-8 -*-
"""
财务模型单元格 - 带完整追溯信息

每个计算结果不只存值，还存这个值是怎么来的
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class ModelResult:
    """
    模型计算结果（带追溯）

    用于工具函数的返回值，记录计算过程
    """
    value: float                              # 计算值
    formula: str                              # 公式（人类可读）
    inputs: Dict[str, float] = field(default_factory=dict)  # 依赖的输入值

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于JSON序列化）"""
        return {
            "value": self.value,
            "formula": self.formula,
            "inputs": self.inputs
        }


@dataclass
class ModelCell:
    """
    财务模型单元格 - 带完整追溯信息

    不只存值，还存这个值是怎么来的，支持完整的依赖链追溯
    """
    name: str                                 # 字段名
    value: float                              # 计算值
    formula: str                              # 公式（人类可读）
    formula_code: str = ""                    # 公式代码（可执行）
    inputs: Dict[str, float] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    source: str = ""                          # 数据来源
    unit: str = "万元"                        # 单位
    note: Optional[str] = None                # 备注

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于JSON序列化）"""
        result = {
            "value": self.value,
            "formula": self.formula,
            "inputs": self.inputs,
        }
        if self.dependencies:
            result["dependencies"] = self.dependencies
        if self.source:
            result["source"] = self.source
        if self.note:
            result["note"] = self.note
        return result

    def explain(self) -> str:
        """生成人类可读的解释"""
        lines = [
            f"【{self.name}】",
            f"  值: {self.value:,.2f} {self.unit}",
            f"  公式: {self.formula}",
        ]

        if self.inputs:
            lines.append("  计算过程:")
            for key, val in self.inputs.items():
                if isinstance(val, float):
                    lines.append(f"    {key} = {val:,.2f}")
                else:
                    lines.append(f"    {key} = {val}")

        if self.source:
            lines.append(f"  来源: {self.source}")

        if self.dependencies:
            lines.append(f"  依赖: {' → '.join(self.dependencies)}")

        return "\n".join(lines)

    @classmethod
    def from_result(cls, name: str, result: ModelResult,
                    source: str = "", unit: str = "万元") -> 'ModelCell':
        """从 ModelResult 创建 ModelCell"""
        return cls(
            name=name,
            value=result.value,
            formula=result.formula,
            inputs=result.inputs,
            source=source,
            unit=unit
        )
