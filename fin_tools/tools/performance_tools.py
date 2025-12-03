# -*- coding: utf-8 -*-
"""
performance_tools.py - 绩效考核原子工具

提供KPI仪表盘、EVA计算、平衡计分卡、OKR进度追踪等功能。
设计为无状态的原子函数，供 LLM 灵活调用组合。
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


# ============================================================
# KPI 仪表盘
# ============================================================

class KPIStatus(Enum):
    """KPI状态"""
    EXCEEDED = "exceeded"      # 超额完成
    ON_TARGET = "on_target"    # 达标
    AT_RISK = "at_risk"        # 风险
    BEHIND = "behind"          # 落后


def kpi_dashboard(
    kpis: List[Dict[str, Any]],
    period: str = "current"
) -> Dict[str, Any]:
    """
    KPI 仪表盘数据

    汇总多个KPI指标的完成情况。

    Args:
        kpis: KPI列表
            [
                {
                    "name": "收入",
                    "target": 1000000,
                    "actual": 950000,
                    "unit": "元",
                    "direction": "higher_better",  # higher_better / lower_better
                    "weight": 0.3,  # 权重（可选）
                    "category": "财务"  # 类别（可选）
                },
                ...
            ]
        period: 考核期间描述

    Returns:
        {
            "period": 考核期间,
            "summary": {
                "total_kpis": KPI总数,
                "exceeded": 超额完成数,
                "on_target": 达标数,
                "at_risk": 风险数,
                "behind": 落后数,
                "overall_score": 综合得分 (0-100),
                "weighted_score": 加权得分
            },
            "kpis": [各KPI详情],
            "by_category": {按类别汇总},
            "highlights": [亮点],
            "concerns": [关注项]
        }

    Example:
        >>> kpi_dashboard([
        ...     {"name": "收入", "target": 1000000, "actual": 1100000, "direction": "higher_better"},
        ...     {"name": "成本率", "target": 0.6, "actual": 0.55, "direction": "lower_better"}
        ... ])
    """
    if not kpis:
        return {
            "period": period,
            "summary": {
                "total_kpis": 0,
                "exceeded": 0,
                "on_target": 0,
                "at_risk": 0,
                "behind": 0,
                "overall_score": 0,
                "weighted_score": 0
            },
            "kpis": [],
            "by_category": {},
            "highlights": [],
            "concerns": []
        }

    kpi_results = []
    category_data = {}
    highlights = []
    concerns = []

    status_counts = {
        "exceeded": 0,
        "on_target": 0,
        "at_risk": 0,
        "behind": 0
    }

    total_weight = 0
    weighted_score_sum = 0
    simple_score_sum = 0

    for kpi in kpis:
        name = kpi.get("name", "未命名")
        target = kpi.get("target", 0)
        actual = kpi.get("actual", 0)
        direction = kpi.get("direction", "higher_better")
        weight = kpi.get("weight", 1.0)
        unit = kpi.get("unit", "")
        category = kpi.get("category", "其他")

        # 计算完成率
        if target != 0:
            if direction == "higher_better":
                completion_rate = actual / target
            else:  # lower_better
                completion_rate = target / actual if actual != 0 else (2.0 if target > 0 else 1.0)
        else:
            completion_rate = 1.0 if actual == 0 else 0.0

        # 计算得分（0-100，超额最高120）
        score = min(120, completion_rate * 100)

        # 判断状态
        if completion_rate >= 1.1:
            status = "exceeded"
            highlights.append(f"{name}: 超额完成 {completion_rate:.0%}")
        elif completion_rate >= 1.0:
            status = "on_target"
        elif completion_rate >= 0.9:
            status = "at_risk"
            concerns.append(f"{name}: 完成率 {completion_rate:.0%}，需关注")
        else:
            status = "behind"
            concerns.append(f"{name}: 完成率 {completion_rate:.0%}，落后于目标")

        status_counts[status] += 1

        # 计算差异
        variance = actual - target
        if direction == "lower_better":
            variance = -variance  # 对于越低越好的指标，反转差异符号

        kpi_result = {
            "name": name,
            "target": target,
            "actual": actual,
            "unit": unit,
            "direction": direction,
            "completion_rate": round(completion_rate, 4),
            "score": round(score, 1),
            "status": status,
            "variance": variance,
            "weight": weight,
            "category": category
        }
        kpi_results.append(kpi_result)

        # 累计得分
        total_weight += weight
        weighted_score_sum += score * weight
        simple_score_sum += score

        # 按类别汇总
        if category not in category_data:
            category_data[category] = {
                "kpis": [],
                "total_score": 0,
                "count": 0
            }
        category_data[category]["kpis"].append(kpi_result)
        category_data[category]["total_score"] += score
        category_data[category]["count"] += 1

    # 计算综合得分
    overall_score = simple_score_sum / len(kpis) if kpis else 0
    weighted_score = weighted_score_sum / total_weight if total_weight > 0 else 0

    # 按类别计算平均得分
    by_category = {}
    for cat, data in category_data.items():
        by_category[cat] = {
            "count": data["count"],
            "avg_score": round(data["total_score"] / data["count"], 1),
            "kpis": [k["name"] for k in data["kpis"]]
        }

    return {
        "period": period,
        "summary": {
            "total_kpis": len(kpis),
            "exceeded": status_counts["exceeded"],
            "on_target": status_counts["on_target"],
            "at_risk": status_counts["at_risk"],
            "behind": status_counts["behind"],
            "overall_score": round(overall_score, 1),
            "weighted_score": round(weighted_score, 1)
        },
        "kpis": kpi_results,
        "by_category": by_category,
        "highlights": highlights[:5],  # 最多5个亮点
        "concerns": concerns[:5]       # 最多5个关注项
    }


# ============================================================
# 经济增加值 (EVA)
# ============================================================

def eva_calc(
    nopat: float,
    invested_capital: float,
    wacc: float,
    adjustments: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    经济增加值 (EVA) 计算

    EVA = NOPAT - (投入资本 × WACC)

    Args:
        nopat: 税后净营业利润 (Net Operating Profit After Tax)
        invested_capital: 投入资本（股东权益 + 有息负债）
        wacc: 加权平均资本成本 (如 0.10 表示 10%)
        adjustments: 会计调整项（可选）
            {
                "rd_capitalized": 研发费用资本化调整,
                "operating_lease": 经营租赁调整,
                "goodwill_amortization": 商誉摊销加回,
                "deferred_tax": 递延税项调整
            }

    Returns:
        {
            "nopat": 调整后NOPAT,
            "invested_capital": 调整后投入资本,
            "wacc": WACC,
            "capital_charge": 资本费用,
            "eva": 经济增加值,
            "eva_spread": EVA利差 (ROIC - WACC),
            "roic": 投入资本回报率,
            "value_created": 是否创造价值,
            "adjustments": 调整明细
        }

    Example:
        >>> eva_calc(
        ...     nopat=5000000,
        ...     invested_capital=30000000,
        ...     wacc=0.10
        ... )
    """
    adjustments = adjustments or {}

    # 调整NOPAT
    adjusted_nopat = nopat
    adjustment_details = {}

    if "rd_capitalized" in adjustments:
        # 研发资本化：加回当期费用化的研发支出
        rd_adj = adjustments["rd_capitalized"]
        adjusted_nopat += rd_adj
        adjustment_details["rd_capitalized"] = rd_adj

    if "goodwill_amortization" in adjustments:
        # 商誉摊销加回
        gw_adj = adjustments["goodwill_amortization"]
        adjusted_nopat += gw_adj
        adjustment_details["goodwill_amortization"] = gw_adj

    if "deferred_tax" in adjustments:
        # 递延税项调整
        dt_adj = adjustments["deferred_tax"]
        adjusted_nopat += dt_adj
        adjustment_details["deferred_tax"] = dt_adj

    # 调整投入资本
    adjusted_capital = invested_capital

    if "rd_capitalized" in adjustments:
        # 研发资本化增加投入资本（假设累计3年）
        adjusted_capital += adjustments["rd_capitalized"] * 2.5

    if "operating_lease" in adjustments:
        # 经营租赁资本化
        ol_adj = adjustments["operating_lease"]
        adjusted_capital += ol_adj
        adjustment_details["operating_lease"] = ol_adj

    # 计算EVA
    capital_charge = adjusted_capital * wacc
    eva = adjusted_nopat - capital_charge

    # 计算ROIC和EVA利差
    roic = adjusted_nopat / adjusted_capital if adjusted_capital > 0 else 0
    eva_spread = roic - wacc

    # 判断是否创造价值
    value_created = eva > 0

    # 分析
    if eva_spread > 0.05:
        analysis = "显著创造股东价值，ROIC大幅超过资本成本"
    elif eva_spread > 0:
        analysis = "创造股东价值，但利差较小，需持续提升"
    elif eva_spread > -0.03:
        analysis = "轻微侵蚀股东价值，需改善运营效率或优化资本结构"
    else:
        analysis = "显著侵蚀股东价值，需重点关注业务改善"

    return {
        "nopat": round(nopat, 2),
        "adjusted_nopat": round(adjusted_nopat, 2),
        "invested_capital": round(invested_capital, 2),
        "adjusted_capital": round(adjusted_capital, 2),
        "wacc": wacc,
        "capital_charge": round(capital_charge, 2),
        "eva": round(eva, 2),
        "roic": round(roic, 4),
        "eva_spread": round(eva_spread, 4),
        "value_created": value_created,
        "adjustments": adjustment_details,
        "analysis": analysis
    }


# ============================================================
# 平衡计分卡 (BSC)
# ============================================================

# 默认BSC四个维度
BSC_PERSPECTIVES = ["财务", "客户", "内部流程", "学习与成长"]


def balanced_scorecard(
    perspectives: Dict[str, List[Dict[str, Any]]],
    weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    平衡计分卡评分

    从财务、客户、内部流程、学习与成长四个维度评估绩效。

    Args:
        perspectives: 各维度指标
            {
                "财务": [
                    {"name": "ROE", "target": 0.15, "actual": 0.18, "weight": 0.4},
                    {"name": "收入增长率", "target": 0.10, "actual": 0.08, "weight": 0.3},
                    ...
                ],
                "客户": [...],
                "内部流程": [...],
                "学习与成长": [...]
            }
        weights: 各维度权重（可选，默认各25%）
            {"财务": 0.25, "客户": 0.25, "内部流程": 0.25, "学习与成长": 0.25}

    Returns:
        {
            "overall_score": 综合得分,
            "perspectives": {
                "财务": {
                    "score": 得分,
                    "weight": 权重,
                    "weighted_score": 加权得分,
                    "metrics": [指标详情]
                },
                ...
            },
            "strengths": [优势维度],
            "weaknesses": [弱势维度],
            "recommendations": [改进建议]
        }

    Example:
        >>> balanced_scorecard({
        ...     "财务": [{"name": "ROE", "target": 0.15, "actual": 0.18}],
        ...     "客户": [{"name": "满意度", "target": 90, "actual": 85}]
        ... })
    """
    default_weights = {p: 0.25 for p in BSC_PERSPECTIVES}
    weights = weights or default_weights

    perspective_results = {}
    total_weighted_score = 0
    total_weight = 0

    strengths = []
    weaknesses = []

    for perspective in BSC_PERSPECTIVES:
        metrics = perspectives.get(perspective, [])
        weight = weights.get(perspective, 0.25)

        if not metrics:
            perspective_results[perspective] = {
                "score": 0,
                "weight": weight,
                "weighted_score": 0,
                "metrics": [],
                "status": "无数据"
            }
            continue

        metric_results = []
        perspective_score_sum = 0
        metric_weight_sum = 0

        for metric in metrics:
            name = metric.get("name", "未命名")
            target = metric.get("target", 0)
            actual = metric.get("actual", 0)
            metric_weight = metric.get("weight", 1.0)
            direction = metric.get("direction", "higher_better")

            # 计算完成率
            if target != 0:
                if direction == "higher_better":
                    completion = actual / target
                else:
                    completion = target / actual if actual != 0 else 1.0
            else:
                completion = 1.0 if actual == 0 else 0.0

            score = min(120, completion * 100)

            metric_results.append({
                "name": name,
                "target": target,
                "actual": actual,
                "completion": round(completion, 4),
                "score": round(score, 1),
                "weight": metric_weight
            })

            perspective_score_sum += score * metric_weight
            metric_weight_sum += metric_weight

        # 维度得分
        perspective_score = perspective_score_sum / metric_weight_sum if metric_weight_sum > 0 else 0
        weighted_score = perspective_score * weight

        # 判断状态
        if perspective_score >= 100:
            status = "优秀"
            strengths.append(perspective)
        elif perspective_score >= 90:
            status = "良好"
        elif perspective_score >= 80:
            status = "达标"
        elif perspective_score >= 70:
            status = "需改进"
            weaknesses.append(perspective)
        else:
            status = "落后"
            weaknesses.append(perspective)

        perspective_results[perspective] = {
            "score": round(perspective_score, 1),
            "weight": weight,
            "weighted_score": round(weighted_score, 1),
            "metrics": metric_results,
            "status": status
        }

        total_weighted_score += weighted_score
        total_weight += weight

    # 综合得分
    overall_score = total_weighted_score / total_weight if total_weight > 0 else 0

    # 生成建议
    recommendations = []
    for weakness in weaknesses:
        if weakness == "财务":
            recommendations.append("加强成本控制，提升盈利能力")
        elif weakness == "客户":
            recommendations.append("提升客户满意度，加强客户关系管理")
        elif weakness == "内部流程":
            recommendations.append("优化业务流程，提高运营效率")
        elif weakness == "学习与成长":
            recommendations.append("加大培训投入，提升员工能力")

    if not recommendations and overall_score >= 90:
        recommendations.append("整体表现优秀，继续保持并追求卓越")

    return {
        "overall_score": round(overall_score, 1),
        "perspectives": perspective_results,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendations": recommendations
    }


# ============================================================
# OKR 进度追踪
# ============================================================

def okr_progress(
    objectives: List[Dict[str, Any]],
    scoring_method: str = "average"
) -> Dict[str, Any]:
    """
    OKR 进度追踪

    追踪目标(Objectives)和关键结果(Key Results)的完成进度。

    Args:
        objectives: 目标列表
            [
                {
                    "objective": "提升产品质量",
                    "owner": "产品部",
                    "key_results": [
                        {
                            "kr": "bug率降低50%",
                            "target": 50,
                            "actual": 45,
                            "unit": "%",
                            "confidence": 0.8  # 信心指数（可选）
                        },
                        ...
                    ]
                },
                ...
            ]
        scoring_method: 评分方法
            - "average": 简单平均
            - "google": Google风格（0.7为满分）

    Returns:
        {
            "summary": {
                "total_objectives": 目标总数,
                "total_krs": KR总数,
                "avg_progress": 平均进度,
                "on_track": 正常推进数,
                "at_risk": 风险数,
                "behind": 落后数
            },
            "objectives": [
                {
                    "objective": 目标,
                    "progress": 进度,
                    "score": 得分,
                    "status": 状态,
                    "key_results": [KR详情]
                },
                ...
            ],
            "by_owner": {按负责人汇总},
            "recommendations": [建议]
        }

    Example:
        >>> okr_progress([
        ...     {
        ...         "objective": "提升收入",
        ...         "key_results": [
        ...             {"kr": "新客户数", "target": 100, "actual": 80},
        ...             {"kr": "客单价", "target": 500, "actual": 550}
        ...         ]
        ...     }
        ... ])
    """
    if not objectives:
        return {
            "summary": {
                "total_objectives": 0,
                "total_krs": 0,
                "avg_progress": 0,
                "on_track": 0,
                "at_risk": 0,
                "behind": 0
            },
            "objectives": [],
            "by_owner": {},
            "recommendations": []
        }

    objective_results = []
    owner_data = {}
    total_krs = 0
    progress_sum = 0

    status_counts = {"on_track": 0, "at_risk": 0, "behind": 0}

    for obj in objectives:
        objective_name = obj.get("objective", "未命名目标")
        owner = obj.get("owner", "未指定")
        key_results = obj.get("key_results", [])

        kr_results = []
        obj_progress_sum = 0

        for kr in key_results:
            kr_name = kr.get("kr", kr.get("name", "未命名KR"))
            target = kr.get("target", 0)
            actual = kr.get("actual", 0)
            unit = kr.get("unit", "")
            confidence = kr.get("confidence", 1.0)
            direction = kr.get("direction", "higher_better")

            # 计算进度
            if target != 0:
                if direction == "higher_better":
                    progress = actual / target
                else:
                    progress = target / actual if actual != 0 else 1.0
            else:
                progress = 1.0 if actual == 0 else 0.0

            progress = min(1.0, progress)  # 封顶100%

            # Google风格评分：0.7为满分
            if scoring_method == "google":
                score = min(1.0, progress / 0.7)
            else:
                score = progress

            kr_results.append({
                "kr": kr_name,
                "target": target,
                "actual": actual,
                "unit": unit,
                "progress": round(progress, 4),
                "score": round(score, 4),
                "confidence": confidence
            })

            obj_progress_sum += progress
            total_krs += 1
            progress_sum += progress

        # 目标整体进度
        obj_progress = obj_progress_sum / len(key_results) if key_results else 0

        # Google风格评分
        if scoring_method == "google":
            obj_score = min(1.0, obj_progress / 0.7)
        else:
            obj_score = obj_progress

        # 判断状态
        if obj_progress >= 0.9:
            status = "on_track"
        elif obj_progress >= 0.7:
            status = "at_risk"
        else:
            status = "behind"

        status_counts[status] += 1

        objective_results.append({
            "objective": objective_name,
            "owner": owner,
            "progress": round(obj_progress, 4),
            "score": round(obj_score, 4),
            "status": status,
            "key_results": kr_results,
            "kr_count": len(key_results)
        })

        # 按负责人汇总
        if owner not in owner_data:
            owner_data[owner] = {
                "objectives": [],
                "total_progress": 0,
                "count": 0
            }
        owner_data[owner]["objectives"].append(objective_name)
        owner_data[owner]["total_progress"] += obj_progress
        owner_data[owner]["count"] += 1

    # 汇总统计
    avg_progress = progress_sum / total_krs if total_krs > 0 else 0

    # 按负责人
    by_owner = {
        owner: {
            "objectives": data["objectives"],
            "avg_progress": round(data["total_progress"] / data["count"], 4) if data["count"] > 0 else 0,
            "count": data["count"]
        }
        for owner, data in owner_data.items()
    }

    # 生成建议
    recommendations = []
    behind_objs = [o for o in objective_results if o["status"] == "behind"]
    if behind_objs:
        recommendations.append(f"有{len(behind_objs)}个目标进度落后，建议重点关注并制定追赶计划")

    at_risk_objs = [o for o in objective_results if o["status"] == "at_risk"]
    if at_risk_objs:
        recommendations.append(f"有{len(at_risk_objs)}个目标存在风险，需密切监控")

    if avg_progress >= 0.9:
        recommendations.append("整体OKR执行良好，继续保持")
    elif avg_progress < 0.5:
        recommendations.append("整体进度偏低，建议检视目标设定是否合理")

    return {
        "summary": {
            "total_objectives": len(objectives),
            "total_krs": total_krs,
            "avg_progress": round(avg_progress, 4),
            "on_track": status_counts["on_track"],
            "at_risk": status_counts["at_risk"],
            "behind": status_counts["behind"]
        },
        "objectives": objective_results,
        "by_owner": by_owner,
        "scoring_method": scoring_method,
        "recommendations": recommendations
    }


# ============================================================
# 工具注册（供 LLM 发现）
# ============================================================

PERFORMANCE_TOOLS = {
    "kpi_dashboard": {
        "function": kpi_dashboard,
        "description": "KPI仪表盘，汇总多个KPI指标完成情况",
        "parameters": ["kpis", "period"]
    },
    "eva_calc": {
        "function": eva_calc,
        "description": "经济增加值(EVA)计算，评估股东价值创造",
        "parameters": ["nopat", "invested_capital", "wacc", "adjustments"]
    },
    "balanced_scorecard": {
        "function": balanced_scorecard,
        "description": "平衡计分卡评分，四维度绩效评估",
        "parameters": ["perspectives", "weights"]
    },
    "okr_progress": {
        "function": okr_progress,
        "description": "OKR进度追踪，追踪目标和关键结果完成度",
        "parameters": ["objectives", "scoring_method"]
    }
}
