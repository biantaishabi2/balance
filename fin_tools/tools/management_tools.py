# -*- coding: utf-8 -*-
"""
management_tools.py - 管理会计原子工具

提供部门损益表、产品盈利分析、成本分摊、本量利分析、盈亏平衡点等功能。
设计为无状态的原子函数，供 LLM 灵活调用组合。
"""

from typing import Dict, List, Any, Optional, Literal
from dataclasses import dataclass


# ============================================================
# 部门损益表
# ============================================================

def dept_pnl(
    revenues: List[Dict[str, Any]],
    direct_costs: List[Dict[str, Any]],
    allocated_costs: Optional[List[Dict[str, Any]]] = None,
    departments: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    部门损益表

    按部门生成损益表，区分直接成本和分摊成本，计算各部门贡献利润。

    Args:
        revenues: 收入明细
            [{"dept": "销售部", "amount": 1000000, "category": "产品销售"}, ...]
        direct_costs: 直接成本明细
            [{"dept": "销售部", "amount": 300000, "category": "销售提成"}, ...]
        allocated_costs: 分摊成本明细（可选）
            [{"dept": "销售部", "amount": 100000, "category": "管理费分摊"}, ...]
        departments: 指定部门列表（可选，默认自动从数据中提取）

    Returns:
        {
            "by_department": {
                "销售部": {
                    "revenue": 收入,
                    "direct_costs": 直接成本,
                    "contribution_margin": 贡献毛利,
                    "allocated_costs": 分摊成本,
                    "operating_profit": 营业利润,
                    "margin_rate": 利润率
                }, ...
            },
            "summary": {
                "total_revenue": 总收入,
                "total_direct_costs": 总直接成本,
                "total_contribution": 总贡献毛利,
                "total_allocated_costs": 总分摊成本,
                "total_operating_profit": 总营业利润
            },
            "ranking": [按贡献毛利排序的部门列表]
        }

    Example:
        >>> dept_pnl(
        ...     revenues=[
        ...         {"dept": "销售部", "amount": 1000000},
        ...         {"dept": "技术部", "amount": 500000}
        ...     ],
        ...     direct_costs=[
        ...         {"dept": "销售部", "amount": 300000},
        ...         {"dept": "技术部", "amount": 200000}
        ...     ]
        ... )
    """
    allocated_costs = allocated_costs or []

    # 自动提取部门列表
    if departments is None:
        dept_set = set()
        for item in revenues:
            dept_set.add(item.get("dept", "未分类"))
        for item in direct_costs:
            dept_set.add(item.get("dept", "未分类"))
        for item in allocated_costs:
            dept_set.add(item.get("dept", "未分类"))
        departments = sorted(list(dept_set))

    # 初始化部门数据
    dept_data = {}
    for dept in departments:
        dept_data[dept] = {
            "revenue": 0,
            "revenue_detail": [],
            "direct_costs": 0,
            "direct_costs_detail": [],
            "allocated_costs": 0,
            "allocated_costs_detail": []
        }

    # 汇总收入
    for item in revenues:
        dept = item.get("dept", "未分类")
        if dept not in dept_data:
            dept_data[dept] = {
                "revenue": 0, "revenue_detail": [],
                "direct_costs": 0, "direct_costs_detail": [],
                "allocated_costs": 0, "allocated_costs_detail": []
            }
        dept_data[dept]["revenue"] += item.get("amount", 0)
        dept_data[dept]["revenue_detail"].append({
            "category": item.get("category", "其他"),
            "amount": item.get("amount", 0)
        })

    # 汇总直接成本
    for item in direct_costs:
        dept = item.get("dept", "未分类")
        if dept not in dept_data:
            dept_data[dept] = {
                "revenue": 0, "revenue_detail": [],
                "direct_costs": 0, "direct_costs_detail": [],
                "allocated_costs": 0, "allocated_costs_detail": []
            }
        dept_data[dept]["direct_costs"] += item.get("amount", 0)
        dept_data[dept]["direct_costs_detail"].append({
            "category": item.get("category", "其他"),
            "amount": item.get("amount", 0)
        })

    # 汇总分摊成本
    for item in allocated_costs:
        dept = item.get("dept", "未分类")
        if dept not in dept_data:
            continue
        dept_data[dept]["allocated_costs"] += item.get("amount", 0)
        dept_data[dept]["allocated_costs_detail"].append({
            "category": item.get("category", "其他"),
            "amount": item.get("amount", 0)
        })

    # 计算各部门利润指标
    by_department = {}
    for dept, data in dept_data.items():
        contribution_margin = data["revenue"] - data["direct_costs"]
        operating_profit = contribution_margin - data["allocated_costs"]
        margin_rate = operating_profit / data["revenue"] if data["revenue"] > 0 else 0

        by_department[dept] = {
            "revenue": data["revenue"],
            "revenue_detail": data["revenue_detail"],
            "direct_costs": data["direct_costs"],
            "direct_costs_detail": data["direct_costs_detail"],
            "contribution_margin": contribution_margin,
            "contribution_margin_rate": contribution_margin / data["revenue"] if data["revenue"] > 0 else 0,
            "allocated_costs": data["allocated_costs"],
            "allocated_costs_detail": data["allocated_costs_detail"],
            "operating_profit": operating_profit,
            "margin_rate": margin_rate
        }

    # 汇总
    total_revenue = sum(d["revenue"] for d in by_department.values())
    total_direct_costs = sum(d["direct_costs"] for d in by_department.values())
    total_contribution = sum(d["contribution_margin"] for d in by_department.values())
    total_allocated_costs = sum(d["allocated_costs"] for d in by_department.values())
    total_operating_profit = sum(d["operating_profit"] for d in by_department.values())

    # 按贡献毛利排序
    ranking = sorted(
        by_department.keys(),
        key=lambda d: by_department[d]["contribution_margin"],
        reverse=True
    )

    return {
        "by_department": by_department,
        "summary": {
            "total_revenue": total_revenue,
            "total_direct_costs": total_direct_costs,
            "total_contribution": total_contribution,
            "total_allocated_costs": total_allocated_costs,
            "total_operating_profit": total_operating_profit,
            "overall_margin_rate": total_operating_profit / total_revenue if total_revenue > 0 else 0
        },
        "ranking": ranking
    }


# ============================================================
# 产品盈利分析
# ============================================================

def product_profitability(
    products: List[Dict[str, Any]],
    include_abc: bool = True
) -> Dict[str, Any]:
    """
    产品盈利分析

    分析各产品的盈利能力，按毛利率排序，可选ABC分类。

    Args:
        products: 产品数据列表
            [{
                "name": "产品A",
                "revenue": 1000000,
                "variable_costs": 400000,
                "fixed_costs": 200000,  # 可选，分摊的固定成本
                "units_sold": 10000     # 可选，销量
            }, ...]
        include_abc: 是否进行ABC分类（按贡献毛利）

    Returns:
        {
            "products": [
                {
                    "name": 产品名,
                    "revenue": 收入,
                    "variable_costs": 变动成本,
                    "contribution_margin": 贡献毛利,
                    "cm_ratio": 贡献毛利率,
                    "fixed_costs": 固定成本,
                    "net_profit": 净利润,
                    "profit_margin": 净利润率,
                    "unit_cm": 单位贡献毛利（如有销量）,
                    "abc_class": ABC分类
                }, ...
            ],
            "summary": {
                "total_revenue": 总收入,
                "total_cm": 总贡献毛利,
                "avg_cm_ratio": 平均贡献毛利率,
                "profitable_count": 盈利产品数,
                "loss_count": 亏损产品数
            },
            "abc_analysis": {
                "A": [A类产品列表],
                "B": [B类产品列表],
                "C": [C类产品列表]
            }
        }

    Example:
        >>> product_profitability([
        ...     {"name": "产品A", "revenue": 1000000, "variable_costs": 400000},
        ...     {"name": "产品B", "revenue": 500000, "variable_costs": 300000}
        ... ])
    """
    analyzed_products = []

    for p in products:
        revenue = p.get("revenue", 0)
        variable_costs = p.get("variable_costs", 0)
        fixed_costs = p.get("fixed_costs", 0)
        units_sold = p.get("units_sold")

        contribution_margin = revenue - variable_costs
        cm_ratio = contribution_margin / revenue if revenue > 0 else 0
        net_profit = contribution_margin - fixed_costs
        profit_margin = net_profit / revenue if revenue > 0 else 0

        product_result = {
            "name": p.get("name", "未命名"),
            "revenue": revenue,
            "variable_costs": variable_costs,
            "contribution_margin": contribution_margin,
            "cm_ratio": cm_ratio,
            "fixed_costs": fixed_costs,
            "net_profit": net_profit,
            "profit_margin": profit_margin
        }

        if units_sold is not None and units_sold > 0:
            product_result["units_sold"] = units_sold
            product_result["unit_price"] = revenue / units_sold
            product_result["unit_variable_cost"] = variable_costs / units_sold
            product_result["unit_cm"] = contribution_margin / units_sold

        analyzed_products.append(product_result)

    # 按贡献毛利排序
    analyzed_products.sort(key=lambda x: x["contribution_margin"], reverse=True)

    # ABC分类（按贡献毛利累计占比）
    abc_analysis = {"A": [], "B": [], "C": []}
    if include_abc and analyzed_products:
        total_cm = sum(p["contribution_margin"] for p in analyzed_products if p["contribution_margin"] > 0)
        if total_cm > 0:
            cumulative = 0
            for p in analyzed_products:
                if p["contribution_margin"] <= 0:
                    p["abc_class"] = "C"
                    abc_analysis["C"].append(p["name"])
                else:
                    cumulative += p["contribution_margin"]
                    pct = cumulative / total_cm
                    if pct <= 0.7:
                        p["abc_class"] = "A"
                        abc_analysis["A"].append(p["name"])
                    elif pct <= 0.9:
                        p["abc_class"] = "B"
                        abc_analysis["B"].append(p["name"])
                    else:
                        p["abc_class"] = "C"
                        abc_analysis["C"].append(p["name"])

    # 汇总统计
    total_revenue = sum(p["revenue"] for p in analyzed_products)
    total_cm = sum(p["contribution_margin"] for p in analyzed_products)
    avg_cm_ratio = total_cm / total_revenue if total_revenue > 0 else 0
    profitable_count = sum(1 for p in analyzed_products if p["net_profit"] > 0)
    loss_count = sum(1 for p in analyzed_products if p["net_profit"] < 0)

    result = {
        "products": analyzed_products,
        "summary": {
            "total_revenue": total_revenue,
            "total_cm": total_cm,
            "avg_cm_ratio": avg_cm_ratio,
            "profitable_count": profitable_count,
            "loss_count": loss_count,
            "breakeven_count": len(analyzed_products) - profitable_count - loss_count
        }
    }

    if include_abc:
        result["abc_analysis"] = abc_analysis

    return result


# ============================================================
# 成本分摊
# ============================================================

def cost_allocation(
    total_cost: float,
    cost_objects: List[Dict[str, Any]],
    method: Literal["direct", "step", "abc"] = "direct",
    drivers: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    成本分摊

    支持直接分摊、阶梯分摊、ABC作业成本法三种方法。

    Args:
        total_cost: 待分摊的总成本
        cost_objects: 成本对象列表
            直接分摊: [{"name": "部门A", "base": 100}, ...]  # base为分摊基础
            阶梯分摊: [{"name": "服务部", "base": 50, "provides_to": ["生产部", "销售部"]}, ...]
            ABC分摊: [{"name": "产品A", "activities": {"机器小时": 100, "订单数": 5}}, ...]
        method: 分摊方法
            - "direct": 直接分摊（按分摊基础比例）
            - "step": 阶梯分摊（服务部门依次分摊）
            - "abc": 作业成本法（按成本动因分摊）
        drivers: ABC方法的成本动因费率（仅abc方法需要）
            {"机器小时": 10, "订单数": 50, ...}

    Returns:
        {
            "method": 使用的方法,
            "allocations": [
                {"name": 对象名, "allocated_cost": 分摊金额, "percentage": 占比}, ...
            ],
            "total_allocated": 已分摊总额,
            "details": 详细计算过程
        }

    Example:
        >>> cost_allocation(
        ...     total_cost=100000,
        ...     cost_objects=[
        ...         {"name": "产品A", "base": 60},
        ...         {"name": "产品B", "base": 40}
        ...     ],
        ...     method="direct"
        ... )
    """
    if method == "direct":
        return _direct_allocation(total_cost, cost_objects)
    elif method == "step":
        return _step_allocation(total_cost, cost_objects)
    elif method == "abc":
        return _abc_allocation(total_cost, cost_objects, drivers or {})
    else:
        raise ValueError(f"不支持的分摊方法: {method}")


def _direct_allocation(total_cost: float, cost_objects: List[Dict[str, Any]]) -> Dict[str, Any]:
    """直接分摊法"""
    total_base = sum(obj.get("base", 0) for obj in cost_objects)

    if total_base == 0:
        # 平均分摊
        avg_cost = total_cost / len(cost_objects) if cost_objects else 0
        allocations = [
            {
                "name": obj.get("name", f"对象{i+1}"),
                "allocated_cost": avg_cost,
                "percentage": 1 / len(cost_objects) if cost_objects else 0,
                "base": obj.get("base", 0)
            }
            for i, obj in enumerate(cost_objects)
        ]
    else:
        allocations = []
        for obj in cost_objects:
            base = obj.get("base", 0)
            pct = base / total_base
            allocated = total_cost * pct
            allocations.append({
                "name": obj.get("name", "未命名"),
                "allocated_cost": allocated,
                "percentage": pct,
                "base": base
            })

    return {
        "method": "direct",
        "method_name": "直接分摊法",
        "allocations": allocations,
        "total_allocated": sum(a["allocated_cost"] for a in allocations),
        "details": {
            "total_cost": total_cost,
            "total_base": total_base,
            "formula": "分摊成本 = 总成本 × (对象分摊基础 / 总分摊基础)"
        }
    }


def _step_allocation(total_cost: float, cost_objects: List[Dict[str, Any]]) -> Dict[str, Any]:
    """阶梯分摊法"""
    # 区分服务部门和生产部门
    service_depts = [obj for obj in cost_objects if obj.get("provides_to")]
    production_depts = [obj for obj in cost_objects if not obj.get("provides_to")]

    # 初始化各部门成本
    dept_costs = {obj["name"]: obj.get("initial_cost", 0) for obj in cost_objects}
    # 将总成本分配给服务部门
    if service_depts:
        per_service = total_cost / len(service_depts)
        for dept in service_depts:
            dept_costs[dept["name"]] += per_service

    allocation_steps = []

    # 按阶梯顺序分摊（服务部门按顺序分摊给后续部门）
    for i, service_dept in enumerate(service_depts):
        dept_name = service_dept["name"]
        provides_to = service_dept.get("provides_to", [])
        dept_cost = dept_costs[dept_name]

        if not provides_to or dept_cost == 0:
            continue

        # 计算接收部门的分摊基础
        receivers = []
        for obj in cost_objects:
            if obj["name"] in provides_to:
                receivers.append(obj)

        total_receiver_base = sum(r.get("base", 0) for r in receivers)

        step_allocations = []
        for receiver in receivers:
            base = receiver.get("base", 0)
            if total_receiver_base > 0:
                pct = base / total_receiver_base
            else:
                pct = 1 / len(receivers)
            allocated = dept_cost * pct
            dept_costs[receiver["name"]] = dept_costs.get(receiver["name"], 0) + allocated
            step_allocations.append({
                "to": receiver["name"],
                "amount": allocated,
                "percentage": pct
            })

        allocation_steps.append({
            "step": i + 1,
            "from": dept_name,
            "cost_to_allocate": dept_cost,
            "allocations": step_allocations
        })

        dept_costs[dept_name] = 0  # 服务部门成本清零

    # 最终结果：只显示生产部门的分摊结果
    final_allocations = []
    total_allocated = 0
    for dept in production_depts:
        cost = dept_costs.get(dept["name"], 0)
        total_allocated += cost
        final_allocations.append({
            "name": dept["name"],
            "allocated_cost": cost,
            "percentage": cost / total_cost if total_cost > 0 else 0
        })

    return {
        "method": "step",
        "method_name": "阶梯分摊法",
        "allocations": final_allocations,
        "total_allocated": total_allocated,
        "details": {
            "total_cost": total_cost,
            "allocation_steps": allocation_steps,
            "formula": "服务部门按顺序将成本分摊给下游部门，已分摊的部门不再接收分摊"
        }
    }


def _abc_allocation(
    total_cost: float,
    cost_objects: List[Dict[str, Any]],
    drivers: Dict[str, float]
) -> Dict[str, Any]:
    """作业成本法"""
    allocations = []
    driver_details = []

    for obj in cost_objects:
        activities = obj.get("activities", {})
        obj_cost = 0
        obj_driver_details = []

        for driver_name, quantity in activities.items():
            rate = drivers.get(driver_name, 0)
            cost = quantity * rate
            obj_cost += cost
            obj_driver_details.append({
                "driver": driver_name,
                "quantity": quantity,
                "rate": rate,
                "cost": cost
            })

        allocations.append({
            "name": obj.get("name", "未命名"),
            "allocated_cost": obj_cost,
            "driver_breakdown": obj_driver_details
        })
        driver_details.append({
            "object": obj.get("name", "未命名"),
            "activities": obj_driver_details
        })

    total_allocated = sum(a["allocated_cost"] for a in allocations)

    # 计算占比
    for alloc in allocations:
        alloc["percentage"] = alloc["allocated_cost"] / total_allocated if total_allocated > 0 else 0

    return {
        "method": "abc",
        "method_name": "作业成本法 (ABC)",
        "allocations": allocations,
        "total_allocated": total_allocated,
        "details": {
            "total_cost": total_cost,
            "cost_drivers": drivers,
            "driver_details": driver_details,
            "formula": "产品成本 = Σ(作业量 × 作业成本率)",
            "variance": total_cost - total_allocated  # 与总成本的差异
        }
    }


# ============================================================
# 本量利分析 (CVP Analysis)
# ============================================================

def cvp_analysis(
    selling_price: float,
    variable_cost: float,
    fixed_costs: float,
    current_volume: Optional[int] = None,
    target_profit: Optional[float] = None,
    tax_rate: float = 0
) -> Dict[str, Any]:
    """
    本量利分析 (Cost-Volume-Profit Analysis)

    分析成本、销量与利润之间的关系，计算盈亏平衡点和目标利润销量。

    Args:
        selling_price: 单位售价
        variable_cost: 单位变动成本
        fixed_costs: 固定成本总额
        current_volume: 当前销量（可选，用于计算当前利润）
        target_profit: 目标利润（可选，用于计算目标销量）
        tax_rate: 所得税税率（可选，默认0）

    Returns:
        {
            "unit_contribution_margin": 单位贡献毛利,
            "cm_ratio": 贡献毛利率,
            "breakeven_units": 盈亏平衡销量,
            "breakeven_sales": 盈亏平衡销售额,
            "current_analysis": {  # 如果提供了current_volume
                "volume": 当前销量,
                "revenue": 收入,
                "total_variable_costs": 变动成本总额,
                "contribution_margin": 贡献毛利,
                "operating_profit": 营业利润,
                "net_profit": 净利润（扣税后）,
                "margin_of_safety": 安全边际,
                "margin_of_safety_rate": 安全边际率,
                "operating_leverage": 经营杠杆系数
            },
            "target_analysis": {  # 如果提供了target_profit
                "target_profit": 目标利润,
                "required_volume": 所需销量,
                "required_sales": 所需销售额,
                "additional_volume": 需增加的销量
            },
            "sensitivity": {
                "price_increase_1pct": 售价提高1%的利润变化,
                "volume_increase_1pct": 销量提高1%的利润变化,
                "variable_cost_decrease_1pct": 变动成本降低1%的利润变化
            }
        }

    Example:
        >>> cvp_analysis(
        ...     selling_price=100,
        ...     variable_cost=60,
        ...     fixed_costs=200000,
        ...     current_volume=10000
        ... )
    """
    # 基本指标
    unit_cm = selling_price - variable_cost
    cm_ratio = unit_cm / selling_price if selling_price > 0 else 0

    # 盈亏平衡点
    if unit_cm > 0:
        breakeven_units = fixed_costs / unit_cm
        breakeven_sales = fixed_costs / cm_ratio
    else:
        breakeven_units = float('inf')
        breakeven_sales = float('inf')

    result = {
        "unit_contribution_margin": unit_cm,
        "cm_ratio": cm_ratio,
        "breakeven_units": breakeven_units,
        "breakeven_sales": breakeven_sales,
        "variable_cost_ratio": variable_cost / selling_price if selling_price > 0 else 0
    }

    # 当前销量分析
    if current_volume is not None:
        revenue = selling_price * current_volume
        total_vc = variable_cost * current_volume
        contribution = unit_cm * current_volume
        operating_profit = contribution - fixed_costs
        net_profit = operating_profit * (1 - tax_rate) if operating_profit > 0 else operating_profit

        # 安全边际
        if breakeven_units != float('inf'):
            margin_of_safety = current_volume - breakeven_units
            margin_of_safety_rate = margin_of_safety / current_volume if current_volume > 0 else 0
        else:
            margin_of_safety = -current_volume
            margin_of_safety_rate = -1

        # 经营杠杆系数
        operating_leverage = contribution / operating_profit if operating_profit != 0 else float('inf')

        result["current_analysis"] = {
            "volume": current_volume,
            "revenue": revenue,
            "total_variable_costs": total_vc,
            "contribution_margin": contribution,
            "fixed_costs": fixed_costs,
            "operating_profit": operating_profit,
            "net_profit": net_profit,
            "margin_of_safety": margin_of_safety,
            "margin_of_safety_rate": margin_of_safety_rate,
            "operating_leverage": operating_leverage
        }

        # 敏感性分析
        if operating_profit != 0:
            # 售价提高1%
            new_price = selling_price * 1.01
            new_profit_price = (new_price - variable_cost) * current_volume - fixed_costs
            price_sensitivity = (new_profit_price - operating_profit) / abs(operating_profit)

            # 销量提高1%
            new_volume = current_volume * 1.01
            new_profit_volume = unit_cm * new_volume - fixed_costs
            volume_sensitivity = (new_profit_volume - operating_profit) / abs(operating_profit)

            # 变动成本降低1%
            new_vc = variable_cost * 0.99
            new_profit_vc = (selling_price - new_vc) * current_volume - fixed_costs
            vc_sensitivity = (new_profit_vc - operating_profit) / abs(operating_profit)

            result["sensitivity"] = {
                "price_increase_1pct": price_sensitivity,
                "volume_increase_1pct": volume_sensitivity,
                "variable_cost_decrease_1pct": vc_sensitivity,
                "interpretation": {
                    "price": f"售价提高1%，利润变化{price_sensitivity*100:.2f}%",
                    "volume": f"销量提高1%，利润变化{volume_sensitivity*100:.2f}%",
                    "variable_cost": f"变动成本降低1%，利润变化{vc_sensitivity*100:.2f}%"
                }
            }

    # 目标利润分析
    if target_profit is not None:
        if unit_cm > 0:
            # 考虑税率
            if tax_rate > 0:
                pre_tax_target = target_profit / (1 - tax_rate)
            else:
                pre_tax_target = target_profit

            required_volume = (fixed_costs + pre_tax_target) / unit_cm
            required_sales = required_volume * selling_price
            additional_volume = required_volume - (current_volume or 0)

            result["target_analysis"] = {
                "target_profit": target_profit,
                "pre_tax_profit_needed": pre_tax_target,
                "required_volume": required_volume,
                "required_sales": required_sales,
                "additional_volume": additional_volume if current_volume else None
            }
        else:
            result["target_analysis"] = {
                "target_profit": target_profit,
                "error": "单位贡献毛利为负，无法实现目标利润"
            }

    return result


# ============================================================
# 盈亏平衡点计算
# ============================================================

def breakeven(
    products: List[Dict[str, Any]],
    fixed_costs: float,
    method: Literal["weighted_avg", "sequential"] = "weighted_avg"
) -> Dict[str, Any]:
    """
    盈亏平衡点计算（多产品）

    计算多产品情况下的综合盈亏平衡点。

    Args:
        products: 产品列表
            [{
                "name": "产品A",
                "selling_price": 100,
                "variable_cost": 60,
                "sales_mix": 0.6  # 销售组合比例（可选，默认平均）
            }, ...]
        fixed_costs: 固定成本总额
        method: 计算方法
            - "weighted_avg": 加权平均法（按销售组合计算综合贡献毛利率）
            - "sequential": 顺序法（按产品优先级依次计算）

    Returns:
        {
            "method": 使用的方法,
            "breakeven_sales": 盈亏平衡销售额,
            "by_product": [
                {
                    "name": 产品名,
                    "breakeven_units": 盈亏平衡销量,
                    "breakeven_sales": 盈亏平衡销售额,
                    "unit_cm": 单位贡献毛利,
                    "cm_ratio": 贡献毛利率
                }, ...
            ],
            "weighted_avg_cm_ratio": 加权平均贡献毛利率,
            "analysis": 分析说明
        }

    Example:
        >>> breakeven(
        ...     products=[
        ...         {"name": "A", "selling_price": 100, "variable_cost": 60, "sales_mix": 0.6},
        ...         {"name": "B", "selling_price": 80, "variable_cost": 40, "sales_mix": 0.4}
        ...     ],
        ...     fixed_costs=200000
        ... )
    """
    # 计算各产品的贡献毛利率
    product_data = []
    for p in products:
        price = p.get("selling_price", 0)
        vc = p.get("variable_cost", 0)
        unit_cm = price - vc
        cm_ratio = unit_cm / price if price > 0 else 0

        product_data.append({
            "name": p.get("name", "未命名"),
            "selling_price": price,
            "variable_cost": vc,
            "unit_cm": unit_cm,
            "cm_ratio": cm_ratio,
            "sales_mix": p.get("sales_mix")
        })

    # 确定销售组合
    has_mix = all(p["sales_mix"] is not None for p in product_data)
    if not has_mix:
        # 默认平均分配
        avg_mix = 1 / len(product_data) if product_data else 0
        for p in product_data:
            p["sales_mix"] = avg_mix

    # 标准化销售组合（确保和为1）
    total_mix = sum(p["sales_mix"] for p in product_data)
    if total_mix > 0:
        for p in product_data:
            p["sales_mix"] = p["sales_mix"] / total_mix

    if method == "weighted_avg":
        return _breakeven_weighted_avg(product_data, fixed_costs)
    else:
        return _breakeven_sequential(product_data, fixed_costs)


def _breakeven_weighted_avg(
    product_data: List[Dict[str, Any]],
    fixed_costs: float
) -> Dict[str, Any]:
    """加权平均法计算盈亏平衡点"""
    # 加权平均贡献毛利率
    weighted_cm_ratio = sum(
        p["cm_ratio"] * p["sales_mix"]
        for p in product_data
    )

    # 综合盈亏平衡销售额
    if weighted_cm_ratio > 0:
        breakeven_sales = fixed_costs / weighted_cm_ratio
    else:
        breakeven_sales = float('inf')

    # 各产品的盈亏平衡销售额和销量
    by_product = []
    for p in product_data:
        product_be_sales = breakeven_sales * p["sales_mix"]
        product_be_units = product_be_sales / p["selling_price"] if p["selling_price"] > 0 else 0

        by_product.append({
            "name": p["name"],
            "sales_mix": p["sales_mix"],
            "unit_cm": p["unit_cm"],
            "cm_ratio": p["cm_ratio"],
            "breakeven_sales": product_be_sales,
            "breakeven_units": product_be_units
        })

    return {
        "method": "weighted_avg",
        "method_name": "加权平均法",
        "breakeven_sales": breakeven_sales,
        "weighted_avg_cm_ratio": weighted_cm_ratio,
        "by_product": by_product,
        "fixed_costs": fixed_costs,
        "analysis": f"在当前销售组合下，需达到 {breakeven_sales:,.0f} 元销售额才能实现盈亏平衡"
    }


def _breakeven_sequential(
    product_data: List[Dict[str, Any]],
    fixed_costs: float
) -> Dict[str, Any]:
    """顺序法计算盈亏平衡点（按贡献毛利率排序，优先销售高毛利产品）"""
    # 按贡献毛利率降序排列
    sorted_products = sorted(product_data, key=lambda x: x["cm_ratio"], reverse=True)

    remaining_fixed = fixed_costs
    by_product = []
    total_be_sales = 0

    for p in sorted_products:
        if remaining_fixed <= 0:
            # 已达到盈亏平衡
            by_product.append({
                "name": p["name"],
                "unit_cm": p["unit_cm"],
                "cm_ratio": p["cm_ratio"],
                "breakeven_sales": 0,
                "breakeven_units": 0,
                "covers_fixed_cost": 0
            })
        else:
            # 计算该产品需要贡献多少
            if p["cm_ratio"] > 0:
                required_sales = remaining_fixed / p["cm_ratio"]
                be_units = required_sales / p["selling_price"] if p["selling_price"] > 0 else 0
                covers = remaining_fixed
                remaining_fixed = 0
            else:
                required_sales = 0
                be_units = 0
                covers = 0

            by_product.append({
                "name": p["name"],
                "unit_cm": p["unit_cm"],
                "cm_ratio": p["cm_ratio"],
                "breakeven_sales": required_sales,
                "breakeven_units": be_units,
                "covers_fixed_cost": covers
            })
            total_be_sales += required_sales

    return {
        "method": "sequential",
        "method_name": "顺序法",
        "breakeven_sales": total_be_sales,
        "by_product": by_product,
        "fixed_costs": fixed_costs,
        "analysis": f"按贡献毛利率优先顺序，需 {total_be_sales:,.0f} 元销售额达到盈亏平衡",
        "priority_order": [p["name"] for p in sorted_products]
    }
