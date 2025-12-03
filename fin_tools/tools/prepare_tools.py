# -*- coding: utf-8 -*-
"""
财报数据准备工具

将完整财报转换为各分析工具所需的标准输入格式。

工具清单:
- prepare_lbo_data: 准备LBO分析所需数据
- prepare_ma_data: 准备M&A分析所需数据
- prepare_dcf_data: 准备DCF估值所需数据
"""

from typing import Dict, Any, List, Optional


def prepare_lbo_data(
    income_statement: Dict[str, float],
    balance_sheet: Dict[str, float],
    transaction: Dict[str, Any] = None,
    debt_structure: Dict[str, Dict] = None,
    operating_assumptions: Dict[str, Any] = None,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    准备LBO分析所需数据

    从完整财报提取关键指标，计算衍生数据，输出lbo_quick_build所需的标准格式。

    Args:
        income_statement: 利润表数据
            - revenue: 营业收入
            - cogs: 营业成本（可选）
            - gross_profit: 毛利润（可选）
            - opex: 运营费用（可选）
            - ebitda: EBITDA
            - depreciation: 折旧摊销（可选）
            - ebit: EBIT（可选）
            - interest_expense: 利息费用（可选）
            - ebt: 税前利润（可选）
            - tax: 所得税（可选）
            - net_income: 净利润（可选）

        balance_sheet: 资产负债表数据
            - cash: 现金（可选）
            - accounts_receivable: 应收账款（可选）
            - inventory: 存货（可选）
            - current_assets: 流动资产（可选）
            - ppe_net: 固定资产净值（可选）
            - total_assets: 总资产（可选）
            - accounts_payable: 应付账款（可选）
            - current_liabilities: 流动负债（可选）
            - long_term_debt: 长期负债（可选）
            - total_equity: 股东权益（可选）

        transaction: 交易假设
            - entry_multiple: 入场倍数
            - exit_multiple: 退出倍数
            - holding_period: 持有期（年）

        debt_structure: 债务结构
            - senior: {percent, rate, amort}
            - sub: {percent, rate, pik}

        operating_assumptions: 运营假设（可选，用于覆盖计算值）
            - revenue_growth: 收入增长率
            - ebitda_margin: EBITDA利润率
            - capex_percent: 资本支出率
            - nwc_percent: 营运资本率

        source: 计算来源标记

    Returns:
        dict: lbo_quick_build所需的标准输入格式

    示例:
        >>> result = prepare_lbo_data(
        ...     income_statement={"revenue": 13700, "ebitda": 3400, "depreciation": 1360},
        ...     balance_sheet={"accounts_receivable": 1200, "inventory": 400, "accounts_payable": 900},
        ...     transaction={"entry_multiple": 7.9, "exit_multiple": 8.0, "holding_period": 5}
        ... )
        >>> result["entry_ebitda"]
        3400
    """
    income = income_statement
    balance = balance_sheet
    txn = transaction or {}
    ops = operating_assumptions or {}

    # === 从财报提取基础数据 ===
    revenue = income.get("revenue", 0)
    ebitda = income.get("ebitda", 0)
    depreciation = income.get("depreciation", 0)
    ebit = income.get("ebit", ebitda - depreciation if depreciation else ebitda * 0.6)
    tax = income.get("tax", 0)
    ebt = income.get("ebt", ebit - income.get("interest_expense", 0))
    net_income = income.get("net_income", 0)

    # === 计算衍生指标 ===

    # EBITDA利润率
    ebitda_margin = ebitda / revenue if revenue > 0 else 0.25

    # 毛利率
    gross_profit = income.get("gross_profit")
    if gross_profit is None and income.get("cogs"):
        gross_profit = revenue - income.get("cogs")
    gross_margin = gross_profit / revenue if gross_profit and revenue > 0 else 0.35

    # 净利率
    net_margin = net_income / revenue if revenue > 0 and net_income else 0.07

    # 税率
    tax_rate = tax / ebt if ebt and ebt > 0 else 0.25

    # D&A占收入比例
    da_percent = depreciation / revenue if revenue > 0 and depreciation else 0.10

    # CapEx（假设等于D&A，维持性资本支出）
    capex = depreciation if depreciation else revenue * 0.08
    capex_percent = capex / revenue if revenue > 0 else 0.08

    # 营运资本
    ar = balance.get("accounts_receivable", 0)
    inventory = balance.get("inventory", 0)
    ap = balance.get("accounts_payable", 0)
    nwc = ar + inventory - ap
    nwc_percent = nwc / revenue if revenue > 0 else 0.05

    # FCF（简化计算）
    fcf = ebitda - tax - capex - (nwc * 0.03)  # 假设NWC变化为NWC的3%

    # === 构建输出 ===

    # 交易参数
    entry_multiple = txn.get("entry_multiple", 8.0)
    exit_multiple = txn.get("exit_multiple", entry_multiple)
    holding_period = txn.get("holding_period", 5)

    # 债务结构
    # 计算企业价值（用于计算债务比例）
    ev = ebitda * txn.get("entry_multiple", 8.0)

    if debt_structure:
        debt_struct = {}
        for name, config in debt_structure.items():
            # 跳过非债务项（如equity_contribution）
            if not isinstance(config, dict):
                continue
            # 标准化名称
            std_name = name.replace("_debt", "")
            # 支持两种格式：amount（绝对值）或 percent（比例）
            if "amount" in config:
                pct = config["amount"] / ev if ev > 0 else 0.3
            else:
                pct = config.get("percent", 0.3)
            debt_struct[std_name] = {
                "amount_percent": pct,
                "interest_rate": config.get("rate", config.get("interest_rate", 0.06)),
                "amortization_rate": config.get("amort", config.get("amortization_rate", 0)),
                "pik_rate": config.get("pik", config.get("pik_rate", 0))
            }
    else:
        # 默认债务结构
        debt_struct = {
            "senior": {"amount_percent": 0.40, "interest_rate": 0.065, "amortization_rate": 0.05},
            "subordinated": {"amount_percent": 0.20, "interest_rate": 0.085, "pik_rate": 0.02}
        }

    # 运营假设（可被覆盖）
    revenue_growth = ops.get("revenue_growth", 0.03)

    output = {
        # LBO核心输入
        "entry_ebitda": ebitda,
        "entry_multiple": entry_multiple,
        "exit_multiple": exit_multiple,
        "holding_period": holding_period,

        # 运营假设
        "revenue_growth": revenue_growth,
        "ebitda_margin": ops.get("ebitda_margin", ebitda_margin),
        "capex_percent": ops.get("capex_percent", capex_percent),
        "nwc_percent": ops.get("nwc_percent", nwc_percent),
        "da_percent": da_percent,
        "tax_rate": ops.get("tax_rate", tax_rate),

        # 债务结构
        "debt_structure": debt_struct,

        # 费用率
        "transaction_fee_rate": txn.get("transaction_fee_rate", 0.02),
        "financing_fee_rate": txn.get("financing_fee_rate", 0.01),

        # 现金扫荡
        "sweep_percent": txn.get("sweep_percent", 0.75),

        # 衍生数据（供参考）
        "_derived": {
            "revenue": revenue,
            "gross_margin": round(gross_margin, 4),
            "ebitda_margin": round(ebitda_margin, 4),
            "net_margin": round(net_margin, 4),
            "tax_rate": round(tax_rate, 4),
            "capex": capex,
            "nwc": nwc,
            "fcf": round(fcf, 2)
        },

        "_source": source
    }

    return output


def prepare_ma_data(
    acquirer: Dict[str, Any],
    target: Dict[str, Any],
    deal_terms: Dict[str, Any] = None,
    synergies: Dict[str, Any] = None,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    准备M&A分析所需数据

    从收购方和目标公司的财报提取关键指标，输出ma_quick_build所需的标准格式。

    Args:
        acquirer: 收购方数据
            - income_statement: 利润表
            - balance_sheet: 资产负债表
            - market_data: 市场数据（stock_price, shares_outstanding）

        target: 目标公司数据
            - income_statement: 利润表
            - balance_sheet: 资产负债表

        deal_terms: 交易条款
            - premium_percent: 溢价率
            - cash_percent: 现金支付比例
            - stock_percent: 股票支付比例

        synergies: 协同效应
            - cost_synergies: 成本协同
            - revenue_synergies: 收入协同

        source: 计算来源标记

    Returns:
        dict: ma_quick_build所需的标准输入格式

    示例:
        >>> result = prepare_ma_data(
        ...     acquirer={"income_statement": {"net_income": 5000}, "market_data": {"stock_price": 150, "shares_outstanding": 1000}},
        ...     target={"income_statement": {"net_income": 960}, "balance_sheet": {"total_equity": 7800}},
        ...     deal_terms={"premium_percent": 0.30, "cash_percent": 0.50}
        ... )
        >>> result["acquirer"]["eps"]
        5.0
    """
    terms = deal_terms or {}
    syn = synergies or {}

    # === 收购方数据 ===
    acq_income = acquirer.get("income_statement", {})
    acq_balance = acquirer.get("balance_sheet", {})
    acq_market = acquirer.get("market_data", {})

    acq_revenue = acq_income.get("revenue", 0)
    acq_ebitda = acq_income.get("ebitda", 0)
    acq_net_income = acq_income.get("net_income", 0)
    acq_shares = acq_market.get("shares_outstanding", 1)
    acq_price = acq_market.get("stock_price", 0)
    acq_eps = acq_net_income / acq_shares if acq_shares > 0 else 0
    acq_pe = acq_price / acq_eps if acq_eps > 0 else 0

    # === 目标公司数据 ===
    tgt_income = target.get("income_statement", {})
    tgt_balance = target.get("balance_sheet", {})

    tgt_revenue = tgt_income.get("revenue", 0)
    tgt_ebitda = tgt_income.get("ebitda", 0)
    tgt_net_income = tgt_income.get("net_income", 0)
    tgt_equity = tgt_balance.get("total_equity", 0)
    tgt_debt = tgt_balance.get("long_term_debt", 0) + tgt_balance.get("short_term_debt", 0)
    tgt_cash = tgt_balance.get("cash", 0)

    # === 交易条款 ===
    premium = terms.get("premium_percent", 0.30)
    cash_pct = terms.get("cash_percent", 0.50)
    stock_pct = terms.get("stock_percent", 1 - cash_pct)

    # 目标公司估值（基于账面价值+溢价）
    offer_price = tgt_equity * (1 + premium)

    output = {
        "acquirer": {
            "revenue": acq_revenue,
            "ebitda": acq_ebitda,
            "net_income": acq_net_income,
            "eps": round(acq_eps, 4),
            "shares_outstanding": acq_shares,
            "stock_price": acq_price,
            "pe_ratio": round(acq_pe, 2),
            "cash": acq_balance.get("cash", 0),
            "debt": acq_balance.get("long_term_debt", 0)
        },
        "target": {
            "revenue": tgt_revenue,
            "ebitda": tgt_ebitda,
            "net_income": tgt_net_income,
            "book_value": tgt_equity,
            "debt": tgt_debt,
            "cash": tgt_cash
        },
        "deal_terms": {
            "premium_percent": premium,
            "cash_percent": cash_pct,
            "stock_percent": stock_pct,
            "offer_price": offer_price
        },
        "synergies": {
            "cost_synergies": syn.get("cost_synergies", 0),
            "revenue_synergies": syn.get("revenue_synergies", 0)
        },
        "_source": source
    }

    return output


def prepare_dcf_data(
    income_statement: Dict[str, float],
    balance_sheet: Dict[str, float],
    projections: Dict[str, Any] = None,
    valuation: Dict[str, float] = None,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    准备DCF估值所需数据

    从完整财报提取基础数据，结合预测假设，生成FCF预测序列。

    Args:
        income_statement: 利润表数据
        balance_sheet: 资产负债表数据

        projections: 预测假设
            - years: 预测年数（默认5）
            - revenue_growth: 收入增长率（可为列表或单值）
            - ebitda_margin: EBITDA利润率（可为列表或单值）
            - capex_percent: 资本支出率
            - nwc_percent: 营运资本率

        valuation: 估值参数
            - wacc: 加权平均资本成本
            - terminal_growth: 永续增长率

        source: 计算来源标记

    Returns:
        dict: dcf_quick_valuate所需的标准输入格式

    示例:
        >>> result = prepare_dcf_data(
        ...     income_statement={"revenue": 13700, "ebitda": 3400},
        ...     balance_sheet={"long_term_debt": 12700, "cash": 800},
        ...     valuation={"wacc": 0.09, "terminal_growth": 0.02}
        ... )
        >>> len(result["fcf_list"])
        5
    """
    income = income_statement
    balance = balance_sheet
    proj = projections or {}
    val = valuation or {}

    # === 基础数据 ===
    revenue = income.get("revenue", 0)
    ebitda = income.get("ebitda", 0)
    depreciation = income.get("depreciation", ebitda * 0.4)
    tax = income.get("tax", 0)
    ebt = income.get("ebt", 0)

    # 税率
    tax_rate = tax / ebt if ebt and ebt > 0 else 0.25

    # 营运资本
    ar = balance.get("accounts_receivable", 0)
    inventory = balance.get("inventory", 0)
    ap = balance.get("accounts_payable", 0)
    nwc = ar + inventory - ap

    # CapEx
    capex = depreciation  # 假设维持性

    # === 预测参数 ===
    years = proj.get("years", 5)
    rev_growth = proj.get("revenue_growth", 0.03)
    ebitda_margin = proj.get("ebitda_margin", ebitda / revenue if revenue > 0 else 0.25)
    capex_pct = proj.get("capex_percent", capex / revenue if revenue > 0 else 0.08)
    nwc_pct = proj.get("nwc_percent", nwc / revenue if revenue > 0 else 0.05)

    # 处理列表或单值
    if not isinstance(rev_growth, list):
        rev_growth = [rev_growth] * years
    if not isinstance(ebitda_margin, list):
        ebitda_margin = [ebitda_margin] * years

    # === 生成FCF预测 ===
    fcf_list = []
    proj_revenue = revenue

    for i in range(years):
        # 预测收入
        proj_revenue = proj_revenue * (1 + rev_growth[i])

        # 预测EBITDA
        proj_ebitda = proj_revenue * ebitda_margin[i]

        # 预测CapEx和NWC变化
        proj_capex = proj_revenue * capex_pct
        proj_nwc = proj_revenue * nwc_pct
        delta_nwc = proj_nwc - (nwc if i == 0 else proj_revenue / (1 + rev_growth[i]) * nwc_pct)

        # 预测税
        proj_tax = proj_ebitda * 0.6 * tax_rate  # 简化：EBIT ≈ 60% EBITDA

        # FCF = EBITDA - Tax - CapEx - ΔNWC
        fcf = proj_ebitda - proj_tax - proj_capex - delta_nwc
        fcf_list.append(round(fcf, 2))

    # === 估值参数 ===
    wacc = val.get("wacc", 0.10)
    terminal_growth = val.get("terminal_growth", 0.02)

    # 净债务
    debt = balance.get("long_term_debt", 0) + balance.get("short_term_debt", 0)
    cash = balance.get("cash", 0)
    net_debt = debt - cash

    # 股数
    shares = balance.get("shares_outstanding", val.get("shares_outstanding", 1))

    output = {
        # DCF核心输入
        "fcf_list": fcf_list,
        "wacc": wacc,
        "terminal_growth": terminal_growth,
        "debt": debt,
        "cash": cash,
        "shares_outstanding": shares,

        # 衍生数据
        "_derived": {
            "base_revenue": revenue,
            "base_ebitda": ebitda,
            "base_fcf": round(ebitda - tax - capex - nwc * 0.03, 2),
            "net_debt": net_debt,
            "ebitda_margin": round(ebitda / revenue, 4) if revenue > 0 else 0,
            "projection_years": years
        },

        "_source": source
    }

    return output
