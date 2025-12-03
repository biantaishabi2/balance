# -*- coding: utf-8 -*-
"""
原子工具模块

提供独立的、可组合的财务计算工具，供LLM灵活调用。

模块结构:
- lbo_tools: LBO原子工具（9个）
- dcf_tools: DCF原子工具（9个）
- three_statement_tools: 三表模型原子工具（11个）
- ma_tools: M&A原子工具（8个）
- ratio_tools: 财务比率分析工具（7个）
- prepare_tools: 数据准备工具（3个）
"""

# LBO 原子工具
from .lbo_tools import (
    calc_purchase_price,
    calc_sources_uses,
    project_operations,
    calc_debt_schedule,
    calc_exit_value,
    calc_equity_proceeds,
    calc_irr,
    calc_moic,
    lbo_quick_build,
)

# DCF 原子工具
from .dcf_tools import (
    calc_capm,
    calc_wacc,
    calc_fcff,
    calc_terminal_value,
    calc_enterprise_value,
    calc_equity_value,
    calc_per_share_value,
    dcf_sensitivity,
    dcf_quick_valuate,
)

# 三表模型原子工具
from .three_statement_tools import (
    forecast_revenue,
    forecast_cost,
    forecast_opex,
    calc_income_statement,
    calc_working_capital,
    calc_depreciation,
    calc_capex,
    calc_operating_cash_flow,
    calc_cash_flow_statement,
    check_balance,
    three_statement_quick_build,
)

# M&A 原子工具
from .ma_tools import (
    calc_offer_price,
    calc_funding_mix,
    calc_goodwill,
    calc_pro_forma,
    calc_accretion_dilution,
    calc_synergies,
    calc_breakeven,
    ma_quick_build,
)

# 财务比率分析工具
from .ratio_tools import (
    calc_profitability,
    calc_liquidity,
    calc_solvency,
    calc_efficiency,
    calc_valuation,
    calc_dupont,
    calc_all_ratios,
)

# 数据准备工具
from .prepare_tools import (
    prepare_lbo_data,
    prepare_ma_data,
    prepare_dcf_data,
)

__all__ = [
    # LBO 工具
    "calc_purchase_price",
    "calc_sources_uses",
    "project_operations",
    "calc_debt_schedule",
    "calc_exit_value",
    "calc_equity_proceeds",
    "calc_irr",
    "calc_moic",
    "lbo_quick_build",
    # DCF 工具
    "calc_capm",
    "calc_wacc",
    "calc_fcff",
    "calc_terminal_value",
    "calc_enterprise_value",
    "calc_equity_value",
    "calc_per_share_value",
    "dcf_sensitivity",
    "dcf_quick_valuate",
    # 三表模型工具
    "forecast_revenue",
    "forecast_cost",
    "forecast_opex",
    "calc_income_statement",
    "calc_working_capital",
    "calc_depreciation",
    "calc_capex",
    "calc_operating_cash_flow",
    "calc_cash_flow_statement",
    "check_balance",
    "three_statement_quick_build",
    # M&A 工具
    "calc_offer_price",
    "calc_funding_mix",
    "calc_goodwill",
    "calc_pro_forma",
    "calc_accretion_dilution",
    "calc_synergies",
    "calc_breakeven",
    "ma_quick_build",
    # 财务比率分析工具
    "calc_profitability",
    "calc_liquidity",
    "calc_solvency",
    "calc_efficiency",
    "calc_valuation",
    "calc_dupont",
    "calc_all_ratios",
    # 数据准备工具
    "prepare_lbo_data",
    "prepare_ma_data",
    "prepare_dcf_data",
]
