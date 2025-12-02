# -*- coding: utf-8 -*-
"""
LBO 原子工具

独立的、可组合的LBO计算工具，供LLM灵活调用。

设计原则:
1. 每个工具独立运行，不依赖类状态
2. 输入输出清晰（dict格式，可序列化为JSON）
3. 可自由组合，LLM可以跳过、替换、插入任何步骤
4. 保留计算追溯信息

工具清单:
- calc_purchase_price: 收购价格
- calc_sources_uses: 资金来源与用途
- project_operations: 预测运营数据
- calc_debt_schedule: 债务计划表
- calc_exit_value: 退出价值
- calc_equity_proceeds: 股权所得
- calc_irr: 内部收益率
- calc_moic: 投资倍数
- lbo_quick_build: 快捷构建（依次调用上述工具）
"""

from typing import Dict, List, Any, Optional, Union


def calc_purchase_price(
    ebitda: float,
    multiple: float,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具1: 计算收购价格

    公式: Purchase Price = EBITDA × Entry Multiple

    Args:
        ebitda: 入场EBITDA
        multiple: 入场倍数
        source: 计算来源标记 ("tool" 或 "llm_override")

    Returns:
        dict: {
            "value": 收购价格,
            "formula": 公式说明,
            "inputs": 输入参数,
            "source": 计算来源
        }

    示例:
        >>> result = calc_purchase_price(100_000_000, 8.0)
        >>> result["value"]
        800000000
    """
    value = ebitda * multiple

    return {
        "value": value,
        "formula": "EBITDA × Entry Multiple",
        "inputs": {
            "ebitda": ebitda,
            "multiple": multiple
        },
        "source": source
    }


def calc_sources_uses(
    purchase_price: float,
    debt_amounts: Dict[str, float],
    transaction_fee_rate: float = 0.02,
    financing_fee_rate: float = 0.01,
    existing_cash: float = 0,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具2: 计算资金来源与用途

    公式: Equity = Total Uses - Total Debt - Existing Cash

    Args:
        purchase_price: 收购价格
        debt_amounts: 各笔债务金额 {"senior": 320000000, "subordinated": 160000000}
        transaction_fee_rate: 交易费用率（默认2%）
        financing_fee_rate: 融资费用率（默认1%）
        existing_cash: 目标公司可用现金
        source: 计算来源标记

    Returns:
        dict: {
            "equity_required": 所需股权,
            "uses": 资金用途明细,
            "sources": 资金来源明细,
            "formula": 公式说明,
            "inputs": 输入参数,
            "source": 计算来源
        }

    示例:
        >>> result = calc_sources_uses(
        ...     purchase_price=800_000_000,
        ...     debt_amounts={"senior": 320_000_000, "sub": 160_000_000}
        ... )
        >>> result["equity_required"]
        344800000.0
    """
    # 计算用途
    transaction_fees = purchase_price * transaction_fee_rate
    total_debt = sum(debt_amounts.values())
    financing_fees = total_debt * financing_fee_rate
    total_uses = purchase_price + transaction_fees + financing_fees

    # 计算来源
    equity_required = total_uses - total_debt - existing_cash

    uses = {
        "purchase_price": purchase_price,
        "transaction_fees": transaction_fees,
        "financing_fees": financing_fees,
        "total_uses": total_uses
    }

    sources = {
        **{f"debt_{k}": v for k, v in debt_amounts.items()},
        "total_debt": total_debt,
        "existing_cash": existing_cash,
        "equity": equity_required,
        "total_sources": total_uses
    }

    return {
        "equity_required": equity_required,
        "uses": uses,
        "sources": sources,
        "formula": "Equity = Total Uses - Total Debt - Existing Cash",
        "inputs": {
            "purchase_price": purchase_price,
            "debt_amounts": debt_amounts,
            "transaction_fee_rate": transaction_fee_rate,
            "financing_fee_rate": financing_fee_rate,
            "existing_cash": existing_cash
        },
        "source": source
    }


def project_operations(
    base_revenue: float,
    years: int,
    revenue_growth: Union[float, List[float]],
    ebitda_margin: Union[float, List[float]],
    capex_percent: float = 0.03,
    nwc_percent: float = 0.10,
    tax_rate: float = 0.25,
    da_percent: float = 0.03,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具3: 预测运营数据

    Args:
        base_revenue: 基期收入
        years: 预测年数
        revenue_growth: 收入增长率（单值或列表）
        ebitda_margin: EBITDA利润率（单值或列表）
        capex_percent: 资本支出占收入比例
        nwc_percent: 营运资本占收入比例
        tax_rate: 税率
        da_percent: 折旧摊销占收入比例
        source: 计算来源标记

    Returns:
        dict: {
            "projections": 各年预测数据列表,
            "summary": 汇总信息,
            "inputs": 输入参数,
            "source": 计算来源
        }

    示例:
        >>> result = project_operations(
        ...     base_revenue=500_000_000,
        ...     years=5,
        ...     revenue_growth=0.05,
        ...     ebitda_margin=0.20
        ... )
        >>> len(result["projections"])
        5
    """
    # 处理输入：转换为列表
    if not isinstance(revenue_growth, list):
        revenue_growth = [revenue_growth] * years
    if not isinstance(ebitda_margin, list):
        ebitda_margin = [ebitda_margin] * years

    projections = []
    revenue = base_revenue
    last_nwc = base_revenue * nwc_percent

    for i in range(years):
        growth = revenue_growth[i] if i < len(revenue_growth) else revenue_growth[-1]
        margin = ebitda_margin[i] if i < len(ebitda_margin) else ebitda_margin[-1]

        revenue = revenue * (1 + growth)
        ebitda = revenue * margin
        da = revenue * da_percent
        ebit = ebitda - da
        capex = revenue * capex_percent
        nwc = revenue * nwc_percent
        delta_nwc = nwc - last_nwc
        last_nwc = nwc

        # UFCF = EBITDA - Capex - ΔNWC (税前、利息前)
        ufcf = ebitda - capex - delta_nwc

        projections.append({
            "year": i + 1,
            "revenue": revenue,
            "ebitda": ebitda,
            "depreciation": da,
            "ebit": ebit,
            "capex": capex,
            "nwc": nwc,
            "delta_nwc": delta_nwc,
            "ufcf": ufcf,
            "tax_rate": tax_rate
        })

    return {
        "projections": projections,
        "summary": {
            "entry_revenue": base_revenue,
            "exit_revenue": projections[-1]["revenue"],
            "exit_ebitda": projections[-1]["ebitda"],
            "total_ufcf": sum(p["ufcf"] for p in projections)
        },
        "inputs": {
            "base_revenue": base_revenue,
            "years": years,
            "revenue_growth": revenue_growth,
            "ebitda_margin": ebitda_margin,
            "capex_percent": capex_percent,
            "nwc_percent": nwc_percent,
            "tax_rate": tax_rate,
            "da_percent": da_percent
        },
        "source": source
    }


def calc_debt_schedule(
    debt_tranches: List[Dict[str, Any]],
    operations: List[Dict[str, float]],
    sweep_percent: float = 0.75,
    min_cash: float = 0,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具4: 构建债务计划表

    Args:
        debt_tranches: 债务层级列表，每项包含:
            - name: 债务名称
            - amount: 初始金额
            - interest_rate: 利率
            - amortization_rate: 每年强制还本比例（默认0）
            - pik_rate: PIK利息率（默认0）
            - priority: 还款优先级（1最高，默认1）
        operations: 运营预测数据（来自 project_operations）
        sweep_percent: 现金扫荡比例
        min_cash: 最低现金保留

    Returns:
        dict: {
            "schedule": 各债务层级的还款计划,
            "annual_summary": 年度汇总,
            "final_debt": 最终剩余债务,
            "total_interest_paid": 总利息支出,
            "inputs": 输入参数,
            "source": 计算来源
        }

    示例:
        >>> tranches = [
        ...     {"name": "senior", "amount": 320_000_000, "interest_rate": 0.06, "amortization_rate": 0.05},
        ...     {"name": "sub", "amount": 160_000_000, "interest_rate": 0.10, "pik_rate": 0.02}
        ... ]
        >>> result = calc_debt_schedule(tranches, operations_data)
    """
    # 处理输入：确保operations是列表
    if isinstance(operations, dict) and "projections" in operations:
        operations = operations["projections"]

    # 初始化债务状态
    tranches_state = []
    for t in debt_tranches:
        tranches_state.append({
            "name": t["name"],
            "initial_amount": t["amount"],
            "interest_rate": t["interest_rate"],
            "amortization_rate": t.get("amortization_rate", 0),
            "pik_rate": t.get("pik_rate", 0),
            "priority": t.get("priority", 1),
            "balance": t["amount"]
        })

    # 按优先级排序
    tranches_state.sort(key=lambda x: x["priority"])

    # 构建计划表
    schedule = {t["name"]: [] for t in tranches_state}
    annual_summary = []
    total_interest_paid = 0

    for ops in operations:
        year = ops["year"]
        ufcf = ops["ufcf"]
        ebit = ops["ebit"]
        tax_rate = ops["tax_rate"]

        # 第一轮：计算利息
        total_interest = 0
        for t in tranches_state:
            interest = t["balance"] * t["interest_rate"]
            total_interest += interest

        total_interest_paid += total_interest

        # 计算税后现金流
        ebt = ebit - total_interest
        taxes = max(ebt * tax_rate, 0)
        net_income = ebt - taxes

        # 可用于还债的现金
        cash_for_debt = ufcf - total_interest - taxes

        # 计算强制还本总额
        total_mandatory = 0
        for t in tranches_state:
            mandatory = t["initial_amount"] * t["amortization_rate"]
            total_mandatory += min(mandatory, t["balance"])

        # 现金扫荡金额
        excess_cash = max(cash_for_debt - total_mandatory - min_cash, 0)
        sweep_amount = excess_cash * sweep_percent

        # 第二轮：按优先级还款
        remaining_sweep = sweep_amount
        year_details = {
            "year": year,
            "ufcf": ufcf,
            "total_interest": total_interest,
            "taxes": taxes,
            "net_income": net_income,
            "cash_for_debt": cash_for_debt,
            "mandatory_amort": 0,
            "cash_sweep": 0,
            "total_debt_paydown": 0,
            "ending_debt": 0
        }

        for t in tranches_state:
            opening = t["balance"]
            cash_interest = opening * t["interest_rate"]
            pik_interest = opening * t["pik_rate"]

            # 强制还本
            mandatory_amort = min(
                t["initial_amount"] * t["amortization_rate"],
                opening + pik_interest
            )

            # 现金扫荡
            available_for_sweep = opening + pik_interest - mandatory_amort
            tranche_sweep = min(remaining_sweep, max(available_for_sweep, 0))

            # 期末余额
            closing = opening + pik_interest - mandatory_amort - tranche_sweep
            t["balance"] = max(closing, 0)

            # 记录
            schedule[t["name"]].append({
                "year": year,
                "opening_balance": opening,
                "cash_interest": cash_interest,
                "pik_interest": pik_interest,
                "mandatory_amort": mandatory_amort,
                "cash_sweep": tranche_sweep,
                "total_principal_payment": mandatory_amort + tranche_sweep,
                "closing_balance": t["balance"]
            })

            remaining_sweep -= tranche_sweep
            year_details["mandatory_amort"] += mandatory_amort
            year_details["cash_sweep"] += tranche_sweep
            year_details["total_debt_paydown"] += mandatory_amort + tranche_sweep
            year_details["ending_debt"] += t["balance"]

        # 自由现金流（扣除还本）
        year_details["fcf_to_equity"] = cash_for_debt - year_details["total_debt_paydown"]

        annual_summary.append(year_details)

    final_debt = sum(t["balance"] for t in tranches_state)

    return {
        "schedule": schedule,
        "annual_summary": annual_summary,
        "final_debt": final_debt,
        "total_interest_paid": total_interest_paid,
        "inputs": {
            "debt_tranches": debt_tranches,
            "sweep_percent": sweep_percent,
            "min_cash": min_cash
        },
        "source": source
    }


def calc_exit_value(
    exit_ebitda: float,
    exit_multiple: float,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具5: 计算退出价值

    公式: Exit Value = Exit EBITDA × Exit Multiple

    Args:
        exit_ebitda: 退出时EBITDA
        exit_multiple: 退出倍数
        source: 计算来源标记

    Returns:
        dict: {
            "value": 退出价值,
            "formula": 公式说明,
            "inputs": 输入参数,
            "source": 计算来源
        }

    示例:
        >>> result = calc_exit_value(130_000_000, 8.0)
        >>> result["value"]
        1040000000
    """
    value = exit_ebitda * exit_multiple

    return {
        "value": value,
        "formula": "Exit EBITDA × Exit Multiple",
        "inputs": {
            "exit_ebitda": exit_ebitda,
            "exit_multiple": exit_multiple
        },
        "source": source
    }


def calc_equity_proceeds(
    exit_value: float,
    ending_debt: float,
    ending_cash: float = 0,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具6: 计算股权所得

    公式: Equity Proceeds = Exit Value - Net Debt

    Args:
        exit_value: 退出价值
        ending_debt: 退出时剩余债务
        ending_cash: 退出时现金
        source: 计算来源标记

    Returns:
        dict: {
            "value": 股权所得,
            "net_debt": 净债务,
            "formula": 公式说明,
            "inputs": 输入参数,
            "source": 计算来源
        }

    示例:
        >>> result = calc_equity_proceeds(1_040_000_000, 180_000_000, 20_000_000)
        >>> result["value"]
        880000000
    """
    net_debt = ending_debt - ending_cash
    value = exit_value - net_debt

    return {
        "value": value,
        "net_debt": net_debt,
        "formula": "Exit Value - Net Debt",
        "inputs": {
            "exit_value": exit_value,
            "ending_debt": ending_debt,
            "ending_cash": ending_cash
        },
        "source": source
    }


def calc_irr(
    cash_flows: List[float],
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具7: 计算内部收益率 (IRR)

    使用牛顿迭代法求解

    Args:
        cash_flows: 现金流序列 [-投入, cf1, cf2, ..., 退出所得]
        source: 计算来源标记

    Returns:
        dict: {
            "value": IRR值,
            "formula": 公式说明,
            "inputs": 输入参数,
            "source": 计算来源
        }

    示例:
        >>> result = calc_irr([-344_000_000, 0, 0, 0, 0, 880_000_000])
        >>> round(result["value"], 3)
        0.207
    """
    # 牛顿迭代法求IRR
    def npv(rate: float, cfs: List[float]) -> float:
        return sum(cf / (1 + rate) ** t for t, cf in enumerate(cfs))

    def npv_derivative(rate: float, cfs: List[float]) -> float:
        return sum(-t * cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cfs))

    # 初始猜测
    irr = 0.10
    for _ in range(100):
        npv_val = npv(irr, cash_flows)
        npv_deriv = npv_derivative(irr, cash_flows)

        if abs(npv_deriv) < 1e-10:
            break

        irr_new = irr - npv_val / npv_deriv

        if abs(irr_new - irr) < 1e-8:
            irr = irr_new
            break

        irr = irr_new

    return {
        "value": irr,
        "formula": "IRR(Cash Flows)",
        "inputs": {
            "cash_flows": cash_flows,
            "years": len(cash_flows) - 1
        },
        "source": source
    }


def calc_moic(
    equity_invested: float,
    equity_proceeds: float,
    interim_distributions: float = 0,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具8: 计算投资倍数 (MOIC)

    公式: MOIC = (Exit Proceeds + Distributions) / Equity Invested

    Args:
        equity_invested: 股权投入
        equity_proceeds: 退出所得
        interim_distributions: 期间分红
        source: 计算来源标记

    Returns:
        dict: {
            "value": MOIC值,
            "formula": 公式说明,
            "inputs": 输入参数,
            "source": 计算来源
        }

    示例:
        >>> result = calc_moic(344_000_000, 880_000_000)
        >>> round(result["value"], 2)
        2.56
    """
    total_return = equity_proceeds + interim_distributions
    value = total_return / equity_invested if equity_invested > 0 else 0

    return {
        "value": value,
        "formula": "(Exit Proceeds + Distributions) / Equity Invested",
        "inputs": {
            "equity_invested": equity_invested,
            "equity_proceeds": equity_proceeds,
            "interim_distributions": interim_distributions,
            "total_return": total_return
        },
        "source": source
    }


def lbo_quick_build(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    快捷构建: 一键完成LBO分析

    内部依次调用所有原子工具。当需要自定义某个步骤时，
    可以单独调用原子工具替代。

    Args:
        inputs: LBO输入参数，包含:
            - entry_ebitda: 入场EBITDA
            - entry_multiple: 入场倍数
            - exit_multiple: 退出倍数
            - holding_period: 持有期
            - revenue_growth: 收入增长率
            - ebitda_margin: EBITDA利润率
            - capex_percent: 资本支出率（默认0.03）
            - nwc_percent: 营运资本率（默认0.10）
            - tax_rate: 税率（默认0.25）
            - transaction_fee_rate: 交易费用率（默认0.02）
            - financing_fee_rate: 融资费用率（默认0.01）
            - debt_structure: 债务结构
            - sweep_percent: 现金扫荡比例（默认0.75）

    Returns:
        dict: 完整LBO分析结果

    示例:
        >>> inputs = {
        ...     "entry_ebitda": 100_000_000,
        ...     "entry_multiple": 8.0,
        ...     "exit_multiple": 8.0,
        ...     "holding_period": 5,
        ...     "revenue_growth": 0.05,
        ...     "ebitda_margin": 0.20,
        ...     "debt_structure": {
        ...         "senior": {"amount_percent": 0.40, "interest_rate": 0.06, "amortization_rate": 0.05},
        ...         "sub": {"amount_percent": 0.20, "interest_rate": 0.10, "pik_rate": 0.02}
        ...     }
        ... }
        >>> result = lbo_quick_build(inputs)
        >>> result["returns"]["irr"]["value"] > 0
        True
    """
    # 1. 收购价格
    purchase = calc_purchase_price(
        inputs["entry_ebitda"],
        inputs["entry_multiple"]
    )
    purchase_price = purchase["value"]

    # 2. 债务设置
    debt_amounts = {}
    debt_tranches = []
    for name, config in inputs["debt_structure"].items():
        amount = purchase_price * config["amount_percent"]
        debt_amounts[name] = amount
        debt_tranches.append({
            "name": name,
            "amount": amount,
            "interest_rate": config["interest_rate"],
            "amortization_rate": config.get("amortization_rate", 0),
            "pik_rate": config.get("pik_rate", 0),
            "priority": config.get("priority", 1)
        })

    # 3. 资金来源与用途
    sources_uses = calc_sources_uses(
        purchase_price=purchase_price,
        debt_amounts=debt_amounts,
        transaction_fee_rate=inputs.get("transaction_fee_rate", 0.02),
        financing_fee_rate=inputs.get("financing_fee_rate", 0.01),
        existing_cash=inputs.get("existing_cash", 0)
    )
    equity_invested = sources_uses["equity_required"]

    # 4. 运营预测
    base_margin = inputs["ebitda_margin"]
    if isinstance(base_margin, list):
        base_margin = base_margin[0]
    base_revenue = inputs["entry_ebitda"] / base_margin

    operations = project_operations(
        base_revenue=base_revenue,
        years=inputs["holding_period"],
        revenue_growth=inputs["revenue_growth"],
        ebitda_margin=inputs["ebitda_margin"],
        capex_percent=inputs.get("capex_percent", 0.03),
        nwc_percent=inputs.get("nwc_percent", 0.10),
        tax_rate=inputs.get("tax_rate", 0.25),
        da_percent=inputs.get("da_percent", 0.03)
    )

    # 5. 债务计划
    debt_schedule = calc_debt_schedule(
        debt_tranches=debt_tranches,
        operations=operations["projections"],
        sweep_percent=inputs.get("sweep_percent", 0.75),
        min_cash=inputs.get("min_cash", 0)
    )

    # 6. 退出分析
    exit_ebitda = operations["summary"]["exit_ebitda"]
    exit_val = calc_exit_value(exit_ebitda, inputs["exit_multiple"])

    ending_debt = debt_schedule["final_debt"]
    equity_proc = calc_equity_proceeds(exit_val["value"], ending_debt)

    # 7. 回报计算
    cash_flows = [-equity_invested]
    for _ in range(inputs["holding_period"] - 1):
        cash_flows.append(0)
    cash_flows.append(equity_proc["value"])

    irr = calc_irr(cash_flows)
    moic = calc_moic(equity_invested, equity_proc["value"])

    # 8. 信用指标
    credit_stats = []
    for ops, summ in zip(operations["projections"], debt_schedule["annual_summary"]):
        total_debt = summ["ending_debt"]
        interest = summ["total_interest"]
        ebitda = ops["ebitda"]

        credit_stats.append({
            "year": ops["year"],
            "debt_to_ebitda": round(total_debt / ebitda, 2) if ebitda > 0 else None,
            "interest_coverage": round(ebitda / interest, 2) if interest > 0 else None,
            "debt_paydown": summ["total_debt_paydown"]
        })

    return {
        "_meta": {
            "model_type": "lbo",
            "holding_period": inputs["holding_period"],
            "built_with": "atomic_tools"
        },
        "transaction": {
            "purchase_price": purchase,
            "sources_uses": sources_uses,
            "equity_invested": equity_invested
        },
        "operating_model": operations,
        "debt_schedule": debt_schedule,
        "exit_analysis": {
            "exit_ebitda": exit_ebitda,
            "exit_value": exit_val,
            "ending_debt": ending_debt,
            "equity_proceeds": equity_proc
        },
        "returns": {
            "irr": irr,
            "moic": moic,
            "cash_flows": cash_flows
        },
        "credit_stats": credit_stats
    }
