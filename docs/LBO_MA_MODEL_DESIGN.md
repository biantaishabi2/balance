# LBO 与 M&A 模型设计文档

## 概述

本文档描述两类高级财务模型的设计：

1. **LBO 模型（杠杆收购）** - 私募股权基金收购分析
2. **M&A 模型（并购）** - 公司并购交易分析

这两个模型都依赖现有的三表模型作为基础。

```
┌─────────────────┐
│   三表模型       │  ← 基础
│ (已实现)        │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐  ┌────────┐
│  LBO   │  │  M&A   │  ← 高级模型
│  模型  │  │  模型  │
└────────┘  └────────┘
```

---

# 第一部分：LBO 模型（杠杆收购）

## 1.1 业务背景

**场景**：私募股权基金（PE）用大量借款收购一家公司，然后用公司的现金流还债，最终卖出获利。

```
典型 LBO 交易结构:

收购价: 10 亿
├── PE 自有资金: 4 亿 (40%)   ← 股权
└── 银行贷款:    6 亿 (60%)   ← 债务（杠杆）

持有期间:
  用公司现金流还债

退出时:
  以 12 亿卖出
  还清剩余债务 3 亿
  PE 拿回 9 亿

回报:
  投入 4 亿，拿回 9 亿
  MOIC = 9/4 = 2.25x
  IRR ≈ 18% (5年)
```

**关键问题**：
- 能借多少钱？（债务容量）
- 每年能还多少？（现金流）
- 最终赚多少倍？（回报率）

---

## 1.2 核心工具设计

### 1.2.1 工具清单

| 工具名 | 功能 | 公式 |
|--------|------|------|
| `calc_purchase_price` | 收购价格 | `价格 = EBITDA × Entry Multiple` |
| `calc_sources_uses` | 资金来源与用途 | 股权 + 债务 = 收购价 + 费用 |
| `build_debt_schedule` | 债务计划表 | 每期还本付息明细 |
| `calc_cash_sweep` | 现金瀑布 | 多余现金优先还债 |
| `calc_exit_value` | 退出价值 | `退出价 = EBITDA × Exit Multiple` |
| `calc_irr` | 内部收益率 | `IRR(现金流序列)` |
| `calc_moic` | 投资倍数 | `退出所得 / 投入资金` |

### 1.2.2 输入格式

```json
{
  "_meta": {
    "model_type": "lbo",
    "target_company": "目标公司",
    "sponsor": "XX资本"
  },

  "operating_assumptions": {
    "entry_ebitda": 100000000,
    "revenue_growth": [0.05, 0.06, 0.07, 0.06, 0.05],
    "ebitda_margin": [0.20, 0.21, 0.22, 0.22, 0.22],
    "capex_percent": 0.03,
    "nwc_percent": 0.10,
    "tax_rate": 0.25
  },

  "transaction_assumptions": {
    "entry_multiple": 8.0,
    "exit_multiple": 8.0,
    "holding_period": 5,
    "transaction_fees": 0.02,
    "financing_fees": 0.01
  },

  "debt_assumptions": {
    "senior_debt": {
      "amount_percent": 0.40,
      "interest_rate": 0.06,
      "amortization": 0.05,
      "term": 7
    },
    "subordinated_debt": {
      "amount_percent": 0.20,
      "interest_rate": 0.10,
      "amortization": 0.0,
      "term": 8,
      "pik_rate": 0.02
    }
  },

  "cash_sweep": {
    "enabled": true,
    "percent": 0.75,
    "priority": ["senior_debt", "subordinated_debt"]
  }
}
```

### 1.2.3 输出格式

```json
{
  "sources_and_uses": {
    "uses": {
      "purchase_price": {
        "value": 800000000,
        "formula": "EBITDA × Entry Multiple",
        "inputs": {"ebitda": 100000000, "multiple": 8.0}
      },
      "transaction_fees": {"value": 16000000},
      "financing_fees": {"value": 8000000},
      "total_uses": {"value": 824000000}
    },
    "sources": {
      "senior_debt": {"value": 320000000},
      "subordinated_debt": {"value": 160000000},
      "equity": {"value": 344000000},
      "total_sources": {"value": 824000000}
    }
  },

  "debt_schedule": {
    "senior_debt": [
      {
        "year": 1,
        "opening_balance": 320000000,
        "interest": 19200000,
        "mandatory_amort": 16000000,
        "cash_sweep": 24000000,
        "closing_balance": 280000000
      }
    ],
    "subordinated_debt": [
      {
        "year": 1,
        "opening_balance": 160000000,
        "cash_interest": 16000000,
        "pik_interest": 3200000,
        "closing_balance": 163200000
      }
    ]
  },

  "operating_model": {
    "year_1": {
      "revenue": 500000000,
      "ebitda": 100000000,
      "ebit": 85000000,
      "interest": 35200000,
      "ebt": 49800000,
      "tax": 12450000,
      "net_income": 37350000,
      "fcf": 52350000
    }
  },

  "exit_analysis": {
    "exit_ebitda": {"value": 130000000},
    "exit_value": {
      "value": 1040000000,
      "formula": "Exit EBITDA × Exit Multiple",
      "inputs": {"ebitda": 130000000, "multiple": 8.0}
    },
    "net_debt_at_exit": {"value": 280000000},
    "equity_proceeds": {
      "value": 760000000,
      "formula": "Exit Value - Net Debt"
    }
  },

  "returns": {
    "moic": {
      "value": 2.21,
      "formula": "Equity Proceeds / Equity Invested",
      "inputs": {"proceeds": 760000000, "invested": 344000000}
    },
    "irr": {
      "value": 0.172,
      "formula": "IRR(Cash Flows)",
      "cash_flows": [-344000000, 0, 0, 0, 0, 760000000]
    },
    "holding_period": 5
  },

  "sensitivity": {
    "entry_multiple_vs_exit_multiple": {
      "headers": {"rows": "Entry Multiple", "columns": "Exit Multiple"},
      "metric": "IRR",
      "data": [
        {"entry": "7.0x", "exit_7x": "15.2%", "exit_8x": "19.8%", "exit_9x": "24.1%"},
        {"entry": "8.0x", "exit_7x": "10.5%", "exit_8x": "17.2%", "exit_9x": "21.3%"},
        {"entry": "9.0x", "exit_7x": "6.2%", "exit_8x": "12.1%", "exit_9x": "17.8%"}
      ]
    }
  }
}
```

---

## 1.3 核心算法实现

### 1.3.1 债务计划表

```python
class DebtTranche:
    """单笔债务"""

    def __init__(self, name: str, amount: float, interest_rate: float,
                 amortization_rate: float = 0, pik_rate: float = 0):
        self.name = name
        self.amount = amount
        self.interest_rate = interest_rate
        self.amortization_rate = amortization_rate
        self.pik_rate = pik_rate
        self.balance = amount

    def calc_period(self, cash_sweep: float = 0) -> dict:
        """
        计算一期的还本付息

        Returns:
            {
                "opening_balance": 期初余额,
                "cash_interest": 现金利息,
                "pik_interest": PIK利息（加到本金）,
                "mandatory_amort": 强制还本,
                "cash_sweep": 现金扫荡还款,
                "closing_balance": 期末余额
            }
        """
        opening = self.balance

        # 现金利息
        cash_interest = opening * self.interest_rate

        # PIK 利息（加到本金，不付现金）
        pik_interest = opening * self.pik_rate

        # 强制还本
        mandatory_amort = self.amount * self.amortization_rate

        # 实际还本 = 强制 + 现金扫荡
        total_principal = min(mandatory_amort + cash_sweep, opening + pik_interest)

        # 期末余额
        closing = opening + pik_interest - total_principal
        self.balance = max(closing, 0)

        return {
            "opening_balance": opening,
            "cash_interest": cash_interest,
            "pik_interest": pik_interest,
            "mandatory_amort": mandatory_amort,
            "cash_sweep": min(cash_sweep, opening - mandatory_amort),
            "closing_balance": self.balance
        }


def build_debt_schedule(debt_tranches: list, fcf_by_year: list,
                        sweep_percent: float = 0.75) -> dict:
    """
    构建完整债务计划表

    Args:
        debt_tranches: 各笔债务列表
        fcf_by_year: 每年自由现金流
        sweep_percent: 现金扫荡比例

    Returns:
        完整的债务计划表
    """
    schedule = {tranche.name: [] for tranche in debt_tranches}

    for year, fcf in enumerate(fcf_by_year, 1):
        total_interest = 0
        total_amort = 0

        # 计算总利息
        for tranche in debt_tranches:
            period = tranche.calc_period(cash_sweep=0)
            total_interest += period["cash_interest"]
            total_amort += period["mandatory_amort"]
            # 重置，因为还要重新算
            tranche.balance = period["opening_balance"]

        # 可用于还债的现金
        cash_for_debt = fcf - total_interest
        available_for_sweep = max(cash_for_debt - total_amort, 0) * sweep_percent

        # 按优先级分配现金扫荡
        for tranche in debt_tranches:
            sweep = min(available_for_sweep, tranche.balance)
            period = tranche.calc_period(cash_sweep=sweep)
            schedule[tranche.name].append({"year": year, **period})
            available_for_sweep -= period["cash_sweep"]

    return schedule
```

### 1.3.2 回报计算

```python
import numpy_financial as npf  # pip install numpy-financial


def calc_irr(cash_flows: list) -> float:
    """
    计算 IRR

    Args:
        cash_flows: 现金流序列 [-投入, 0, 0, 0, 0, 退出所得]

    Returns:
        IRR (年化)
    """
    return npf.irr(cash_flows)


def calc_moic(equity_invested: float, equity_proceeds: float) -> float:
    """
    计算投资倍数

    MOIC = 退出所得 / 投入资金
    """
    return equity_proceeds / equity_invested


def calc_cash_on_cash(equity_invested: float, total_distributions: float) -> float:
    """
    计算现金回报倍数（包含期间分红）

    CoC = 总分配 / 投入资金
    """
    return total_distributions / equity_invested
```

---

## 1.4 LBO 测试场景

### 1.4.1 基础功能测试

| 场景 | 输入 | 预期结果 |
|------|------|----------|
| 标准交易 | EBITDA=1亿, 8x入场, 8x退出, 5年 | IRR≈17%, MOIC≈2.2x |
| 零杠杆 | 100%股权收购 | IRR = 退出回报率 |
| 高杠杆 | 70%债务 | IRR 更高（如果能还清） |
| 估值提升 | 8x入场, 10x退出 | IRR 显著提高 |
| 估值下降 | 8x入场, 6x退出 | IRR 可能为负 |

### 1.4.2 债务还款测试

| 场景 | 输入 | 预期结果 |
|------|------|----------|
| 正常还款 | FCF 充足 | 债务逐年下降 |
| 现金扫荡 | sweep=75% | 多余现金优先还债 |
| 无法还款 | FCF < 利息 | 债务上升（PIK 累积） |
| 提前还清 | FCF 很大 | 债务快速归零 |

### 1.4.3 敏感性测试

| 场景 | 变量 | 预期结果 |
|------|------|----------|
| 入场倍数敏感性 | 7x-9x | IRR 与入场倍数负相关 |
| 退出倍数敏感性 | 7x-9x | IRR 与退出倍数正相关 |
| 增长率敏感性 | 0%-10% | 增长越快，IRR 越高 |
| 杠杆敏感性 | 40%-70% | 适度杠杆提升 IRR |

### 1.4.4 边界情况测试

| 场景 | 输入 | 预期结果 |
|------|------|----------|
| EBITDA 为负 | 亏损公司 | 无法支撑债务，报错或警告 |
| 退出价 < 债务 | 重大亏损 | 股权价值为 0，IRR 为 -100% |
| 持有期为 0 | 即买即卖 | IRR = (退出-入场)/入场 |
| 超长持有期 | 20 年 | IRR 收敛到运营增长率 |

---

# 第二部分：M&A 模型（并购）

## 2.1 业务背景

**场景**：A 公司收购 B 公司，需要分析交易对 A 公司的财务影响。

```
并购交易示例:

收购方: 腾讯 (市值 3000 亿)
目标方: 某游戏公司 (估值 100 亿)

支付方式:
├── 现金: 60 亿
└── 腾讯股票: 40 亿 (发行新股)

关键问题:
├── 每股收益是增厚还是稀释？(Accretion/Dilution)
├── 合并后资产负债表长什么样？(Pro Forma)
├── 要确认多少商誉？(Goodwill)
└── 协同效应能覆盖溢价吗？(Synergies)
```

**核心概念**：

| 术语 | 含义 |
|------|------|
| Accretion | 增厚 - 收购后 EPS 上升 |
| Dilution | 稀释 - 收购后 EPS 下降 |
| Goodwill | 商誉 - 收购溢价超过净资产部分 |
| PPA | 购买价格分摊 - 把收购价分配到各项资产 |
| Synergies | 协同效应 - 合并后的成本节约或收入增加 |

---

## 2.2 核心工具设计

### 2.2.1 工具清单

| 工具名 | 功能 | 公式 |
|--------|------|------|
| `calc_purchase_price` | 收购价格 | 股价×股数 或 EBITDA×倍数 |
| `calc_funding_mix` | 融资结构 | 现金 + 股票 + 新债 = 收购价 |
| `calc_goodwill` | 商誉计算 | 收购价 - 目标净资产公允价值 |
| `build_ppa` | 购买价格分摊 | 分配到各项资产和商誉 |
| `build_pro_forma` | 合并报表 | 收购方 + 目标方 + 调整 |
| `calc_accretion_dilution` | 增厚/稀释 | 合并EPS vs 独立EPS |
| `calc_synergies` | 协同效应 | 成本节约 + 收入协同 |
| `calc_breakeven` | 盈亏平衡 | 需要多少协同才能不稀释 |

### 2.2.2 输入格式

```json
{
  "_meta": {
    "model_type": "ma",
    "acquirer": "收购方公司",
    "target": "目标公司",
    "deal_date": "2025-06-30"
  },

  "acquirer_financials": {
    "share_price": 100,
    "shares_outstanding": 1000000000,
    "net_income": 50000000000,
    "total_assets": 500000000000,
    "total_liabilities": 200000000000,
    "cash": 100000000000
  },

  "target_financials": {
    "share_price": 50,
    "shares_outstanding": 200000000,
    "net_income": 2000000000,
    "total_assets": 30000000000,
    "total_liabilities": 10000000000,
    "book_value": 20000000000
  },

  "deal_terms": {
    "offer_price_per_share": 65,
    "premium_percent": 0.30,
    "payment_mix": {
      "cash_percent": 0.60,
      "stock_percent": 0.40
    },
    "new_debt": 0
  },

  "purchase_price_allocation": {
    "intangible_assets_fv": 5000000000,
    "intangible_amortization_years": 10,
    "fixed_assets_step_up": 1000000000,
    "deferred_tax_liability": 1500000000
  },

  "synergies": {
    "cost_synergies": {
      "year_1": 500000000,
      "year_2": 800000000,
      "year_3": 1000000000
    },
    "revenue_synergies": {
      "year_1": 0,
      "year_2": 200000000,
      "year_3": 500000000
    },
    "integration_costs": {
      "year_1": 300000000,
      "year_2": 100000000
    }
  },

  "financing_assumptions": {
    "cost_of_debt": 0.05,
    "tax_rate": 0.25,
    "acquirer_pe_ratio": 20
  }
}
```

### 2.2.3 输出格式

```json
{
  "deal_summary": {
    "purchase_price": {
      "value": 13000000000,
      "formula": "Offer Price × Target Shares",
      "inputs": {"offer_price": 65, "shares": 200000000}
    },
    "premium": {
      "value": 3000000000,
      "percent": 0.30,
      "formula": "(Offer - Current) / Current"
    },
    "funding": {
      "cash": {"value": 7800000000, "percent": 0.60},
      "stock": {"value": 5200000000, "percent": 0.40, "shares_issued": 52000000}
    }
  },

  "purchase_price_allocation": {
    "target_book_value": 20000000000,
    "fair_value_adjustments": {
      "intangible_assets": 5000000000,
      "fixed_assets_step_up": 1000000000,
      "deferred_tax_liability": -1500000000
    },
    "adjusted_net_assets": 24500000000,
    "goodwill": {
      "value": -11500000000,
      "formula": "Purchase Price - Adjusted Net Assets",
      "note": "负商誉表示bargain purchase"
    }
  },

  "pro_forma_balance_sheet": {
    "assets": {
      "cash": {
        "acquirer": 100000000000,
        "target": 5000000000,
        "adjustment": -7800000000,
        "pro_forma": 97200000000
      },
      "goodwill": {
        "acquirer": 10000000000,
        "target": 0,
        "adjustment": 0,
        "pro_forma": 10000000000
      },
      "total_assets": {
        "pro_forma": 540000000000
      }
    },
    "equity": {
      "common_stock": {
        "acquirer": 100000000000,
        "adjustment": 5200000000,
        "pro_forma": 105200000000
      }
    }
  },

  "accretion_dilution": {
    "standalone_acquirer": {
      "net_income": 50000000000,
      "shares": 1000000000,
      "eps": 50.00
    },
    "pro_forma": {
      "acquirer_net_income": 50000000000,
      "target_net_income": 2000000000,
      "synergies_net": 375000000,
      "intangible_amort": -375000000,
      "interest_expense": -292500000,
      "combined_net_income": 51707500000,
      "combined_shares": 1052000000,
      "eps": 49.15
    },
    "accretion_dilution": {
      "value": -0.85,
      "percent": -0.017,
      "status": "Dilutive",
      "formula": "Pro Forma EPS - Standalone EPS"
    }
  },

  "synergy_analysis": {
    "total_synergies_pv": {
      "value": 8500000000,
      "formula": "Σ Synergies / (1+r)^t"
    },
    "premium_paid": 3000000000,
    "synergy_coverage": {
      "value": 2.83,
      "formula": "Synergies PV / Premium",
      "interpretation": "协同效应覆盖溢价2.83倍"
    }
  },

  "breakeven_analysis": {
    "synergies_needed": {
      "value": 893000000,
      "formula": "使EPS不稀释需要的年化协同效应"
    },
    "years_to_accretion": {
      "value": 2,
      "note": "第2年开始EPS增厚"
    }
  },

  "sensitivity": {
    "synergies_vs_stock_percent": {
      "headers": {"rows": "协同效应", "columns": "股票支付比例"},
      "metric": "EPS Accretion %",
      "data": [
        {"synergies": "5亿", "stock_20%": "+2.1%", "stock_40%": "-1.7%", "stock_60%": "-5.2%"},
        {"synergies": "10亿", "stock_20%": "+4.5%", "stock_40%": "+1.2%", "stock_60%": "-2.8%"},
        {"synergies": "15亿", "stock_20%": "+6.8%", "stock_40%": "+3.9%", "stock_60%": "+0.5%"}
      ]
    }
  }
}
```

---

## 2.3 核心算法实现

### 2.3.1 增厚/稀释分析

```python
def calc_accretion_dilution(
    acquirer_net_income: float,
    acquirer_shares: float,
    target_net_income: float,
    purchase_price: float,
    cash_percent: float,
    stock_percent: float,
    acquirer_share_price: float,
    cost_of_debt: float,
    tax_rate: float,
    synergies: float = 0,
    intangible_amort: float = 0
) -> dict:
    """
    计算并购的增厚/稀释效应

    Args:
        acquirer_net_income: 收购方净利润
        acquirer_shares: 收购方股数
        target_net_income: 目标方净利润
        purchase_price: 收购价格
        cash_percent: 现金支付比例
        stock_percent: 股票支付比例
        acquirer_share_price: 收购方股价
        cost_of_debt: 债务成本
        tax_rate: 税率
        synergies: 协同效应（税前）
        intangible_amort: 无形资产摊销

    Returns:
        增厚/稀释分析结果
    """
    # 收购方独立 EPS
    standalone_eps = acquirer_net_income / acquirer_shares

    # 融资成本
    cash_used = purchase_price * cash_percent
    foregone_interest = cash_used * cost_of_debt * (1 - tax_rate)  # 损失的利息收入

    # 新发股票
    stock_value = purchase_price * stock_percent
    new_shares = stock_value / acquirer_share_price

    # 合并净利润
    combined_net_income = (
        acquirer_net_income
        + target_net_income
        - foregone_interest                    # 减：损失的利息收入
        + synergies * (1 - tax_rate)           # 加：税后协同效应
        - intangible_amort * (1 - tax_rate)    # 减：税后摊销
    )

    # 合并股数
    combined_shares = acquirer_shares + new_shares

    # 合并 EPS
    pro_forma_eps = combined_net_income / combined_shares

    # 增厚/稀释
    accretion = pro_forma_eps - standalone_eps
    accretion_percent = accretion / standalone_eps

    return {
        "standalone": {
            "net_income": acquirer_net_income,
            "shares": acquirer_shares,
            "eps": standalone_eps
        },
        "pro_forma": {
            "net_income": combined_net_income,
            "shares": combined_shares,
            "eps": pro_forma_eps
        },
        "accretion_dilution": {
            "value": accretion,
            "percent": accretion_percent,
            "status": "Accretive" if accretion > 0 else "Dilutive"
        }
    }
```

### 2.3.2 商誉计算

```python
def calc_goodwill(
    purchase_price: float,
    target_book_value: float,
    fair_value_adjustments: dict
) -> dict:
    """
    计算商誉

    商誉 = 收购价 - 目标公司净资产公允价值

    Args:
        purchase_price: 收购价格
        target_book_value: 目标公司账面净资产
        fair_value_adjustments: 公允价值调整
            - intangible_assets: 确认的无形资产
            - fixed_assets_step_up: 固定资产增值
            - deferred_tax_liability: 递延税负债

    Returns:
        商誉计算结果
    """
    # 调整后净资产 = 账面 + 无形资产 + 固定资产增值 - 递延税
    adjusted_net_assets = (
        target_book_value
        + fair_value_adjustments.get("intangible_assets", 0)
        + fair_value_adjustments.get("fixed_assets_step_up", 0)
        - fair_value_adjustments.get("deferred_tax_liability", 0)
    )

    goodwill = purchase_price - adjusted_net_assets

    return {
        "target_book_value": target_book_value,
        "fair_value_adjustments": fair_value_adjustments,
        "adjusted_net_assets": {
            "value": adjusted_net_assets,
            "formula": "Book Value + FV Adjustments"
        },
        "goodwill": {
            "value": goodwill,
            "formula": "Purchase Price - Adjusted Net Assets",
            "note": "负值表示廉价收购(Bargain Purchase)" if goodwill < 0 else ""
        }
    }
```

### 2.3.3 协同效应分析

```python
def calc_synergy_value(
    cost_synergies: list,
    revenue_synergies: list,
    integration_costs: list,
    discount_rate: float,
    tax_rate: float,
    margin_on_revenue: float = 0.20
) -> dict:
    """
    计算协同效应现值

    Args:
        cost_synergies: 各年成本协同（税前）
        revenue_synergies: 各年收入协同
        integration_costs: 整合成本
        discount_rate: 折现率
        tax_rate: 税率
        margin_on_revenue: 收入协同的利润率

    Returns:
        协同效应分析结果
    """
    years = max(len(cost_synergies), len(revenue_synergies))

    total_pv = 0
    yearly_details = []

    for year in range(years):
        cost_syn = cost_synergies[year] if year < len(cost_synergies) else cost_synergies[-1]
        rev_syn = revenue_synergies[year] if year < len(revenue_synergies) else revenue_synergies[-1]
        integ = integration_costs[year] if year < len(integration_costs) else 0

        # 税后协同
        profit_from_revenue = rev_syn * margin_on_revenue
        gross_synergy = cost_syn + profit_from_revenue - integ
        net_synergy = gross_synergy * (1 - tax_rate)

        # 折现
        discount_factor = 1 / (1 + discount_rate) ** (year + 1)
        pv = net_synergy * discount_factor

        total_pv += pv

        yearly_details.append({
            "year": year + 1,
            "cost_synergies": cost_syn,
            "revenue_synergies": rev_syn,
            "integration_costs": integ,
            "net_synergy": net_synergy,
            "present_value": pv
        })

    return {
        "yearly_details": yearly_details,
        "total_pv": {
            "value": total_pv,
            "formula": "Σ Net Synergies / (1+r)^t"
        }
    }
```

---

## 2.4 M&A 测试场景

### 2.4.1 基础功能测试

| 场景 | 输入 | 预期结果 |
|------|------|----------|
| 全现金收购 | 100%现金 | 无股份稀释，但利息成本 |
| 全股票收购 | 100%股票 | 有股份稀释，无利息成本 |
| 混合支付 | 60%现金+40%股票 | 中间状态 |
| 高溢价收购 | 50%溢价 | 商誉很大，更可能稀释 |
| 无溢价收购 | 0%溢价 | 商誉 = FV调整，更可能增厚 |

### 2.4.2 增厚/稀释测试

| 场景 | 条件 | 预期结果 |
|------|------|----------|
| 目标PE < 收购方PE | 低估值收购 | 更可能增厚 |
| 目标PE > 收购方PE | 高估值收购 | 更可能稀释 |
| 大量协同效应 | 协同 > 溢价 | 抵消稀释 |
| 高股票比例 | 80%股票支付 | 稀释更严重 |

### 2.4.3 商誉测试

| 场景 | 输入 | 预期结果 |
|------|------|----------|
| 正商誉 | 收购价 > 净资产FV | 确认商誉资产 |
| 零商誉 | 收购价 = 净资产FV | 无商誉 |
| 负商誉 | 收购价 < 净资产FV | Bargain Purchase，计入利润 |
| 高无形资产 | 识别大量无形资产 | 商誉减少，摊销增加 |

### 2.4.4 敏感性测试

| 场景 | 变量 | 预期结果 |
|------|------|----------|
| 支付方式敏感性 | 现金0%-100% | 现金越多，稀释越少 |
| 溢价敏感性 | 溢价10%-50% | 溢价越高，越可能稀释 |
| 协同敏感性 | 协同0-20亿 | 协同越大，越可能增厚 |
| 目标利润敏感性 | 净利润变化±20% | 影响合并后EPS |

### 2.4.5 边界情况测试

| 场景 | 输入 | 预期结果 |
|------|------|----------|
| 目标亏损 | 目标净利润为负 | 拖累合并利润 |
| 收购方亏损 | 收购方净利润为负 | 基准EPS为负，增厚/稀释意义不同 |
| 反向收购 | 目标规模 > 收购方 | 会计上被收购方是收购方 |
| 现金不足 | 现金 < 现金支付 | 需要额外融资 |

---

# 第三部分：集成到现有系统

## 3.1 目录结构

```
financial_model/
├── models/
│   ├── three_statement.py      # 现有
│   ├── dcf.py                  # 现有
│   ├── scenario.py             # 现有
│   ├── advanced.py             # 现有
│   ├── lbo.py                  # 新增
│   └── ma.py                   # 新增
│
├── tests/
│   ├── test_lbo.py             # 新增
│   └── test_ma.py              # 新增
```

## 3.2 依赖关系

```
                ┌─────────────────┐
                │  三表模型        │
                │ ThreeStatement  │
                └────────┬────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │   DCF   │    │   LBO   │    │   M&A   │
    │  模型   │    │  模型   │    │  模型   │
    └─────────┘    └─────────┘    └─────────┘
                         │               │
                         └───────┬───────┘
                                 ▼
                          ┌─────────────┐
                          │ Excel/报告  │
                          │   输出      │
                          └─────────────┘
```

## 3.3 API 设计

```python
# 统一的模型接口

from financial_model import LBOModel, MAModel

# LBO 模型
lbo = LBOModel()
lbo_result = lbo.build(lbo_inputs)
lbo_result = lbo.sensitivity_entry_exit(entry_range, exit_range)

# M&A 模型
ma = MAModel()
ma_result = ma.build(ma_inputs)
ma_result = ma.calc_accretion_dilution()
ma_result = ma.sensitivity_synergies_payment()
```

---

## 3.4 实现优先级

| 模块 | 优先级 | 复杂度 | 依赖 |
|------|--------|--------|------|
| LBO 基础模型 | P1 | ⭐⭐⭐ | 三表模型 |
| LBO 债务计划表 | P1 | ⭐⭐ | - |
| LBO 回报计算 | P1 | ⭐ | numpy-financial |
| M&A 增厚/稀释 | P1 | ⭐⭐ | - |
| M&A 商誉计算 | P2 | ⭐ | - |
| M&A 合并报表 | P2 | ⭐⭐⭐ | 三表模型 |
| M&A 协同效应 | P2 | ⭐⭐ | DCF |
| Excel 输出 | P3 | ⭐⭐ | ExcelWriter |

---

## 3.5 测试数据准备

### LBO 测试案例

```json
{
  "case_name": "标准LBO测试",
  "entry_ebitda": 100000000,
  "entry_multiple": 8.0,
  "exit_multiple": 8.0,
  "holding_period": 5,
  "debt_percent": 0.60,
  "expected_irr": 0.17,
  "expected_moic": 2.2
}
```

### M&A 测试案例

```json
{
  "case_name": "增厚型收购",
  "acquirer_pe": 20,
  "target_pe": 12,
  "premium": 0.25,
  "stock_percent": 0.50,
  "synergies": 500000000,
  "expected_result": "Accretive"
}
```

---

# 第四部分：原子工具设计

## 4.1 设计理念

**问题**：`build()` 是个黑盒，LLM无法灵活调整中间步骤。

**解决方案**：将 LBO/M&A 模型拆分为独立的原子工具，每个工具：
- 独立运行，不依赖类状态
- 输入输出清晰（JSON格式）
- 可自由组合，LLM可以跳过、替换、插入任何步骤

```
┌─────────────────────────────────────────────────────────────┐
│                      LLM 工作流程                            │
├─────────────────────────────────────────────────────────────┤
│  用户: "帮我做LBO，入场8倍，但收购价用净资产+30%溢价"        │
│                                                             │
│  LLM:                                                       │
│    1. 跳过 calc_purchase_price（用户要自定义）              │
│    2. 自己算: 净资产 × 1.3 = 7亿                            │
│    3. 调用 calc_sources_uses(purchase_price=7亿, ...)       │
│    4. 调用 calc_debt_schedule(...)                          │
│    5. 调用 calc_exit_value(...)                             │
│    6. 调用 calc_returns(...)                                │
│    7. 调用 export_excel(...)                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 4.2 LBO 原子工具清单

### 工具1: calc_purchase_price

**功能**：计算收购价格

```python
# 输入
{
  "ebitda": 100000000,
  "multiple": 8.0
}

# 输出
{
  "value": 800000000,
  "formula": "EBITDA × Entry Multiple",
  "inputs": {"ebitda": 100000000, "multiple": 8.0}
}
```

**替代方式**：LLM可以不调用此工具，自己用任何方式计算收购价（净资产+溢价、DCF、可比交易等）

---

### 工具2: calc_sources_uses

**功能**：计算资金来源与用途

```python
# 输入
{
  "purchase_price": 800000000,
  "transaction_fee_rate": 0.02,
  "financing_fee_rate": 0.01,
  "debt_amounts": {"senior": 320000000, "sub": 160000000},
  "existing_cash": 0
}

# 输出
{
  "equity_required": 344000000,
  "total_debt": 480000000,
  "uses": {
    "purchase_price": 800000000,
    "transaction_fees": 16000000,
    "financing_fees": 4800000,
    "total": 820800000
  },
  "sources": {
    "senior_debt": 320000000,
    "sub_debt": 160000000,
    "equity": 344000000,
    "total": 820800000
  },
  "formula": "Equity = Total Uses - Total Debt",
  "inputs": {...}
}
```

---

### 工具3: project_operations

**功能**：预测运营数据（收入、EBITDA、现金流）

```python
# 输入
{
  "base_revenue": 500000000,
  "years": 5,
  "revenue_growth": [0.05, 0.06, 0.07, 0.06, 0.05],
  "ebitda_margin": [0.20, 0.21, 0.22, 0.22, 0.22],
  "capex_percent": 0.03,
  "nwc_percent": 0.10,
  "tax_rate": 0.25
}

# 输出
{
  "projections": [
    {"year": 1, "revenue": 525000000, "ebitda": 105000000, "ufcf": 78750000},
    {"year": 2, "revenue": 556500000, "ebitda": 116865000, "ufcf": 87649000},
    ...
  ]
}
```

---

### 工具4: calc_debt_schedule

**功能**：构建债务计划表

```python
# 输入
{
  "debt_tranches": [
    {"name": "senior", "amount": 320000000, "rate": 0.06, "amort": 0.05},
    {"name": "sub", "amount": 160000000, "rate": 0.10, "pik": 0.02}
  ],
  "fcf_by_year": [78750000, 87649000, ...],
  "sweep_percent": 0.75
}

# 输出
{
  "schedule": {
    "senior": [
      {"year": 1, "opening": 320000000, "interest": 19200000, "paydown": 40000000, "closing": 280000000},
      ...
    ],
    "sub": [...]
  },
  "final_debt": 180000000,
  "total_interest_paid": 156000000
}
```

---

### 工具5: calc_exit_value

**功能**：计算退出价值

```python
# 输入
{
  "exit_ebitda": 130000000,
  "exit_multiple": 8.0
}

# 输出
{
  "value": 1040000000,
  "formula": "Exit EBITDA × Exit Multiple",
  "inputs": {"exit_ebitda": 130000000, "exit_multiple": 8.0}
}
```

**替代方式**：LLM可以用P/E倍数、DCF或其他方式计算退出价值

---

### 工具6: calc_equity_proceeds

**功能**：计算股权所得

```python
# 输入
{
  "exit_value": 1040000000,
  "ending_debt": 180000000,
  "ending_cash": 20000000
}

# 输出
{
  "value": 880000000,
  "formula": "Exit Value - Net Debt",
  "inputs": {...}
}
```

---

### 工具7: calc_irr

**功能**：计算内部收益率

```python
# 输入
{
  "cash_flows": [-344000000, 0, 0, 0, 0, 880000000]
}

# 输出
{
  "value": 0.207,
  "formula": "IRR(Cash Flows)",
  "inputs": {"cash_flows": [...], "years": 5}
}
```

---

### 工具8: calc_moic

**功能**：计算投资倍数

```python
# 输入
{
  "equity_invested": 344000000,
  "equity_proceeds": 880000000,
  "distributions": 0
}

# 输出
{
  "value": 2.56,
  "formula": "(Proceeds + Distributions) / Invested",
  "inputs": {...}
}
```

---

### 工具9: export_excel

**功能**：导出Excel报告

```python
# 输入
{
  "transaction": {...},
  "operations": {...},
  "debt_schedule": {...},
  "exit": {...},
  "returns": {...},
  "filename": "lbo_analysis.xlsx"
}

# 输出
{
  "status": "success",
  "filepath": "lbo_analysis.xlsx"
}
```

---

## 4.3 覆盖与追溯

当LLM跳过某个工具自己计算时，应记录追溯信息：

```python
# LLM自己算的收购价
{
  "value": 750000000,
  "formula": "用户自定义",
  "inputs": {
    "source": "llm_calculated",
    "method": "净资产 × 1.3",
    "note": "用户要求用净资产+30%溢价"
  }
}
```

这样：
- 后续工具正常使用这个值
- 追溯链完整，知道这个值怎么来的
- Excel导出时可以标注"用户自定义"

---

## 4.4 便捷入口

保留 `lbo.build()` 作为快捷方式，内部调用原子工具：

```python
# 简单场景：一键完成
result = lbo.build(inputs)

# 等价于依次调用：
# calc_purchase_price → calc_sources_uses → project_operations
# → calc_debt_schedule → calc_exit_value → calc_equity_proceeds
# → calc_irr → calc_moic
```

LLM可以根据用户需求选择：
- 全部默认 → 调 `build()`
- 部分自定义 → 调单个原子工具组合

---

## 4.5 M&A 原子工具清单

| 工具名 | 功能 | 可替代 |
|--------|------|--------|
| `calc_offer_price` | 计算报价 | 可用其他估值方法 |
| `calc_funding_mix` | 融资结构 | 可自定义现金/股票比例 |
| `calc_goodwill` | 商誉计算 | 可调整公允价值 |
| `calc_pro_forma` | 合并报表 | 可加入自定义调整 |
| `calc_accretion_dilution` | 增厚/稀释 | - |
| `calc_synergies` | 协同效应 | 可自定义协同假设 |
| `calc_breakeven` | 盈亏平衡 | - |

---

## 4.6 实现优先级

| 阶段 | 内容 | 状态 |
|------|------|------|
| P0 | LBO模型基础实现 | ✅ 已完成 |
| P0 | 测试用例 (89%覆盖率) | ✅ 已完成 |
| P0 | Excel导出 | ✅ 已完成 |
| P1 | **原子工具拆分** | 🔲 待做 |
| P1 | 覆盖与追溯机制 | 🔲 待做 |
| P2 | M&A模型实现 | 🔲 待做 |
| P2 | M&A原子工具 | 🔲 待做 |
