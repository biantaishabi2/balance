# -*- coding: utf-8 -*-
"""
audit_tools.py - 会计审计原子工具

提供试算平衡检查、调整分录建议、审计抽样、合并报表抵消等功能。
设计为无状态的原子函数，供 LLM 灵活调用组合。
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import random
import math


# ============================================================
# 试算平衡检查
# ============================================================

class AccountType(Enum):
    """科目类型"""
    ASSET = "asset"           # 资产
    LIABILITY = "liability"   # 负债
    EQUITY = "equity"         # 权益
    REVENUE = "revenue"       # 收入
    EXPENSE = "expense"       # 费用


# 常用科目借贷方向
NORMAL_BALANCE = {
    "asset": "debit",
    "liability": "credit",
    "equity": "credit",
    "revenue": "credit",
    "expense": "debit",
}


def trial_balance(
    accounts: List[Dict[str, Any]],
    tolerance: float = 0.01
) -> Dict[str, Any]:
    """
    试算平衡检查

    验证借方总额与贷方总额是否平衡。

    Args:
        accounts: 科目余额列表
            [
                {
                    "code": "1001",
                    "name": "库存现金",
                    "type": "asset",  # asset/liability/equity/revenue/expense
                    "debit": 50000,   # 借方余额
                    "credit": 0       # 贷方余额
                },
                ...
            ]
        tolerance: 允许的误差范围（默认0.01元）

    Returns:
        {
            "balanced": 是否平衡,
            "total_debit": 借方总额,
            "total_credit": 贷方总额,
            "difference": 差额,
            "by_type": {按科目类型汇总},
            "issues": [问题列表],
            "accounts": [科目详情（含异常标记）]
        }

    Example:
        >>> trial_balance([
        ...     {"code": "1001", "name": "现金", "type": "asset", "debit": 10000, "credit": 0},
        ...     {"code": "2001", "name": "应付", "type": "liability", "debit": 0, "credit": 10000}
        ... ])
    """
    if not accounts:
        return {
            "balanced": True,
            "total_debit": 0,
            "total_credit": 0,
            "difference": 0,
            "by_type": {},
            "issues": [],
            "accounts": []
        }

    total_debit = 0
    total_credit = 0
    issues = []
    account_results = []

    # 按类型汇总
    by_type = {
        "asset": {"debit": 0, "credit": 0, "net": 0, "count": 0},
        "liability": {"debit": 0, "credit": 0, "net": 0, "count": 0},
        "equity": {"debit": 0, "credit": 0, "net": 0, "count": 0},
        "revenue": {"debit": 0, "credit": 0, "net": 0, "count": 0},
        "expense": {"debit": 0, "credit": 0, "net": 0, "count": 0},
    }

    for acc in accounts:
        code = acc.get("code", "")
        name = acc.get("name", "未命名")
        acc_type = acc.get("type", "asset")
        debit = acc.get("debit", 0) or 0
        credit = acc.get("credit", 0) or 0

        total_debit += debit
        total_credit += credit

        # 计算净额
        net_balance = debit - credit

        # 检查方向是否正常
        normal_dir = NORMAL_BALANCE.get(acc_type, "debit")
        is_normal = True
        warning = None

        if normal_dir == "debit" and net_balance < 0:
            is_normal = False
            warning = f"资产/费用类科目出现贷方余额"
        elif normal_dir == "credit" and net_balance > 0:
            is_normal = False
            warning = f"负债/权益/收入类科目出现借方余额"

        if not is_normal:
            issues.append({
                "type": "abnormal_balance",
                "code": code,
                "name": name,
                "message": warning,
                "net_balance": net_balance
            })

        # 检查同时有借贷发生（期末余额应只有一方）
        if debit > 0 and credit > 0:
            issues.append({
                "type": "both_sides",
                "code": code,
                "name": name,
                "message": "科目同时存在借贷余额，请检查是否为发生额",
                "debit": debit,
                "credit": credit
            })

        account_results.append({
            "code": code,
            "name": name,
            "type": acc_type,
            "debit": debit,
            "credit": credit,
            "net_balance": net_balance,
            "is_normal": is_normal,
            "warning": warning
        })

        # 按类型累计
        if acc_type in by_type:
            by_type[acc_type]["debit"] += debit
            by_type[acc_type]["credit"] += credit
            by_type[acc_type]["net"] += net_balance
            by_type[acc_type]["count"] += 1

    # 计算差额
    difference = total_debit - total_credit
    balanced = abs(difference) <= tolerance

    if not balanced:
        issues.insert(0, {
            "type": "unbalanced",
            "message": f"试算不平衡，差额 {difference:,.2f} 元",
            "total_debit": total_debit,
            "total_credit": total_credit,
            "difference": difference
        })

    # 验证会计恒等式：资产 = 负债 + 权益
    assets_net = by_type["asset"]["net"]
    liabilities_net = -by_type["liability"]["net"]  # 贷方为正
    equity_net = -by_type["equity"]["net"]  # 贷方为正

    equation_diff = assets_net - (liabilities_net + equity_net)
    if abs(equation_diff) > tolerance:
        issues.append({
            "type": "equation_imbalance",
            "message": f"会计恒等式不平衡：资产({assets_net:,.2f}) ≠ 负债({liabilities_net:,.2f}) + 权益({equity_net:,.2f})",
            "assets": assets_net,
            "liabilities": liabilities_net,
            "equity": equity_net,
            "difference": equation_diff
        })

    return {
        "balanced": balanced,
        "total_debit": round(total_debit, 2),
        "total_credit": round(total_credit, 2),
        "difference": round(difference, 2),
        "by_type": {
            k: {
                "debit": round(v["debit"], 2),
                "credit": round(v["credit"], 2),
                "net": round(v["net"], 2),
                "count": v["count"]
            }
            for k, v in by_type.items() if v["count"] > 0
        },
        "equation": {
            "assets": round(assets_net, 2),
            "liabilities": round(liabilities_net, 2),
            "equity": round(equity_net, 2),
            "balanced": abs(equation_diff) <= tolerance
        },
        "issues": issues,
        "accounts": account_results,
        "account_count": len(accounts)
    }


# ============================================================
# 调整分录建议
# ============================================================

class AdjustmentType(Enum):
    """调整类型"""
    ACCRUAL = "accrual"           # 应计项目
    DEFERRAL = "deferral"         # 递延项目
    DEPRECIATION = "depreciation" # 折旧
    AMORTIZATION = "amortization" # 摊销
    BAD_DEBT = "bad_debt"         # 坏账
    INVENTORY = "inventory"       # 存货调整
    RECLASSIFICATION = "reclassification"  # 重分类


def adjusting_entries(
    items: List[Dict[str, Any]],
    period_end: str = ""
) -> Dict[str, Any]:
    """
    调整分录建议

    根据期末调整事项生成调整分录。

    Args:
        items: 需要调整的事项列表
            [
                {
                    "type": "accrual",  # 调整类型
                    "description": "计提12月工资",
                    "amount": 500000,
                    "details": {
                        # 根据类型不同，包含不同的详细信息
                    }
                },
                ...
            ]

            支持的调整类型：
            - accrual: 应计费用/收入
                details: {"expense_account": "费用科目", "liability_account": "负债科目"}
            - deferral: 递延费用/收入
                details: {"asset_account": "资产科目", "expense_account": "费用科目",
                         "total_periods": 总期数, "current_period": 当前期数}
            - depreciation: 折旧
                details: {"asset_name": "资产名称", "original_cost": 原值,
                         "salvage_value": 残值, "useful_life": 使用年限,
                         "method": "straight_line/declining"}
            - bad_debt: 坏账
                details: {"ar_balance": 应收余额, "provision_rate": 计提比例}
            - inventory: 存货调整
                details: {"book_value": 账面价值, "market_value": 市场价值}
            - reclassification: 重分类
                details: {"from_account": 原科目, "to_account": 目标科目, "reason": 原因}

        period_end: 期末日期（如 "2024-12-31"）

    Returns:
        {
            "period_end": 期末日期,
            "entries": [调整分录列表],
            "summary": {
                "total_entries": 分录数量,
                "total_debit": 借方总额,
                "total_credit": 贷方总额,
                "by_type": 按类型统计
            }
        }

    Example:
        >>> adjusting_entries([
        ...     {
        ...         "type": "accrual",
        ...         "description": "计提12月工资",
        ...         "amount": 500000,
        ...         "details": {"expense_account": "管理费用-工资", "liability_account": "应付职工薪酬"}
        ...     }
        ... ])
    """
    if not items:
        return {
            "period_end": period_end,
            "entries": [],
            "summary": {
                "total_entries": 0,
                "total_debit": 0,
                "total_credit": 0,
                "by_type": {}
            }
        }

    entries = []
    by_type = {}
    total_debit = 0
    total_credit = 0

    for idx, item in enumerate(items, 1):
        adj_type = item.get("type", "")
        description = item.get("description", "")
        amount = item.get("amount", 0)
        details = item.get("details", {})

        entry = {
            "entry_no": idx,
            "type": adj_type,
            "description": description,
            "lines": [],
            "amount": amount
        }

        # 根据类型生成分录
        if adj_type == "accrual":
            # 应计费用：借 费用，贷 负债
            expense_acc = details.get("expense_account", "费用")
            liability_acc = details.get("liability_account", "应付款项")
            entry["lines"] = [
                {"account": expense_acc, "debit": amount, "credit": 0},
                {"account": liability_acc, "debit": 0, "credit": amount}
            ]

        elif adj_type == "deferral":
            # 递延费用摊销：借 费用，贷 资产
            asset_acc = details.get("asset_account", "待摊费用")
            expense_acc = details.get("expense_account", "费用")
            total_periods = details.get("total_periods", 12)
            current_period = details.get("current_period", 1)

            # 如果未提供amount，按期数计算
            if amount == 0 and "total_amount" in details:
                amount = details["total_amount"] / total_periods

            entry["lines"] = [
                {"account": expense_acc, "debit": amount, "credit": 0},
                {"account": asset_acc, "debit": 0, "credit": amount}
            ]
            entry["note"] = f"第{current_period}/{total_periods}期摊销"
            entry["amount"] = amount

        elif adj_type == "depreciation":
            # 折旧：借 费用，贷 累计折旧
            asset_name = details.get("asset_name", "固定资产")
            original_cost = details.get("original_cost", 0)
            salvage_value = details.get("salvage_value", 0)
            useful_life = details.get("useful_life", 10)
            method = details.get("method", "straight_line")
            periods_per_year = details.get("periods_per_year", 12)

            if method == "straight_line":
                # 直线法：(原值 - 残值) / 使用年限 / 12
                annual_dep = (original_cost - salvage_value) / useful_life if useful_life > 0 else 0
                dep_amount = annual_dep / periods_per_year
            else:
                # 双倍余额递减法
                net_book_value = details.get("net_book_value", original_cost)
                rate = 2 / useful_life if useful_life > 0 else 0
                annual_dep = net_book_value * rate
                dep_amount = annual_dep / periods_per_year

            if amount == 0:
                amount = dep_amount

            entry["lines"] = [
                {"account": f"折旧费用-{asset_name}", "debit": amount, "credit": 0},
                {"account": f"累计折旧-{asset_name}", "debit": 0, "credit": amount}
            ]
            entry["amount"] = round(amount, 2)

        elif adj_type == "amortization":
            # 摊销：借 费用，贷 累计摊销
            asset_name = details.get("asset_name", "无形资产")
            original_cost = details.get("original_cost", 0)
            useful_life = details.get("useful_life", 10)
            periods_per_year = details.get("periods_per_year", 12)

            if amount == 0:
                annual_amort = original_cost / useful_life if useful_life > 0 else 0
                amount = annual_amort / periods_per_year

            entry["lines"] = [
                {"account": f"摊销费用-{asset_name}", "debit": amount, "credit": 0},
                {"account": f"累计摊销-{asset_name}", "debit": 0, "credit": amount}
            ]
            entry["amount"] = round(amount, 2)

        elif adj_type == "bad_debt":
            # 坏账准备：借 信用减值损失，贷 坏账准备
            ar_balance = details.get("ar_balance", 0)
            provision_rate = details.get("provision_rate", 0.05)
            existing_provision = details.get("existing_provision", 0)

            required_provision = ar_balance * provision_rate
            provision_amount = required_provision - existing_provision

            if amount == 0:
                amount = provision_amount

            if amount >= 0:
                entry["lines"] = [
                    {"account": "信用减值损失", "debit": abs(amount), "credit": 0},
                    {"account": "坏账准备", "debit": 0, "credit": abs(amount)}
                ]
            else:
                # 转回
                entry["lines"] = [
                    {"account": "坏账准备", "debit": abs(amount), "credit": 0},
                    {"account": "信用减值损失", "debit": 0, "credit": abs(amount)}
                ]
                entry["note"] = "坏账准备转回"

            entry["amount"] = round(abs(amount), 2)
            entry["calculation"] = {
                "ar_balance": ar_balance,
                "provision_rate": provision_rate,
                "required_provision": round(required_provision, 2),
                "existing_provision": existing_provision,
                "adjustment": round(provision_amount, 2)
            }

        elif adj_type == "inventory":
            # 存货跌价：借 资产减值损失，贷 存货跌价准备
            book_value = details.get("book_value", 0)
            market_value = details.get("market_value", 0)
            existing_provision = details.get("existing_provision", 0)

            required_provision = max(0, book_value - market_value)
            provision_amount = required_provision - existing_provision

            if amount == 0:
                amount = provision_amount

            if amount >= 0:
                entry["lines"] = [
                    {"account": "资产减值损失", "debit": abs(amount), "credit": 0},
                    {"account": "存货跌价准备", "debit": 0, "credit": abs(amount)}
                ]
            else:
                # 转回
                entry["lines"] = [
                    {"account": "存货跌价准备", "debit": abs(amount), "credit": 0},
                    {"account": "资产减值损失", "debit": 0, "credit": abs(amount)}
                ]
                entry["note"] = "存货跌价准备转回"

            entry["amount"] = round(abs(amount), 2)

        elif adj_type == "reclassification":
            # 重分类
            from_acc = details.get("from_account", "原科目")
            to_acc = details.get("to_account", "目标科目")
            reason = details.get("reason", "")

            entry["lines"] = [
                {"account": to_acc, "debit": amount, "credit": 0},
                {"account": from_acc, "debit": 0, "credit": amount}
            ]
            if reason:
                entry["note"] = reason

        else:
            # 自定义分录
            debit_acc = details.get("debit_account", "借方科目")
            credit_acc = details.get("credit_account", "贷方科目")
            entry["lines"] = [
                {"account": debit_acc, "debit": amount, "credit": 0},
                {"account": credit_acc, "debit": 0, "credit": amount}
            ]

        # 累计统计
        entry_debit = sum(line.get("debit", 0) for line in entry["lines"])
        entry_credit = sum(line.get("credit", 0) for line in entry["lines"])
        total_debit += entry_debit
        total_credit += entry_credit

        # 按类型统计
        if adj_type not in by_type:
            by_type[adj_type] = {"count": 0, "amount": 0}
        by_type[adj_type]["count"] += 1
        by_type[adj_type]["amount"] += entry.get("amount", 0)

        entries.append(entry)

    return {
        "period_end": period_end,
        "entries": entries,
        "summary": {
            "total_entries": len(entries),
            "total_debit": round(total_debit, 2),
            "total_credit": round(total_credit, 2),
            "by_type": {k: {"count": v["count"], "amount": round(v["amount"], 2)}
                       for k, v in by_type.items()}
        }
    }


# ============================================================
# 审计抽样
# ============================================================

class SamplingMethod(Enum):
    """抽样方法"""
    RANDOM = "random"           # 简单随机抽样
    SYSTEMATIC = "systematic"   # 系统抽样
    MUS = "mus"                 # 货币单位抽样 (Monetary Unit Sampling)
    STRATIFIED = "stratified"   # 分层抽样


def audit_sampling(
    population: List[Dict[str, Any]],
    method: str = "random",
    sample_size: Optional[int] = None,
    confidence_level: float = 0.95,
    tolerable_error: Optional[float] = None,
    expected_error: float = 0,
    strata_field: Optional[str] = None,
    value_field: str = "amount",
    seed: Optional[int] = None
) -> Dict[str, Any]:
    """
    审计抽样

    支持多种抽样方法用于实质性测试。

    Args:
        population: 总体数据列表
            [
                {"id": "INV001", "amount": 50000, "customer": "客户A", ...},
                ...
            ]
        method: 抽样方法
            - "random": 简单随机抽样
            - "systematic": 系统抽样（每隔N个抽取）
            - "mus": 货币单位抽样（按金额概率抽取）
            - "stratified": 分层抽样
        sample_size: 样本量（可选，未指定时根据参数计算）
        confidence_level: 置信水平（默认95%）
        tolerable_error: 可容忍错报（用于计算样本量）
        expected_error: 预期错报率（默认0）
        strata_field: 分层字段（仅用于分层抽样）
        value_field: 金额字段名（默认"amount"）
        seed: 随机种子（用于复现结果）

    Returns:
        {
            "method": 抽样方法,
            "population_size": 总体规模,
            "population_value": 总体金额,
            "sample_size": 样本量,
            "sample_value": 样本金额,
            "coverage": 金额覆盖率,
            "samples": [抽中的样本],
            "parameters": {抽样参数},
            "high_value_items": [大额项目（全部抽取）]
        }

    Example:
        >>> audit_sampling(
        ...     population=[{"id": f"INV{i}", "amount": i*1000} for i in range(1, 101)],
        ...     method="mus",
        ...     sample_size=20
        ... )
    """
    if seed is not None:
        random.seed(seed)

    if not population:
        return {
            "method": method,
            "population_size": 0,
            "population_value": 0,
            "sample_size": 0,
            "sample_value": 0,
            "coverage": 0,
            "samples": [],
            "parameters": {},
            "high_value_items": []
        }

    # 计算总体统计
    population_size = len(population)
    population_value = sum(item.get(value_field, 0) for item in population)

    # 确定样本量
    if sample_size is None:
        if tolerable_error and tolerable_error > 0:
            # 使用可容忍错报计算样本量
            # 简化公式：n = (置信系数 * 总体) / 可容忍错报
            confidence_factor = {0.90: 2.31, 0.95: 3.0, 0.99: 4.61}.get(confidence_level, 3.0)
            sample_size = int(math.ceil(confidence_factor * population_value / tolerable_error))
            sample_size = min(sample_size, population_size)
        else:
            # 默认样本量：总体的10%，最少25个，最多100个
            sample_size = max(25, min(100, int(population_size * 0.1)))

    sample_size = min(sample_size, population_size)

    # 识别大额项目（超过可容忍错报的项目全部抽取）
    high_value_items = []
    remaining_population = population.copy()

    if tolerable_error and tolerable_error > 0:
        high_value_items = [item for item in population if item.get(value_field, 0) >= tolerable_error]
        remaining_population = [item for item in population if item.get(value_field, 0) < tolerable_error]
        # 调整剩余样本量
        sample_size = max(0, sample_size - len(high_value_items))

    samples = []

    if method == "random":
        # 简单随机抽样
        if remaining_population:
            samples = random.sample(remaining_population, min(sample_size, len(remaining_population)))

    elif method == "systematic":
        # 系统抽样
        if remaining_population and sample_size > 0:
            interval = len(remaining_population) // sample_size
            interval = max(1, interval)
            start = random.randint(0, interval - 1) if interval > 1 else 0
            indices = list(range(start, len(remaining_population), interval))[:sample_size]
            samples = [remaining_population[i] for i in indices]

    elif method == "mus":
        # 货币单位抽样
        if remaining_population and sample_size > 0:
            total_value = sum(abs(item.get(value_field, 0)) for item in remaining_population)
            if total_value > 0:
                interval = total_value / sample_size
                start = random.uniform(0, interval)

                selected_indices = set()
                cumulative = 0
                sample_point = start

                for i, item in enumerate(remaining_population):
                    item_value = abs(item.get(value_field, 0))
                    cumulative += item_value

                    while sample_point <= cumulative and len(selected_indices) < sample_size:
                        selected_indices.add(i)
                        sample_point += interval

                samples = [remaining_population[i] for i in sorted(selected_indices)]

    elif method == "stratified":
        # 分层抽样
        if remaining_population and sample_size > 0:
            # 按字段或金额范围分层
            if strata_field:
                strata = {}
                for item in remaining_population:
                    stratum = item.get(strata_field, "其他")
                    if stratum not in strata:
                        strata[stratum] = []
                    strata[stratum].append(item)
            else:
                # 按金额分层：小额、中额、大额
                strata = {"小额": [], "中额": [], "大额": []}
                if remaining_population:
                    values = [item.get(value_field, 0) for item in remaining_population]
                    q1, q3 = sorted(values)[len(values)//4], sorted(values)[3*len(values)//4]
                    for item in remaining_population:
                        v = item.get(value_field, 0)
                        if v <= q1:
                            strata["小额"].append(item)
                        elif v <= q3:
                            strata["中额"].append(item)
                        else:
                            strata["大额"].append(item)

            # 按层比例抽样
            total_in_strata = sum(len(s) for s in strata.values())
            for stratum_name, stratum_items in strata.items():
                if stratum_items:
                    stratum_sample_size = max(1, int(sample_size * len(stratum_items) / total_in_strata))
                    stratum_sample_size = min(stratum_sample_size, len(stratum_items))
                    samples.extend(random.sample(stratum_items, stratum_sample_size))

    # 合并大额项目和抽样结果
    all_samples = high_value_items + samples

    # 计算样本统计
    sample_value = sum(item.get(value_field, 0) for item in all_samples)
    coverage = sample_value / population_value if population_value > 0 else 0

    return {
        "method": method,
        "population_size": population_size,
        "population_value": round(population_value, 2),
        "sample_size": len(all_samples),
        "sample_value": round(sample_value, 2),
        "coverage": round(coverage, 4),
        "samples": all_samples,
        "parameters": {
            "confidence_level": confidence_level,
            "tolerable_error": tolerable_error,
            "expected_error": expected_error,
            "seed": seed
        },
        "high_value_items": high_value_items,
        "sampling_interval": round(population_value / sample_size, 2) if sample_size > 0 else 0
    }


# ============================================================
# 合并报表抵消
# ============================================================

def consolidation(
    parent: Dict[str, Any],
    subsidiaries: List[Dict[str, Any]],
    intercompany: Optional[List[Dict[str, Any]]] = None,
    investments: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    合并报表抵消

    计算合并报表所需的抵消分录。

    Args:
        parent: 母公司报表数据
            {
                "name": "母公司",
                "assets": 总资产,
                "liabilities": 总负债,
                "equity": 所有者权益,
                "revenue": 收入,
                "expenses": 费用,
                "net_income": 净利润,
                "accounts": {  # 明细科目（可选）
                    "long_term_investment": 长期股权投资,
                    "accounts_receivable": 应收账款,
                    "accounts_payable": 应付账款,
                    ...
                }
            }
        subsidiaries: 子公司报表数据列表
            [
                {
                    "name": "子公司A",
                    "ownership": 0.8,  # 持股比例
                    "assets": 总资产,
                    "liabilities": 总负债,
                    "equity": 所有者权益,
                    "paid_in_capital": 实收资本,
                    "capital_reserve": 资本公积,
                    "retained_earnings": 留存收益,
                    "revenue": 收入,
                    "expenses": 费用,
                    "net_income": 净利润,
                    "fair_value_adjustment": 公允价值调整（可选）
                },
                ...
            ]
        intercompany: 内部交易列表
            [
                {
                    "type": "sale",  # sale/service/loan/dividend
                    "from": "母公司",
                    "to": "子公司A",
                    "amount": 金额,
                    "unrealized_profit": 未实现利润（存货中）,
                    "details": {...}
                },
                ...
            ]
        investments: 投资信息（用于抵消长期股权投资）
            [
                {
                    "subsidiary": "子公司A",
                    "investment_cost": 投资成本,
                    "acquisition_date": "2020-01-01",
                    "goodwill": 商誉（已计算）
                },
                ...
            ]

    Returns:
        {
            "eliminations": [抵消分录列表],
            "consolidated": {合并后金额},
            "minority_interest": {少数股东权益},
            "goodwill": 商誉总额,
            "summary": {汇总信息}
        }

    Example:
        >>> consolidation(
        ...     parent={"name": "母公司", "assets": 10000000, "liabilities": 4000000, "equity": 6000000},
        ...     subsidiaries=[
        ...         {"name": "子公司A", "ownership": 0.8, "assets": 5000000,
        ...          "liabilities": 2000000, "equity": 3000000}
        ...     ]
        ... )
    """
    eliminations = []
    elimination_no = 0

    # 汇总数据
    total_assets = parent.get("assets", 0)
    total_liabilities = parent.get("liabilities", 0)
    total_equity = parent.get("equity", 0)
    total_revenue = parent.get("revenue", 0)
    total_expenses = parent.get("expenses", 0)
    total_net_income = parent.get("net_income", 0)

    total_goodwill = 0
    total_minority_interest = 0
    minority_income = 0

    # 处理每个子公司
    for sub in subsidiaries:
        sub_name = sub.get("name", "子公司")
        ownership = sub.get("ownership", 1.0)
        minority_rate = 1 - ownership

        sub_assets = sub.get("assets", 0)
        sub_liabilities = sub.get("liabilities", 0)
        sub_equity = sub.get("equity", 0)
        sub_revenue = sub.get("revenue", 0)
        sub_expenses = sub.get("expenses", 0)
        sub_net_income = sub.get("net_income", 0)

        # 公允价值调整
        fv_adjustment = sub.get("fair_value_adjustment", 0)

        # 加总子公司报表
        total_assets += sub_assets + fv_adjustment
        total_liabilities += sub_liabilities
        total_revenue += sub_revenue
        total_expenses += sub_expenses
        total_net_income += sub_net_income

        # 1. 抵消长期股权投资与子公司权益
        investment_info = None
        if investments:
            investment_info = next((inv for inv in investments if inv.get("subsidiary") == sub_name), None)

        if investment_info:
            investment_cost = investment_info.get("investment_cost", 0)
            goodwill = investment_info.get("goodwill", 0)
        else:
            # 估算投资成本和商誉
            investment_cost = sub_equity * ownership
            goodwill = 0

        # 计算少数股东权益
        minority_equity = sub_equity * minority_rate
        minority_ni = sub_net_income * minority_rate

        total_minority_interest += minority_equity
        minority_income += minority_ni
        total_goodwill += goodwill

        elimination_no += 1
        eliminations.append({
            "entry_no": elimination_no,
            "type": "investment_equity",
            "description": f"抵消母公司对{sub_name}的长期股权投资",
            "lines": [
                {"account": f"实收资本-{sub_name}", "debit": sub.get("paid_in_capital", sub_equity * 0.5), "credit": 0},
                {"account": f"资本公积-{sub_name}", "debit": sub.get("capital_reserve", sub_equity * 0.2), "credit": 0},
                {"account": f"留存收益-{sub_name}", "debit": sub.get("retained_earnings", sub_equity * 0.3), "credit": 0},
                {"account": "商誉", "debit": goodwill, "credit": 0} if goodwill > 0 else None,
                {"account": f"长期股权投资-{sub_name}", "debit": 0, "credit": investment_cost},
                {"account": "少数股东权益", "debit": 0, "credit": minority_equity}
            ],
            "subsidiary": sub_name,
            "ownership": ownership
        })
        # 过滤掉None
        eliminations[-1]["lines"] = [l for l in eliminations[-1]["lines"] if l is not None]

        # 2. 抵消少数股东损益
        if minority_ni != 0:
            elimination_no += 1
            eliminations.append({
                "entry_no": elimination_no,
                "type": "minority_income",
                "description": f"确认{sub_name}少数股东损益",
                "lines": [
                    {"account": "少数股东损益", "debit": minority_ni if minority_ni > 0 else 0,
                     "credit": -minority_ni if minority_ni < 0 else 0},
                    {"account": "少数股东权益", "debit": 0 if minority_ni > 0 else -minority_ni,
                     "credit": minority_ni if minority_ni > 0 else 0}
                ],
                "subsidiary": sub_name,
                "amount": minority_ni
            })

    # 3. 处理内部交易抵消
    intercompany_eliminations = 0
    unrealized_profit_total = 0

    if intercompany:
        for txn in intercompany:
            txn_type = txn.get("type", "sale")
            from_entity = txn.get("from", "")
            to_entity = txn.get("to", "")
            amount = txn.get("amount", 0)
            unrealized_profit = txn.get("unrealized_profit", 0)

            elimination_no += 1
            intercompany_eliminations += amount

            if txn_type == "sale":
                # 内部销售抵消
                eliminations.append({
                    "entry_no": elimination_no,
                    "type": "intercompany_sale",
                    "description": f"抵消{from_entity}向{to_entity}的内部销售",
                    "lines": [
                        {"account": "营业收入", "debit": amount, "credit": 0},
                        {"account": "营业成本", "debit": 0, "credit": amount - unrealized_profit},
                        {"account": "存货", "debit": 0, "credit": unrealized_profit} if unrealized_profit > 0 else None
                    ],
                    "amount": amount
                })
                eliminations[-1]["lines"] = [l for l in eliminations[-1]["lines"] if l is not None]

                # 调整合并金额
                total_revenue -= amount
                total_expenses -= (amount - unrealized_profit)
                total_assets -= unrealized_profit
                unrealized_profit_total += unrealized_profit

            elif txn_type == "service":
                # 内部服务抵消
                eliminations.append({
                    "entry_no": elimination_no,
                    "type": "intercompany_service",
                    "description": f"抵消{from_entity}向{to_entity}的内部服务",
                    "lines": [
                        {"account": "营业收入", "debit": amount, "credit": 0},
                        {"account": "管理费用/销售费用", "debit": 0, "credit": amount}
                    ],
                    "amount": amount
                })
                total_revenue -= amount
                total_expenses -= amount

            elif txn_type == "dividend":
                # 内部股利抵消
                eliminations.append({
                    "entry_no": elimination_no,
                    "type": "intercompany_dividend",
                    "description": f"抵消{from_entity}收到{to_entity}的股利",
                    "lines": [
                        {"account": "投资收益", "debit": amount, "credit": 0},
                        {"account": "利润分配-应付股利", "debit": 0, "credit": amount}
                    ],
                    "amount": amount
                })
                # 股利已在净利润中反映

            elif txn_type == "loan":
                # 内部借款抵消
                interest = txn.get("interest", 0)
                eliminations.append({
                    "entry_no": elimination_no,
                    "type": "intercompany_loan",
                    "description": f"抵消{from_entity}与{to_entity}的内部借款",
                    "lines": [
                        {"account": "其他应付款/短期借款", "debit": amount, "credit": 0},
                        {"account": "其他应收款/应收利息", "debit": 0, "credit": amount},
                        {"account": "利息收入", "debit": interest, "credit": 0} if interest > 0 else None,
                        {"account": "利息支出", "debit": 0, "credit": interest} if interest > 0 else None
                    ],
                    "amount": amount
                })
                eliminations[-1]["lines"] = [l for l in eliminations[-1]["lines"] if l is not None]
                total_assets -= amount
                total_liabilities -= amount

            elif txn_type == "receivable_payable":
                # 应收应付抵消
                eliminations.append({
                    "entry_no": elimination_no,
                    "type": "intercompany_ar_ap",
                    "description": f"抵消{from_entity}与{to_entity}的内部往来",
                    "lines": [
                        {"account": "应付账款", "debit": amount, "credit": 0},
                        {"account": "应收账款", "debit": 0, "credit": amount}
                    ],
                    "amount": amount
                })
                total_assets -= amount
                total_liabilities -= amount

    # 计算合并后金额
    # 抵消长期股权投资
    parent_investments = parent.get("accounts", {}).get("long_term_investment", 0)
    consolidated_assets = total_assets - parent_investments + total_goodwill

    # 抵消内部往来后的净权益（归属于母公司）
    parent_equity = total_equity + total_net_income - minority_income - unrealized_profit_total

    return {
        "eliminations": eliminations,
        "consolidated": {
            "assets": round(consolidated_assets, 2),
            "liabilities": round(total_liabilities, 2),
            "equity": round(parent_equity, 2),
            "revenue": round(total_revenue, 2),
            "expenses": round(total_expenses, 2),
            "net_income": round(total_net_income - minority_income, 2),
            "goodwill": round(total_goodwill, 2)
        },
        "minority_interest": {
            "equity": round(total_minority_interest, 2),
            "income": round(minority_income, 2)
        },
        "goodwill": round(total_goodwill, 2),
        "summary": {
            "subsidiaries_count": len(subsidiaries),
            "elimination_entries": len(eliminations),
            "intercompany_eliminated": round(intercompany_eliminations, 2),
            "unrealized_profit_eliminated": round(unrealized_profit_total, 2)
        }
    }


# ============================================================
# 工具注册（供 LLM 发现）
# ============================================================

AUDIT_TOOLS = {
    "trial_balance": {
        "function": trial_balance,
        "description": "试算平衡检查，验证借贷平衡和会计恒等式",
        "parameters": ["accounts", "tolerance"]
    },
    "adjusting_entries": {
        "function": adjusting_entries,
        "description": "调整分录建议，生成期末调整分录",
        "parameters": ["items", "period_end"]
    },
    "audit_sampling": {
        "function": audit_sampling,
        "description": "审计抽样，支持随机/系统/MUS/分层抽样",
        "parameters": ["population", "method", "sample_size", "confidence_level", "tolerable_error"]
    },
    "consolidation": {
        "function": consolidation,
        "description": "合并报表抵消，计算抵消分录和合并金额",
        "parameters": ["parent", "subsidiaries", "intercompany", "investments"]
    }
}
