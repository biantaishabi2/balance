# -*- coding: utf-8 -*-
"""
cash_tools.py - 资金管理原子工具

提供现金流预测、营运资金周期分析、现金流驱动因素分解等功能。
设计为无状态的原子函数，供 LLM 灵活调用组合。
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


# ============================================================
# 13周现金流预测
# ============================================================

def cash_forecast_13w(
    opening_cash: float,
    receivables_schedule: List[Dict[str, Any]],
    payables_schedule: List[Dict[str, Any]],
    recurring_inflows: Optional[List[Dict[str, Any]]] = None,
    recurring_outflows: Optional[List[Dict[str, Any]]] = None,
    weeks: int = 13
) -> Dict[str, Any]:
    """
    13周现金流预测

    生成未来13周的现金流入流出预测，识别资金缺口。

    Args:
        opening_cash: 期初现金余额
        receivables_schedule: 应收回款计划
            [{"week": 1, "amount": 100, "source": "客户A"}, ...]
        payables_schedule: 应付付款计划
            [{"week": 1, "amount": 80, "payee": "供应商B"}, ...]
        recurring_inflows: 固定收入项目（每周重复）
            [{"amount": 10, "description": "租金收入"}, ...]
        recurring_outflows: 固定支出项目（每周重复）
            [{"amount": 50, "description": "工资"}, ...]
        weeks: 预测周数，默认13周

    Returns:
        {
            "weekly_forecast": [...],     # 每周详细预测
            "summary": {
                "total_inflows": 总流入,
                "total_outflows": 总流出,
                "net_cash_flow": 净现金流,
                "ending_cash": 期末现金
            },
            "funding_gaps": [...],        # 资金缺口周次
            "min_balance": {              # 最低余额信息
                "week": 周次,
                "balance": 余额
            }
        }

    Example:
        >>> cash_forecast_13w(
        ...     opening_cash=1000,
        ...     receivables_schedule=[{"week": 1, "amount": 500}, {"week": 3, "amount": 800}],
        ...     payables_schedule=[{"week": 2, "amount": 600}],
        ...     recurring_outflows=[{"amount": 100, "description": "工资"}]
        ... )
    """
    recurring_inflows = recurring_inflows or []
    recurring_outflows = recurring_outflows or []

    # 初始化每周数据
    weekly_forecast = []
    current_balance = opening_cash

    # 预计算每周的收付款
    weekly_inflows = {i: [] for i in range(1, weeks + 1)}
    weekly_outflows = {i: [] for i in range(1, weeks + 1)}

    # 应收回款
    for item in receivables_schedule:
        week = item.get("week", 1)
        if 1 <= week <= weeks:
            weekly_inflows[week].append({
                "amount": item.get("amount", 0),
                "source": item.get("source", "应收回款"),
                "type": "receivable"
            })

    # 应付付款
    for item in payables_schedule:
        week = item.get("week", 1)
        if 1 <= week <= weeks:
            weekly_outflows[week].append({
                "amount": item.get("amount", 0),
                "payee": item.get("payee", "应付账款"),
                "type": "payable"
            })

    # 生成每周预测
    total_inflows = 0
    total_outflows = 0
    funding_gaps = []
    min_balance = {"week": 0, "balance": opening_cash}

    for week in range(1, weeks + 1):
        # 本周流入
        week_inflows = weekly_inflows[week].copy()
        for recurring in recurring_inflows:
            week_inflows.append({
                "amount": recurring.get("amount", 0),
                "source": recurring.get("description", "固定收入"),
                "type": "recurring"
            })

        # 本周流出
        week_outflows = weekly_outflows[week].copy()
        for recurring in recurring_outflows:
            week_outflows.append({
                "amount": recurring.get("amount", 0),
                "payee": recurring.get("description", "固定支出"),
                "type": "recurring"
            })

        # 计算金额
        inflow_total = sum(item["amount"] for item in week_inflows)
        outflow_total = sum(item["amount"] for item in week_outflows)
        net_flow = inflow_total - outflow_total
        ending_balance = current_balance + net_flow

        total_inflows += inflow_total
        total_outflows += outflow_total

        # 记录资金缺口
        if ending_balance < 0:
            funding_gaps.append({
                "week": week,
                "shortfall": abs(ending_balance)
            })

        # 更新最低余额
        if ending_balance < min_balance["balance"]:
            min_balance = {"week": week, "balance": ending_balance}

        weekly_forecast.append({
            "week": week,
            "opening_balance": current_balance,
            "inflows": week_inflows,
            "inflow_total": inflow_total,
            "outflows": week_outflows,
            "outflow_total": outflow_total,
            "net_flow": net_flow,
            "ending_balance": ending_balance
        })

        current_balance = ending_balance

    return {
        "weekly_forecast": weekly_forecast,
        "summary": {
            "opening_cash": opening_cash,
            "total_inflows": total_inflows,
            "total_outflows": total_outflows,
            "net_cash_flow": total_inflows - total_outflows,
            "ending_cash": current_balance
        },
        "funding_gaps": funding_gaps,
        "has_funding_gap": len(funding_gaps) > 0,
        "min_balance": min_balance,
        "weeks": weeks
    }


# ============================================================
# 营运资金周期
# ============================================================

def working_capital_cycle(
    accounts_receivable: float,
    inventory: float,
    accounts_payable: float,
    revenue: float,
    cogs: float,
    period_days: int = 365
) -> Dict[str, Any]:
    """
    营运资金周期分析

    计算现金转换周期(CCC)及各组成部分。

    Args:
        accounts_receivable: 应收账款余额
        inventory: 存货余额
        accounts_payable: 应付账款余额
        revenue: 营业收入（年化或指定期间）
        cogs: 销售成本（年化或指定期间）
        period_days: 数据对应的天数，默认365天（年度）

    Returns:
        {
            "dso": 应收周转天数 (Days Sales Outstanding),
            "dio": 存货周转天数 (Days Inventory Outstanding),
            "dpo": 应付周转天数 (Days Payable Outstanding),
            "ccc": 现金转换周期 (Cash Conversion Cycle),
            "working_capital": 营运资金需求,
            "analysis": {
                "ar_turnover": 应收周转率,
                "inventory_turnover": 存货周转率,
                "ap_turnover": 应付周转率
            },
            "interpretation": 分析解读
        }

    Example:
        >>> working_capital_cycle(
        ...     accounts_receivable=1200,
        ...     inventory=400,
        ...     accounts_payable=900,
        ...     revenue=13700,
        ...     cogs=8900
        ... )
    """
    # 计算日均值
    daily_revenue = revenue / period_days
    daily_cogs = cogs / period_days

    # DSO - 应收周转天数
    dso = accounts_receivable / daily_revenue if daily_revenue > 0 else 0

    # DIO - 存货周转天数
    dio = inventory / daily_cogs if daily_cogs > 0 else 0

    # DPO - 应付周转天数
    dpo = accounts_payable / daily_cogs if daily_cogs > 0 else 0

    # CCC - 现金转换周期
    ccc = dso + dio - dpo

    # 周转率
    ar_turnover = revenue / accounts_receivable if accounts_receivable > 0 else 0
    inventory_turnover = cogs / inventory if inventory > 0 else 0
    ap_turnover = cogs / accounts_payable if accounts_payable > 0 else 0

    # 营运资金需求（简化计算）
    working_capital = accounts_receivable + inventory - accounts_payable

    # 营运资金占收入比
    wc_revenue_ratio = working_capital / revenue if revenue > 0 else 0

    # 解读
    if ccc < 0:
        interpretation = "负现金周期：公司在付款给供应商之前就收到了客户付款，现金流状况良好（如预收款模式）"
    elif ccc < 30:
        interpretation = "现金周期较短：营运资金管理效率高"
    elif ccc < 60:
        interpretation = "现金周期适中：营运资金管理正常"
    elif ccc < 90:
        interpretation = "现金周期较长：可能需要优化收款或存货管理"
    else:
        interpretation = "现金周期过长：营运资金占用大，需要关注现金流压力"

    return {
        "dso": round(dso, 1),
        "dio": round(dio, 1),
        "dpo": round(dpo, 1),
        "ccc": round(ccc, 1),
        "working_capital": working_capital,
        "wc_revenue_ratio": wc_revenue_ratio,
        "analysis": {
            "ar_turnover": round(ar_turnover, 2),
            "inventory_turnover": round(inventory_turnover, 2),
            "ap_turnover": round(ap_turnover, 2)
        },
        "interpretation": interpretation,
        "inputs": {
            "accounts_receivable": accounts_receivable,
            "inventory": inventory,
            "accounts_payable": accounts_payable,
            "revenue": revenue,
            "cogs": cogs,
            "period_days": period_days
        }
    }


# ============================================================
# 现金流驱动因素分解
# ============================================================

def cash_drivers(
    period1: Dict[str, Any],
    period2: Dict[str, Any]
) -> Dict[str, Any]:
    """
    现金流驱动因素分解

    分解两期之间现金流变动的主要驱动因素。

    Args:
        period1: 期初数据
            {
                "cash_flow_operating": 经营活动现金流,
                "cash_flow_investing": 投资活动现金流,
                "cash_flow_financing": 筹资活动现金流,
                "net_income": 净利润（可选）,
                "depreciation": 折旧（可选）,
                "ar_change": 应收变动（可选）,
                "inventory_change": 存货变动（可选）,
                "ap_change": 应付变动（可选）,
                "capex": 资本支出（可选）,
                "debt_change": 债务变动（可选）
            }
        period2: 期末数据（格式同上）

    Returns:
        {
            "changes": {
                "operating": 经营活动变动,
                "investing": 投资活动变动,
                "financing": 筹资活动变动,
                "total": 总变动
            },
            "drivers": [...],             # 驱动因素排名
            "operating_bridge": {...},    # 经营活动分解
            "analysis": 分析结论
        }

    Example:
        >>> cash_drivers(
        ...     period1={"cash_flow_operating": 1000, "cash_flow_investing": -500, "cash_flow_financing": -200},
        ...     period2={"cash_flow_operating": 1200, "cash_flow_investing": -800, "cash_flow_financing": -100}
        ... )
    """
    # 三大活动变动
    operating_change = period2.get("cash_flow_operating", 0) - period1.get("cash_flow_operating", 0)
    investing_change = period2.get("cash_flow_investing", 0) - period1.get("cash_flow_investing", 0)
    financing_change = period2.get("cash_flow_financing", 0) - period1.get("cash_flow_financing", 0)
    total_change = operating_change + investing_change + financing_change

    # 驱动因素详细分解
    drivers = []

    # 经营活动分解
    operating_drivers = []

    if "net_income" in period1 and "net_income" in period2:
        ni_change = period2["net_income"] - period1["net_income"]
        operating_drivers.append({"factor": "净利润变动", "amount": ni_change})

    if "depreciation" in period1 and "depreciation" in period2:
        dep_change = period2["depreciation"] - period1["depreciation"]
        operating_drivers.append({"factor": "折旧变动", "amount": dep_change})

    if "ar_change" in period1 and "ar_change" in period2:
        # 应收增加是现金流出，所以取负
        ar_impact = -(period2["ar_change"] - period1["ar_change"])
        operating_drivers.append({"factor": "应收账款影响", "amount": ar_impact})

    if "inventory_change" in period1 and "inventory_change" in period2:
        inv_impact = -(period2["inventory_change"] - period1["inventory_change"])
        operating_drivers.append({"factor": "存货影响", "amount": inv_impact})

    if "ap_change" in period1 and "ap_change" in period2:
        ap_impact = period2["ap_change"] - period1["ap_change"]
        operating_drivers.append({"factor": "应付账款影响", "amount": ap_impact})

    # 投资活动分解
    investing_drivers = []

    if "capex" in period1 and "capex" in period2:
        capex_change = period2["capex"] - period1["capex"]
        investing_drivers.append({"factor": "资本支出变动", "amount": -capex_change})

    # 筹资活动分解
    financing_drivers = []

    if "debt_change" in period1 and "debt_change" in period2:
        debt_impact = period2["debt_change"] - period1["debt_change"]
        financing_drivers.append({"factor": "债务变动", "amount": debt_impact})

    if "dividend" in period1 and "dividend" in period2:
        div_change = period2["dividend"] - period1["dividend"]
        financing_drivers.append({"factor": "股利支付变动", "amount": -div_change})

    # 汇总所有驱动因素
    all_drivers = [
        {"category": "经营活动", "change": operating_change, "drivers": operating_drivers},
        {"category": "投资活动", "change": investing_change, "drivers": investing_drivers},
        {"category": "筹资活动", "change": financing_change, "drivers": financing_drivers}
    ]

    # 按影响大小排序
    impact_ranking = sorted([
        {"factor": "经营活动", "amount": operating_change},
        {"factor": "投资活动", "amount": investing_change},
        {"factor": "筹资活动", "amount": financing_change}
    ], key=lambda x: abs(x["amount"]), reverse=True)

    # 分析结论
    if total_change > 0:
        main_driver = impact_ranking[0]
        if main_driver["amount"] > 0:
            analysis = f"现金流改善 {total_change:,.0f}，主要由{main_driver['factor']}贡献 {main_driver['amount']:,.0f}"
        else:
            analysis = f"现金流改善 {total_change:,.0f}，但{main_driver['factor']}下降 {main_driver['amount']:,.0f}"
    elif total_change < 0:
        main_driver = impact_ranking[0]
        if main_driver["amount"] < 0:
            analysis = f"现金流恶化 {total_change:,.0f}，主要由{main_driver['factor']}导致 {main_driver['amount']:,.0f}"
        else:
            analysis = f"现金流恶化 {total_change:,.0f}，尽管{main_driver['factor']}贡献 {main_driver['amount']:,.0f}"
    else:
        analysis = "现金流保持稳定"

    return {
        "changes": {
            "operating": operating_change,
            "investing": investing_change,
            "financing": financing_change,
            "total": total_change
        },
        "period1_totals": {
            "operating": period1.get("cash_flow_operating", 0),
            "investing": period1.get("cash_flow_investing", 0),
            "financing": period1.get("cash_flow_financing", 0),
            "total": period1.get("cash_flow_operating", 0) + period1.get("cash_flow_investing", 0) + period1.get("cash_flow_financing", 0)
        },
        "period2_totals": {
            "operating": period2.get("cash_flow_operating", 0),
            "investing": period2.get("cash_flow_investing", 0),
            "financing": period2.get("cash_flow_financing", 0),
            "total": period2.get("cash_flow_operating", 0) + period2.get("cash_flow_investing", 0) + period2.get("cash_flow_financing", 0)
        },
        "impact_ranking": impact_ranking,
        "detailed_drivers": all_drivers,
        "analysis": analysis
    }


# ============================================================
# 工具注册（供 LLM 发现）
# ============================================================

CASH_TOOLS = {
    "cash_forecast_13w": {
        "function": cash_forecast_13w,
        "description": "13周现金流预测，识别资金缺口",
        "parameters": ["opening_cash", "receivables_schedule", "payables_schedule", "recurring_inflows", "recurring_outflows", "weeks"]
    },
    "working_capital_cycle": {
        "function": working_capital_cycle,
        "description": "营运资金周期分析，计算DSO/DIO/DPO/CCC",
        "parameters": ["accounts_receivable", "inventory", "accounts_payable", "revenue", "cogs", "period_days"]
    },
    "cash_drivers": {
        "function": cash_drivers,
        "description": "现金流驱动因素分解，分析变动原因",
        "parameters": ["period1", "period2"]
    }
}
