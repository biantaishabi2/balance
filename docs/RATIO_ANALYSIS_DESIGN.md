# 财务比率分析工具设计文档

## 概述

为 fm CLI 添加 `ratio` 命令，提供全面的财务比率分析能力，包括盈利能力、偿债能力、运营效率、估值指标和杜邦分析。

```
fm ratio - 财务比率分析

用法: fm ratio <subcommand> [options] < input.json

子命令:
  calc        计算比率
  dupont      杜邦分析
  compare     同业对比
  trend       趋势分析
```

---

## 1. 命令结构

### 1.1 总体架构

```
fm ratio
├── calc                   # 计算比率
│   ├── --type             # 比率类型 (profitability/liquidity/solvency/efficiency/valuation/all)
│   └── --format           # 输出格式
│
├── dupont                 # 杜邦分析
│   ├── --levels           # 分解层级 (3/5)
│   └── --periods          # 多期对比
│
├── compare                # 同业对比
│   ├── --peers            # 对比公司列表
│   └── --metrics          # 对比指标
│
└── trend                  # 趋势分析
    ├── --periods          # 期数
    └── --metrics          # 分析指标
```

---

## 2. fm ratio calc

### 2.1 基本用法

```bash
# 计算所有比率
fm ratio calc --type all < financial.json

# 计算盈利能力比率
fm ratio calc --type profitability < financial.json

# 计算流动性比率
fm ratio calc --type liquidity < financial.json
```

### 2.2 输入格式

```json
{
  "income_statement": {
    "revenue": 150000000000,
    "cost_of_revenue": 45000000000,
    "gross_profit": 105000000000,
    "operating_expenses": 30000000000,
    "operating_income": 75000000000,
    "interest_expense": 500000000,
    "ebit": 75500000000,
    "ebitda": 82000000000,
    "net_income": 62000000000
  },
  "balance_sheet": {
    "cash": 50000000000,
    "accounts_receivable": 12000000000,
    "inventory": 8000000000,
    "current_assets": 75000000000,
    "total_assets": 200000000000,
    "accounts_payable": 15000000000,
    "short_term_debt": 5000000000,
    "current_liabilities": 25000000000,
    "long_term_debt": 30000000000,
    "total_liabilities": 60000000000,
    "total_equity": 140000000000
  },
  "market_data": {
    "stock_price": 150.00,
    "shares_outstanding": 1000000000,
    "market_cap": 150000000000
  }
}
```

### 2.3 比率类型详解

#### 盈利能力 (profitability)

```bash
fm ratio calc --type profitability < financial.json
```

**输出:**
```json
{
  "type": "profitability",
  "ratios": {
    "gross_margin": {
      "value": 0.70,
      "formula": "gross_profit / revenue",
      "interpretation": "毛利率70%，盈利能力强"
    },
    "operating_margin": {
      "value": 0.50,
      "formula": "operating_income / revenue",
      "interpretation": "营业利润率50%"
    },
    "net_margin": {
      "value": 0.4133,
      "formula": "net_income / revenue",
      "interpretation": "净利率41.33%"
    },
    "ebitda_margin": {
      "value": 0.5467,
      "formula": "ebitda / revenue",
      "interpretation": "EBITDA利润率54.67%"
    },
    "roa": {
      "value": 0.31,
      "formula": "net_income / total_assets",
      "interpretation": "资产回报率31%"
    },
    "roe": {
      "value": 0.4429,
      "formula": "net_income / total_equity",
      "interpretation": "净资产收益率44.29%"
    },
    "roic": {
      "value": 0.3647,
      "formula": "nopat / invested_capital",
      "interpretation": "投入资本回报率36.47%"
    }
  }
}
```

#### 流动性/偿债能力 (liquidity)

```bash
fm ratio calc --type liquidity < financial.json
```

**输出:**
```json
{
  "type": "liquidity",
  "ratios": {
    "current_ratio": {
      "value": 3.0,
      "formula": "current_assets / current_liabilities",
      "benchmark": ">1.5 良好",
      "interpretation": "流动比率3.0，短期偿债能力强"
    },
    "quick_ratio": {
      "value": 2.68,
      "formula": "(current_assets - inventory) / current_liabilities",
      "benchmark": ">1.0 良好",
      "interpretation": "速动比率2.68，速动资产充足"
    },
    "cash_ratio": {
      "value": 2.0,
      "formula": "cash / current_liabilities",
      "benchmark": ">0.5 良好",
      "interpretation": "现金比率2.0，现金储备充裕"
    }
  }
}
```

#### 资本结构/杠杆 (solvency)

```bash
fm ratio calc --type solvency < financial.json
```

**输出:**
```json
{
  "type": "solvency",
  "ratios": {
    "debt_to_equity": {
      "value": 0.25,
      "formula": "total_debt / total_equity",
      "interpretation": "负债权益比0.25，杠杆较低"
    },
    "debt_to_assets": {
      "value": 0.175,
      "formula": "total_debt / total_assets",
      "interpretation": "资产负债率17.5%"
    },
    "debt_to_ebitda": {
      "value": 0.427,
      "formula": "total_debt / ebitda",
      "interpretation": "债务/EBITDA 0.43x，偿债能力强"
    },
    "interest_coverage": {
      "value": 151.0,
      "formula": "ebit / interest_expense",
      "benchmark": ">3.0 健康",
      "interpretation": "利息覆盖倍数151x，利息支付无压力"
    },
    "equity_multiplier": {
      "value": 1.43,
      "formula": "total_assets / total_equity",
      "interpretation": "权益乘数1.43"
    }
  }
}
```

#### 运营效率 (efficiency)

```bash
fm ratio calc --type efficiency < financial.json
```

**输出:**
```json
{
  "type": "efficiency",
  "ratios": {
    "asset_turnover": {
      "value": 0.75,
      "formula": "revenue / total_assets",
      "interpretation": "总资产周转率0.75次/年"
    },
    "inventory_turnover": {
      "value": 5.625,
      "formula": "cost_of_revenue / inventory",
      "interpretation": "存货周转率5.63次/年"
    },
    "inventory_days": {
      "value": 64.89,
      "formula": "365 / inventory_turnover",
      "interpretation": "存货周转天数65天"
    },
    "receivable_turnover": {
      "value": 12.5,
      "formula": "revenue / accounts_receivable",
      "interpretation": "应收账款周转率12.5次/年"
    },
    "receivable_days": {
      "value": 29.2,
      "formula": "365 / receivable_turnover",
      "interpretation": "应收账款周转天数29天"
    },
    "payable_turnover": {
      "value": 3.0,
      "formula": "cost_of_revenue / accounts_payable",
      "interpretation": "应付账款周转率3次/年"
    },
    "payable_days": {
      "value": 121.67,
      "formula": "365 / payable_turnover",
      "interpretation": "应付账款周转天数122天"
    },
    "cash_conversion_cycle": {
      "value": -27.58,
      "formula": "inventory_days + receivable_days - payable_days",
      "interpretation": "现金转换周期-28天，营运资本效率极高"
    }
  }
}
```

#### 估值指标 (valuation)

```bash
fm ratio calc --type valuation < financial.json
```

**输出:**
```json
{
  "type": "valuation",
  "ratios": {
    "pe_ratio": {
      "value": 24.19,
      "formula": "market_cap / net_income",
      "interpretation": "市盈率24.19x"
    },
    "pb_ratio": {
      "value": 1.07,
      "formula": "market_cap / total_equity",
      "interpretation": "市净率1.07x"
    },
    "ps_ratio": {
      "value": 1.0,
      "formula": "market_cap / revenue",
      "interpretation": "市销率1.0x"
    },
    "ev_ebitda": {
      "value": 1.59,
      "formula": "(market_cap + debt - cash) / ebitda",
      "interpretation": "EV/EBITDA 1.59x"
    },
    "ev_revenue": {
      "value": 0.87,
      "formula": "(market_cap + debt - cash) / revenue",
      "interpretation": "EV/Revenue 0.87x"
    },
    "earnings_yield": {
      "value": 0.0413,
      "formula": "net_income / market_cap",
      "interpretation": "盈利收益率4.13%"
    }
  }
}
```

---

## 3. fm ratio dupont

### 3.1 三因素杜邦分析

```bash
fm ratio dupont --levels 3 < financial.json
```

**输出:**
```json
{
  "model": "dupont_3_factor",
  "roe": 0.4429,
  "decomposition": {
    "net_margin": {
      "value": 0.4133,
      "formula": "net_income / revenue",
      "label": "净利率"
    },
    "asset_turnover": {
      "value": 0.75,
      "formula": "revenue / total_assets",
      "label": "资产周转率"
    },
    "equity_multiplier": {
      "value": 1.4286,
      "formula": "total_assets / total_equity",
      "label": "权益乘数"
    }
  },
  "formula": "ROE = 净利率 × 资产周转率 × 权益乘数",
  "verification": "0.4133 × 0.75 × 1.4286 = 0.4429 ✓"
}
```

### 3.2 五因素杜邦分析

```bash
fm ratio dupont --levels 5 < financial.json
```

**输出:**
```json
{
  "model": "dupont_5_factor",
  "roe": 0.4429,
  "decomposition": {
    "tax_burden": {
      "value": 0.82,
      "formula": "net_income / ebt",
      "label": "税负系数 (1-税率)"
    },
    "interest_burden": {
      "value": 0.9934,
      "formula": "ebt / ebit",
      "label": "利息负担系数"
    },
    "operating_margin": {
      "value": 0.5033,
      "formula": "ebit / revenue",
      "label": "息税前利润率"
    },
    "asset_turnover": {
      "value": 0.75,
      "formula": "revenue / total_assets",
      "label": "资产周转率"
    },
    "equity_multiplier": {
      "value": 1.4286,
      "formula": "total_assets / total_equity",
      "label": "权益乘数"
    }
  },
  "formula": "ROE = 税负系数 × 利息负担 × 营业利润率 × 资产周转率 × 权益乘数",
  "insights": [
    "税负系数0.82说明有效税率约18%",
    "利息负担系数接近1，利息支出影响极小",
    "高营业利润率(50.33%)是ROE的主要驱动因素",
    "较低的权益乘数(1.43)说明杠杆使用保守"
  ]
}
```

### 3.3 多期杜邦对比

```bash
fm ratio dupont --levels 3 --periods 3 < multi_year_financial.json
```

**输出:**
```json
{
  "model": "dupont_3_factor_trend",
  "periods": ["2022", "2023", "2024"],
  "roe_trend": [0.38, 0.41, 0.4429],
  "decomposition_trend": {
    "net_margin": [0.38, 0.40, 0.4133],
    "asset_turnover": [0.72, 0.73, 0.75],
    "equity_multiplier": [1.39, 1.41, 1.4286]
  },
  "driver_analysis": {
    "primary_driver": "net_margin",
    "contribution": {
      "net_margin": "+3.3%",
      "asset_turnover": "+2.8%",
      "equity_multiplier": "+2.8%"
    },
    "insight": "净利率改善是ROE提升的主要驱动因素"
  }
}
```

---

## 4. fm ratio compare

同业对比分析

```bash
fm ratio compare --peers "AAPL,MSFT,GOOGL" --metrics "roe,roic,net_margin,debt_to_equity"
```

**输出:**
```json
{
  "comparison": {
    "metrics": {
      "roe": {
        "AAPL": 0.44,
        "MSFT": 0.38,
        "GOOGL": 0.28,
        "industry_avg": 0.25
      },
      "roic": {
        "AAPL": 0.36,
        "MSFT": 0.32,
        "GOOGL": 0.25,
        "industry_avg": 0.18
      },
      "net_margin": {
        "AAPL": 0.41,
        "MSFT": 0.35,
        "GOOGL": 0.22,
        "industry_avg": 0.15
      },
      "debt_to_equity": {
        "AAPL": 0.25,
        "MSFT": 0.35,
        "GOOGL": 0.10,
        "industry_avg": 0.45
      }
    },
    "ranking": {
      "roe": ["AAPL", "MSFT", "GOOGL"],
      "roic": ["AAPL", "MSFT", "GOOGL"],
      "net_margin": ["AAPL", "MSFT", "GOOGL"]
    }
  }
}
```

---

## 5. fm ratio trend

趋势分析

```bash
fm ratio trend --periods 5 --metrics "roe,net_margin,asset_turnover" < multi_year.json
```

**输出:**
```json
{
  "trend_analysis": {
    "roe": {
      "values": [0.35, 0.38, 0.40, 0.42, 0.44],
      "cagr": 0.0587,
      "trend": "上升",
      "volatility": 0.023
    },
    "net_margin": {
      "values": [0.35, 0.37, 0.39, 0.40, 0.41],
      "cagr": 0.0404,
      "trend": "稳步上升",
      "volatility": 0.015
    }
  }
}
```

---

## 6. 原子工具

### 6.1 工具列表（按类别聚合）

| 工具名 | 功能 | 包含比率 |
|--------|------|----------|
| `calc_profitability` | 盈利能力分析 | 毛利率、净利率、ROE、ROA、ROIC、EBITDA利润率 |
| `calc_liquidity` | 流动性分析 | 流动比率、速动比率、现金比率 |
| `calc_solvency` | 偿债能力分析 | 负债率、利息覆盖、债务/EBITDA、权益乘数 |
| `calc_efficiency` | 运营效率分析 | 资产周转率、存货周转、应收周转、现金转换周期 |
| `calc_valuation` | 估值分析 | PE、PB、PS、EV/EBITDA、EV/Revenue |
| `calc_dupont` | 杜邦分析 | 3因素/5因素分解 |

**共 6 个原子工具**，每个工具输出该类别下所有比率。

### 6.2 工具调用示例

```bash
# 计算盈利能力比率
fm tool run calc_profitability < financial.json

# 输出（包含所有盈利能力指标）
{
  "gross_margin": 0.70,
  "operating_margin": 0.50,
  "net_margin": 0.4133,
  "ebitda_margin": 0.5467,
  "roa": 0.31,
  "roe": 0.4429,
  "roic": 0.3647
}
```

```bash
# 计算运营效率比率
fm tool run calc_efficiency < financial.json

# 输出
{
  "asset_turnover": 0.75,
  "inventory_turnover": 5.63,
  "inventory_days": 64.89,
  "receivable_turnover": 12.5,
  "receivable_days": 29.2,
  "payable_days": 121.67,
  "cash_conversion_cycle": -27.58
}
```

```bash
# 杜邦分析
fm tool run calc_dupont --levels 5 < financial.json
```

---

## 7. 与其他命令集成

### 7.1 管道用法

```bash
# 获取数据 → 比率分析
fm data fetch --source eastmoney --ticker 600519 --metric financial | fm ratio calc --type all

# 比率分析 → 输出报告
fm ratio calc --type all < financial.json | fm report generate --template ratio_analysis

# DCF + 比率综合分析
fm data fetch --source yahoo --ticker AAPL --metric financial | tee >(fm dcf calc) >(fm ratio calc --type all)
```

### 7.2 LLM 调用示例

```
用户: 分析茅台的财务健康状况

LLM 调用:
1. fm data fetch --source eastmoney --ticker 600519 --metric financial
2. fm ratio calc --type all < financial.json
3. fm ratio dupont --levels 5 < financial.json
4. 综合分析结果，生成报告
```

---

## 8. 实现架构

### 8.1 模块结构

```
balance/
├── fm.py                      # CLI 入口
├── ratio_analysis/
│   ├── __init__.py
│   ├── profitability.py      # 盈利能力比率
│   ├── liquidity.py          # 流动性比率
│   ├── solvency.py           # 偿债能力比率
│   ├── efficiency.py         # 运营效率比率
│   ├── valuation.py          # 估值比率
│   └── dupont.py             # 杜邦分析
└── tools/
    └── ratio_tools.py        # 原子工具
```

### 8.2 核心计算函数

```python
def calc_roe(net_income: float, total_equity: float) -> dict:
    """计算净资产收益率"""
    roe = net_income / total_equity
    return {
        "roe": round(roe, 4),
        "formula": "net_income / total_equity",
        "interpretation": interpret_roe(roe)
    }

def calc_dupont_3(net_income: float, revenue: float,
                  total_assets: float, total_equity: float) -> dict:
    """三因素杜邦分析"""
    net_margin = net_income / revenue
    asset_turnover = revenue / total_assets
    equity_multiplier = total_assets / total_equity
    roe = net_margin * asset_turnover * equity_multiplier

    return {
        "roe": round(roe, 4),
        "decomposition": {
            "net_margin": round(net_margin, 4),
            "asset_turnover": round(asset_turnover, 4),
            "equity_multiplier": round(equity_multiplier, 4)
        }
    }
```

---

## 9. 行业基准

内置行业基准数据，用于比较分析：

```json
{
  "benchmarks": {
    "technology": {
      "gross_margin": {"good": 0.60, "avg": 0.45},
      "net_margin": {"good": 0.20, "avg": 0.10},
      "roe": {"good": 0.25, "avg": 0.15},
      "current_ratio": {"good": 2.0, "avg": 1.5}
    },
    "consumer_staples": {
      "gross_margin": {"good": 0.40, "avg": 0.30},
      "net_margin": {"good": 0.15, "avg": 0.08},
      "roe": {"good": 0.20, "avg": 0.12}
    },
    "financials": {
      "roe": {"good": 0.15, "avg": 0.10},
      "debt_to_equity": {"good": 8.0, "avg": 12.0}
    }
  }
}
```

---

## 10. 更新后的工具总数

添加 data + ratio 命令后，fm CLI 工具总数：

| 类别 | 原有 | 新增 | 合计 |
|------|------|------|------|
| LBO | 9 | - | 9 |
| M&A | 8 | - | 8 |
| DCF | 9 | - | 9 |
| 三表 | 11 | - | 11 |
| **数据源** | - | **7** | 7 |
| **比率分析** | - | **6** | 6 |
| **合计** | 37 | **13** | **50** |
