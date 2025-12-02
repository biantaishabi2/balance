# 财务建模工具设计

## 概述

本文档定义两类核心建模工具：
1. **三表模型工具** - 预测利润表、资产负债表、现金流量表
2. **DCF估值工具** - 基于自由现金流折现估算企业价值

两者关系：**DCF 依赖三表模型**（需要先有三表才能算 FCF）

```
┌─────────────────┐      ┌─────────────────┐
│   三表模型工具   │ ───→ │   DCF估值工具   │
│                 │      │                 │
│ • 利润表        │      │ • FCFF计算      │
│ • 资产负债表    │      │ • WACC计算      │
│ • 现金流量表    │      │ • 终值计算      │
│                 │      │ • 敏感性分析    │
└─────────────────┘      └─────────────────┘
```

---

## 一、三表模型工具

### 1.1 工具清单

| 工具名 | 功能 | 公式 |
|--------|------|------|
| `revenue_forecast` | 收入预测 | `revenue = last_revenue × (1 + growth_rate)` |
| `cost_forecast` | 成本预测 | `cost = revenue × (1 - gross_margin)` |
| `opex_forecast` | 费用预测 | `opex = revenue × opex_ratio` |
| `working_capital` | 营运资本 | `AR = revenue / 365 × ar_days` |
| `depreciation` | 折旧计算 | `dep = (cost - salvage) / useful_life` |
| `interest` | 利息计算 | `interest = debt × interest_rate` |
| `tax` | 所得税计算 | `tax = max(ebt, 0) × tax_rate` |
| `balance_check` | 配平检验 | `assets = liabilities + equity` |

### 1.2 输入格式 (JSON)

```json
{
  "base_data": {
    "last_revenue": 28307198.70,
    "last_cost": 21142714.70,
    "opening_cash": 32424158.60,
    "opening_debt": 9375638.80,
    "opening_equity": 27345617.40,
    "opening_receivable": 6648123.50,
    "opening_payable": 21492614.50,
    "opening_inventory": 8021155.80,
    "fixed_assets": 12862270.20,
    "accum_depreciation": 1286227.02
  },

  "assumptions": {
    "growth_rate": 0.09,
    "gross_margin": 0.253,
    "opex_ratio": 0.097,
    "ar_days": 64,
    "ap_days": 120,
    "inv_days": 102,
    "capex_ratio": 0.042,
    "interest_rate": 0.0233,
    "tax_rate": 0.1386,
    "depreciation_years": 10
  }
}
```

### 1.3 输出格式 (JSON，带追溯)

```json
{
  "income_statement": {
    "revenue": {
      "value": 30854846.58,
      "formula": "last_revenue × (1 + growth_rate)",
      "inputs": {
        "last_revenue": 28307198.70,
        "growth_rate": 0.09
      }
    },
    "cost": {
      "value": 23048570.40,
      "formula": "revenue × (1 - gross_margin)",
      "inputs": {
        "revenue": 30854846.58,
        "gross_margin": 0.253
      }
    },
    "gross_profit": {
      "value": 7806276.18,
      "formula": "revenue - cost",
      "inputs": {
        "revenue": 30854846.58,
        "cost": 23048570.40
      }
    },
    "opex": {
      "value": 2992920.12,
      "formula": "revenue × opex_ratio",
      "inputs": {
        "revenue": 30854846.58,
        "opex_ratio": 0.097
      }
    },
    "ebit": {
      "value": 4813356.06,
      "formula": "gross_profit - opex",
      "inputs": {
        "gross_profit": 7806276.18,
        "opex": 2992920.12
      }
    },
    "interest": {
      "value": 218526.49,
      "formula": "opening_debt × interest_rate",
      "inputs": {
        "opening_debt": 9375638.80,
        "interest_rate": 0.0233
      }
    },
    "ebt": {
      "value": 4594829.57,
      "formula": "ebit - interest",
      "inputs": {
        "ebit": 4813356.06,
        "interest": 218526.49
      }
    },
    "tax": {
      "value": 636843.38,
      "formula": "ebt × tax_rate",
      "inputs": {
        "ebt": 4594829.57,
        "tax_rate": 0.1386
      }
    },
    "net_income": {
      "value": 3957986.19,
      "formula": "ebt - tax",
      "inputs": {
        "ebt": 4594829.57,
        "tax": 636843.38
      }
    }
  },

  "balance_sheet": {
    "assets": {
      "cash": {...},
      "accounts_receivable": {...},
      "inventory": {...},
      "fixed_assets_net": {...},
      "total_assets": {...}
    },
    "liabilities": {
      "accounts_payable": {...},
      "debt": {...},
      "total_liabilities": {...}
    },
    "equity": {
      "equity_capital": {...},
      "retained_earnings": {...},
      "total_equity": {...}
    }
  },

  "cash_flow": {
    "operating": {
      "net_income": {...},
      "add_depreciation": {...},
      "delta_working_capital": {...},
      "operating_cash_flow": {...}
    },
    "investing": {
      "capex": {...},
      "investing_cash_flow": {...}
    },
    "financing": {
      "debt_change": {...},
      "dividends": {...},
      "financing_cash_flow": {...}
    },
    "net_cash_change": {...}
  },

  "validation": {
    "balance_sheet_balanced": true,
    "cash_flow_reconciled": true,
    "balance_diff": 0.0
  }
}
```

### 1.4 工具实现

```python
# tools/three_statement.py

import pandas as pd
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class ModelResult:
    """模型计算结果（带追溯）"""
    value: float
    formula: str
    inputs: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "formula": self.formula,
            "inputs": self.inputs
        }


class ThreeStatementModel:
    """
    三表模型工具集

    使用方法:
        model = ThreeStatementModel(base_data)
        result = model.build(assumptions)
    """

    def __init__(self, base_data: dict):
        """
        初始化模型

        Args:
            base_data: 基础财报数据（上期数据）
        """
        self.base = base_data
        self.results = {}

    # ==================== 利润表工具 ====================

    def forecast_revenue(self, growth_rate: float) -> ModelResult:
        """
        收入预测

        公式: revenue = last_revenue × (1 + growth_rate)

        Args:
            growth_rate: 收入增长率 (如 0.09 表示 9%)

        Returns:
            ModelResult: 包含值、公式、输入的结果对象
        """
        last_rev = self.base['last_revenue']
        value = last_rev * (1 + growth_rate)

        return ModelResult(
            value=value,
            formula="last_revenue × (1 + growth_rate)",
            inputs={"last_revenue": last_rev, "growth_rate": growth_rate}
        )

    def forecast_cost(self, revenue: float, gross_margin: float) -> ModelResult:
        """
        成本预测

        公式: cost = revenue × (1 - gross_margin)

        Args:
            revenue: 营业收入
            gross_margin: 毛利率 (如 0.253 表示 25.3%)

        Returns:
            ModelResult
        """
        value = revenue * (1 - gross_margin)

        return ModelResult(
            value=value,
            formula="revenue × (1 - gross_margin)",
            inputs={"revenue": revenue, "gross_margin": gross_margin}
        )

    def forecast_opex(self, revenue: float, opex_ratio: float) -> ModelResult:
        """
        费用预测

        公式: opex = revenue × opex_ratio
        """
        value = revenue * opex_ratio

        return ModelResult(
            value=value,
            formula="revenue × opex_ratio",
            inputs={"revenue": revenue, "opex_ratio": opex_ratio}
        )

    def calc_interest(self, debt: float, interest_rate: float) -> ModelResult:
        """
        利息计算

        公式: interest = debt × interest_rate
        """
        value = debt * interest_rate

        return ModelResult(
            value=value,
            formula="debt × interest_rate",
            inputs={"debt": debt, "interest_rate": interest_rate}
        )

    def calc_tax(self, ebt: float, tax_rate: float) -> ModelResult:
        """
        所得税计算

        公式: tax = max(ebt, 0) × tax_rate
        注意: 亏损时税为0（简化处理，不考虑递延税）
        """
        value = max(ebt, 0) * tax_rate

        return ModelResult(
            value=value,
            formula="max(ebt, 0) × tax_rate",
            inputs={"ebt": ebt, "tax_rate": tax_rate}
        )

    # ==================== 资产负债表工具 ====================

    def calc_working_capital(self,
                             revenue: float,
                             cost: float,
                             ar_days: float,
                             ap_days: float,
                             inv_days: float) -> Dict[str, ModelResult]:
        """
        营运资本预测

        公式:
            AR = revenue / 365 × ar_days
            AP = cost / 365 × ap_days
            Inv = cost / 365 × inv_days
        """
        ar = revenue / 365 * ar_days
        ap = cost / 365 * ap_days
        inv = cost / 365 * inv_days

        return {
            "accounts_receivable": ModelResult(
                value=ar,
                formula="revenue / 365 × ar_days",
                inputs={"revenue": revenue, "ar_days": ar_days}
            ),
            "accounts_payable": ModelResult(
                value=ap,
                formula="cost / 365 × ap_days",
                inputs={"cost": cost, "ap_days": ap_days}
            ),
            "inventory": ModelResult(
                value=inv,
                formula="cost / 365 × inv_days",
                inputs={"cost": cost, "inv_days": inv_days}
            )
        }

    def calc_depreciation(self,
                          fixed_assets: float,
                          useful_life: float,
                          salvage: float = 0) -> ModelResult:
        """
        折旧计算（直线法）

        公式: depreciation = (fixed_assets - salvage) / useful_life
        """
        value = (fixed_assets - salvage) / useful_life

        return ModelResult(
            value=value,
            formula="(fixed_assets - salvage) / useful_life",
            inputs={
                "fixed_assets": fixed_assets,
                "salvage": salvage,
                "useful_life": useful_life
            }
        )

    # ==================== 现金流量表工具 ====================

    def calc_operating_cash_flow(self,
                                  net_income: float,
                                  depreciation: float,
                                  delta_ar: float,
                                  delta_inv: float,
                                  delta_ap: float) -> ModelResult:
        """
        经营现金流计算（间接法）

        公式: OCF = net_income + depreciation - Δar - Δinv + Δap
        """
        delta_nwc = delta_ar + delta_inv - delta_ap
        value = net_income + depreciation - delta_nwc

        return ModelResult(
            value=value,
            formula="net_income + depreciation - ΔNWC",
            inputs={
                "net_income": net_income,
                "depreciation": depreciation,
                "delta_ar": delta_ar,
                "delta_inv": delta_inv,
                "delta_ap": delta_ap,
                "delta_nwc": delta_nwc
            }
        )

    # ==================== 配平检验 ====================

    def check_balance(self,
                      total_assets: float,
                      total_liabilities: float,
                      total_equity: float) -> Dict[str, Any]:
        """
        资产负债表配平检验

        公式: assets = liabilities + equity
        """
        diff = total_assets - (total_liabilities + total_equity)
        is_balanced = abs(diff) < 0.01  # 允许0.01的误差

        return {
            "is_balanced": is_balanced,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "total_equity": total_equity,
            "difference": diff
        }

    # ==================== 主构建方法 ====================

    def build(self, assumptions: dict) -> dict:
        """
        构建完整三表模型

        Args:
            assumptions: 驱动假设

        Returns:
            dict: 完整的三表数据（带追溯信息）
        """
        # 利润表
        revenue = self.forecast_revenue(assumptions['growth_rate'])
        cost = self.forecast_cost(revenue.value, assumptions['gross_margin'])
        opex = self.forecast_opex(revenue.value, assumptions['opex_ratio'])

        gross_profit = revenue.value - cost.value
        ebit = gross_profit - opex.value

        interest = self.calc_interest(
            self.base['opening_debt'],
            assumptions['interest_rate']
        )
        ebt = ebit - interest.value
        tax = self.calc_tax(ebt, assumptions['tax_rate'])
        net_income = ebt - tax.value

        # 营运资本
        wc = self.calc_working_capital(
            revenue.value, cost.value,
            assumptions['ar_days'],
            assumptions['ap_days'],
            assumptions['inv_days']
        )

        # 折旧
        depreciation = self.calc_depreciation(
            self.base['fixed_assets'],
            assumptions['depreciation_years']
        )

        # 组装结果
        result = {
            "income_statement": {
                "revenue": revenue.to_dict(),
                "cost": cost.to_dict(),
                "gross_profit": {
                    "value": gross_profit,
                    "formula": "revenue - cost",
                    "inputs": {"revenue": revenue.value, "cost": cost.value}
                },
                "opex": opex.to_dict(),
                "ebit": {
                    "value": ebit,
                    "formula": "gross_profit - opex",
                    "inputs": {"gross_profit": gross_profit, "opex": opex.value}
                },
                "interest": interest.to_dict(),
                "ebt": {
                    "value": ebt,
                    "formula": "ebit - interest",
                    "inputs": {"ebit": ebit, "interest": interest.value}
                },
                "tax": tax.to_dict(),
                "net_income": {
                    "value": net_income,
                    "formula": "ebt - tax",
                    "inputs": {"ebt": ebt, "tax": tax.value}
                }
            },
            "working_capital": {
                k: v.to_dict() for k, v in wc.items()
            },
            "depreciation": depreciation.to_dict()
        }

        return result
```

---

## 二、DCF 估值工具

### 2.1 工具清单

| 工具名 | 功能 | 公式 |
|--------|------|------|
| `calc_fcff` | 企业自由现金流 | `FCFF = EBIT×(1-t) + D&A - CapEx - ΔNWC` |
| `calc_fcfe` | 股权自由现金流 | `FCFE = FCFF - Interest×(1-t) + ΔDebt` |
| `calc_capm` | 股权成本(CAPM) | `Re = Rf + β × MRP` |
| `calc_wacc` | 加权资本成本 | `WACC = E/(D+E)×Re + D/(D+E)×Rd×(1-t)` |
| `calc_terminal_value` | 终值(永续增长) | `TV = FCF×(1+g) / (WACC-g)` |
| `calc_terminal_multiple` | 终值(退出倍数) | `TV = EBITDA × Exit_Multiple` |
| `calc_dcf_value` | 企业价值 | `EV = Σ FCF/(1+r)^t + TV/(1+r)^n` |
| `calc_equity_value` | 股权价值 | `Equity = EV - Debt + Cash` |
| `sensitivity_analysis` | 敏感性分析 | WACC × g 矩阵 |

### 2.2 输入格式 (JSON)

```json
{
  "fcf_projections": {
    "year_1": 1000000,
    "year_2": 1100000,
    "year_3": 1210000,
    "year_4": 1331000,
    "year_5": 1464100
  },

  "wacc_inputs": {
    "risk_free_rate": 0.03,
    "beta": 1.2,
    "market_risk_premium": 0.05,
    "cost_of_debt": 0.04,
    "tax_rate": 0.25,
    "debt_ratio": 0.30
  },

  "terminal_inputs": {
    "method": "perpetual_growth",
    "terminal_growth": 0.02,
    "exit_multiple": null
  },

  "balance_sheet_adjustments": {
    "cash": 5000000,
    "debt": 3000000,
    "minority_interest": 0,
    "shares_outstanding": 1000000
  },

  "sensitivity_config": {
    "wacc_range": [0.08, 0.09, 0.10, 0.11, 0.12],
    "growth_range": [0.01, 0.015, 0.02, 0.025, 0.03]
  }
}
```

### 2.3 输出格式 (JSON，带追溯)

```json
{
  "cost_of_equity": {
    "value": 0.09,
    "formula": "Rf + β × MRP",
    "inputs": {
      "risk_free_rate": 0.03,
      "beta": 1.2,
      "market_risk_premium": 0.05
    }
  },

  "wacc": {
    "value": 0.0745,
    "formula": "E/(D+E) × Re + D/(D+E) × Rd × (1-t)",
    "inputs": {
      "cost_of_equity": 0.09,
      "cost_of_debt": 0.04,
      "tax_rate": 0.25,
      "debt_ratio": 0.30,
      "equity_ratio": 0.70
    }
  },

  "fcf_present_values": {
    "year_1": {
      "fcf": 1000000,
      "discount_factor": 0.9307,
      "present_value": 930700
    },
    "year_2": {...},
    "...": "..."
  },

  "terminal_value": {
    "value": 27400000,
    "formula": "FCF × (1+g) / (WACC - g)",
    "inputs": {
      "final_fcf": 1464100,
      "terminal_growth": 0.02,
      "wacc": 0.0745
    },
    "present_value": 19100000
  },

  "enterprise_value": {
    "value": 25000000,
    "formula": "Σ PV(FCF) + PV(TV)",
    "inputs": {
      "pv_of_fcf": 5900000,
      "pv_of_terminal": 19100000
    }
  },

  "equity_value": {
    "value": 27000000,
    "formula": "EV - Debt + Cash",
    "inputs": {
      "enterprise_value": 25000000,
      "debt": 3000000,
      "cash": 5000000
    }
  },

  "per_share_value": {
    "value": 27.00,
    "formula": "Equity Value / Shares",
    "inputs": {
      "equity_value": 27000000,
      "shares_outstanding": 1000000
    }
  },

  "sensitivity_matrix": {
    "headers": {
      "rows": "WACC",
      "columns": "Terminal Growth"
    },
    "data": [
      {"wacc": "8.0%", "g=1.0%": 32.5, "g=1.5%": 35.2, "g=2.0%": 38.4},
      {"wacc": "9.0%", "g=1.0%": 28.1, "g=1.5%": 30.2, "g=2.0%": 32.8},
      {"wacc": "10.0%", "g=1.0%": 24.5, "g=1.5%": 26.1, "g=2.0%": 28.0}
    ]
  }
}
```

### 2.4 工具实现

```python
# tools/dcf.py

import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

@dataclass
class ModelResult:
    """模型计算结果（带追溯）"""
    value: float
    formula: str
    inputs: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "formula": self.formula,
            "inputs": self.inputs
        }


class DCFModel:
    """
    DCF估值工具集

    使用方法:
        dcf = DCFModel()
        wacc = dcf.calc_wacc(...)
        ev = dcf.calc_enterprise_value(...)
    """

    # ==================== 自由现金流计算 ====================

    def calc_fcff(self,
                  ebit: float,
                  tax_rate: float,
                  depreciation: float,
                  capex: float,
                  delta_nwc: float) -> ModelResult:
        """
        企业自由现金流 (Free Cash Flow to Firm)

        公式: FCFF = EBIT × (1-t) + D&A - CapEx - ΔNWC

        Args:
            ebit: 息税前利润
            tax_rate: 税率
            depreciation: 折旧与摊销
            capex: 资本支出
            delta_nwc: 净营运资本变动

        Returns:
            ModelResult
        """
        nopat = ebit * (1 - tax_rate)
        value = nopat + depreciation - capex - delta_nwc

        return ModelResult(
            value=value,
            formula="EBIT × (1-t) + D&A - CapEx - ΔNWC",
            inputs={
                "ebit": ebit,
                "tax_rate": tax_rate,
                "nopat": nopat,
                "depreciation": depreciation,
                "capex": capex,
                "delta_nwc": delta_nwc
            }
        )

    def calc_fcfe(self,
                  fcff: float,
                  interest: float,
                  tax_rate: float,
                  delta_debt: float) -> ModelResult:
        """
        股权自由现金流 (Free Cash Flow to Equity)

        公式: FCFE = FCFF - Interest × (1-t) + ΔDebt

        Args:
            fcff: 企业自由现金流
            interest: 利息费用
            tax_rate: 税率
            delta_debt: 净借款变动

        Returns:
            ModelResult
        """
        after_tax_interest = interest * (1 - tax_rate)
        value = fcff - after_tax_interest + delta_debt

        return ModelResult(
            value=value,
            formula="FCFF - Interest × (1-t) + ΔDebt",
            inputs={
                "fcff": fcff,
                "interest": interest,
                "tax_rate": tax_rate,
                "after_tax_interest": after_tax_interest,
                "delta_debt": delta_debt
            }
        )

    # ==================== 折现率计算 ====================

    def calc_capm(self,
                  risk_free_rate: float,
                  beta: float,
                  market_risk_premium: float) -> ModelResult:
        """
        CAPM计算股权成本

        公式: Re = Rf + β × MRP

        Args:
            risk_free_rate: 无风险利率 (如10年期国债收益率)
            beta: 贝塔系数 (系统性风险)
            market_risk_premium: 市场风险溢价 (Rm - Rf)

        Returns:
            ModelResult
        """
        value = risk_free_rate + beta * market_risk_premium

        return ModelResult(
            value=value,
            formula="Rf + β × MRP",
            inputs={
                "risk_free_rate": risk_free_rate,
                "beta": beta,
                "market_risk_premium": market_risk_premium
            }
        )

    def calc_wacc(self,
                  cost_of_equity: float,
                  cost_of_debt: float,
                  tax_rate: float,
                  debt_ratio: float) -> ModelResult:
        """
        加权平均资本成本 (WACC)

        公式: WACC = E/(D+E) × Re + D/(D+E) × Rd × (1-t)

        Args:
            cost_of_equity: 股权成本 (Re)
            cost_of_debt: 债务成本 (Rd)
            tax_rate: 税率
            debt_ratio: 负债率 D/(D+E)

        Returns:
            ModelResult
        """
        equity_ratio = 1 - debt_ratio
        after_tax_debt_cost = cost_of_debt * (1 - tax_rate)
        value = equity_ratio * cost_of_equity + debt_ratio * after_tax_debt_cost

        return ModelResult(
            value=value,
            formula="E/(D+E) × Re + D/(D+E) × Rd × (1-t)",
            inputs={
                "cost_of_equity": cost_of_equity,
                "cost_of_debt": cost_of_debt,
                "tax_rate": tax_rate,
                "debt_ratio": debt_ratio,
                "equity_ratio": equity_ratio,
                "after_tax_debt_cost": after_tax_debt_cost
            }
        )

    # ==================== 终值计算 ====================

    def calc_terminal_value_perpetual(self,
                                       final_fcf: float,
                                       wacc: float,
                                       terminal_growth: float) -> ModelResult:
        """
        永续增长法计算终值

        公式: TV = FCF × (1+g) / (WACC - g)

        Args:
            final_fcf: 预测期最后一年的FCF
            wacc: 加权平均资本成本
            terminal_growth: 永续增长率

        Returns:
            ModelResult

        注意:
            - terminal_growth 必须小于 wacc
            - 一般用GDP增速或通胀率作为参考 (1%-3%)
        """
        if terminal_growth >= wacc:
            raise ValueError(f"Terminal growth ({terminal_growth}) must be less than WACC ({wacc})")

        value = final_fcf * (1 + terminal_growth) / (wacc - terminal_growth)

        return ModelResult(
            value=value,
            formula="FCF × (1+g) / (WACC - g)",
            inputs={
                "final_fcf": final_fcf,
                "terminal_growth": terminal_growth,
                "wacc": wacc
            }
        )

    def calc_terminal_value_multiple(self,
                                      final_ebitda: float,
                                      exit_multiple: float) -> ModelResult:
        """
        退出倍数法计算终值

        公式: TV = EBITDA × Exit Multiple

        Args:
            final_ebitda: 预测期最后一年的EBITDA
            exit_multiple: 退出倍数 (行业可比公司的EV/EBITDA)

        Returns:
            ModelResult
        """
        value = final_ebitda * exit_multiple

        return ModelResult(
            value=value,
            formula="EBITDA × Exit_Multiple",
            inputs={
                "final_ebitda": final_ebitda,
                "exit_multiple": exit_multiple
            }
        )

    # ==================== 估值计算 ====================

    def calc_enterprise_value(self,
                               fcf_list: List[float],
                               wacc: float,
                               terminal_value: float) -> ModelResult:
        """
        计算企业价值

        公式: EV = Σ FCF/(1+WACC)^t + TV/(1+WACC)^n

        Args:
            fcf_list: 各年FCF列表
            wacc: 折现率
            terminal_value: 终值

        Returns:
            ModelResult
        """
        # 计算各期FCF现值
        pv_fcf_list = []
        for t, fcf in enumerate(fcf_list):
            discount_factor = 1 / (1 + wacc) ** (t + 1)
            pv = fcf * discount_factor
            pv_fcf_list.append({
                "year": t + 1,
                "fcf": fcf,
                "discount_factor": discount_factor,
                "present_value": pv
            })

        pv_fcf_total = sum(item["present_value"] for item in pv_fcf_list)

        # 计算终值现值
        n = len(fcf_list)
        pv_terminal = terminal_value / (1 + wacc) ** n

        # 企业价值
        value = pv_fcf_total + pv_terminal

        return ModelResult(
            value=value,
            formula="Σ FCF/(1+WACC)^t + TV/(1+WACC)^n",
            inputs={
                "pv_of_fcf": pv_fcf_total,
                "pv_of_terminal": pv_terminal,
                "terminal_value": terminal_value,
                "wacc": wacc,
                "projection_years": n,
                "fcf_details": pv_fcf_list
            }
        )

    def calc_equity_value(self,
                           enterprise_value: float,
                           debt: float,
                           cash: float,
                           minority_interest: float = 0) -> ModelResult:
        """
        计算股权价值

        公式: Equity = EV - Debt + Cash - Minority Interest

        Args:
            enterprise_value: 企业价值
            debt: 有息负债
            cash: 现金及等价物
            minority_interest: 少数股东权益

        Returns:
            ModelResult
        """
        value = enterprise_value - debt + cash - minority_interest

        return ModelResult(
            value=value,
            formula="EV - Debt + Cash - Minority",
            inputs={
                "enterprise_value": enterprise_value,
                "debt": debt,
                "cash": cash,
                "minority_interest": minority_interest
            }
        )

    def calc_per_share_value(self,
                              equity_value: float,
                              shares_outstanding: float) -> ModelResult:
        """
        计算每股价值

        公式: Per Share Value = Equity Value / Shares Outstanding
        """
        value = equity_value / shares_outstanding

        return ModelResult(
            value=value,
            formula="Equity Value / Shares Outstanding",
            inputs={
                "equity_value": equity_value,
                "shares_outstanding": shares_outstanding
            }
        )

    # ==================== 敏感性分析 ====================

    def sensitivity_analysis(self,
                              fcf_list: List[float],
                              wacc_range: List[float],
                              growth_range: List[float],
                              debt: float,
                              cash: float,
                              shares: float) -> pd.DataFrame:
        """
        敏感性分析矩阵

        生成 WACC × Terminal Growth 的每股价值矩阵

        Args:
            fcf_list: 各年FCF
            wacc_range: WACC范围 [0.08, 0.09, 0.10, ...]
            growth_range: 永续增长率范围 [0.01, 0.02, ...]
            debt: 负债
            cash: 现金
            shares: 股数

        Returns:
            pd.DataFrame: 敏感性矩阵
        """
        matrix = []

        for wacc in wacc_range:
            row = {"WACC": f"{wacc:.1%}"}
            for g in growth_range:
                try:
                    # 终值
                    tv = self.calc_terminal_value_perpetual(
                        fcf_list[-1], wacc, g
                    )
                    # 企业价值
                    ev = self.calc_enterprise_value(
                        fcf_list, wacc, tv.value
                    )
                    # 股权价值
                    eq = self.calc_equity_value(
                        ev.value, debt, cash
                    )
                    # 每股价值
                    per_share = eq.value / shares
                    row[f"g={g:.1%}"] = round(per_share, 2)
                except ValueError:
                    row[f"g={g:.1%}"] = "N/A"

            matrix.append(row)

        return pd.DataFrame(matrix).set_index("WACC")

    # ==================== 主估值方法 ====================

    def valuate(self, inputs: dict) -> dict:
        """
        执行完整DCF估值

        Args:
            inputs: DCF输入参数 (见输入格式)

        Returns:
            dict: 完整估值结果 (见输出格式)
        """
        # WACC计算
        wacc_inputs = inputs['wacc_inputs']

        re = self.calc_capm(
            wacc_inputs['risk_free_rate'],
            wacc_inputs['beta'],
            wacc_inputs['market_risk_premium']
        )

        wacc = self.calc_wacc(
            re.value,
            wacc_inputs['cost_of_debt'],
            wacc_inputs['tax_rate'],
            wacc_inputs['debt_ratio']
        )

        # FCF列表
        fcf_list = list(inputs['fcf_projections'].values())

        # 终值
        term_inputs = inputs['terminal_inputs']
        if term_inputs['method'] == 'perpetual_growth':
            tv = self.calc_terminal_value_perpetual(
                fcf_list[-1],
                wacc.value,
                term_inputs['terminal_growth']
            )
        else:
            tv = self.calc_terminal_value_multiple(
                fcf_list[-1] * 1.2,  # 假设EBITDA
                term_inputs['exit_multiple']
            )

        # 企业价值
        ev = self.calc_enterprise_value(fcf_list, wacc.value, tv.value)

        # 股权价值
        bs = inputs['balance_sheet_adjustments']
        equity = self.calc_equity_value(ev.value, bs['debt'], bs['cash'])

        # 每股价值
        per_share = self.calc_per_share_value(equity.value, bs['shares_outstanding'])

        # 敏感性分析
        sens_config = inputs.get('sensitivity_config', {})
        sensitivity = None
        if sens_config:
            sensitivity = self.sensitivity_analysis(
                fcf_list,
                sens_config['wacc_range'],
                sens_config['growth_range'],
                bs['debt'],
                bs['cash'],
                bs['shares_outstanding']
            )

        return {
            "cost_of_equity": re.to_dict(),
            "wacc": wacc.to_dict(),
            "terminal_value": tv.to_dict(),
            "enterprise_value": ev.to_dict(),
            "equity_value": equity.to_dict(),
            "per_share_value": per_share.to_dict(),
            "sensitivity_matrix": sensitivity.to_dict() if sensitivity is not None else None
        }
```

---

## 三、JSON API 接口

### 3.1 三表模型接口

```python
# api/three_statement_api.py

import json
from tools.three_statement import ThreeStatementModel

def run_three_statement(input_json: str) -> str:
    """
    三表模型API

    Args:
        input_json: 输入JSON字符串

    Returns:
        str: 输出JSON字符串（带追溯）
    """
    data = json.loads(input_json)

    model = ThreeStatementModel(data['base_data'])
    result = model.build(data['assumptions'])

    return json.dumps(result, ensure_ascii=False, indent=2)
```

### 3.2 DCF估值接口

```python
# api/dcf_api.py

import json
from tools.dcf import DCFModel

def run_dcf(input_json: str) -> str:
    """
    DCF估值API

    Args:
        input_json: 输入JSON字符串

    Returns:
        str: 输出JSON字符串（带追溯）
    """
    data = json.loads(input_json)

    dcf = DCFModel()
    result = dcf.valuate(data)

    return json.dumps(result, ensure_ascii=False, indent=2)
```

### 3.3 使用示例

```python
# 三表模型
input_3s = """
{
  "base_data": {"last_revenue": 28307198.70, ...},
  "assumptions": {"growth_rate": 0.09, ...}
}
"""
output_3s = run_three_statement(input_3s)
print(output_3s)

# DCF估值
input_dcf = """
{
  "fcf_projections": {"year_1": 1000000, ...},
  "wacc_inputs": {"risk_free_rate": 0.03, ...},
  "terminal_inputs": {"method": "perpetual_growth", "terminal_growth": 0.02},
  "balance_sheet_adjustments": {"cash": 5000000, "debt": 3000000, ...}
}
"""
output_dcf = run_dcf(input_dcf)
print(output_dcf)
```

---

## 四、工具对比总结

| 维度 | 三表模型 | DCF模型 |
|------|---------|---------|
| **目的** | 预测财务状况 | 估算公司价值 |
| **输入** | 历史数据 + 增长假设 | 三表数据 + 折现参数 |
| **输出** | 利润表/资产负债表/现金流量表 | 企业价值/股权价值/每股价值 |
| **核心公式** | 收入×毛利率、周转天数 | FCFF、WACC、终值 |
| **依赖关系** | 独立 | 依赖三表模型 |
| **验证方式** | 资产=负债+权益 | 敏感性分析合理性 |

---

## 五、扩展方向

1. **递延税模块** - 处理亏损抵扣、加速折旧等
2. **租赁资本化** - IFRS 16 使用权资产
3. **LBO模型** - 杠杆收购估值
4. **并购模型** - 合并报表、协同效应
5. **蒙特卡洛** - 概率分布模拟
