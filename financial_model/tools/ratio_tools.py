# -*- coding: utf-8 -*-
"""
财务比率分析原子工具

独立的、可组合的财务比率计算工具，供LLM灵活调用。

设计原则:
1. 每个工具独立运行，不依赖类状态
2. 输入输出清晰（dict格式，可序列化为JSON）
3. 可自由组合，LLM可以跳过、替换、插入任何步骤
4. 保留计算追溯信息

工具清单:
- calc_profitability: 盈利能力分析（毛利率、净利率、ROE、ROA、ROIC）
- calc_liquidity: 流动性分析（流动比率、速动比率、现金比率）
- calc_solvency: 偿债能力分析（负债率、利息覆盖、权益乘数）
- calc_efficiency: 运营效率分析（资产周转率、存货周转、应收周转）
- calc_valuation: 估值分析（PE、PB、PS、EV/EBITDA）
- calc_dupont: 杜邦分析（3因素/5因素分解）
"""

from typing import Dict, Any, Optional, List


def _interpret_ratio(name: str, value: float, benchmarks: Dict[str, float] = None) -> str:
    """生成比率解读"""
    if benchmarks is None:
        benchmarks = {}

    interpretations = {
        "gross_margin": lambda v: f"毛利率{v:.1%}，{'盈利能力强' if v > 0.5 else '盈利能力一般' if v > 0.3 else '盈利能力较弱'}",
        "operating_margin": lambda v: f"营业利润率{v:.1%}",
        "net_margin": lambda v: f"净利率{v:.1%}",
        "ebitda_margin": lambda v: f"EBITDA利润率{v:.1%}",
        "roa": lambda v: f"资产回报率{v:.1%}",
        "roe": lambda v: f"净资产收益率{v:.1%}，{'优秀' if v > 0.20 else '良好' if v > 0.15 else '一般'}",
        "roic": lambda v: f"投入资本回报率{v:.1%}",
        "current_ratio": lambda v: f"流动比率{v:.2f}，{'短期偿债能力强' if v > 2 else '短期偿债能力一般' if v > 1.5 else '短期偿债能力较弱'}",
        "quick_ratio": lambda v: f"速动比率{v:.2f}，{'速动资产充足' if v > 1 else '速动资产较紧'}",
        "cash_ratio": lambda v: f"现金比率{v:.2f}，{'现金储备充裕' if v > 0.5 else '现金储备一般'}",
        "debt_to_equity": lambda v: f"负债权益比{v:.2f}，{'杠杆较低' if v < 0.5 else '杠杆适中' if v < 1 else '杠杆较高'}",
        "debt_to_assets": lambda v: f"资产负债率{v:.1%}",
        "debt_to_ebitda": lambda v: f"债务/EBITDA {v:.2f}x，{'偿债能力强' if v < 2 else '偿债能力一般' if v < 4 else '偿债压力较大'}",
        "interest_coverage": lambda v: f"利息覆盖倍数{v:.1f}x，{'利息支付无压力' if v > 5 else '利息覆盖充足' if v > 3 else '利息覆盖偏低'}",
        "equity_multiplier": lambda v: f"权益乘数{v:.2f}",
        "asset_turnover": lambda v: f"总资产周转率{v:.2f}次/年",
        "inventory_turnover": lambda v: f"存货周转率{v:.2f}次/年",
        "inventory_days": lambda v: f"存货周转天数{v:.0f}天",
        "receivable_turnover": lambda v: f"应收账款周转率{v:.2f}次/年",
        "receivable_days": lambda v: f"应收账款周转天数{v:.0f}天",
        "payable_turnover": lambda v: f"应付账款周转率{v:.2f}次/年",
        "payable_days": lambda v: f"应付账款周转天数{v:.0f}天",
        "cash_conversion_cycle": lambda v: f"现金转换周期{v:.0f}天，{'营运资本效率极高' if v < 0 else '营运资本效率良好' if v < 30 else '营运资本效率一般'}",
        "pe_ratio": lambda v: f"市盈率{v:.2f}x",
        "pb_ratio": lambda v: f"市净率{v:.2f}x",
        "ps_ratio": lambda v: f"市销率{v:.2f}x",
        "ev_ebitda": lambda v: f"EV/EBITDA {v:.2f}x",
        "ev_revenue": lambda v: f"EV/Revenue {v:.2f}x",
        "earnings_yield": lambda v: f"盈利收益率{v:.2%}",
    }

    if name in interpretations:
        return interpretations[name](value)
    return f"{name}: {value:.4f}"


def calc_profitability(
    revenue: float,
    cost_of_revenue: float = None,
    gross_profit: float = None,
    operating_income: float = None,
    net_income: float = None,
    ebitda: float = None,
    total_assets: float = None,
    total_equity: float = None,
    invested_capital: float = None,
    tax_rate: float = 0.25,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具1: 盈利能力分析

    计算多项盈利能力指标：毛利率、营业利润率、净利率、EBITDA利润率、ROA、ROE、ROIC

    Args:
        revenue: 营业收入
        cost_of_revenue: 营业成本（可选，如未提供则需gross_profit）
        gross_profit: 毛利润（可选，如未提供则从revenue-cost计算）
        operating_income: 营业利润
        net_income: 净利润
        ebitda: EBITDA
        total_assets: 总资产
        total_equity: 股东权益
        invested_capital: 投入资本（可选，默认使用total_equity + debt）
        tax_rate: 税率（用于ROIC计算）
        source: 计算来源标记

    Returns:
        dict: 包含所有盈利能力比率的结果

    示例:
        >>> result = calc_profitability(
        ...     revenue=150_000_000_000,
        ...     gross_profit=105_000_000_000,
        ...     operating_income=75_000_000_000,
        ...     net_income=62_000_000_000,
        ...     total_assets=200_000_000_000,
        ...     total_equity=140_000_000_000
        ... )
        >>> round(result["ratios"]["gross_margin"]["value"], 2)
        0.7
    """
    ratios = {}

    # 毛利率
    if gross_profit is not None:
        gp = gross_profit
    elif cost_of_revenue is not None:
        gp = revenue - cost_of_revenue
    else:
        gp = None

    if gp is not None and revenue > 0:
        gross_margin = gp / revenue
        ratios["gross_margin"] = {
            "value": round(gross_margin, 4),
            "formula": "gross_profit / revenue",
            "interpretation": _interpret_ratio("gross_margin", gross_margin)
        }

    # 营业利润率
    if operating_income is not None and revenue > 0:
        op_margin = operating_income / revenue
        ratios["operating_margin"] = {
            "value": round(op_margin, 4),
            "formula": "operating_income / revenue",
            "interpretation": _interpret_ratio("operating_margin", op_margin)
        }

    # 净利率
    if net_income is not None and revenue > 0:
        net_margin = net_income / revenue
        ratios["net_margin"] = {
            "value": round(net_margin, 4),
            "formula": "net_income / revenue",
            "interpretation": _interpret_ratio("net_margin", net_margin)
        }

    # EBITDA利润率
    if ebitda is not None and revenue > 0:
        ebitda_margin = ebitda / revenue
        ratios["ebitda_margin"] = {
            "value": round(ebitda_margin, 4),
            "formula": "ebitda / revenue",
            "interpretation": _interpret_ratio("ebitda_margin", ebitda_margin)
        }

    # ROA
    if net_income is not None and total_assets is not None and total_assets > 0:
        roa = net_income / total_assets
        ratios["roa"] = {
            "value": round(roa, 4),
            "formula": "net_income / total_assets",
            "interpretation": _interpret_ratio("roa", roa)
        }

    # ROE
    if net_income is not None and total_equity is not None and total_equity > 0:
        roe = net_income / total_equity
        ratios["roe"] = {
            "value": round(roe, 4),
            "formula": "net_income / total_equity",
            "interpretation": _interpret_ratio("roe", roe)
        }

    # ROIC
    if operating_income is not None and invested_capital is not None and invested_capital > 0:
        nopat = operating_income * (1 - tax_rate)
        roic = nopat / invested_capital
        ratios["roic"] = {
            "value": round(roic, 4),
            "formula": "nopat / invested_capital",
            "interpretation": _interpret_ratio("roic", roic)
        }
    elif operating_income is not None and total_equity is not None and total_assets is not None:
        # 简化计算：invested_capital ≈ total_equity + debt (假设debt = total_assets - total_equity * 0.3)
        ic = total_equity + (total_assets - total_equity) * 0.5
        if ic > 0:
            nopat = operating_income * (1 - tax_rate)
            roic = nopat / ic
            ratios["roic"] = {
                "value": round(roic, 4),
                "formula": "nopat / invested_capital",
                "interpretation": _interpret_ratio("roic", roic)
            }

    return {
        "type": "profitability",
        "ratios": ratios,
        "source": source
    }


def calc_liquidity(
    cash: float = None,
    accounts_receivable: float = None,
    inventory: float = None,
    current_assets: float = None,
    current_liabilities: float = None,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具2: 流动性分析

    计算流动性指标：流动比率、速动比率、现金比率

    Args:
        cash: 现金及等价物
        accounts_receivable: 应收账款
        inventory: 存货
        current_assets: 流动资产
        current_liabilities: 流动负债
        source: 计算来源标记

    Returns:
        dict: 包含所有流动性比率的结果

    示例:
        >>> result = calc_liquidity(
        ...     cash=50_000_000_000,
        ...     inventory=8_000_000_000,
        ...     current_assets=75_000_000_000,
        ...     current_liabilities=25_000_000_000
        ... )
        >>> result["ratios"]["current_ratio"]["value"]
        3.0
    """
    ratios = {}

    if current_liabilities is None or current_liabilities <= 0:
        return {
            "type": "liquidity",
            "ratios": {},
            "error": "current_liabilities is required and must be positive",
            "source": source
        }

    # 流动比率
    if current_assets is not None:
        current_ratio = current_assets / current_liabilities
        ratios["current_ratio"] = {
            "value": round(current_ratio, 4),
            "formula": "current_assets / current_liabilities",
            "benchmark": ">1.5 良好",
            "interpretation": _interpret_ratio("current_ratio", current_ratio)
        }

    # 速动比率
    if current_assets is not None and inventory is not None:
        quick_assets = current_assets - inventory
        quick_ratio = quick_assets / current_liabilities
        ratios["quick_ratio"] = {
            "value": round(quick_ratio, 4),
            "formula": "(current_assets - inventory) / current_liabilities",
            "benchmark": ">1.0 良好",
            "interpretation": _interpret_ratio("quick_ratio", quick_ratio)
        }

    # 现金比率
    if cash is not None:
        cash_ratio = cash / current_liabilities
        ratios["cash_ratio"] = {
            "value": round(cash_ratio, 4),
            "formula": "cash / current_liabilities",
            "benchmark": ">0.5 良好",
            "interpretation": _interpret_ratio("cash_ratio", cash_ratio)
        }

    return {
        "type": "liquidity",
        "ratios": ratios,
        "source": source
    }


def calc_solvency(
    total_debt: float = None,
    short_term_debt: float = None,
    long_term_debt: float = None,
    total_liabilities: float = None,
    total_equity: float = None,
    total_assets: float = None,
    ebit: float = None,
    ebitda: float = None,
    interest_expense: float = None,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具3: 偿债能力/资本结构分析

    计算偿债能力指标：负债权益比、资产负债率、债务/EBITDA、利息覆盖倍数、权益乘数

    Args:
        total_debt: 总有息负债（可选，如未提供则从short_term + long_term计算）
        short_term_debt: 短期负债
        long_term_debt: 长期负债
        total_liabilities: 总负债
        total_equity: 股东权益
        total_assets: 总资产
        ebit: 息税前利润
        ebitda: EBITDA
        interest_expense: 利息费用
        source: 计算来源标记

    Returns:
        dict: 包含所有偿债能力比率的结果

    示例:
        >>> result = calc_solvency(
        ...     total_debt=35_000_000_000,
        ...     total_equity=140_000_000_000,
        ...     total_assets=200_000_000_000,
        ...     ebit=75_500_000_000,
        ...     ebitda=82_000_000_000,
        ...     interest_expense=500_000_000
        ... )
        >>> result["ratios"]["interest_coverage"]["value"]
        151.0
    """
    ratios = {}

    # 计算总债务
    if total_debt is None:
        if short_term_debt is not None and long_term_debt is not None:
            total_debt = short_term_debt + long_term_debt
        elif total_liabilities is not None and total_equity is not None and total_assets is not None:
            # 粗略估计有息负债
            total_debt = total_liabilities * 0.6

    # 负债权益比
    if total_debt is not None and total_equity is not None and total_equity > 0:
        de_ratio = total_debt / total_equity
        ratios["debt_to_equity"] = {
            "value": round(de_ratio, 4),
            "formula": "total_debt / total_equity",
            "interpretation": _interpret_ratio("debt_to_equity", de_ratio)
        }

    # 资产负债率
    if total_debt is not None and total_assets is not None and total_assets > 0:
        da_ratio = total_debt / total_assets
        ratios["debt_to_assets"] = {
            "value": round(da_ratio, 4),
            "formula": "total_debt / total_assets",
            "interpretation": _interpret_ratio("debt_to_assets", da_ratio)
        }

    # 债务/EBITDA
    if total_debt is not None and ebitda is not None and ebitda > 0:
        debt_ebitda = total_debt / ebitda
        ratios["debt_to_ebitda"] = {
            "value": round(debt_ebitda, 4),
            "formula": "total_debt / ebitda",
            "interpretation": _interpret_ratio("debt_to_ebitda", debt_ebitda)
        }

    # 利息覆盖倍数
    if ebit is not None and interest_expense is not None and interest_expense > 0:
        interest_cov = ebit / interest_expense
        ratios["interest_coverage"] = {
            "value": round(interest_cov, 4),
            "formula": "ebit / interest_expense",
            "benchmark": ">3.0 健康",
            "interpretation": _interpret_ratio("interest_coverage", interest_cov)
        }

    # 权益乘数
    if total_assets is not None and total_equity is not None and total_equity > 0:
        eq_mult = total_assets / total_equity
        ratios["equity_multiplier"] = {
            "value": round(eq_mult, 4),
            "formula": "total_assets / total_equity",
            "interpretation": _interpret_ratio("equity_multiplier", eq_mult)
        }

    return {
        "type": "solvency",
        "ratios": ratios,
        "source": source
    }


def calc_efficiency(
    revenue: float = None,
    cost_of_revenue: float = None,
    total_assets: float = None,
    inventory: float = None,
    accounts_receivable: float = None,
    accounts_payable: float = None,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具4: 运营效率分析

    计算运营效率指标：资产周转率、存货周转率/天数、应收账款周转率/天数、
                      应付账款周转率/天数、现金转换周期

    Args:
        revenue: 营业收入
        cost_of_revenue: 营业成本
        total_assets: 总资产
        inventory: 存货
        accounts_receivable: 应收账款
        accounts_payable: 应付账款
        source: 计算来源标记

    Returns:
        dict: 包含所有运营效率比率的结果

    示例:
        >>> result = calc_efficiency(
        ...     revenue=150_000_000_000,
        ...     cost_of_revenue=45_000_000_000,
        ...     total_assets=200_000_000_000,
        ...     inventory=8_000_000_000,
        ...     accounts_receivable=12_000_000_000,
        ...     accounts_payable=15_000_000_000
        ... )
        >>> result["ratios"]["asset_turnover"]["value"]
        0.75
    """
    ratios = {}

    # 资产周转率
    if revenue is not None and total_assets is not None and total_assets > 0:
        asset_turn = revenue / total_assets
        ratios["asset_turnover"] = {
            "value": round(asset_turn, 4),
            "formula": "revenue / total_assets",
            "interpretation": _interpret_ratio("asset_turnover", asset_turn)
        }

    # 存货周转率/天数
    if cost_of_revenue is not None and inventory is not None and inventory > 0:
        inv_turn = cost_of_revenue / inventory
        inv_days = 365 / inv_turn
        ratios["inventory_turnover"] = {
            "value": round(inv_turn, 4),
            "formula": "cost_of_revenue / inventory",
            "interpretation": _interpret_ratio("inventory_turnover", inv_turn)
        }
        ratios["inventory_days"] = {
            "value": round(inv_days, 2),
            "formula": "365 / inventory_turnover",
            "interpretation": _interpret_ratio("inventory_days", inv_days)
        }

    # 应收账款周转率/天数
    if revenue is not None and accounts_receivable is not None and accounts_receivable > 0:
        recv_turn = revenue / accounts_receivable
        recv_days = 365 / recv_turn
        ratios["receivable_turnover"] = {
            "value": round(recv_turn, 4),
            "formula": "revenue / accounts_receivable",
            "interpretation": _interpret_ratio("receivable_turnover", recv_turn)
        }
        ratios["receivable_days"] = {
            "value": round(recv_days, 2),
            "formula": "365 / receivable_turnover",
            "interpretation": _interpret_ratio("receivable_days", recv_days)
        }

    # 应付账款周转率/天数
    if cost_of_revenue is not None and accounts_payable is not None and accounts_payable > 0:
        pay_turn = cost_of_revenue / accounts_payable
        pay_days = 365 / pay_turn
        ratios["payable_turnover"] = {
            "value": round(pay_turn, 4),
            "formula": "cost_of_revenue / accounts_payable",
            "interpretation": _interpret_ratio("payable_turnover", pay_turn)
        }
        ratios["payable_days"] = {
            "value": round(pay_days, 2),
            "formula": "365 / payable_turnover",
            "interpretation": _interpret_ratio("payable_days", pay_days)
        }

    # 现金转换周期
    if "inventory_days" in ratios and "receivable_days" in ratios and "payable_days" in ratios:
        ccc = ratios["inventory_days"]["value"] + ratios["receivable_days"]["value"] - ratios["payable_days"]["value"]
        ratios["cash_conversion_cycle"] = {
            "value": round(ccc, 2),
            "formula": "inventory_days + receivable_days - payable_days",
            "interpretation": _interpret_ratio("cash_conversion_cycle", ccc)
        }

    return {
        "type": "efficiency",
        "ratios": ratios,
        "source": source
    }


def calc_valuation(
    market_cap: float = None,
    stock_price: float = None,
    shares_outstanding: float = None,
    net_income: float = None,
    total_equity: float = None,
    revenue: float = None,
    ebitda: float = None,
    total_debt: float = None,
    cash: float = None,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具5: 估值分析

    计算估值指标：PE、PB、PS、EV/EBITDA、EV/Revenue、盈利收益率

    Args:
        market_cap: 市值（可选，如未提供则从stock_price * shares计算）
        stock_price: 股价
        shares_outstanding: 流通股数
        net_income: 净利润
        total_equity: 股东权益（账面价值）
        revenue: 营业收入
        ebitda: EBITDA
        total_debt: 总有息负债
        cash: 现金
        source: 计算来源标记

    Returns:
        dict: 包含所有估值比率的结果

    示例:
        >>> result = calc_valuation(
        ...     market_cap=150_000_000_000,
        ...     net_income=62_000_000_000,
        ...     total_equity=140_000_000_000,
        ...     revenue=150_000_000_000,
        ...     ebitda=82_000_000_000,
        ...     total_debt=35_000_000_000,
        ...     cash=50_000_000_000
        ... )
        >>> round(result["ratios"]["pe_ratio"]["value"], 2)
        2.42
    """
    ratios = {}

    # 计算市值
    if market_cap is None:
        if stock_price is not None and shares_outstanding is not None:
            market_cap = stock_price * shares_outstanding

    if market_cap is None or market_cap <= 0:
        return {
            "type": "valuation",
            "ratios": {},
            "error": "market_cap is required (or stock_price + shares_outstanding)",
            "source": source
        }

    # PE
    if net_income is not None and net_income > 0:
        pe = market_cap / net_income
        ratios["pe_ratio"] = {
            "value": round(pe, 4),
            "formula": "market_cap / net_income",
            "interpretation": _interpret_ratio("pe_ratio", pe)
        }

        # 盈利收益率（PE的倒数）
        earnings_yield = net_income / market_cap
        ratios["earnings_yield"] = {
            "value": round(earnings_yield, 4),
            "formula": "net_income / market_cap",
            "interpretation": _interpret_ratio("earnings_yield", earnings_yield)
        }

    # PB
    if total_equity is not None and total_equity > 0:
        pb = market_cap / total_equity
        ratios["pb_ratio"] = {
            "value": round(pb, 4),
            "formula": "market_cap / total_equity",
            "interpretation": _interpret_ratio("pb_ratio", pb)
        }

    # PS
    if revenue is not None and revenue > 0:
        ps = market_cap / revenue
        ratios["ps_ratio"] = {
            "value": round(ps, 4),
            "formula": "market_cap / revenue",
            "interpretation": _interpret_ratio("ps_ratio", ps)
        }

    # EV计算
    debt = total_debt if total_debt is not None else 0
    cash_val = cash if cash is not None else 0
    ev = market_cap + debt - cash_val

    # EV/EBITDA
    if ebitda is not None and ebitda > 0:
        ev_ebitda = ev / ebitda
        ratios["ev_ebitda"] = {
            "value": round(ev_ebitda, 4),
            "formula": "(market_cap + debt - cash) / ebitda",
            "interpretation": _interpret_ratio("ev_ebitda", ev_ebitda)
        }

    # EV/Revenue
    if revenue is not None and revenue > 0:
        ev_rev = ev / revenue
        ratios["ev_revenue"] = {
            "value": round(ev_rev, 4),
            "formula": "(market_cap + debt - cash) / revenue",
            "interpretation": _interpret_ratio("ev_revenue", ev_rev)
        }

    return {
        "type": "valuation",
        "ratios": ratios,
        "enterprise_value": ev,
        "source": source
    }


def calc_dupont(
    net_income: float,
    revenue: float,
    total_assets: float,
    total_equity: float,
    ebit: float = None,
    ebt: float = None,
    levels: int = 3,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具6: 杜邦分析

    分解ROE为多个驱动因素

    3因素模型: ROE = 净利率 × 资产周转率 × 权益乘数
    5因素模型: ROE = 税负系数 × 利息负担 × 营业利润率 × 资产周转率 × 权益乘数

    Args:
        net_income: 净利润
        revenue: 营业收入
        total_assets: 总资产
        total_equity: 股东权益
        ebit: 息税前利润（5因素分解需要）
        ebt: 税前利润（5因素分解需要）
        levels: 分解层级（3或5）
        source: 计算来源标记

    Returns:
        dict: 杜邦分析结果

    示例:
        >>> result = calc_dupont(
        ...     net_income=62_000_000_000,
        ...     revenue=150_000_000_000,
        ...     total_assets=200_000_000_000,
        ...     total_equity=140_000_000_000,
        ...     levels=3
        ... )
        >>> round(result["roe"], 4)
        0.4429
    """
    # 基本指标
    net_margin = net_income / revenue if revenue > 0 else 0
    asset_turnover = revenue / total_assets if total_assets > 0 else 0
    equity_multiplier = total_assets / total_equity if total_equity > 0 else 0

    # 计算ROE
    roe = net_margin * asset_turnover * equity_multiplier

    if levels == 3:
        return {
            "model": "dupont_3_factor",
            "roe": round(roe, 4),
            "decomposition": {
                "net_margin": {
                    "value": round(net_margin, 4),
                    "formula": "net_income / revenue",
                    "label": "净利率"
                },
                "asset_turnover": {
                    "value": round(asset_turnover, 4),
                    "formula": "revenue / total_assets",
                    "label": "资产周转率"
                },
                "equity_multiplier": {
                    "value": round(equity_multiplier, 4),
                    "formula": "total_assets / total_equity",
                    "label": "权益乘数"
                }
            },
            "formula": "ROE = 净利率 × 资产周转率 × 权益乘数",
            "verification": f"{net_margin:.4f} × {asset_turnover:.4f} × {equity_multiplier:.4f} = {roe:.4f} ✓",
            "source": source
        }

    elif levels == 5:
        if ebit is None or ebt is None:
            return {
                "error": "5因素分解需要 ebit 和 ebt 参数",
                "source": source
            }

        # 5因素分解
        tax_burden = net_income / ebt if ebt > 0 else 0  # 税负系数 (1-税率)
        interest_burden = ebt / ebit if ebit > 0 else 0  # 利息负担系数
        operating_margin = ebit / revenue if revenue > 0 else 0  # 息税前利润率

        # 验证
        roe_5 = tax_burden * interest_burden * operating_margin * asset_turnover * equity_multiplier

        # 生成洞察
        insights = []
        effective_tax = 1 - tax_burden
        insights.append(f"税负系数{tax_burden:.2f}说明有效税率约{effective_tax:.0%}")

        if interest_burden > 0.95:
            insights.append("利息负担系数接近1，利息支出影响极小")
        else:
            insights.append(f"利息负担系数{interest_burden:.2f}，利息支出对利润有一定影响")

        if operating_margin > 0.3:
            insights.append(f"高营业利润率({operating_margin:.1%})是ROE的主要驱动因素")
        else:
            insights.append(f"营业利润率({operating_margin:.1%})处于一般水平")

        if equity_multiplier < 2:
            insights.append(f"较低的权益乘数({equity_multiplier:.2f})说明杠杆使用保守")
        else:
            insights.append(f"权益乘数({equity_multiplier:.2f})说明使用了较高杠杆")

        return {
            "model": "dupont_5_factor",
            "roe": round(roe_5, 4),
            "decomposition": {
                "tax_burden": {
                    "value": round(tax_burden, 4),
                    "formula": "net_income / ebt",
                    "label": "税负系数 (1-税率)"
                },
                "interest_burden": {
                    "value": round(interest_burden, 4),
                    "formula": "ebt / ebit",
                    "label": "利息负担系数"
                },
                "operating_margin": {
                    "value": round(operating_margin, 4),
                    "formula": "ebit / revenue",
                    "label": "息税前利润率"
                },
                "asset_turnover": {
                    "value": round(asset_turnover, 4),
                    "formula": "revenue / total_assets",
                    "label": "资产周转率"
                },
                "equity_multiplier": {
                    "value": round(equity_multiplier, 4),
                    "formula": "total_assets / total_equity",
                    "label": "权益乘数"
                }
            },
            "formula": "ROE = 税负系数 × 利息负担 × 营业利润率 × 资产周转率 × 权益乘数",
            "insights": insights,
            "source": source
        }

    else:
        return {
            "error": f"不支持的分解层级: {levels}，请使用 3 或 5",
            "source": source
        }


def calc_all_ratios(
    income_statement: Dict[str, float] = None,
    balance_sheet: Dict[str, float] = None,
    market_data: Dict[str, float] = None,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    计算所有比率（便捷入口）

    Args:
        income_statement: 利润表数据
        balance_sheet: 资产负债表数据
        market_data: 市场数据
        source: 计算来源标记

    Returns:
        dict: 包含所有类别比率的完整结果
    """
    result = {
        "_meta": {
            "model_type": "ratio_analysis",
            "built_with": "atomic_tools"
        }
    }

    income = income_statement or {}
    balance = balance_sheet or {}
    market = market_data or {}

    # 盈利能力
    if income.get("revenue"):
        result["profitability"] = calc_profitability(
            revenue=income.get("revenue"),
            gross_profit=income.get("gross_profit"),
            cost_of_revenue=income.get("cost_of_revenue"),
            operating_income=income.get("operating_income"),
            net_income=income.get("net_income"),
            ebitda=income.get("ebitda"),
            total_assets=balance.get("total_assets"),
            total_equity=balance.get("total_equity"),
            source=source
        )

    # 流动性
    if balance.get("current_liabilities"):
        result["liquidity"] = calc_liquidity(
            cash=balance.get("cash"),
            inventory=balance.get("inventory"),
            current_assets=balance.get("current_assets"),
            current_liabilities=balance.get("current_liabilities"),
            source=source
        )

    # 偿债能力
    if balance.get("total_equity"):
        total_debt = balance.get("total_debt")
        if total_debt is None and balance.get("short_term_debt") is not None:
            total_debt = balance.get("short_term_debt", 0) + balance.get("long_term_debt", 0)

        result["solvency"] = calc_solvency(
            total_debt=total_debt,
            total_equity=balance.get("total_equity"),
            total_assets=balance.get("total_assets"),
            total_liabilities=balance.get("total_liabilities"),
            ebit=income.get("ebit"),
            ebitda=income.get("ebitda"),
            interest_expense=income.get("interest_expense"),
            source=source
        )

    # 运营效率
    if income.get("revenue") and balance.get("total_assets"):
        result["efficiency"] = calc_efficiency(
            revenue=income.get("revenue"),
            cost_of_revenue=income.get("cost_of_revenue"),
            total_assets=balance.get("total_assets"),
            inventory=balance.get("inventory"),
            accounts_receivable=balance.get("accounts_receivable"),
            accounts_payable=balance.get("accounts_payable"),
            source=source
        )

    # 估值
    if market.get("market_cap") or (market.get("stock_price") and market.get("shares_outstanding")):
        result["valuation"] = calc_valuation(
            market_cap=market.get("market_cap"),
            stock_price=market.get("stock_price"),
            shares_outstanding=market.get("shares_outstanding"),
            net_income=income.get("net_income"),
            total_equity=balance.get("total_equity"),
            revenue=income.get("revenue"),
            ebitda=income.get("ebitda"),
            total_debt=balance.get("total_debt") or (balance.get("short_term_debt", 0) + balance.get("long_term_debt", 0)),
            cash=balance.get("cash"),
            source=source
        )

    # 杜邦分析
    if income.get("net_income") and income.get("revenue") and balance.get("total_assets") and balance.get("total_equity"):
        result["dupont_3"] = calc_dupont(
            net_income=income.get("net_income"),
            revenue=income.get("revenue"),
            total_assets=balance.get("total_assets"),
            total_equity=balance.get("total_equity"),
            levels=3,
            source=source
        )

        if income.get("ebit") and income.get("ebt"):
            result["dupont_5"] = calc_dupont(
                net_income=income.get("net_income"),
                revenue=income.get("revenue"),
                total_assets=balance.get("total_assets"),
                total_equity=balance.get("total_equity"),
                ebit=income.get("ebit"),
                ebt=income.get("ebt"),
                levels=5,
                source=source
            )

    return result
