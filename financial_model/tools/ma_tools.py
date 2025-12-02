# -*- coding: utf-8 -*-
"""
M&A 原子工具

独立的、可组合的并购分析计算工具，供LLM灵活调用。

设计原则:
1. 每个工具独立运行，不依赖类状态
2. 输入输出清晰（dict格式，可序列化为JSON）
3. 可自由组合，LLM可以跳过、替换、插入任何步骤
4. 保留计算追溯信息

工具清单:
- calc_offer_price: 计算收购报价
- calc_funding_mix: 融资结构
- calc_goodwill: 商誉计算
- calc_pro_forma: 合并报表
- calc_accretion_dilution: 增厚/稀释分析
- calc_synergies: 协同效应分析
- calc_breakeven: 盈亏平衡分析
- ma_quick_build: 快捷构建（依次调用上述工具）
"""

from typing import Dict, List, Any, Optional, Union


def calc_offer_price(
    target_share_price: float,
    target_shares: float,
    premium_percent: float = 0.0,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具1: 计算收购报价

    公式: Offer Price = Target Share Price × (1 + Premium)
          Total Purchase = Offer Price × Shares Outstanding

    Args:
        target_share_price: 目标公司当前股价
        target_shares: 目标公司流通股数
        premium_percent: 收购溢价比例（如0.30表示30%溢价）
        source: 计算来源标记 ("tool" 或 "llm_override")

    Returns:
        dict: {
            "offer_price_per_share": 每股报价,
            "total_purchase_price": 总收购价格,
            "premium": 溢价详情,
            "formula": 公式说明,
            "inputs": 输入参数,
            "source": 计算来源
        }

    示例:
        >>> result = calc_offer_price(50, 200_000_000, 0.30)
        >>> result["offer_price_per_share"]
        65.0
        >>> result["total_purchase_price"]
        13000000000
    """
    offer_price_per_share = target_share_price * (1 + premium_percent)
    total_purchase_price = offer_price_per_share * target_shares
    premium_value = total_purchase_price - (target_share_price * target_shares)

    return {
        "offer_price_per_share": offer_price_per_share,
        "total_purchase_price": total_purchase_price,
        "premium": {
            "percent": premium_percent,
            "value": premium_value
        },
        "formula": "Offer Price = Share Price × (1 + Premium)",
        "inputs": {
            "target_share_price": target_share_price,
            "target_shares": target_shares,
            "premium_percent": premium_percent
        },
        "source": source
    }


def calc_funding_mix(
    total_purchase_price: float,
    cash_percent: float,
    stock_percent: float,
    acquirer_share_price: float,
    new_debt: float = 0,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具2: 计算融资结构

    公式: Cash + Stock + New Debt = Total Purchase Price

    Args:
        total_purchase_price: 总收购价格
        cash_percent: 现金支付比例
        stock_percent: 股票支付比例
        acquirer_share_price: 收购方股价
        new_debt: 新增债务融资
        source: 计算来源标记

    Returns:
        dict: {
            "cash_amount": 现金支付金额,
            "stock_amount": 股票支付金额,
            "new_shares_issued": 新发行股数,
            "new_debt": 新增债务,
            "formula": 公式说明,
            "inputs": 输入参数,
            "source": 计算来源
        }

    示例:
        >>> result = calc_funding_mix(13_000_000_000, 0.60, 0.40, 100)
        >>> result["cash_amount"]
        7800000000.0
        >>> result["new_shares_issued"]
        52000000.0
    """
    # 验证比例
    total_percent = cash_percent + stock_percent
    remaining_from_debt = total_purchase_price * (1 - total_percent) if total_percent < 1 else 0

    cash_amount = total_purchase_price * cash_percent
    stock_amount = total_purchase_price * stock_percent
    new_shares_issued = stock_amount / acquirer_share_price if acquirer_share_price > 0 else 0

    # 如果现金+股票不足100%，差额由新债务填补
    if new_debt == 0 and total_percent < 1:
        new_debt = remaining_from_debt

    return {
        "cash_amount": cash_amount,
        "stock_amount": stock_amount,
        "new_shares_issued": new_shares_issued,
        "new_debt": new_debt,
        "funding_breakdown": {
            "cash": {"value": cash_amount, "percent": cash_percent},
            "stock": {"value": stock_amount, "percent": stock_percent},
            "debt": {"value": new_debt, "percent": new_debt / total_purchase_price if total_purchase_price > 0 else 0}
        },
        "formula": "Cash + Stock + New Debt = Total Purchase Price",
        "inputs": {
            "total_purchase_price": total_purchase_price,
            "cash_percent": cash_percent,
            "stock_percent": stock_percent,
            "acquirer_share_price": acquirer_share_price,
            "new_debt": new_debt
        },
        "source": source
    }


def calc_goodwill(
    purchase_price: float,
    target_book_value: float,
    fair_value_adjustments: Optional[Dict[str, float]] = None,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具3: 计算商誉

    公式: Goodwill = Purchase Price - Adjusted Net Assets
          Adjusted Net Assets = Book Value + FV Adjustments

    Args:
        purchase_price: 收购价格
        target_book_value: 目标公司账面净资产
        fair_value_adjustments: 公允价值调整，包含:
            - intangible_assets: 确认的无形资产（正值）
            - fixed_assets_step_up: 固定资产增值（正值）
            - deferred_tax_liability: 递延税负债（正值，会被减去）
        source: 计算来源标记

    Returns:
        dict: {
            "goodwill": 商誉金额,
            "adjusted_net_assets": 调整后净资产,
            "is_bargain_purchase": 是否为廉价收购,
            "formula": 公式说明,
            "inputs": 输入参数,
            "source": 计算来源
        }

    示例:
        >>> result = calc_goodwill(
        ...     13_000_000_000,
        ...     20_000_000_000,
        ...     {"intangible_assets": 5_000_000_000, "fixed_assets_step_up": 1_000_000_000, "deferred_tax_liability": 1_500_000_000}
        ... )
        >>> result["goodwill"] < 0  # 负商誉（廉价收购）
        True
    """
    if fair_value_adjustments is None:
        fair_value_adjustments = {}

    # 计算调整后净资产
    intangible_assets = fair_value_adjustments.get("intangible_assets", 0)
    fixed_assets_step_up = fair_value_adjustments.get("fixed_assets_step_up", 0)
    deferred_tax_liability = fair_value_adjustments.get("deferred_tax_liability", 0)

    adjusted_net_assets = (
        target_book_value
        + intangible_assets
        + fixed_assets_step_up
        - deferred_tax_liability
    )

    goodwill = purchase_price - adjusted_net_assets
    is_bargain_purchase = goodwill < 0

    return {
        "goodwill": goodwill,
        "adjusted_net_assets": adjusted_net_assets,
        "is_bargain_purchase": is_bargain_purchase,
        "details": {
            "target_book_value": target_book_value,
            "intangible_assets": intangible_assets,
            "fixed_assets_step_up": fixed_assets_step_up,
            "deferred_tax_liability": deferred_tax_liability
        },
        "formula": "Goodwill = Purchase Price - (Book Value + FV Adjustments)",
        "inputs": {
            "purchase_price": purchase_price,
            "target_book_value": target_book_value,
            "fair_value_adjustments": fair_value_adjustments
        },
        "note": "负商誉表示廉价收购(Bargain Purchase)，计入利润" if is_bargain_purchase else "",
        "source": source
    }


def calc_pro_forma(
    acquirer_financials: Dict[str, float],
    target_financials: Dict[str, float],
    deal_adjustments: Dict[str, float],
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具4: 构建合并报表

    Args:
        acquirer_financials: 收购方财务数据，包含:
            - total_assets: 总资产
            - cash: 现金
            - goodwill: 原有商誉
            - total_liabilities: 总负债
            - total_equity: 总权益
        target_financials: 目标公司财务数据（同上）
        deal_adjustments: 交易调整，包含:
            - cash_used: 使用的现金
            - new_debt: 新增债务
            - new_equity_issued: 新发行股权价值
            - goodwill_created: 新增商誉
            - target_equity_eliminated: 消除的目标公司权益
            - intangible_assets_created: 新确认的无形资产
        source: 计算来源标记

    Returns:
        dict: {
            "pro_forma_balance_sheet": 合并资产负债表,
            "is_balanced": 是否配平,
            "formula": 公式说明,
            "inputs": 输入参数,
            "source": 计算来源
        }

    示例:
        >>> acquirer = {"total_assets": 500_000_000_000, "cash": 100_000_000_000, ...}
        >>> target = {"total_assets": 30_000_000_000, ...}
        >>> adjustments = {"cash_used": 7_800_000_000, "goodwill_created": 5_000_000_000, ...}
        >>> result = calc_pro_forma(acquirer, target, adjustments)
    """
    # 合并资产
    pro_forma_cash = (
        acquirer_financials.get("cash", 0)
        + target_financials.get("cash", 0)
        - deal_adjustments.get("cash_used", 0)
    )

    pro_forma_goodwill = (
        acquirer_financials.get("goodwill", 0)
        + target_financials.get("goodwill", 0)
        + deal_adjustments.get("goodwill_created", 0)
    )

    intangible_assets = (
        acquirer_financials.get("intangible_assets", 0)
        + target_financials.get("intangible_assets", 0)
        + deal_adjustments.get("intangible_assets_created", 0)
    )

    # 其他资产 = 总资产 - 现金 - 商誉 - 无形资产
    acquirer_other_assets = (
        acquirer_financials.get("total_assets", 0)
        - acquirer_financials.get("cash", 0)
        - acquirer_financials.get("goodwill", 0)
        - acquirer_financials.get("intangible_assets", 0)
    )
    target_other_assets = (
        target_financials.get("total_assets", 0)
        - target_financials.get("cash", 0)
        - target_financials.get("goodwill", 0)
        - target_financials.get("intangible_assets", 0)
    )
    fixed_assets_step_up = deal_adjustments.get("fixed_assets_step_up", 0)

    pro_forma_other_assets = acquirer_other_assets + target_other_assets + fixed_assets_step_up

    pro_forma_total_assets = pro_forma_cash + pro_forma_goodwill + intangible_assets + pro_forma_other_assets

    # 合并负债
    pro_forma_liabilities = (
        acquirer_financials.get("total_liabilities", 0)
        + target_financials.get("total_liabilities", 0)
        + deal_adjustments.get("new_debt", 0)
        + deal_adjustments.get("deferred_tax_liability", 0)
    )

    # 合并权益
    # 收购方权益 + 新发行股权 - 消除目标公司权益（因为用收购价替代了）
    pro_forma_equity = (
        acquirer_financials.get("total_equity", 0)
        + deal_adjustments.get("new_equity_issued", 0)
    )
    # 注：目标公司权益被消除，由商誉和调整后资产替代

    # 检查配平
    is_balanced = abs(pro_forma_total_assets - pro_forma_liabilities - pro_forma_equity) < 1

    return {
        "pro_forma_balance_sheet": {
            "assets": {
                "cash": {
                    "acquirer": acquirer_financials.get("cash", 0),
                    "target": target_financials.get("cash", 0),
                    "adjustment": -deal_adjustments.get("cash_used", 0),
                    "pro_forma": pro_forma_cash
                },
                "goodwill": {
                    "acquirer": acquirer_financials.get("goodwill", 0),
                    "target": target_financials.get("goodwill", 0),
                    "adjustment": deal_adjustments.get("goodwill_created", 0),
                    "pro_forma": pro_forma_goodwill
                },
                "intangible_assets": {
                    "acquirer": acquirer_financials.get("intangible_assets", 0),
                    "target": target_financials.get("intangible_assets", 0),
                    "adjustment": deal_adjustments.get("intangible_assets_created", 0),
                    "pro_forma": intangible_assets
                },
                "other_assets": {
                    "acquirer": acquirer_other_assets,
                    "target": target_other_assets,
                    "adjustment": fixed_assets_step_up,
                    "pro_forma": pro_forma_other_assets
                },
                "total_assets": pro_forma_total_assets
            },
            "liabilities": {
                "total_liabilities": {
                    "acquirer": acquirer_financials.get("total_liabilities", 0),
                    "target": target_financials.get("total_liabilities", 0),
                    "adjustment": deal_adjustments.get("new_debt", 0) + deal_adjustments.get("deferred_tax_liability", 0),
                    "pro_forma": pro_forma_liabilities
                }
            },
            "equity": {
                "total_equity": {
                    "acquirer": acquirer_financials.get("total_equity", 0),
                    "adjustment": deal_adjustments.get("new_equity_issued", 0),
                    "pro_forma": pro_forma_equity
                }
            }
        },
        "is_balanced": is_balanced,
        "balance_check": {
            "total_assets": pro_forma_total_assets,
            "total_liabilities_and_equity": pro_forma_liabilities + pro_forma_equity,
            "difference": pro_forma_total_assets - pro_forma_liabilities - pro_forma_equity
        },
        "formula": "Pro Forma = Acquirer + Target + Deal Adjustments",
        "inputs": {
            "acquirer_financials": acquirer_financials,
            "target_financials": target_financials,
            "deal_adjustments": deal_adjustments
        },
        "source": source
    }


def calc_accretion_dilution(
    acquirer_net_income: float,
    acquirer_shares: float,
    target_net_income: float,
    purchase_price: float,
    cash_percent: float,
    stock_percent: float,
    acquirer_share_price: float,
    cost_of_debt: float = 0.05,
    tax_rate: float = 0.25,
    foregone_interest_rate: float = 0.03,
    synergies: float = 0,
    intangible_amort: float = 0,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具5: 计算增厚/稀释分析

    判断收购后EPS是上升（增厚）还是下降（稀释）

    Args:
        acquirer_net_income: 收购方净利润
        acquirer_shares: 收购方流通股数
        target_net_income: 目标公司净利润
        purchase_price: 收购价格
        cash_percent: 现金支付比例
        stock_percent: 股票支付比例
        acquirer_share_price: 收购方股价
        cost_of_debt: 新债务成本（如果有债务融资）
        tax_rate: 税率
        foregone_interest_rate: 损失的现金利息收益率
        synergies: 协同效应（税前）
        intangible_amort: 无形资产年摊销额
        source: 计算来源标记

    Returns:
        dict: {
            "standalone_eps": 收购前EPS,
            "pro_forma_eps": 合并后EPS,
            "accretion_dilution": 增厚/稀释金额,
            "accretion_dilution_percent": 增厚/稀释比例,
            "status": "Accretive" 或 "Dilutive",
            "formula": 公式说明,
            "inputs": 输入参数,
            "source": 计算来源
        }

    示例:
        >>> result = calc_accretion_dilution(
        ...     acquirer_net_income=50_000_000_000,
        ...     acquirer_shares=1_000_000_000,
        ...     target_net_income=2_000_000_000,
        ...     purchase_price=13_000_000_000,
        ...     cash_percent=0.60,
        ...     stock_percent=0.40,
        ...     acquirer_share_price=100
        ... )
        >>> result["status"]
        'Dilutive'
    """
    # 收购方独立EPS
    standalone_eps = acquirer_net_income / acquirer_shares if acquirer_shares > 0 else 0

    # 计算融资成本
    cash_used = purchase_price * cash_percent
    debt_percent = 1 - cash_percent - stock_percent
    new_debt = purchase_price * debt_percent if debt_percent > 0 else 0

    # 损失的利息收入（税后）
    foregone_interest = cash_used * foregone_interest_rate * (1 - tax_rate)

    # 新债务利息支出（税后）
    debt_interest = new_debt * cost_of_debt * (1 - tax_rate)

    # 新发行股票数
    stock_value = purchase_price * stock_percent
    new_shares = stock_value / acquirer_share_price if acquirer_share_price > 0 else 0

    # 合并净利润
    combined_net_income = (
        acquirer_net_income
        + target_net_income
        - foregone_interest                    # 减：损失的利息收入
        - debt_interest                        # 减：新债务利息
        + synergies * (1 - tax_rate)           # 加：税后协同效应
        - intangible_amort * (1 - tax_rate)    # 减：税后无形资产摊销
    )

    # 合并股数
    combined_shares = acquirer_shares + new_shares

    # 合并EPS
    pro_forma_eps = combined_net_income / combined_shares if combined_shares > 0 else 0

    # 增厚/稀释
    accretion_dilution = pro_forma_eps - standalone_eps
    accretion_dilution_percent = accretion_dilution / standalone_eps if standalone_eps != 0 else 0
    status = "Accretive" if accretion_dilution > 0 else "Dilutive" if accretion_dilution < 0 else "Neutral"

    return {
        "standalone": {
            "net_income": acquirer_net_income,
            "shares": acquirer_shares,
            "eps": standalone_eps
        },
        "pro_forma": {
            "acquirer_net_income": acquirer_net_income,
            "target_net_income": target_net_income,
            "foregone_interest": -foregone_interest,
            "debt_interest": -debt_interest,
            "synergies_net": synergies * (1 - tax_rate),
            "intangible_amort_net": -intangible_amort * (1 - tax_rate),
            "combined_net_income": combined_net_income,
            "new_shares_issued": new_shares,
            "combined_shares": combined_shares,
            "eps": pro_forma_eps
        },
        "accretion_dilution": {
            "value": accretion_dilution,
            "percent": accretion_dilution_percent,
            "status": status
        },
        "formula": "Pro Forma EPS = Combined Net Income / Combined Shares",
        "inputs": {
            "acquirer_net_income": acquirer_net_income,
            "acquirer_shares": acquirer_shares,
            "target_net_income": target_net_income,
            "purchase_price": purchase_price,
            "cash_percent": cash_percent,
            "stock_percent": stock_percent,
            "acquirer_share_price": acquirer_share_price,
            "cost_of_debt": cost_of_debt,
            "tax_rate": tax_rate,
            "foregone_interest_rate": foregone_interest_rate,
            "synergies": synergies,
            "intangible_amort": intangible_amort
        },
        "source": source
    }


def calc_synergies(
    cost_synergies: Union[float, List[float]],
    revenue_synergies: Union[float, List[float]] = 0,
    integration_costs: Union[float, List[float]] = 0,
    years: int = 5,
    discount_rate: float = 0.10,
    tax_rate: float = 0.25,
    margin_on_revenue: float = 0.20,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具6: 计算协同效应价值

    Args:
        cost_synergies: 成本协同（税前）- 单值或各年列表
        revenue_synergies: 收入协同 - 单值或各年列表
        integration_costs: 整合成本 - 单值或各年列表
        years: 分析年数
        discount_rate: 折现率
        tax_rate: 税率
        margin_on_revenue: 收入协同的利润率
        source: 计算来源标记

    Returns:
        dict: {
            "total_synergies_pv": 协同效应总现值,
            "yearly_details": 各年明细,
            "formula": 公式说明,
            "inputs": 输入参数,
            "source": 计算来源
        }

    示例:
        >>> result = calc_synergies(
        ...     cost_synergies=[500_000_000, 800_000_000, 1_000_000_000],
        ...     revenue_synergies=[0, 200_000_000, 500_000_000],
        ...     integration_costs=[300_000_000, 100_000_000, 0],
        ...     discount_rate=0.10
        ... )
        >>> result["total_synergies_pv"] > 0
        True
    """
    # 转换为列表
    if not isinstance(cost_synergies, list):
        cost_synergies = [cost_synergies] * years
    if not isinstance(revenue_synergies, list):
        revenue_synergies = [revenue_synergies] * years
    if not isinstance(integration_costs, list):
        integration_costs = [integration_costs] * years

    total_pv = 0
    yearly_details = []

    for year in range(years):
        cost_syn = cost_synergies[year] if year < len(cost_synergies) else cost_synergies[-1]
        rev_syn = revenue_synergies[year] if year < len(revenue_synergies) else revenue_synergies[-1]
        integ = integration_costs[year] if year < len(integration_costs) else 0

        # 收入协同转化为利润
        profit_from_revenue = rev_syn * margin_on_revenue

        # 税前总协同
        gross_synergy = cost_syn + profit_from_revenue - integ

        # 税后协同
        net_synergy = gross_synergy * (1 - tax_rate)

        # 折现
        discount_factor = 1 / (1 + discount_rate) ** (year + 1)
        pv = net_synergy * discount_factor

        total_pv += pv

        yearly_details.append({
            "year": year + 1,
            "cost_synergies": cost_syn,
            "revenue_synergies": rev_syn,
            "profit_from_revenue": profit_from_revenue,
            "integration_costs": integ,
            "gross_synergy": gross_synergy,
            "net_synergy": net_synergy,
            "discount_factor": discount_factor,
            "present_value": pv
        })

    # 计算终值（假设最后一年协同持续）
    final_net_synergy = yearly_details[-1]["net_synergy"]
    terminal_value = final_net_synergy / discount_rate  # 永续年金
    tv_pv = terminal_value / (1 + discount_rate) ** years

    total_pv_with_terminal = total_pv + tv_pv

    return {
        "total_synergies_pv": total_pv,
        "total_synergies_pv_with_terminal": total_pv_with_terminal,
        "terminal_value": {
            "value": terminal_value,
            "present_value": tv_pv
        },
        "yearly_details": yearly_details,
        "summary": {
            "total_cost_synergies": sum(d["cost_synergies"] for d in yearly_details),
            "total_revenue_synergies": sum(d["revenue_synergies"] for d in yearly_details),
            "total_integration_costs": sum(d["integration_costs"] for d in yearly_details)
        },
        "formula": "PV = Σ Net Synergies / (1+r)^t",
        "inputs": {
            "cost_synergies": cost_synergies,
            "revenue_synergies": revenue_synergies,
            "integration_costs": integration_costs,
            "years": years,
            "discount_rate": discount_rate,
            "tax_rate": tax_rate,
            "margin_on_revenue": margin_on_revenue
        },
        "source": source
    }


def calc_breakeven(
    acquirer_net_income: float,
    acquirer_shares: float,
    target_net_income: float,
    purchase_price: float,
    cash_percent: float,
    stock_percent: float,
    acquirer_share_price: float,
    cost_of_debt: float = 0.05,
    tax_rate: float = 0.25,
    foregone_interest_rate: float = 0.03,
    intangible_amort: float = 0,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具7: 计算盈亏平衡（需要多少协同效应才能不稀释）

    Args:
        （同 calc_accretion_dilution）

    Returns:
        dict: {
            "synergies_needed": 使EPS不稀释所需的年化协同效应（税前）,
            "current_dilution": 当前稀释情况,
            "formula": 公式说明,
            "inputs": 输入参数,
            "source": 计算来源
        }

    示例:
        >>> result = calc_breakeven(
        ...     acquirer_net_income=50_000_000_000,
        ...     acquirer_shares=1_000_000_000,
        ...     target_net_income=2_000_000_000,
        ...     purchase_price=13_000_000_000,
        ...     cash_percent=0.60,
        ...     stock_percent=0.40,
        ...     acquirer_share_price=100
        ... )
        >>> result["synergies_needed"] > 0  # 需要协同才能不稀释
        True
    """
    # 先计算无协同时的结果
    base_result = calc_accretion_dilution(
        acquirer_net_income=acquirer_net_income,
        acquirer_shares=acquirer_shares,
        target_net_income=target_net_income,
        purchase_price=purchase_price,
        cash_percent=cash_percent,
        stock_percent=stock_percent,
        acquirer_share_price=acquirer_share_price,
        cost_of_debt=cost_of_debt,
        tax_rate=tax_rate,
        foregone_interest_rate=foregone_interest_rate,
        synergies=0,
        intangible_amort=intangible_amort
    )

    standalone_eps = base_result["standalone"]["eps"]
    combined_shares = base_result["pro_forma"]["combined_shares"]
    current_combined_ni = base_result["pro_forma"]["combined_net_income"]

    # 计算需要的净利润增加额
    # 目标: Combined NI / Combined Shares = Standalone EPS
    # 即: Combined NI = Standalone EPS × Combined Shares
    target_combined_ni = standalone_eps * combined_shares
    ni_gap = target_combined_ni - current_combined_ni

    # 转换为税前协同效应
    # NI Gap = Synergies × (1 - tax_rate)
    # Synergies = NI Gap / (1 - tax_rate)
    synergies_needed = ni_gap / (1 - tax_rate) if (1 - tax_rate) > 0 else 0

    # 判断当前状态
    current_dilution = base_result["accretion_dilution"]

    return {
        "synergies_needed": max(synergies_needed, 0),  # 负值意味着已经增厚，不需要协同
        "synergies_needed_for_accretion": synergies_needed,  # 保留原值，负值表示已增厚
        "current_dilution": current_dilution,
        "analysis": {
            "standalone_eps": standalone_eps,
            "current_pro_forma_eps": base_result["pro_forma"]["eps"],
            "target_combined_ni": target_combined_ni,
            "current_combined_ni": current_combined_ni,
            "ni_gap": ni_gap
        },
        "interpretation": (
            f"需要年化税前协同效应 {synergies_needed:,.0f} 才能使EPS不稀释"
            if synergies_needed > 0
            else "当前交易已经增厚EPS，无需额外协同"
        ),
        "formula": "Synergies Needed = (Target EPS × Combined Shares - Current Combined NI) / (1 - Tax Rate)",
        "inputs": {
            "acquirer_net_income": acquirer_net_income,
            "acquirer_shares": acquirer_shares,
            "target_net_income": target_net_income,
            "purchase_price": purchase_price,
            "cash_percent": cash_percent,
            "stock_percent": stock_percent,
            "acquirer_share_price": acquirer_share_price,
            "cost_of_debt": cost_of_debt,
            "tax_rate": tax_rate,
            "foregone_interest_rate": foregone_interest_rate,
            "intangible_amort": intangible_amort
        },
        "source": source
    }


def ma_quick_build(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    快捷构建: 一键完成M&A分析

    内部依次调用所有原子工具。当需要自定义某个步骤时，
    可以单独调用原子工具替代。

    Args:
        inputs: M&A输入参数，包含:
            - acquirer: 收购方财务数据
                - share_price: 股价
                - shares_outstanding: 流通股数
                - net_income: 净利润
                - total_assets: 总资产
                - total_liabilities: 总负债
                - total_equity: 总权益
                - cash: 现金
                - goodwill: 商誉
            - target: 目标公司财务数据（同上）
            - deal_terms: 交易条款
                - premium_percent: 溢价比例
                - cash_percent: 现金支付比例
                - stock_percent: 股票支付比例
            - ppa: 购买价格分摊（可选）
                - intangible_assets: 无形资产
                - intangible_amortization_years: 摊销年限
                - fixed_assets_step_up: 固定资产增值
                - deferred_tax_liability: 递延税负债
            - synergies: 协同效应假设（可选）
                - cost_synergies: 成本协同
                - revenue_synergies: 收入协同
                - integration_costs: 整合成本
            - assumptions: 其他假设
                - tax_rate: 税率
                - cost_of_debt: 债务成本
                - discount_rate: 折现率
                - foregone_interest_rate: 损失利息率

    Returns:
        dict: 完整M&A分析结果

    示例:
        >>> inputs = {
        ...     "acquirer": {"share_price": 100, "shares_outstanding": 1_000_000_000, ...},
        ...     "target": {"share_price": 50, "shares_outstanding": 200_000_000, ...},
        ...     "deal_terms": {"premium_percent": 0.30, "cash_percent": 0.60, "stock_percent": 0.40}
        ... }
        >>> result = ma_quick_build(inputs)
    """
    acquirer = inputs["acquirer"]
    target = inputs["target"]
    deal_terms = inputs["deal_terms"]
    ppa = inputs.get("ppa", {})
    synergies_input = inputs.get("synergies", {})
    assumptions = inputs.get("assumptions", {})

    tax_rate = assumptions.get("tax_rate", 0.25)
    cost_of_debt = assumptions.get("cost_of_debt", 0.05)
    discount_rate = assumptions.get("discount_rate", 0.10)
    foregone_interest_rate = assumptions.get("foregone_interest_rate", 0.03)

    # 1. 收购报价
    offer = calc_offer_price(
        target_share_price=target["share_price"],
        target_shares=target["shares_outstanding"],
        premium_percent=deal_terms["premium_percent"]
    )
    purchase_price = offer["total_purchase_price"]

    # 2. 融资结构
    funding = calc_funding_mix(
        total_purchase_price=purchase_price,
        cash_percent=deal_terms["cash_percent"],
        stock_percent=deal_terms["stock_percent"],
        acquirer_share_price=acquirer["share_price"],
        new_debt=deal_terms.get("new_debt", 0)
    )

    # 3. 商誉计算
    target_book_value = target.get("total_equity", target.get("book_value", 0))
    goodwill_result = calc_goodwill(
        purchase_price=purchase_price,
        target_book_value=target_book_value,
        fair_value_adjustments={
            "intangible_assets": ppa.get("intangible_assets", 0),
            "fixed_assets_step_up": ppa.get("fixed_assets_step_up", 0),
            "deferred_tax_liability": ppa.get("deferred_tax_liability", 0)
        }
    )

    # 4. 无形资产摊销
    intangible_assets = ppa.get("intangible_assets", 0)
    amort_years = ppa.get("intangible_amortization_years", 10)
    intangible_amort = intangible_assets / amort_years if amort_years > 0 else 0

    # 5. 增厚/稀释分析（无协同）
    base_ad = calc_accretion_dilution(
        acquirer_net_income=acquirer["net_income"],
        acquirer_shares=acquirer["shares_outstanding"],
        target_net_income=target["net_income"],
        purchase_price=purchase_price,
        cash_percent=deal_terms["cash_percent"],
        stock_percent=deal_terms["stock_percent"],
        acquirer_share_price=acquirer["share_price"],
        cost_of_debt=cost_of_debt,
        tax_rate=tax_rate,
        foregone_interest_rate=foregone_interest_rate,
        synergies=0,
        intangible_amort=intangible_amort
    )

    # 6. 协同效应分析
    synergies_result = None
    if synergies_input:
        synergies_result = calc_synergies(
            cost_synergies=synergies_input.get("cost_synergies", 0),
            revenue_synergies=synergies_input.get("revenue_synergies", 0),
            integration_costs=synergies_input.get("integration_costs", 0),
            years=synergies_input.get("years", 5),
            discount_rate=discount_rate,
            tax_rate=tax_rate,
            margin_on_revenue=synergies_input.get("margin_on_revenue", 0.20)
        )

    # 7. 增厚/稀释分析（含协同）
    ad_with_synergies = None
    if synergies_input:
        # 使用第一年协同作为代表
        year1_synergies = synergies_input.get("cost_synergies", 0)
        if isinstance(year1_synergies, list):
            year1_synergies = year1_synergies[0] if year1_synergies else 0

        ad_with_synergies = calc_accretion_dilution(
            acquirer_net_income=acquirer["net_income"],
            acquirer_shares=acquirer["shares_outstanding"],
            target_net_income=target["net_income"],
            purchase_price=purchase_price,
            cash_percent=deal_terms["cash_percent"],
            stock_percent=deal_terms["stock_percent"],
            acquirer_share_price=acquirer["share_price"],
            cost_of_debt=cost_of_debt,
            tax_rate=tax_rate,
            foregone_interest_rate=foregone_interest_rate,
            synergies=year1_synergies,
            intangible_amort=intangible_amort
        )

    # 8. 盈亏平衡分析
    breakeven = calc_breakeven(
        acquirer_net_income=acquirer["net_income"],
        acquirer_shares=acquirer["shares_outstanding"],
        target_net_income=target["net_income"],
        purchase_price=purchase_price,
        cash_percent=deal_terms["cash_percent"],
        stock_percent=deal_terms["stock_percent"],
        acquirer_share_price=acquirer["share_price"],
        cost_of_debt=cost_of_debt,
        tax_rate=tax_rate,
        foregone_interest_rate=foregone_interest_rate,
        intangible_amort=intangible_amort
    )

    # 9. 合并报表
    pro_forma = calc_pro_forma(
        acquirer_financials={
            "total_assets": acquirer.get("total_assets", 0),
            "cash": acquirer.get("cash", 0),
            "goodwill": acquirer.get("goodwill", 0),
            "intangible_assets": acquirer.get("intangible_assets", 0),
            "total_liabilities": acquirer.get("total_liabilities", 0),
            "total_equity": acquirer.get("total_equity", 0)
        },
        target_financials={
            "total_assets": target.get("total_assets", 0),
            "cash": target.get("cash", 0),
            "goodwill": target.get("goodwill", 0),
            "intangible_assets": target.get("intangible_assets", 0),
            "total_liabilities": target.get("total_liabilities", 0),
            "total_equity": target.get("total_equity", 0)
        },
        deal_adjustments={
            "cash_used": funding["cash_amount"],
            "new_debt": funding["new_debt"],
            "new_equity_issued": funding["stock_amount"],
            "goodwill_created": max(goodwill_result["goodwill"], 0),
            "intangible_assets_created": ppa.get("intangible_assets", 0),
            "fixed_assets_step_up": ppa.get("fixed_assets_step_up", 0),
            "deferred_tax_liability": ppa.get("deferred_tax_liability", 0)
        }
    )

    # 10. 协同效应覆盖率
    synergy_coverage = None
    if synergies_result and offer["premium"]["value"] > 0:
        synergy_coverage = {
            "synergies_pv": synergies_result["total_synergies_pv_with_terminal"],
            "premium_paid": offer["premium"]["value"],
            "coverage_ratio": synergies_result["total_synergies_pv_with_terminal"] / offer["premium"]["value"],
            "interpretation": (
                "协同效应现值覆盖溢价 {:.2f}x".format(
                    synergies_result["total_synergies_pv_with_terminal"] / offer["premium"]["value"]
                )
            )
        }

    return {
        "_meta": {
            "model_type": "ma",
            "acquirer": inputs.get("acquirer_name", "Acquirer"),
            "target": inputs.get("target_name", "Target"),
            "built_with": "atomic_tools"
        },
        "deal_summary": {
            "offer": offer,
            "funding": funding,
            "purchase_price": purchase_price,
            "premium": offer["premium"]
        },
        "purchase_price_allocation": goodwill_result,
        "intangible_amortization": {
            "annual_amortization": intangible_amort,
            "years": amort_years
        },
        "accretion_dilution": {
            "without_synergies": base_ad,
            "with_synergies": ad_with_synergies
        },
        "synergies": synergies_result,
        "synergy_coverage": synergy_coverage,
        "breakeven": breakeven,
        "pro_forma_balance_sheet": pro_forma
    }
