# -*- coding: utf-8 -*-
"""
三表模型原子工具

独立的、可组合的三表模型计算工具，供LLM灵活调用。

设计原则:
1. 每个工具独立运行，不依赖类状态
2. 输入输出清晰（dict格式，可序列化为JSON）
3. 可自由组合，LLM可以跳过、替换、插入任何步骤
4. 期初数据作为参数显式传递
5. 保留计算追溯信息

工具清单:
- forecast_revenue: 收入预测
- forecast_cost: 成本预测
- forecast_opex: 费用预测
- calc_income_statement: 完整利润表计算
- calc_working_capital: 营运资本计算
- calc_depreciation: 折旧计算
- calc_capex: 资本支出
- calc_operating_cash_flow: 经营现金流（间接法）
- calc_cash_flow_statement: 完整现金流量表
- check_balance: 资产负债表配平检验
- three_statement_quick_build: 快捷构建入口
"""

from typing import Dict, List, Any, Optional, Union


def forecast_revenue(
    last_revenue: float,
    growth_rate: float,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具1: 收入预测

    公式: revenue = last_revenue × (1 + growth_rate)

    Args:
        last_revenue: 上期收入
        growth_rate: 收入增长率（如 0.09 表示 9%）
        source: 计算来源标记 ("tool" 或 "llm_override")

    Returns:
        dict: {
            "value": 预测收入,
            "formula": 公式说明,
            "inputs": 输入参数,
            "source": 计算来源
        }

    示例:
        >>> result = forecast_revenue(500_000_000, 0.09)
        >>> result["value"]
        545000000.0
    """
    value = last_revenue * (1 + growth_rate)

    return {
        "value": value,
        "formula": "last_revenue × (1 + growth_rate)",
        "inputs": {
            "last_revenue": last_revenue,
            "growth_rate": growth_rate
        },
        "source": source
    }


def forecast_cost(
    revenue: float,
    gross_margin: float,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具2: 成本预测

    公式: cost = revenue × (1 - gross_margin)

    Args:
        revenue: 营业收入
        gross_margin: 毛利率（如 0.25 表示 25%）
        source: 计算来源标记

    Returns:
        dict: {
            "value": 预测成本,
            "formula": 公式说明,
            "inputs": 输入参数,
            "source": 计算来源
        }

    示例:
        >>> result = forecast_cost(545_000_000, 0.25)
        >>> result["value"]
        408750000.0
    """
    value = revenue * (1 - gross_margin)

    return {
        "value": value,
        "formula": "revenue × (1 - gross_margin)",
        "inputs": {
            "revenue": revenue,
            "gross_margin": gross_margin
        },
        "source": source
    }


def forecast_opex(
    revenue: float,
    opex_ratio: float,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具3: 费用预测

    公式: opex = revenue × opex_ratio

    Args:
        revenue: 营业收入
        opex_ratio: 费用率（如 0.12 表示 12%）
        source: 计算来源标记

    Returns:
        dict: {
            "value": 预测费用,
            "formula": 公式说明,
            "inputs": 输入参数,
            "source": 计算来源
        }

    示例:
        >>> result = forecast_opex(545_000_000, 0.12)
        >>> result["value"]
        65400000.0
    """
    value = revenue * opex_ratio

    return {
        "value": value,
        "formula": "revenue × opex_ratio",
        "inputs": {
            "revenue": revenue,
            "opex_ratio": opex_ratio
        },
        "source": source
    }


def calc_income_statement(
    revenue: float,
    cost: float,
    opex: float,
    interest: float,
    tax_rate: float,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具4: 完整利润表计算

    计算从毛利到净利润的完整利润表

    Args:
        revenue: 营业收入
        cost: 营业成本
        opex: 营业费用（销售+管理+研发）
        interest: 利息费用
        tax_rate: 税率
        source: 计算来源标记

    Returns:
        dict: {
            "gross_profit": 毛利,
            "ebit": 营业利润,
            "ebt": 税前利润,
            "tax": 所得税,
            "net_income": 净利润,
            "details": 明细,
            "source": 计算来源
        }

    示例:
        >>> result = calc_income_statement(545_000_000, 408_750_000, 65_400_000, 5_000_000, 0.25)
        >>> result["net_income"] > 0
        True
    """
    gross_profit = revenue - cost
    ebit = gross_profit - opex
    ebt = ebit - interest
    tax = max(ebt, 0) * tax_rate  # 亏损时不交税
    net_income = ebt - tax

    return {
        "gross_profit": gross_profit,
        "ebit": ebit,
        "ebt": ebt,
        "tax": tax,
        "net_income": net_income,
        "details": {
            "revenue": {
                "value": revenue,
                "formula": "input"
            },
            "cost": {
                "value": cost,
                "formula": "input"
            },
            "gross_profit": {
                "value": gross_profit,
                "formula": "revenue - cost"
            },
            "gross_margin": {
                "value": gross_profit / revenue if revenue > 0 else 0,
                "formula": "gross_profit / revenue"
            },
            "opex": {
                "value": opex,
                "formula": "input"
            },
            "ebit": {
                "value": ebit,
                "formula": "gross_profit - opex"
            },
            "ebit_margin": {
                "value": ebit / revenue if revenue > 0 else 0,
                "formula": "ebit / revenue"
            },
            "interest": {
                "value": interest,
                "formula": "input"
            },
            "ebt": {
                "value": ebt,
                "formula": "ebit - interest"
            },
            "tax": {
                "value": tax,
                "formula": "max(ebt, 0) × tax_rate"
            },
            "net_income": {
                "value": net_income,
                "formula": "ebt - tax"
            },
            "net_margin": {
                "value": net_income / revenue if revenue > 0 else 0,
                "formula": "net_income / revenue"
            }
        },
        "source": source
    }


def calc_working_capital(
    revenue: float,
    cost: float,
    ar_days: float,
    ap_days: float,
    inv_days: float,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具5: 营运资本计算

    公式:
        AR = revenue / 365 × ar_days
        AP = cost / 365 × ap_days
        Inv = cost / 365 × inv_days

    Args:
        revenue: 营业收入
        cost: 营业成本
        ar_days: 应收账款周转天数
        ap_days: 应付账款周转天数
        inv_days: 存货周转天数
        source: 计算来源标记

    Returns:
        dict: {
            "receivable": 应收账款,
            "payable": 应付账款,
            "inventory": 存货,
            "net_working_capital": 净营运资本,
            "formulas": 各项公式,
            "source": 计算来源
        }

    示例:
        >>> result = calc_working_capital(545_000_000, 408_750_000, 60, 45, 30)
        >>> result["receivable"] > 0
        True
    """
    receivable = revenue / 365 * ar_days
    payable = cost / 365 * ap_days
    inventory = cost / 365 * inv_days
    net_working_capital = receivable + inventory - payable

    return {
        "receivable": receivable,
        "payable": payable,
        "inventory": inventory,
        "net_working_capital": net_working_capital,
        "formulas": {
            "receivable": "revenue / 365 × ar_days",
            "payable": "cost / 365 × ap_days",
            "inventory": "cost / 365 × inv_days",
            "net_working_capital": "receivable + inventory - payable"
        },
        "inputs": {
            "revenue": revenue,
            "cost": cost,
            "ar_days": ar_days,
            "ap_days": ap_days,
            "inv_days": inv_days
        },
        "source": source
    }


def calc_depreciation(
    fixed_assets: float,
    useful_life: float,
    salvage: float = 0,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具6: 折旧计算（直线法）

    公式: depreciation = (fixed_assets - salvage) / useful_life

    Args:
        fixed_assets: 固定资产原值
        useful_life: 使用年限
        salvage: 残值（默认0）
        source: 计算来源标记

    Returns:
        dict: {
            "value": 年折旧额,
            "formula": 公式说明,
            "inputs": 输入参数,
            "source": 计算来源
        }

    示例:
        >>> result = calc_depreciation(100_000_000, 10)
        >>> result["value"]
        10000000.0
    """
    value = (fixed_assets - salvage) / useful_life if useful_life > 0 else 0

    return {
        "value": value,
        "formula": "(fixed_assets - salvage) / useful_life",
        "inputs": {
            "fixed_assets": fixed_assets,
            "salvage": salvage,
            "useful_life": useful_life
        },
        "source": source
    }


def calc_capex(
    revenue: float,
    capex_ratio: float,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具7: 资本支出计算

    公式: capex = revenue × capex_ratio

    Args:
        revenue: 营业收入
        capex_ratio: 资本支出比率（如 0.05 表示 5%）
        source: 计算来源标记

    Returns:
        dict: {
            "value": 资本支出,
            "formula": 公式说明,
            "inputs": 输入参数,
            "source": 计算来源
        }

    示例:
        >>> result = calc_capex(545_000_000, 0.05)
        >>> result["value"]
        27250000.0
    """
    value = revenue * capex_ratio

    return {
        "value": value,
        "formula": "revenue × capex_ratio",
        "inputs": {
            "revenue": revenue,
            "capex_ratio": capex_ratio
        },
        "source": source
    }


def calc_operating_cash_flow(
    net_income: float,
    depreciation: float,
    delta_ar: float,
    delta_inv: float,
    delta_ap: float,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具8: 经营现金流计算（间接法）

    公式: OCF = net_income + depreciation - Δar - Δinv + Δap

    Args:
        net_income: 净利润
        depreciation: 折旧
        delta_ar: 应收账款变动（增加为正）
        delta_inv: 存货变动（增加为正）
        delta_ap: 应付账款变动（增加为正）
        source: 计算来源标记

    Returns:
        dict: {
            "value": 经营现金流,
            "formula": 公式说明,
            "inputs": 输入参数（包含ΔNWC明细）,
            "source": 计算来源
        }

    示例:
        >>> result = calc_operating_cash_flow(49_387_500, 10_000_000, 5_000_000, 2_000_000, 3_000_000)
        >>> result["value"]
        55387500.0
    """
    delta_nwc = delta_ar + delta_inv - delta_ap
    value = net_income + depreciation - delta_nwc

    return {
        "value": value,
        "formula": "net_income + depreciation - ΔNWC",
        "inputs": {
            "net_income": net_income,
            "depreciation": depreciation,
            "delta_ar": delta_ar,
            "delta_inv": delta_inv,
            "delta_ap": delta_ap,
            "delta_nwc": delta_nwc
        },
        "source": source
    }


def calc_cash_flow_statement(
    net_income: float,
    depreciation: float,
    delta_ar: float,
    delta_inv: float,
    delta_ap: float,
    capex: float,
    dividend: float,
    delta_debt: float = 0,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具9: 完整现金流量表计算（间接法）

    计算经营、投资、筹资三类现金流

    注意：使用间接法时，净利润已包含利息费用的扣除，
    因此筹资现金流不再单独扣除利息（避免双重计算）。

    Args:
        net_income: 净利润
        depreciation: 折旧
        delta_ar: 应收账款变动
        delta_inv: 存货变动
        delta_ap: 应付账款变动
        capex: 资本支出
        dividend: 股利分配
        delta_debt: 债务变动（借款为正，还款为负）
        source: 计算来源标记

    Returns:
        dict: {
            "operating_cf": 经营现金流,
            "investing_cf": 投资现金流,
            "financing_cf": 筹资现金流,
            "net_cash_change": 净现金变动,
            "details": 明细,
            "source": 计算来源
        }

    示例:
        >>> result = calc_cash_flow_statement(
        ...     net_income=49_387_500,
        ...     depreciation=10_000_000,
        ...     delta_ar=5_000_000,
        ...     delta_inv=2_000_000,
        ...     delta_ap=3_000_000,
        ...     capex=27_250_000,
        ...     dividend=15_000_000
        ... )
        >>> "operating_cf" in result
        True
    """
    # 经营现金流（间接法：从净利润出发，利息已在净利润中扣除）
    delta_nwc = delta_ar + delta_inv - delta_ap
    operating_cf = net_income + depreciation - delta_nwc

    # 投资现金流
    investing_cf = -capex

    # 筹资现金流（不再扣除利息，因为已在净利润中扣除）
    financing_cf = -dividend + delta_debt

    # 净现金变动
    net_cash_change = operating_cf + investing_cf + financing_cf

    return {
        "operating_cf": operating_cf,
        "investing_cf": investing_cf,
        "financing_cf": financing_cf,
        "net_cash_change": net_cash_change,
        "details": {
            "operating": {
                "net_income": net_income,
                "add_depreciation": depreciation,
                "less_delta_ar": -delta_ar,
                "less_delta_inv": -delta_inv,
                "add_delta_ap": delta_ap,
                "delta_nwc": delta_nwc,
                "total": operating_cf
            },
            "investing": {
                "capex": -capex,
                "total": investing_cf
            },
            "financing": {
                "dividend_paid": -dividend,
                "debt_change": delta_debt,
                "total": financing_cf
            }
        },
        "source": source
    }


def check_balance(
    total_assets: float,
    total_liabilities: float,
    total_equity: float,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具10: 资产负债表配平检验

    公式: assets = liabilities + equity

    Args:
        total_assets: 资产合计
        total_liabilities: 负债合计
        total_equity: 权益合计
        source: 计算来源标记

    Returns:
        dict: {
            "is_balanced": 是否配平,
            "difference": 差额,
            "details": 明细,
            "source": 计算来源
        }

    示例:
        >>> result = check_balance(500_000_000, 200_000_000, 300_000_000)
        >>> result["is_balanced"]
        True
    """
    diff = total_assets - (total_liabilities + total_equity)
    is_balanced = abs(diff) < 0.01  # 允许0.01的误差

    return {
        "is_balanced": is_balanced,
        "difference": diff,
        "details": {
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "total_equity": total_equity,
            "liabilities_plus_equity": total_liabilities + total_equity
        },
        "source": source
    }


def three_statement_quick_build(
    base_data: Dict[str, Any],
    assumptions: Dict[str, Any]
) -> Dict[str, Any]:
    """
    工具11: 快捷构建入口

    一键完成三表模型预测，内部依次调用所有原子工具。
    当需要自定义某个步骤时，可以单独调用原子工具替代。

    Args:
        base_data: 基期数据，包含:
            - last_revenue: 上期收入
            - closing_cash: 期末现金
            - closing_receivable: 期末应收
            - closing_inventory: 期末存货
            - closing_payable: 期末应付
            - closing_debt: 期末债务
            - closing_equity: 期末权益
            - fixed_asset_gross: 固定资产原值
            - fixed_asset_life: 使用年限
            - accum_depreciation: 累计折旧
            - company: 公司名称（可选）
            - period: 期间（可选）

        assumptions: 预测假设，包含:
            - growth_rate: 收入增长率
            - gross_margin: 毛利率
            - opex_ratio: 费用率
            - ar_days: 应收周转天数
            - ap_days: 应付周转天数
            - inv_days: 存货周转天数
            - capex_ratio: 资本支出比率
            - interest_rate: 利率
            - tax_rate: 税率
            - dividend_ratio: 分红比率（默认0.3）

    Returns:
        dict: 完整三表模型结果

    示例:
        >>> base = {"last_revenue": 500_000_000, "closing_cash": 100_000_000, ...}
        >>> assumptions = {"growth_rate": 0.09, "gross_margin": 0.25, ...}
        >>> result = three_statement_quick_build(base, assumptions)
        >>> result["validation"]["is_balanced"]
        True
    """
    # ========== 1. 利润表计算 ==========
    revenue_result = forecast_revenue(
        base_data["last_revenue"],
        assumptions["growth_rate"]
    )
    revenue = revenue_result["value"]

    cost_result = forecast_cost(revenue, assumptions["gross_margin"])
    cost = cost_result["value"]

    opex_result = forecast_opex(revenue, assumptions["opex_ratio"])
    opex = opex_result["value"]

    # 利息（基于期初负债）
    opening_debt = base_data.get("closing_debt", 0)
    interest = opening_debt * assumptions["interest_rate"]

    income_stmt = calc_income_statement(
        revenue,
        cost,
        opex,
        interest,
        assumptions["tax_rate"]
    )
    net_income = income_stmt["net_income"]

    # ========== 2. 营运资本计算 ==========
    working_cap = calc_working_capital(
        revenue,
        cost,
        assumptions["ar_days"],
        assumptions["ap_days"],
        assumptions["inv_days"]
    )

    # 期初营运资本
    opening_ar = base_data.get("closing_receivable", 0)
    opening_inv = base_data.get("closing_inventory", 0)
    opening_ap = base_data.get("closing_payable", 0)

    # 期末营运资本
    closing_ar = working_cap["receivable"]
    closing_inv = working_cap["inventory"]
    closing_ap = working_cap["payable"]

    # 变动额
    delta_ar = closing_ar - opening_ar
    delta_inv = closing_inv - opening_inv
    delta_ap = closing_ap - opening_ap

    # ========== 3. 固定资产和折旧 ==========
    fixed_assets_gross = base_data.get("fixed_asset_gross", 0)
    useful_life = base_data.get("fixed_asset_life", 10)
    opening_accum_dep = base_data.get("accum_depreciation", 0)

    capex_result = calc_capex(revenue, assumptions["capex_ratio"])
    capex = capex_result["value"]

    # 新的固定资产原值
    new_fixed_assets = fixed_assets_gross + capex

    depreciation_result = calc_depreciation(new_fixed_assets, useful_life)
    depreciation = depreciation_result["value"]

    # 累计折旧
    closing_accum_dep = opening_accum_dep + depreciation

    # 固定资产净值
    closing_fixed_net = new_fixed_assets - closing_accum_dep

    # ========== 4. 现金流量表计算 ==========
    dividend_ratio = assumptions.get("dividend_ratio", 0.3)
    dividend = max(net_income, 0) * dividend_ratio

    cash_flow = calc_cash_flow_statement(
        net_income,
        depreciation,
        delta_ar,
        delta_inv,
        delta_ap,
        capex,
        dividend
    )

    # 期末现金
    opening_cash = base_data.get("closing_cash", 0)
    closing_cash = opening_cash + cash_flow["net_cash_change"]

    # ========== 5. 资产负债表计算 ==========
    # 资产
    total_assets = closing_cash + closing_ar + closing_inv + closing_fixed_net

    # 负债
    closing_debt = opening_debt  # 假设债务不变
    total_liabilities = closing_debt + closing_ap

    # 权益
    opening_equity = base_data.get("closing_equity", 0)
    retained_change = net_income - dividend
    closing_equity = opening_equity + retained_change

    # 配平检验
    balance_check = check_balance(total_assets, total_liabilities, closing_equity)

    # ========== 6. 组装结果 ==========
    return {
        "_meta": {
            "model_type": "three_statement",
            "company": base_data.get("company", ""),
            "base_period": base_data.get("period", ""),
            "built_with": "atomic_tools"
        },

        "income_statement": {
            "revenue": revenue_result,
            "cost": cost_result,
            "gross_profit": {
                "value": income_stmt["gross_profit"],
                "formula": "revenue - cost",
                "source": "tool"
            },
            "opex": opex_result,
            "ebit": {
                "value": income_stmt["ebit"],
                "formula": "gross_profit - opex",
                "source": "tool"
            },
            "interest": {
                "value": interest,
                "formula": "opening_debt × interest_rate",
                "source": "tool"
            },
            "ebt": {
                "value": income_stmt["ebt"],
                "formula": "ebit - interest",
                "source": "tool"
            },
            "tax": {
                "value": income_stmt["tax"],
                "formula": "max(ebt, 0) × tax_rate",
                "source": "tool"
            },
            "net_income": {
                "value": income_stmt["net_income"],
                "formula": "ebt - tax",
                "source": "tool"
            }
        },

        "balance_sheet": {
            "assets": {
                "cash": {
                    "value": closing_cash,
                    "formula": "opening_cash + net_cash_change"
                },
                "receivable": {
                    "value": closing_ar,
                    "formula": "revenue / 365 × ar_days"
                },
                "inventory": {
                    "value": closing_inv,
                    "formula": "cost / 365 × inv_days"
                },
                "fixed_assets_net": {
                    "value": closing_fixed_net,
                    "formula": "fixed_assets_gross + capex - accum_depreciation"
                },
                "total_assets": {
                    "value": total_assets
                }
            },
            "liabilities": {
                "payable": {
                    "value": closing_ap,
                    "formula": "cost / 365 × ap_days"
                },
                "debt": {
                    "value": closing_debt
                },
                "total_liabilities": {
                    "value": total_liabilities
                }
            },
            "equity": {
                "opening_equity": {
                    "value": opening_equity
                },
                "retained_change": {
                    "value": retained_change,
                    "formula": "net_income - dividend"
                },
                "total_equity": {
                    "value": closing_equity
                }
            }
        },

        "cash_flow": {
            "operating": {
                "value": cash_flow["operating_cf"],
                "formula": "net_income + depreciation - ΔNWC",
                "details": cash_flow["details"]["operating"]
            },
            "investing": {
                "value": cash_flow["investing_cf"],
                "formula": "-capex",
                "details": cash_flow["details"]["investing"]
            },
            "financing": {
                "value": cash_flow["financing_cf"],
                "formula": "-interest - dividend + Δdebt",
                "details": cash_flow["details"]["financing"]
            },
            "net_change": {
                "value": cash_flow["net_cash_change"],
                "formula": "OCF + ICF + FCF"
            },
            "closing_cash": {
                "value": closing_cash
            }
        },

        "validation": balance_check,

        "working_capital": {
            "receivable": working_cap["receivable"],
            "payable": working_cap["payable"],
            "inventory": working_cap["inventory"],
            "net_working_capital": working_cap["net_working_capital"],
            "delta_ar": delta_ar,
            "delta_inv": delta_inv,
            "delta_ap": delta_ap,
            "delta_nwc": delta_ar + delta_inv - delta_ap
        },

        "fixed_assets": {
            "opening_gross": fixed_assets_gross,
            "capex": capex_result,
            "closing_gross": new_fixed_assets,
            "depreciation": depreciation_result,
            "opening_accum_dep": opening_accum_dep,
            "closing_accum_dep": closing_accum_dep,
            "closing_net": closing_fixed_net
        }
    }
