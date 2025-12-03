# -*- coding: utf-8 -*-
"""
单元格位置追踪器

记录变量写入的单元格位置，供公式引用
"""

from typing import Dict, Optional
from openpyxl.utils import get_column_letter


class CellTracker:
    """
    单元格位置追踪器

    记录变量名 → 单元格地址的映射，用于生成公式时引用

    使用方法:
        tracker = CellTracker()

        # 写入时记录位置
        tracker.set("growth_rate", row=2, col=3)      # C2
        tracker.set("last_revenue", row=3, col=2)     # B3

        # 生成公式时获取引用
        tracker.get("growth_rate")                    # 返回 "C2"
        tracker.get("growth_rate", absolute=True)     # 返回 "$C$2"
        tracker.get("growth_rate", abs_col=True)      # 返回 "$C2"
    """

    def __init__(self):
        self.cell_map: Dict[str, str] = {}

    def set(self, name: str, row: int, col: int) -> str:
        """
        记录变量的单元格位置

        Args:
            name: 变量名
            row: 行号 (1-based)
            col: 列号 (1-based)

        Returns:
            单元格地址 (如 "C2")
        """
        cell_addr = f"{get_column_letter(col)}{row}"
        self.cell_map[name] = cell_addr
        return cell_addr

    def set_addr(self, name: str, addr: str) -> str:
        """
        直接用地址字符串记录位置

        Args:
            name: 变量名
            addr: 单元格地址 (如 "C2")

        Returns:
            单元格地址
        """
        self.cell_map[name] = addr
        return addr

    def get(self, name: str,
            absolute: bool = False,
            abs_row: bool = False,
            abs_col: bool = False) -> Optional[str]:
        """
        获取变量的单元格引用

        Args:
            name: 变量名
            absolute: 完全绝对引用 ($C$2)
            abs_row: 行绝对引用 (C$2)
            abs_col: 列绝对引用 ($C2)

        Returns:
            单元格引用字符串，变量不存在返回 None
        """
        cell = self.cell_map.get(name)
        if not cell:
            return None

        col_letter = ''.join(c for c in cell if c.isalpha())
        row_num = ''.join(c for c in cell if c.isdigit())

        if absolute:
            return f"${col_letter}${row_num}"
        elif abs_row:
            return f"{col_letter}${row_num}"
        elif abs_col:
            return f"${col_letter}{row_num}"
        else:
            return cell

    def get_or_value(self, name: str, value: float, absolute: bool = False) -> str:
        """
        获取单元格引用，如果不存在则返回值本身

        用于公式中某些值可能是常量而非单元格引用的情况

        Args:
            name: 变量名
            value: 如果变量不存在，使用的默认值
            absolute: 是否使用绝对引用

        Returns:
            单元格引用或值字符串
        """
        ref = self.get(name, absolute=absolute)
        if ref:
            return ref
        return str(value)

    def has(self, name: str) -> bool:
        """检查变量是否已记录"""
        return name in self.cell_map

    def clear(self):
        """清空所有记录"""
        self.cell_map.clear()

    def get_all(self) -> Dict[str, str]:
        """获取所有映射"""
        return self.cell_map.copy()

    def __contains__(self, name: str) -> bool:
        return name in self.cell_map

    def __repr__(self):
        return f"CellTracker({self.cell_map})"
