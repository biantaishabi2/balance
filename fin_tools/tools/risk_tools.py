# -*- coding: utf-8 -*-
"""
risk_tools.py - 风险管理原子工具

提供客户信用评分、应收账龄分析、坏账准备计算、汇率风险敞口等功能。
设计为无状态的原子函数，供 LLM 灵活调用组合。
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, date
from collections import defaultdict


# ============================================================
# 客户信用评分
# ============================================================

# 默认评分权重
DEFAULT_CREDIT_WEIGHTS = {
    "payment_history": 0.35,      # 付款历史
    "credit_utilization": 0.20,  # 信用额度使用率
    "relationship_length": 0.15, # 合作时长
    "order_frequency": 0.10,     # 订单频率
    "financial_health": 0.20,    # 财务状况
}

# 信用等级划分
CREDIT_GRADES = [
    (90, "AAA", "优质客户，可给予最优惠条款"),
    (80, "AA", "良好客户，可适当放宽信用"),
    (70, "A", "正常客户，标准信用条款"),
    (60, "BBB", "关注客户，需加强监控"),
    (50, "BB", "风险客户，建议缩短账期"),
    (40, "B", "高风险客户，建议预付款"),
    (0, "C", "极高风险，建议停止赊销"),
]


def credit_score(
    customer_data: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    客户信用评分

    基于多维度指标计算客户信用分数。

    Args:
        customer_data: 客户数据
            {
                "customer_id": 客户ID,
                "customer_name": 客户名称,
                "payment_history": {
                    "on_time_rate": 准时付款率 (0-1),
                    "avg_days_late": 平均逾期天数,
                    "max_days_late": 最大逾期天数
                },
                "credit_utilization": {
                    "credit_limit": 信用额度,
                    "current_ar": 当前应收余额
                },
                "relationship": {
                    "years": 合作年限,
                    "total_transactions": 历史交易次数
                },
                "order_frequency": {
                    "orders_per_year": 年订单数,
                    "avg_order_value": 平均订单金额
                },
                "financial_health": {
                    "current_ratio": 流动比率（可选）,
                    "debt_ratio": 资产负债率（可选）,
                    "profitable": 是否盈利（可选）
                }
            }
        weights: 各维度权重（可选，默认使用系统权重）

    Returns:
        {
            "score": 综合评分 (0-100),
            "grade": 信用等级,
            "grade_desc": 等级说明,
            "dimension_scores": {各维度得分},
            "risk_factors": [风险因素列表],
            "recommendations": [建议列表]
        }

    Example:
        >>> credit_score({
        ...     "customer_name": "ABC公司",
        ...     "payment_history": {"on_time_rate": 0.95, "avg_days_late": 3},
        ...     "credit_utilization": {"credit_limit": 100000, "current_ar": 60000},
        ...     "relationship": {"years": 5}
        ... })
    """
    weights = weights or DEFAULT_CREDIT_WEIGHTS

    dimension_scores = {}
    risk_factors = []
    recommendations = []

    # 1. 付款历史评分 (0-100)
    payment = customer_data.get("payment_history", {})
    on_time_rate = payment.get("on_time_rate", 0.8)
    avg_days_late = payment.get("avg_days_late", 0)
    max_days_late = payment.get("max_days_late", 0)

    payment_score = on_time_rate * 100
    # 逾期天数扣分
    if avg_days_late > 0:
        payment_score -= min(avg_days_late * 2, 30)
    if max_days_late > 60:
        payment_score -= 10
        risk_factors.append(f"曾有超过60天的逾期记录（最长{max_days_late}天）")

    payment_score = max(0, min(100, payment_score))
    dimension_scores["payment_history"] = round(payment_score, 1)

    if on_time_rate < 0.7:
        risk_factors.append(f"准时付款率偏低（{on_time_rate:.0%}）")
        recommendations.append("建议缩短账期或要求部分预付款")

    # 2. 信用额度使用率评分 (0-100)
    credit = customer_data.get("credit_utilization", {})
    credit_limit = credit.get("credit_limit", 0)
    current_ar = credit.get("current_ar", 0)

    if credit_limit > 0:
        utilization = current_ar / credit_limit
        # 使用率30%-70%最佳
        if utilization <= 0.3:
            utilization_score = 80 + utilization * 66.7  # 0-30% -> 80-100
        elif utilization <= 0.7:
            utilization_score = 100 - (utilization - 0.3) * 50  # 30-70% -> 100-80
        else:
            utilization_score = 80 - (utilization - 0.7) * 200  # 70-100% -> 80-20
            if utilization > 0.9:
                risk_factors.append(f"信用额度使用率过高（{utilization:.0%}）")
                recommendations.append("建议提高信用额度或加快回款")
        utilization_score = max(0, min(100, utilization_score))
    else:
        utilization_score = 50  # 无信用额度记录
        utilization = 0

    dimension_scores["credit_utilization"] = round(utilization_score, 1)

    # 3. 合作时长评分 (0-100)
    relationship = customer_data.get("relationship", {})
    years = relationship.get("years", 0)

    if years >= 5:
        relationship_score = 100
    elif years >= 3:
        relationship_score = 80 + (years - 3) * 10
    elif years >= 1:
        relationship_score = 60 + (years - 1) * 10
    else:
        relationship_score = 40 + years * 20

    dimension_scores["relationship_length"] = round(relationship_score, 1)

    if years < 1:
        risk_factors.append("新客户，合作时间不足1年")
        recommendations.append("建议采用保守的信用政策")

    # 4. 订单频率评分 (0-100)
    order = customer_data.get("order_frequency", {})
    orders_per_year = order.get("orders_per_year", 0)

    if orders_per_year >= 12:
        frequency_score = 100
    elif orders_per_year >= 6:
        frequency_score = 70 + (orders_per_year - 6) * 5
    elif orders_per_year >= 1:
        frequency_score = 40 + (orders_per_year - 1) * 6
    else:
        frequency_score = 30

    dimension_scores["order_frequency"] = round(frequency_score, 1)

    # 5. 财务状况评分 (0-100)
    financial = customer_data.get("financial_health", {})

    if financial:
        financial_score = 60  # 基础分

        current_ratio = financial.get("current_ratio")
        if current_ratio is not None:
            if current_ratio >= 2:
                financial_score += 15
            elif current_ratio >= 1.5:
                financial_score += 10
            elif current_ratio >= 1:
                financial_score += 5
            else:
                financial_score -= 10
                risk_factors.append(f"流动比率偏低（{current_ratio:.2f}）")

        debt_ratio = financial.get("debt_ratio")
        if debt_ratio is not None:
            if debt_ratio <= 0.4:
                financial_score += 15
            elif debt_ratio <= 0.6:
                financial_score += 10
            elif debt_ratio <= 0.7:
                financial_score += 5
            else:
                financial_score -= 10
                risk_factors.append(f"资产负债率偏高（{debt_ratio:.0%}）")

        if financial.get("profitable", True):
            financial_score += 10
        else:
            financial_score -= 10
            risk_factors.append("客户处于亏损状态")

        financial_score = max(0, min(100, financial_score))
    else:
        financial_score = 50  # 无财务数据，给中等分

    dimension_scores["financial_health"] = round(financial_score, 1)

    # 计算综合评分
    total_score = sum(
        dimension_scores.get(dim, 50) * weight
        for dim, weight in weights.items()
    )
    total_score = round(total_score, 1)

    # 确定信用等级
    grade = "C"
    grade_desc = "极高风险"
    for threshold, g, desc in CREDIT_GRADES:
        if total_score >= threshold:
            grade = g
            grade_desc = desc
            break

    # 生成建议
    if not recommendations:
        if grade in ["AAA", "AA"]:
            recommendations.append("可考虑延长账期或提高信用额度")
        elif grade == "A":
            recommendations.append("维持当前信用政策")
        elif grade in ["BBB", "BB"]:
            recommendations.append("加强应收账款监控")

    return {
        "customer_id": customer_data.get("customer_id"),
        "customer_name": customer_data.get("customer_name"),
        "score": total_score,
        "grade": grade,
        "grade_desc": grade_desc,
        "dimension_scores": dimension_scores,
        "weights": weights,
        "risk_factors": risk_factors,
        "recommendations": recommendations
    }


# ============================================================
# 应收账款账龄分析
# ============================================================

# 默认账龄区间
DEFAULT_AGING_BUCKETS = [
    (0, 30, "0-30天"),
    (31, 60, "31-60天"),
    (61, 90, "61-90天"),
    (91, 180, "91-180天"),
    (181, 365, "181-365天"),
    (366, float('inf'), "1年以上"),
]


def ar_aging(
    receivables: List[Dict[str, Any]],
    as_of_date: Optional[str] = None,
    aging_buckets: Optional[List[tuple]] = None
) -> Dict[str, Any]:
    """
    应收账款账龄分析

    按账龄区间分析应收账款分布。

    Args:
        receivables: 应收账款明细列表
            [
                {
                    "invoice_id": 发票号,
                    "customer_id": 客户ID,
                    "customer_name": 客户名称,
                    "invoice_date": 发票日期 (YYYY-MM-DD),
                    "due_date": 到期日期 (YYYY-MM-DD),
                    "amount": 金额,
                    "paid_amount": 已收金额（可选，默认0）
                },
                ...
            ]
        as_of_date: 截止日期 (YYYY-MM-DD)，默认当天
        aging_buckets: 账龄区间定义（可选）

    Returns:
        {
            "as_of_date": 截止日期,
            "total_ar": 应收总额,
            "aging_summary": {
                "0-30天": {"amount": 金额, "count": 笔数, "pct": 占比},
                ...
            },
            "by_customer": [按客户汇总],
            "overdue_summary": {
                "total_overdue": 逾期总额,
                "overdue_rate": 逾期率,
                "avg_days_overdue": 平均逾期天数
            },
            "details": [明细列表]
        }

    Example:
        >>> ar_aging([
        ...     {"invoice_id": "INV001", "customer_name": "客户A",
        ...      "invoice_date": "2024-10-01", "due_date": "2024-10-31", "amount": 10000},
        ...     {"invoice_id": "INV002", "customer_name": "客户B",
        ...      "invoice_date": "2024-09-01", "due_date": "2024-09-30", "amount": 20000}
        ... ], as_of_date="2024-11-15")
    """
    if not receivables:
        return {
            "as_of_date": as_of_date or date.today().isoformat(),
            "total_ar": 0,
            "aging_summary": {},
            "by_customer": [],
            "overdue_summary": {
                "total_overdue": 0,
                "overdue_rate": 0,
                "overdue_count": 0,
                "avg_days_overdue": 0
            },
            "details": [],
            "invoice_count": 0
        }

    aging_buckets = aging_buckets or DEFAULT_AGING_BUCKETS

    # 解析截止日期
    if as_of_date:
        ref_date = datetime.strptime(as_of_date, "%Y-%m-%d").date()
    else:
        ref_date = date.today()
        as_of_date = ref_date.isoformat()

    # 初始化账龄汇总
    aging_summary = {bucket[2]: {"amount": 0, "count": 0} for bucket in aging_buckets}

    # 按客户汇总
    customer_summary = defaultdict(lambda: {"total": 0, "overdue": 0, "buckets": defaultdict(float)})

    # 逾期统计
    total_overdue = 0
    total_days_overdue = 0
    overdue_count = 0

    details = []

    for item in receivables:
        amount = item.get("amount", 0)
        paid_amount = item.get("paid_amount", 0)
        outstanding = amount - paid_amount

        if outstanding <= 0:
            continue  # 已结清

        # 计算账龄（从发票日期）
        invoice_date_str = item.get("invoice_date")
        due_date_str = item.get("due_date")

        if invoice_date_str:
            invoice_date = datetime.strptime(invoice_date_str, "%Y-%m-%d").date()
            age_days = (ref_date - invoice_date).days
        else:
            age_days = 0

        # 计算逾期天数
        if due_date_str:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            days_overdue = max(0, (ref_date - due_date).days)
        else:
            days_overdue = 0

        # 确定账龄区间
        bucket_name = aging_buckets[-1][2]  # 默认最后一个区间
        for start, end, name in aging_buckets:
            if start <= age_days <= end:
                bucket_name = name
                break

        # 更新汇总
        aging_summary[bucket_name]["amount"] += outstanding
        aging_summary[bucket_name]["count"] += 1

        # 更新客户汇总
        customer_id = item.get("customer_id", item.get("customer_name", "未知"))
        customer_name = item.get("customer_name", customer_id)
        customer_summary[customer_id]["customer_name"] = customer_name
        customer_summary[customer_id]["total"] += outstanding
        customer_summary[customer_id]["buckets"][bucket_name] += outstanding

        if days_overdue > 0:
            total_overdue += outstanding
            total_days_overdue += days_overdue * outstanding  # 加权天数
            overdue_count += 1
            customer_summary[customer_id]["overdue"] += outstanding

        # 明细
        details.append({
            "invoice_id": item.get("invoice_id"),
            "customer_id": customer_id,
            "customer_name": customer_name,
            "invoice_date": invoice_date_str,
            "due_date": due_date_str,
            "amount": amount,
            "paid_amount": paid_amount,
            "outstanding": outstanding,
            "age_days": age_days,
            "days_overdue": days_overdue,
            "aging_bucket": bucket_name
        })

    # 计算总额和占比
    total_ar = sum(b["amount"] for b in aging_summary.values())

    for bucket_name in aging_summary:
        if total_ar > 0:
            aging_summary[bucket_name]["pct"] = round(
                aging_summary[bucket_name]["amount"] / total_ar, 4
            )
        else:
            aging_summary[bucket_name]["pct"] = 0

    # 按客户汇总列表
    by_customer = [
        {
            "customer_id": cid,
            "customer_name": data["customer_name"],
            "total": round(data["total"], 2),
            "overdue": round(data["overdue"], 2),
            "overdue_rate": round(data["overdue"] / data["total"], 4) if data["total"] > 0 else 0,
            "buckets": dict(data["buckets"])
        }
        for cid, data in sorted(customer_summary.items(), key=lambda x: -x[1]["total"])
    ]

    # 逾期汇总
    avg_days_overdue = round(total_days_overdue / total_overdue, 1) if total_overdue > 0 else 0

    return {
        "as_of_date": as_of_date,
        "total_ar": round(total_ar, 2),
        "aging_summary": aging_summary,
        "by_customer": by_customer,
        "overdue_summary": {
            "total_overdue": round(total_overdue, 2),
            "overdue_rate": round(total_overdue / total_ar, 4) if total_ar > 0 else 0,
            "overdue_count": overdue_count,
            "avg_days_overdue": avg_days_overdue
        },
        "details": details,
        "invoice_count": len(details)
    }


# ============================================================
# 坏账准备计算
# ============================================================

# 默认坏账计提比例（按账龄）
DEFAULT_PROVISION_RATES = {
    "0-30天": 0.01,       # 1%
    "31-60天": 0.03,      # 3%
    "61-90天": 0.05,      # 5%
    "91-180天": 0.10,     # 10%
    "181-365天": 0.30,    # 30%
    "1年以上": 0.50,      # 50%
}


def bad_debt_provision(
    aging_data: Dict[str, Any],
    provision_rates: Optional[Dict[str, float]] = None,
    specific_provisions: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    坏账准备计算

    基于账龄分析计算坏账准备金额。

    Args:
        aging_data: 账龄分析数据（ar_aging函数的输出）或简化格式
            {
                "aging_summary": {
                    "0-30天": {"amount": 金额},
                    ...
                }
            }
            或简化格式：
            {
                "0-30天": 金额,
                "31-60天": 金额,
                ...
            }
        provision_rates: 各账龄区间的计提比例（可选）
        specific_provisions: 特定客户的专项计提
            [{"customer_name": "客户A", "amount": 金额, "rate": 计提比例, "reason": "原因"}, ...]

    Returns:
        {
            "total_ar": 应收总额,
            "general_provision": 一般坏账准备,
            "specific_provision": 专项坏账准备,
            "total_provision": 坏账准备合计,
            "provision_rate": 综合计提比例,
            "by_aging": [各账龄计提明细],
            "by_specific": [专项计提明细]
        }

    Example:
        >>> bad_debt_provision({
        ...     "aging_summary": {
        ...         "0-30天": {"amount": 500000},
        ...         "31-60天": {"amount": 200000},
        ...         "61-90天": {"amount": 100000}
        ...     }
        ... })
    """
    provision_rates = provision_rates or DEFAULT_PROVISION_RATES
    specific_provisions = specific_provisions or []

    # 解析账龄数据
    if "aging_summary" in aging_data:
        # ar_aging 输出格式
        aging_summary = aging_data["aging_summary"]
        aging_amounts = {
            bucket: data.get("amount", 0) if isinstance(data, dict) else data
            for bucket, data in aging_summary.items()
        }
    else:
        # 简化格式
        aging_amounts = aging_data

    # 计算一般坏账准备
    by_aging = []
    general_provision = 0
    total_ar = 0

    for bucket, amount in aging_amounts.items():
        if isinstance(amount, dict):
            amount = amount.get("amount", 0)

        total_ar += amount
        rate = provision_rates.get(bucket, 0.05)  # 默认5%
        provision = amount * rate

        by_aging.append({
            "aging_bucket": bucket,
            "amount": round(amount, 2),
            "provision_rate": rate,
            "provision": round(provision, 2)
        })

        general_provision += provision

    # 按账龄排序
    aging_order = ["0-30天", "31-60天", "61-90天", "91-180天", "181-365天", "1年以上"]
    by_aging.sort(key=lambda x: aging_order.index(x["aging_bucket"]) if x["aging_bucket"] in aging_order else 99)

    # 计算专项坏账准备
    by_specific = []
    specific_provision = 0

    for item in specific_provisions:
        amount = item.get("amount", 0)
        rate = item.get("rate", 1.0)  # 默认100%计提
        provision = amount * rate

        by_specific.append({
            "customer_name": item.get("customer_name"),
            "amount": round(amount, 2),
            "provision_rate": rate,
            "provision": round(provision, 2),
            "reason": item.get("reason", "")
        })

        specific_provision += provision

    # 汇总
    total_provision = general_provision + specific_provision
    provision_rate = total_provision / total_ar if total_ar > 0 else 0

    return {
        "total_ar": round(total_ar, 2),
        "general_provision": round(general_provision, 2),
        "specific_provision": round(specific_provision, 2),
        "total_provision": round(total_provision, 2),
        "provision_rate": round(provision_rate, 4),
        "by_aging": by_aging,
        "by_specific": by_specific,
        "provision_rates_used": provision_rates
    }


# ============================================================
# 汇率风险敞口
# ============================================================

def fx_exposure(
    assets: List[Dict[str, Any]],
    liabilities: List[Dict[str, Any]],
    base_currency: str = "CNY",
    exchange_rates: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    汇率风险敞口分析

    计算各币种的净敞口和潜在损益。

    Args:
        assets: 外币资产列表
            [{"currency": "USD", "amount": 100000, "description": "美元存款"}, ...]
        liabilities: 外币负债列表
            [{"currency": "USD", "amount": 50000, "description": "美元借款"}, ...]
        base_currency: 本位币（默认CNY）
        exchange_rates: 汇率表（可选，货币对本位币的汇率）
            {"USD": 7.2, "EUR": 7.8, "JPY": 0.048}

    Returns:
        {
            "base_currency": 本位币,
            "by_currency": {
                "USD": {
                    "assets": 资产总额,
                    "liabilities": 负债总额,
                    "net_exposure": 净敞口,
                    "exposure_type": "long"/"short",
                    "base_value": 本位币价值,
                    "sensitivity": {
                        "1%": 1%汇率变动损益,
                        "5%": 5%汇率变动损益,
                        "10%": 10%汇率变动损益
                    }
                },
                ...
            },
            "total_exposure": {
                "gross": 总敞口绝对值,
                "net_long": 净多头,
                "net_short": 净空头
            },
            "var_analysis": {
                "方差分析（如有足够数据）
            }
        }

    Example:
        >>> fx_exposure(
        ...     assets=[
        ...         {"currency": "USD", "amount": 100000},
        ...         {"currency": "EUR", "amount": 50000}
        ...     ],
        ...     liabilities=[
        ...         {"currency": "USD", "amount": 30000}
        ...     ],
        ...     exchange_rates={"USD": 7.2, "EUR": 7.8}
        ... )
    """
    # 默认汇率（仅作参考）
    default_rates = {
        "USD": 7.20,
        "EUR": 7.80,
        "GBP": 9.10,
        "JPY": 0.048,
        "HKD": 0.92,
        "SGD": 5.35,
        "AUD": 4.70,
        "CAD": 5.30,
        "CHF": 8.10,
    }

    rates = exchange_rates or default_rates

    # 按币种汇总
    currency_data = defaultdict(lambda: {"assets": 0, "liabilities": 0, "asset_items": [], "liability_items": []})

    for item in assets:
        currency = item.get("currency", "USD")
        amount = item.get("amount", 0)
        currency_data[currency]["assets"] += amount
        currency_data[currency]["asset_items"].append(item)

    for item in liabilities:
        currency = item.get("currency", "USD")
        amount = item.get("amount", 0)
        currency_data[currency]["liabilities"] += amount
        currency_data[currency]["liability_items"].append(item)

    # 分析各币种
    by_currency = {}
    total_gross = 0
    total_net_long = 0
    total_net_short = 0

    for currency, data in currency_data.items():
        if currency == base_currency:
            continue  # 跳过本位币

        net_exposure = data["assets"] - data["liabilities"]
        exposure_type = "long" if net_exposure > 0 else "short" if net_exposure < 0 else "balanced"

        rate = rates.get(currency, 1.0)
        base_value = net_exposure * rate

        # 敏感性分析
        sensitivity = {
            "1%": round(abs(base_value) * 0.01, 2),
            "5%": round(abs(base_value) * 0.05, 2),
            "10%": round(abs(base_value) * 0.10, 2),
        }

        by_currency[currency] = {
            "assets": round(data["assets"], 2),
            "liabilities": round(data["liabilities"], 2),
            "net_exposure": round(net_exposure, 2),
            "exposure_type": exposure_type,
            "exchange_rate": rate,
            "base_value": round(base_value, 2),
            "sensitivity": sensitivity
        }

        # 汇总
        total_gross += abs(net_exposure * rate)
        if net_exposure > 0:
            total_net_long += base_value
        else:
            total_net_short += abs(base_value)

    # 风险评估
    risk_level = "低"
    recommendations = []

    if total_gross > 0:
        # 判断集中度
        max_exposure = max((abs(d["base_value"]) for d in by_currency.values()), default=0)
        concentration = max_exposure / total_gross if total_gross > 0 else 0

        if concentration > 0.7:
            risk_level = "高"
            recommendations.append("外汇敞口高度集中，建议分散币种风险")
        elif concentration > 0.5:
            risk_level = "中"
            recommendations.append("外汇敞口较集中，建议关注主要币种波动")
        else:
            risk_level = "低"

        # 净敞口方向
        net_position = total_net_long - total_net_short
        if abs(net_position) > total_gross * 0.3:
            if net_position > 0:
                recommendations.append("整体净多头敞口，本位币升值将带来损失")
            else:
                recommendations.append("整体净空头敞口，本位币贬值将带来损失")

    if not recommendations:
        recommendations.append("外汇风险敞口处于可控范围")

    return {
        "base_currency": base_currency,
        "by_currency": by_currency,
        "total_exposure": {
            "gross": round(total_gross, 2),
            "net_long": round(total_net_long, 2),
            "net_short": round(total_net_short, 2),
            "net_position": round(total_net_long - total_net_short, 2)
        },
        "risk_assessment": {
            "risk_level": risk_level,
            "recommendations": recommendations
        },
        "exchange_rates_used": {k: v for k, v in rates.items() if k in by_currency}
    }


# ============================================================
# 工具注册（供 LLM 发现）
# ============================================================

RISK_TOOLS = {
    "credit_score": {
        "function": credit_score,
        "description": "客户信用评分，多维度评估客户信用风险",
        "parameters": ["customer_data", "weights"]
    },
    "ar_aging": {
        "function": ar_aging,
        "description": "应收账款账龄分析，按账龄区间统计应收款",
        "parameters": ["receivables", "as_of_date", "aging_buckets"]
    },
    "bad_debt_provision": {
        "function": bad_debt_provision,
        "description": "坏账准备计算，基于账龄计提坏账准备",
        "parameters": ["aging_data", "provision_rates", "specific_provisions"]
    },
    "fx_exposure": {
        "function": fx_exposure,
        "description": "汇率风险敞口分析，计算各币种净敞口",
        "parameters": ["assets", "liabilities", "base_currency", "exchange_rates"]
    }
}
