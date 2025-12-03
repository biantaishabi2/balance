# -*- coding: utf-8 -*-
"""
Excel 公式构建器

根据 Python 计算逻辑生成对应的 Excel 公式
"""

from typing import List, Set
from .cell_tracker import CellTracker


class FormulaBuilder:
    """
    Excel 公式构建器

    根据变量名和单元格位置，生成 Excel 公式

    使用方法:
        tracker = CellTracker()
        tracker.set("last_revenue", 3, 2)  # B3
        tracker.set("growth_rate", 2, 3)   # C2

        builder = FormulaBuilder(tracker)
        builder.register_param("growth_rate")  # 参数用绝对引用

        # 生成公式
        f = builder.growth("last_revenue", "growth_rate")
        # 返回: "=B3*(1+$C$2)"
    """

    def __init__(self, tracker: CellTracker, param_absolute: bool = True):
        """
        Args:
            tracker: 单元格追踪器
            param_absolute: 参数类变量是否使用绝对引用（默认是）
        """
        self.tracker = tracker
        self.param_absolute = param_absolute

        # 哪些变量是参数（应该用绝对引用）
        self.params: Set[str] = set()

    def register_param(self, *names):
        """
        注册参数变量（这些变量在公式中使用绝对引用）

        Args:
            *names: 参数名称列表
        """
        self.params.update(names)

    def unregister_param(self, *names):
        """取消注册参数"""
        self.params.difference_update(names)

    def clear_params(self):
        """清空所有参数"""
        self.params.clear()

    def ref(self, name: str, force_absolute: bool = None) -> str:
        """
        获取变量的单元格引用

        参数类变量自动使用绝对引用

        Args:
            name: 变量名
            force_absolute: 强制使用绝对引用（覆盖默认行为）

        Returns:
            单元格引用字符串，如果变量不存在返回变量名本身
        """
        # 判断是否使用绝对引用
        if force_absolute is not None:
            use_absolute = force_absolute
        else:
            is_param = name in self.params
            use_absolute = self.param_absolute and is_param

        ref = self.tracker.get(name, absolute=use_absolute)
        return ref if ref else name

    def ref_or_value(self, name_or_value, force_absolute: bool = None) -> str:
        """
        获取引用或直接返回值

        如果是字符串且在 tracker 中，返回引用
        否则返回值本身（数字或字符串）
        """
        if isinstance(name_or_value, str):
            if self.tracker.has(name_or_value):
                return self.ref(name_or_value, force_absolute)
            # 可能是表达式如 "1+growth_rate"
            return name_or_value
        else:
            # 数字
            return str(name_or_value)

    # ==================== 基础公式 ====================

    def add(self, *terms) -> str:
        """
        加法: =A1+B1+C1

        Args:
            *terms: 变量名或数值

        Returns:
            Excel 公式字符串
        """
        refs = [self.ref_or_value(t) for t in terms]
        return "=" + "+".join(refs)

    def subtract(self, a, b) -> str:
        """
        减法: =A1-B1

        Args:
            a: 被减数（变量名或数值）
            b: 减数（变量名或数值）

        Returns:
            Excel 公式字符串
        """
        return f"={self.ref_or_value(a)}-{self.ref_or_value(b)}"

    def multiply(self, a, b) -> str:
        """
        乘法: =A1*B1

        Args:
            a: 乘数（变量名或数值）
            b: 乘数（变量名或数值）

        Returns:
            Excel 公式字符串
        """
        return f"={self.ref_or_value(a)}*{self.ref_or_value(b)}"

    def divide(self, a, b) -> str:
        """
        除法: =A1/B1

        Args:
            a: 被除数（变量名或数值）
            b: 除数（变量名或数值）

        Returns:
            Excel 公式字符串
        """
        return f"={self.ref_or_value(a)}/{self.ref_or_value(b)}"

    # ==================== 财务模型常用公式 ====================

    def growth(self, base: str, rate: str) -> str:
        """
        增长公式: base × (1 + rate)

        用于: 收入 = 上期收入 × (1 + 增长率)

        Args:
            base: 基数变量名
            rate: 增长率变量名

        Returns:
            Excel 公式，如 "=B3*(1+$C$2)"
        """
        return f"={self.ref(base)}*(1+{self.ref(rate)})"

    def margin(self, total: str, rate: str) -> str:
        """
        扣减比率公式: total × (1 - rate)

        用于: 成本 = 收入 × (1 - 毛利率)

        Args:
            total: 总额变量名
            rate: 比率变量名

        Returns:
            Excel 公式，如 "=B4*(1-$C$3)"
        """
        return f"={self.ref(total)}*(1-{self.ref(rate)})"

    def ratio(self, total: str, rate: str) -> str:
        """
        比率公式: total × rate

        用于: 费用 = 收入 × 费用率

        Args:
            total: 总额变量名
            rate: 比率变量名

        Returns:
            Excel 公式，如 "=B4*$C$4"
        """
        return f"={self.ref(total)}*{self.ref(rate)}"

    def turnover_days(self, base: str, days: str, days_in_year: int = 365) -> str:
        """
        周转天数公式: base / days_in_year × days

        用于: 应收账款 = 收入 / 365 × 应收周转天数

        Args:
            base: 基数变量名（收入或成本）
            days: 周转天数变量名
            days_in_year: 一年天数（默认365）

        Returns:
            Excel 公式，如 "=B4/365*$C$5"
        """
        return f"={self.ref(base)}/{days_in_year}*{self.ref(days)}"

    def tax(self, ebt: str, rate: str) -> str:
        """
        所得税公式: MAX(ebt, 0) × rate

        用于: 所得税 = MAX(税前利润, 0) × 税率

        Args:
            ebt: 税前利润变量名
            rate: 税率变量名

        Returns:
            Excel 公式，如 "=MAX(B10,0)*$C$6"
        """
        return f"=MAX({self.ref(ebt)},0)*{self.ref(rate)}"

    def depreciation(self, asset: str, years: str) -> str:
        """
        直线折旧: asset / years

        Args:
            asset: 固定资产变量名
            years: 折旧年限变量名

        Returns:
            Excel 公式，如 "=B15/$C$7"
        """
        return f"={self.ref(asset)}/{self.ref(years)}"

    def sum_range(self, start_ref: str, end_ref: str) -> str:
        """
        SUM 公式

        Args:
            start_ref: 起始单元格引用
            end_ref: 结束单元格引用

        Returns:
            Excel 公式，如 "=SUM(B2:B10)"
        """
        return f"=SUM({start_ref}:{end_ref})"

    def sum_cells(self, *cells) -> str:
        """
        SUM 多个单元格

        Args:
            *cells: 变量名列表

        Returns:
            Excel 公式，如 "=SUM(B2,B5,B8)"
        """
        refs = [self.ref(c) for c in cells]
        return f"=SUM({','.join(refs)})"

    def max_zero(self, value: str) -> str:
        """
        MAX(value, 0) - 取正值

        Args:
            value: 变量名

        Returns:
            Excel 公式，如 "=MAX(B10,0)"
        """
        return f"=MAX({self.ref(value)},0)"

    def if_positive(self, condition: str, if_true: str, if_false: str = "0") -> str:
        """
        IF 条件公式

        Args:
            condition: 条件表达式
            if_true: 为真时的值/公式
            if_false: 为假时的值/公式

        Returns:
            Excel 公式
        """
        return f"=IF({condition},{if_true},{if_false})"

    def npv(self, rate: str, first_cf: str, last_cf: str) -> str:
        """
        NPV 公式

        Args:
            rate: 折现率变量名
            first_cf: 第一个现金流单元格
            last_cf: 最后一个现金流单元格

        Returns:
            Excel 公式，如 "=NPV($C$1,B2:B6)"
        """
        rate_ref = self.ref(rate)
        return f"=NPV({rate_ref},{first_cf}:{last_cf})"

    def irr(self, first_cf: str, last_cf: str) -> str:
        """
        IRR 公式

        Args:
            first_cf: 第一个现金流单元格
            last_cf: 最后一个现金流单元格

        Returns:
            Excel 公式，如 "=IRR(B2:B7)"
        """
        return f"=IRR({first_cf}:{last_cf})"

    # ==================== 自定义公式 ====================

    def custom(self, template: str, **kwargs) -> str:
        """
        自定义公式模板

        用法:
            builder.custom("{a}*(1+{b})", a="revenue", b="growth_rate")
            # 返回: "=B3*(1+$C$2)"

        Args:
            template: 公式模板，用 {变量名} 作为占位符
            **kwargs: 变量名映射

        Returns:
            Excel 公式字符串
        """
        refs = {k: self.ref(v) for k, v in kwargs.items()}
        return "=" + template.format(**refs)

    def raw(self, formula: str) -> str:
        """
        原始公式（不做任何处理）

        Args:
            formula: 完整的 Excel 公式（不含等号）

        Returns:
            Excel 公式字符串（加上等号）
        """
        if formula.startswith("="):
            return formula
        return "=" + formula
