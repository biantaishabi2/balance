# Excel 公式生成工具增强设计

## 概述

当前系统输出 Excel 时，单元格写入的是**计算后的值**，公式只作为文字备注显示。本文档描述如何增强为**真正的 Excel 公式输出**，让用户可以在 Excel 中直接修改参数并自动重算。

### 现状 vs 目标

```
【现状】值模式
┌────────┬─────────────┬──────────────────────┐
│  科目  │  金额(万元) │        公式          │
├────────┼─────────────┼──────────────────────┤
│ 增长率 │    9.0%     │ 用户输入             │
│ 上期收入│ 28,307,198 │ 历史数据             │
│ 收入   │ 30,854,846  │ "上期×(1+增长率)"    │  ← 文字描述，不能自动算
└────────┴─────────────┴──────────────────────┘
改了增长率 → 收入不会变，要重新跑 Python


【目标】公式模式
┌────────┬─────────────────────┐
│  科目  │      金额/公式       │
├────────┼─────────────────────┤
│ 增长率 │       0.09          │  ← C2 (可以直接改)
│ 上期收入│   28307198         │  ← B3
│ 收入   │   =B3*(1+$C$2)      │  ← 真正的 Excel 公式
└────────┴─────────────────────┘
改 C2 为 0.15 → 收入自动变成 32,553,278
```

---

## 一、核心组件设计

### 1.1 CellTracker（单元格位置追踪器）

**职责**：记录每个变量写入的单元格位置，供后续公式引用。

```python
# fin_tools/io/cell_tracker.py

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
        """
        ref = self.get(name, absolute=absolute)
        if ref:
            return ref
        return str(value)

    def clear(self):
        """清空所有记录"""
        self.cell_map.clear()

    def get_all(self) -> Dict[str, str]:
        """获取所有映射"""
        return self.cell_map.copy()
```

### 1.2 FormulaBuilder（公式构建器）

**职责**：根据计算逻辑和单元格引用，生成 Excel 公式字符串。

```python
# fin_tools/io/formula_builder.py

from typing import Dict, List, Optional
from .cell_tracker import CellTracker


class FormulaBuilder:
    """
    Excel 公式构建器

    根据 Python 计算逻辑生成对应的 Excel 公式

    使用方法:
        tracker = CellTracker()
        builder = FormulaBuilder(tracker)

        # 简单公式
        f = builder.multiply("last_revenue", "1+growth_rate")
        # 如果 last_revenue=B3, growth_rate=C2
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
        self.params: set = set()

    def register_param(self, *names):
        """注册参数变量（这些变量在公式中使用绝对引用）"""
        self.params.update(names)

    def ref(self, name: str) -> str:
        """
        获取变量的单元格引用

        参数类变量自动使用绝对引用
        """
        is_param = name in self.params
        absolute = self.param_absolute and is_param
        return self.tracker.get(name, absolute=absolute) or name

    # ==================== 基础公式 ====================

    def add(self, *terms) -> str:
        """加法: =A1+B1+C1"""
        refs = [self.ref(t) if isinstance(t, str) and not t.replace('.','').isdigit()
                else str(t) for t in terms]
        return "=" + "+".join(refs)

    def subtract(self, a, b) -> str:
        """减法: =A1-B1"""
        return f"={self.ref(a)}-{self.ref(b)}"

    def multiply(self, a, b) -> str:
        """乘法: =A1*B1"""
        ref_a = self.ref(a) if isinstance(a, str) else str(a)
        ref_b = self.ref(b) if isinstance(b, str) else str(b)
        return f"={ref_a}*{ref_b}"

    def divide(self, a, b) -> str:
        """除法: =A1/B1"""
        return f"={self.ref(a)}/{self.ref(b)}"

    # ==================== 财务模型常用公式 ====================

    def growth(self, base: str, rate: str) -> str:
        """
        增长公式: base × (1 + rate)

        Excel: =B2*(1+$C$1)
        """
        return f"={self.ref(base)}*(1+{self.ref(rate)})"

    def margin(self, total: str, rate: str) -> str:
        """
        比率公式: total × rate

        用于: 成本 = 收入 × (1-毛利率)
        Excel: =B3*(1-$C$2)
        """
        return f"={self.ref(total)}*(1-{self.ref(rate)})"

    def ratio(self, total: str, rate: str) -> str:
        """
        比率公式: total × rate

        用于: 费用 = 收入 × 费用率
        Excel: =B3*$C$3
        """
        return f"={self.ref(total)}*{self.ref(rate)}"

    def turnover_days(self, base: str, days: str, days_in_year: int = 365) -> str:
        """
        周转天数公式: base / days_in_year × days

        用于: 应收账款 = 收入 / 365 × 应收周转天数
        Excel: =B3/365*$C$4
        """
        return f"={self.ref(base)}/{days_in_year}*{self.ref(days)}"

    def tax(self, ebt: str, rate: str) -> str:
        """
        所得税公式: MAX(ebt, 0) × rate

        Excel: =MAX(B10,0)*$C$5
        """
        return f"=MAX({self.ref(ebt)},0)*{self.ref(rate)}"

    def depreciation(self, asset: str, years: str) -> str:
        """
        直线折旧: asset / years

        Excel: =B15/$C$6
        """
        return f"={self.ref(asset)}/{self.ref(years)}"

    def npv(self, rate: str, cash_flows: List[str]) -> str:
        """
        NPV 公式

        Excel: =NPV($C$1,B2:B6)
        """
        if len(cash_flows) == 1:
            return f"=NPV({self.ref(rate)},{self.ref(cash_flows[0])})"

        # 假设是连续单元格
        first = self.ref(cash_flows[0])
        last = self.ref(cash_flows[-1])
        col = ''.join(c for c in first if c.isalpha())
        row_start = ''.join(c for c in first if c.isdigit())
        row_end = ''.join(c for c in last if c.isdigit())

        return f"=NPV({self.ref(rate)},{col}{row_start}:{col}{row_end})"

    def sum_range(self, start: str, end: str) -> str:
        """
        SUM 公式

        Excel: =SUM(B2:B10)
        """
        return f"=SUM({self.ref(start)}:{self.ref(end)})"

    # ==================== 自定义公式 ====================

    def custom(self, template: str, **kwargs) -> str:
        """
        自定义公式模板

        用法:
            builder.custom("{a}*(1+{b})", a="revenue", b="growth_rate")
            # 返回: "=B3*(1+$C$2)"
        """
        refs = {k: self.ref(v) for k, v in kwargs.items()}
        return "=" + template.format(**refs)
```

---

## 二、ExcelWriter 增强

### 2.1 双模式支持

```python
# fin_tools/io/excel_writer.py (增强版)

class ExcelWriter:
    """
    Excel 导出工具（增强版）

    支持两种输出模式：
    - value: 写入计算值 + 公式备注（现有模式）
    - formula: 写入真正的 Excel 公式（新模式）
    """

    def __init__(self, mode: str = "value"):
        """
        Args:
            mode: 输出模式
                - "value": 写值，公式作为备注（默认，兼容现有行为）
                - "formula": 写真正的 Excel 公式
        """
        if mode not in ("value", "formula"):
            raise ValueError(f"mode 必须是 'value' 或 'formula'，收到: {mode}")

        self.mode = mode
        self.wb = Workbook()
        self.wb.remove(self.wb.active)

        # 公式模式需要的组件
        if mode == "formula":
            self.tracker = CellTracker()
            self.builder = FormulaBuilder(self.tracker)
        else:
            self.tracker = None
            self.builder = None

        # ... 样式定义同原来 ...

    def _write_model_cell(self, ws, row: int, col: int,
                          name: str, value: float,
                          formula: str = None,
                          excel_formula: str = None):
        """
        写入模型单元格

        Args:
            ws: 工作表
            row: 行号
            col: 列号
            name: 变量名（用于追踪）
            value: 计算值
            formula: 人类可读公式（value 模式用）
            excel_formula: Excel 公式（formula 模式用）
        """
        cell = ws.cell(row=row, column=col)

        if self.mode == "formula" and excel_formula:
            # 公式模式：写入 Excel 公式
            cell.value = excel_formula
        else:
            # 值模式：写入计算值
            cell.value = value

        # 记录位置（供后续公式引用）
        if self.tracker and name:
            self.tracker.set(name, row, col)

        cell.border = self.thin_border
        cell.alignment = Alignment(horizontal='right')

        return row
```

### 2.2 三表模型公式输出示例

```python
def write_three_statement_formula(self, result: Dict, sheet_name: str = "三表模型"):
    """
    以公式模式写入三表模型

    布局:
        A列: 科目名称
        B列: 金额/公式
        C列: 参数（增长率、毛利率等）
    """
    ws = self.wb.create_sheet(title=sheet_name)

    # 设置列宽
    self._set_column_width(ws, 1, 20)  # 科目
    self._set_column_width(ws, 2, 18)  # 金额
    self._set_column_width(ws, 3, 15)  # 参数

    row = 1

    # ===== 参数区 =====
    row = self._write_title(ws, row, "驱动假设")
    row = self._write_header_row(ws, row, ["参数", "值"])

    assumptions = result.get("_inputs", {}).get("assumptions", {})
    params = [
        ("growth_rate", "收入增长率", assumptions.get("growth_rate", 0.09)),
        ("gross_margin", "毛利率", assumptions.get("gross_margin", 0.253)),
        ("opex_ratio", "费用率", assumptions.get("opex_ratio", 0.097)),
        ("tax_rate", "税率", assumptions.get("tax_rate", 0.1386)),
    ]

    for name, label, value in params:
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=2, value=value)
        ws.cell(row=row, column=2).number_format = '0.0%'
        self.tracker.set(name, row, 2)  # 记录参数位置
        self.builder.register_param(name)  # 注册为参数（绝对引用）
        row += 1

    row += 1

    # ===== 利润表 =====
    row = self._write_title(ws, row, "利润表")
    row = self._write_header_row(ws, row, ["科目", "金额(万元)"])

    income = result.get("income_statement", {})

    # 上期收入（基础数据）
    last_revenue = result.get("_inputs", {}).get("base_data", {}).get("last_revenue", 0)
    ws.cell(row=row, column=1, value="上期收入")
    ws.cell(row=row, column=2, value=last_revenue)
    self.tracker.set("last_revenue", row, 2)
    row += 1

    # 收入 = 上期 × (1 + 增长率)
    ws.cell(row=row, column=1, value="营业收入")
    ws.cell(row=row, column=2, value=self.builder.growth("last_revenue", "growth_rate"))
    self.tracker.set("revenue", row, 2)
    row += 1

    # 成本 = 收入 × (1 - 毛利率)
    ws.cell(row=row, column=1, value="营业成本")
    ws.cell(row=row, column=2, value=self.builder.margin("revenue", "gross_margin"))
    self.tracker.set("cost", row, 2)
    row += 1

    # 毛利 = 收入 - 成本
    ws.cell(row=row, column=1, value="毛利")
    ws.cell(row=row, column=2, value=self.builder.subtract("revenue", "cost"))
    self.tracker.set("gross_profit", row, 2)
    row += 1

    # 费用 = 收入 × 费用率
    ws.cell(row=row, column=1, value="营业费用")
    ws.cell(row=row, column=2, value=self.builder.ratio("revenue", "opex_ratio"))
    self.tracker.set("opex", row, 2)
    row += 1

    # 营业利润 = 毛利 - 费用
    ws.cell(row=row, column=1, value="营业利润")
    ws.cell(row=row, column=2, value=self.builder.subtract("gross_profit", "opex"))
    self.tracker.set("ebit", row, 2)
    row += 1

    # ... 继续其他科目 ...
```

---

## 三、集成到现有系统

### 3.1 改动清单

| 文件 | 改动 | 说明 |
|------|------|------|
| `io/cell_tracker.py` | 新增 | 单元格位置追踪器 |
| `io/formula_builder.py` | 新增 | 公式构建器 |
| `io/__init__.py` | 修改 | 导出新组件 |
| `io/excel_writer.py` | 修改 | 增加 mode 参数，支持公式输出 |
| `core/cell.py` | 可选修改 | 增加 excel_formula 字段 |

### 3.2 兼容性保证

```python
# 默认行为不变
writer = ExcelWriter()  # mode="value"，与现有代码完全兼容
writer.write_three_statement(result)
writer.save("output.xlsx")

# 新功能：公式模式
writer = ExcelWriter(mode="formula")
writer.write_three_statement(result)
writer.save("output_formula.xlsx")
```

### 3.3 使用示例

```python
from fin_tools import ThreeStatementModel, ExcelWriter

# 构建模型
model = ThreeStatementModel(base_data)
result = model.build(assumptions)

# 方式1: 值模式（现有方式）
writer = ExcelWriter(mode="value")
writer.write_three_statement(result)
writer.save("三表模型_值.xlsx")

# 方式2: 公式模式（新增）
writer = ExcelWriter(mode="formula")
writer.write_three_statement(result)
writer.save("三表模型_公式.xlsx")
# 打开后可以直接改参数，自动重算
```

---

## 四、布局设计

### 4.1 推荐的 Excel 布局

```
┌────────────────────────────────────────────────────────────────┐
│  A           │  B          │  C         │  D                   │
├──────────────┼─────────────┼────────────┼──────────────────────┤
│ 【驱动假设】  │             │            │                      │
│ 收入增长率   │    9.0%     │ ← 可修改   │                      │  Row 2
│ 毛利率       │   25.3%     │            │                      │  Row 3
│ 费用率       │    9.7%     │            │                      │  Row 4
│ 税率         │   13.86%    │            │                      │  Row 5
├──────────────┼─────────────┼────────────┼──────────────────────┤
│ 【利润表】    │   金额      │   公式     │  说明                │
│ 上期收入     │ 28,307,198  │ (基础数据) │                      │  Row 8
│ 营业收入     │ =B8*(1+$B$2)│            │ 30,854,846           │  Row 9
│ 营业成本     │ =B9*(1-$B$3)│            │ 23,048,570           │  Row 10
│ 毛利         │ =B9-B10     │            │  7,806,276           │  Row 11
│ 营业费用     │ =B9*$B$4    │            │  2,992,920           │  Row 12
│ 营业利润     │ =B11-B12    │            │  4,813,356           │  Row 13
│ 所得税       │ =MAX(B13,0)*$B$5│        │    667,159           │  Row 14
│ 净利润       │ =B13-B14    │            │  4,146,196           │  Row 15
└──────────────┴─────────────┴────────────┴──────────────────────┘

参数使用绝对引用 ($B$2)，数据使用相对引用 (B9)
改 B2 的增长率 → 所有数字自动重算
```

### 4.2 公式引用规则

| 变量类型 | 引用方式 | 示例 | 原因 |
|----------|----------|------|------|
| 参数（假设） | 绝对引用 | $B$2 | 参数固定在一个位置，不随复制变化 |
| 上期数据 | 相对引用 | B8 | 可能需要拖拽复制到多期 |
| 计算结果 | 相对引用 | B9 | 同上 |

---

## 五、测试场景

### 5.1 基础功能测试

| 场景 | 操作 | 预期结果 |
|------|------|----------|
| 参数修改 | 改增长率 9% → 15% | 收入从 30,854,846 变为 32,553,278 |
| 级联更新 | 改毛利率 25.3% → 30% | 成本、毛利、净利润全部联动更新 |
| 公式正确性 | 点击单元格查看公式栏 | 显示 =B8*(1+$B$2) 而非值 |
| 绝对引用 | 复制收入公式到其他行 | 参数引用 $B$2 不变 |

### 5.2 边界情况测试

| 场景 | 操作 | 预期结果 |
|------|------|----------|
| 零值 | 增长率设为 0% | 收入 = 上期收入 |
| 负值 | 增长率设为 -10% | 收入正确计算为下降 |
| 亏损 | 调参数使税前利润为负 | 所得税 = 0（MAX 函数生效） |
| 大数值 | 收入超过 10 亿 | 公式正常计算，无溢出 |

### 5.3 兼容性测试

| 场景 | 操作 | 预期结果 |
|------|------|----------|
| Excel 打开 | 用 Excel 2016+ 打开 | 公式正常显示和计算 |
| WPS 打开 | 用 WPS 打开 | 公式正常工作 |
| 重新保存 | Excel 打开后保存 | 公式保留，不变成值 |
| 值模式兼容 | mode="value" | 与现有输出完全一致 |

---

## 六、实现步骤

### Phase 1: 基础组件（1-2天）

1. 创建 `io/cell_tracker.py`
2. 创建 `io/formula_builder.py`
3. 单元测试

### Phase 2: ExcelWriter 改造（1-2天）

1. 增加 mode 参数
2. 实现 `write_three_statement` 公式模式
3. 确保 value 模式兼容

### Phase 3: 完善和测试（1天）

1. 实现 `write_dcf` 公式模式
2. 实现 `write_scenario_comparison` 公式模式
3. 集成测试

---

## 七、后续扩展

1. **多期预测**：支持 Year1, Year2, ... 的横向公式
2. **交叉引用**：支持跨 Sheet 引用
3. **条件格式**：负数自动变红
4. **数据验证**：参数单元格加下拉框或范围限制
