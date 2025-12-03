# 财报数据准备工具设计文档

## 概述

为 LBO、M&A、DCF 等分析工具提供**前置数据准备工具**，将完整财报转换为各分析工具所需的标准输入格式。

## 问题

现有分析工具的输入是"假设驱动"的：

```python
# 现状：需要手动提取和转换数据
lbo_quick_build({
    "entry_ebitda": 3400,      # 用户需要从财报中找
    "ebitda_margin": 0.25,     # 用户需要自己算
    "capex_percent": 0.08,     # 用户需要假设
    ...
})
```

用户希望直接输入完整财报：

```python
# 理想：输入原始财报，工具自动提取
prepare_lbo_data({
    "income_statement": {...},
    "balance_sheet": {...}
}) → 标准LBO输入
```

---

## 新增工具

### 1. prepare_lbo_data

从完整财报提取 LBO 分析所需数据。

**输入：**
```json
{
  "income_statement": {
    "revenue": 13700,
    "cogs": 8900,
    "gross_profit": 4800,
    "opex": 1400,
    "ebitda": 3400,
    "depreciation": 1360,
    "ebit": 2040,
    "interest_expense": 760,
    "ebt": 1280,
    "tax": 320,
    "net_income": 960
  },
  "balance_sheet": {
    "cash": 800,
    "accounts_receivable": 1200,
    "inventory": 400,
    "current_assets": 2400,
    "ppe_net": 18000,
    "total_assets": 22000,
    "accounts_payable": 900,
    "current_liabilities": 1500,
    "long_term_debt": 12700,
    "total_equity": 7800
  },
  "transaction": {
    "entry_multiple": 7.9,
    "exit_multiple": 8.0,
    "holding_period": 5
  },
  "debt_structure": {
    "senior": {"percent": 0.50, "rate": 0.065, "amort": 0.05},
    "sub": {"percent": 0.20, "rate": 0.085}
  }
}
```

**输出：**
```json
{
  "entry_ebitda": 3400,
  "entry_multiple": 7.9,
  "exit_multiple": 8.0,
  "holding_period": 5,
  "revenue_growth": 0.03,
  "ebitda_margin": 0.248,
  "capex_percent": 0.076,
  "nwc_percent": 0.051,
  "da_percent": 0.099,
  "tax_rate": 0.25,
  "debt_structure": {
    "senior": {"amount_percent": 0.50, "interest_rate": 0.065, "amortization_rate": 0.05},
    "sub": {"amount_percent": 0.20, "interest_rate": 0.085}
  },
  "_derived": {
    "gross_margin": 0.35,
    "ebitda_margin": 0.248,
    "net_margin": 0.070,
    "capex": 1040,
    "nwc": 700,
    "fcf": 1800
  }
}
```

**计算逻辑：**
```python
# 从财报提取/计算
ebitda_margin = ebitda / revenue
capex_percent = depreciation / revenue  # 假设CapEx ≈ D&A（维持性）
nwc = (accounts_receivable + inventory) - accounts_payable
nwc_percent = nwc / revenue
da_percent = depreciation / revenue
tax_rate = tax / ebt if ebt > 0 else 0.25

# 估算收入增长（如无历史数据，默认3%）
revenue_growth = 0.03

# 计算FCF
fcf = ebitda - tax - capex - delta_nwc
```

---

### 2. prepare_ma_data

从完整财报提取 M&A 分析所需数据。

**输入：**
```json
{
  "acquirer": {
    "income_statement": {...},
    "balance_sheet": {...},
    "market_data": {
      "stock_price": 150,
      "shares_outstanding": 1000
    }
  },
  "target": {
    "income_statement": {...},
    "balance_sheet": {...}
  },
  "deal_terms": {
    "premium_percent": 0.30,
    "cash_percent": 0.50,
    "stock_percent": 0.50
  }
}
```

**输出：**
```json
{
  "acquirer": {
    "revenue": 50000,
    "ebitda": 10000,
    "net_income": 5000,
    "eps": 5.0,
    "shares": 1000,
    "stock_price": 150,
    "pe_ratio": 30
  },
  "target": {
    "revenue": 13700,
    "ebitda": 3400,
    "net_income": 960,
    "book_value": 7800
  },
  "deal_terms": {
    "premium_percent": 0.30,
    "cash_percent": 0.50,
    "stock_percent": 0.50
  }
}
```

---

### 3. prepare_dcf_data

从完整财报提取 DCF 估值所需数据。

**输入：**
```json
{
  "income_statement": {...},
  "balance_sheet": {...},
  "projections": {
    "years": 5,
    "revenue_growth": [0.05, 0.05, 0.04, 0.04, 0.03],
    "ebitda_margin": [0.25, 0.26, 0.26, 0.27, 0.27]
  },
  "valuation": {
    "wacc": 0.09,
    "terminal_growth": 0.02
  }
}
```

**输出：**
```json
{
  "base_revenue": 13700,
  "base_ebitda": 3400,
  "fcf_projections": [1800, 1900, 2000, 2100, 2200],
  "wacc": 0.09,
  "terminal_growth": 0.02,
  "net_debt": 11900,
  "shares_outstanding": 1000,
  "_derived": {
    "base_fcf": 1800,
    "base_margins": {
      "gross": 0.35,
      "ebitda": 0.248,
      "net": 0.070
    }
  }
}
```

---

## CLI 集成

### 命令结构

```bash
# 准备LBO数据
fm prepare lbo < financials.json

# 准备MA数据
fm prepare ma < deal.json

# 准备DCF数据
fm prepare dcf < financials.json

# 管道用法：准备 + 分析
fm prepare lbo < financials.json | fm lbo calc
fm prepare lbo < financials.json | fm lbo sensitivity --entry 7,8,9 --exit 7,8,9
```

### 工具注册

```python
TOOL_REGISTRY = {
    # ... 现有工具 ...

    # Prepare 工具
    "prepare_lbo_data": ("financial_model.tools.prepare_tools", "LBO数据准备"),
    "prepare_ma_data": ("financial_model.tools.prepare_tools", "MA数据准备"),
    "prepare_dcf_data": ("financial_model.tools.prepare_tools", "DCF数据准备"),
}
```

---

## LLM 调用示例

```
用户: 分析这个公司的LBO可行性
     [粘贴完整财报]

LLM 调用:
1. prepare_lbo_data(financials) → 标准输入
2. lbo_quick_build(标准输入) → 基准案例
3. lbo_sensitivity(标准输入) → 敏感性分析
4. 输出报告
```

---

## 实现架构

```
financial_model/tools/
├── lbo_tools.py           # 现有
├── ma_tools.py            # 现有
├── dcf_tools.py           # 现有
├── ratio_tools.py         # 现有
└── prepare_tools.py       # 新增
    ├── prepare_lbo_data()
    ├── prepare_ma_data()
    └── prepare_dcf_data()
```

---

## 工具总数更新

| 类别 | 原有 | 新增 | 合计 |
|------|------|------|------|
| LBO | 9 | - | 9 |
| M&A | 8 | - | 8 |
| DCF | 9 | - | 9 |
| 三表 | 11 | - | 11 |
| 比率分析 | 7 | - | 7 |
| **数据准备** | - | **3** | 3 |
| **合计** | 44 | **3** | **47** |
