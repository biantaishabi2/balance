# -*- coding: utf-8 -*-
"""
budget_tools.py - 预算分析原子工具

提供预算差异分析、弹性预算、滚动预测、趋势分析等功能。
设计为无状态的原子函数，供 LLM 灵活调用组合。
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import statistics


# ============================================================
# 数据类
# ============================================================

@dataclass
class VarianceItem:
    """差异分析项"""
    account: str
    budget: float
    actual: float
    variance: float
    variance_pct: float
    is_favorable: bool
    is_significant: bool


@dataclass
class FlexBudgetItem:
    """弹性预算项"""
    account: str
    original_budget: float
    flexed_budget: float
    actual: float
    volume_variance: float
    efficiency_variance: float


# ============================================================
# 预算差异分析
# ============================================================

def variance_analysis(
    budget: Dict[str, float],
    actual: Dict[str, float],
    threshold: float = 0.10,
    account_types: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    预算 vs 实际差异分析

    Args:
        budget: 预算数据，格式 {"科目名": 金额}
        actual: 实际数据，格式 {"科目名": 金额}
        threshold: 重大差异阈值，默认10%
        account_types: 科目类型，用于判断有利/不利
                      {"revenue": ["收入", "销售"], "expense": ["成本", "费用"]}

    Returns:
        {
            "variances": [...],           # 各科目差异列表
            "summary": {
                "total_budget": 总预算,
                "total_actual": 总实际,
                "total_variance": 总差异,
                "total_variance_pct": 差异百分比
            },
            "significant_items": [...],   # 重大差异项
            "favorable_count": 有利差异数,
            "unfavorable_count": 不利差异数
        }

    Example:
        >>> variance_analysis(
        ...     budget={"收入": 1000, "成本": 600, "费用": 200},
        ...     actual={"收入": 1100, "成本": 650, "费用": 180},
        ...     threshold=0.05
        ... )
    """
    if account_types is None:
        account_types = {
            "revenue": ["收入", "销售", "revenue", "sales", "income"],
            "expense": ["成本", "费用", "cost", "expense", "支出"]
        }

    def is_revenue_account(name: str) -> bool:
        name_lower = name.lower()
        return any(kw in name_lower for kw in account_types.get("revenue", []))

    def is_expense_account(name: str) -> bool:
        name_lower = name.lower()
        return any(kw in name_lower for kw in account_types.get("expense", []))

    # 合并所有科目
    all_accounts = set(budget.keys()) | set(actual.keys())

    variances = []
    total_budget = 0
    total_actual = 0
    favorable_count = 0
    unfavorable_count = 0

    for account in sorted(all_accounts):
        b = budget.get(account, 0)
        a = actual.get(account, 0)
        variance = a - b
        variance_pct = variance / b if b != 0 else (float('inf') if variance != 0 else 0)

        # 判断有利/不利
        if is_revenue_account(account):
            # 收入类：实际>预算 有利
            is_favorable = variance >= 0
        elif is_expense_account(account):
            # 费用类：实际<预算 有利
            is_favorable = variance <= 0
        else:
            # 其他：默认正差异有利
            is_favorable = variance >= 0

        is_significant = abs(variance_pct) >= threshold if variance_pct != float('inf') else True

        variances.append({
            "account": account,
            "budget": b,
            "actual": a,
            "variance": variance,
            "variance_pct": variance_pct if variance_pct != float('inf') else None,
            "is_favorable": is_favorable,
            "is_significant": is_significant
        })

        total_budget += b
        total_actual += a

        if is_favorable:
            favorable_count += 1
        else:
            unfavorable_count += 1

    total_variance = total_actual - total_budget
    total_variance_pct = total_variance / total_budget if total_budget != 0 else 0

    significant_items = [v for v in variances if v["is_significant"]]

    return {
        "variances": variances,
        "summary": {
            "total_budget": total_budget,
            "total_actual": total_actual,
            "total_variance": total_variance,
            "total_variance_pct": total_variance_pct
        },
        "significant_items": significant_items,
        "favorable_count": favorable_count,
        "unfavorable_count": unfavorable_count,
        "threshold": threshold
    }


# ============================================================
# 弹性预算
# ============================================================

def flex_budget(
    original_budget: Dict[str, float],
    budget_volume: float,
    actual_volume: float,
    cost_behavior: Dict[str, str],
    actual: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    弹性预算计算

    根据实际业务量调整预算，区分固定成本和变动成本。

    Args:
        original_budget: 原预算数据 {"科目": 金额}
        budget_volume: 预算业务量
        actual_volume: 实际业务量
        cost_behavior: 成本性态 {"科目": "fixed"/"variable"/"mixed:0.6"}
                       mixed:0.6 表示60%是变动成本
        actual: 实际数据（可选，用于计算效率差异）

    Returns:
        {
            "flexed_budget": {...},       # 调整后预算
            "volume_ratio": 业务量比率,
            "adjustments": [...],         # 各科目调整明细
            "variances": {                # 差异分解（如有实际数据）
                "volume_variance": 业务量差异,
                "efficiency_variance": 效率差异
            }
        }

    Example:
        >>> flex_budget(
        ...     original_budget={"材料": 100, "人工": 80, "折旧": 50},
        ...     budget_volume=1000,
        ...     actual_volume=1200,
        ...     cost_behavior={"材料": "variable", "人工": "mixed:0.7", "折旧": "fixed"}
        ... )
    """
    volume_ratio = actual_volume / budget_volume if budget_volume != 0 else 1

    flexed_budget = {}
    adjustments = []

    for account, amount in original_budget.items():
        behavior = cost_behavior.get(account, "fixed")

        if behavior == "variable":
            # 完全变动成本
            flexed = amount * volume_ratio
            variable_portion = 1.0
        elif behavior == "fixed":
            # 完全固定成本
            flexed = amount
            variable_portion = 0.0
        elif behavior.startswith("mixed:"):
            # 混合成本
            variable_portion = float(behavior.split(":")[1])
            fixed_part = amount * (1 - variable_portion)
            variable_part = amount * variable_portion * volume_ratio
            flexed = fixed_part + variable_part
        else:
            # 默认固定
            flexed = amount
            variable_portion = 0.0

        flexed_budget[account] = flexed
        adjustments.append({
            "account": account,
            "original": amount,
            "flexed": flexed,
            "adjustment": flexed - amount,
            "behavior": behavior,
            "variable_portion": variable_portion
        })

    result = {
        "flexed_budget": flexed_budget,
        "volume_ratio": volume_ratio,
        "budget_volume": budget_volume,
        "actual_volume": actual_volume,
        "adjustments": adjustments,
        "total_original": sum(original_budget.values()),
        "total_flexed": sum(flexed_budget.values())
    }

    # 如果提供了实际数据，计算差异分解
    if actual is not None:
        total_original = sum(original_budget.values())
        total_flexed = sum(flexed_budget.values())
        total_actual = sum(actual.get(k, 0) for k in original_budget.keys())

        # 业务量差异 = 弹性预算 - 原预算
        volume_variance = total_flexed - total_original
        # 效率差异 = 实际 - 弹性预算
        efficiency_variance = total_actual - total_flexed

        result["variances"] = {
            "volume_variance": volume_variance,
            "efficiency_variance": efficiency_variance,
            "total_variance": total_actual - total_original
        }
        result["actual"] = actual
        result["total_actual"] = total_actual

    return result


# ============================================================
# 滚动预测
# ============================================================

def rolling_forecast(
    historical_data: List[Dict[str, Any]],
    periods: int = 3,
    method: str = "moving_avg",
    window: int = 3
) -> Dict[str, Any]:
    """
    滚动预测

    基于历史数据生成未来N期预测。

    Args:
        historical_data: 历史数据列表
            [{"period": "2024-01", "revenue": 1000, "cost": 600}, ...]
        periods: 预测期数（默认3期）
        method: 预测方法
            - "moving_avg": 移动平均（默认）
            - "weighted_avg": 加权移动平均（近期权重更高）
            - "linear": 线性回归
            - "growth_rate": 基于平均增长率
        window: 移动平均窗口大小（默认3期）

    Returns:
        {
            "forecast": [...],            # 预测数据
            "method": 使用的方法,
            "metrics": [...],             # 预测的指标列表
            "trend": {                    # 趋势信息
                "direction": "up"/"down"/"stable",
                "avg_growth_rate": 平均增长率
            }
        }

    Example:
        >>> rolling_forecast(
        ...     historical_data=[
        ...         {"period": "2024-01", "revenue": 1000},
        ...         {"period": "2024-02", "revenue": 1050},
        ...         {"period": "2024-03", "revenue": 1100}
        ...     ],
        ...     periods=3,
        ...     method="moving_avg"
        ... )
    """
    if not historical_data:
        return {"error": "历史数据不能为空"}

    if len(historical_data) < 2:
        return {"error": "历史数据至少需要2期"}

    # 识别数值型指标
    sample = historical_data[0]
    metrics = [k for k, v in sample.items() if isinstance(v, (int, float)) and k != "period"]

    # 提取各指标的历史值
    metric_values = {m: [d.get(m, 0) for d in historical_data] for m in metrics}

    forecast = []
    trend_info = {}

    # 生成预测期的名称
    last_period = historical_data[-1].get("period", f"T{len(historical_data)}")

    for m in metrics:
        values = metric_values[m]

        if method == "moving_avg":
            # 简单移动平均
            predictions = _moving_average_forecast(values, periods, window)
        elif method == "weighted_avg":
            # 加权移动平均
            predictions = _weighted_average_forecast(values, periods, window)
        elif method == "linear":
            # 线性回归
            predictions = _linear_forecast(values, periods)
        elif method == "growth_rate":
            # 增长率法
            predictions = _growth_rate_forecast(values, periods)
        else:
            predictions = _moving_average_forecast(values, periods, window)

        # 计算趋势
        if len(values) >= 2:
            growth_rates = [(values[i] - values[i-1]) / values[i-1]
                          for i in range(1, len(values)) if values[i-1] != 0]
            avg_growth = statistics.mean(growth_rates) if growth_rates else 0

            if avg_growth > 0.02:
                direction = "up"
            elif avg_growth < -0.02:
                direction = "down"
            else:
                direction = "stable"

            trend_info[m] = {
                "direction": direction,
                "avg_growth_rate": avg_growth
            }

        metric_values[m + "_forecast"] = predictions

    # 组装预测结果
    for i in range(periods):
        period_name = f"F{i+1}"  # Forecast period 1, 2, 3...
        forecast_item = {"period": period_name}
        for m in metrics:
            forecast_item[m] = metric_values[m + "_forecast"][i]
        forecast.append(forecast_item)

    return {
        "forecast": forecast,
        "method": method,
        "window": window if method in ["moving_avg", "weighted_avg"] else None,
        "metrics": metrics,
        "historical_periods": len(historical_data),
        "forecast_periods": periods,
        "trend": trend_info
    }


def _moving_average_forecast(values: List[float], periods: int, window: int) -> List[float]:
    """简单移动平均预测"""
    predictions = []
    extended = values.copy()

    for _ in range(periods):
        # 取最近window期的平均
        recent = extended[-window:] if len(extended) >= window else extended
        pred = sum(recent) / len(recent)
        predictions.append(pred)
        extended.append(pred)

    return predictions


def _weighted_average_forecast(values: List[float], periods: int, window: int) -> List[float]:
    """加权移动平均预测（近期权重更高）"""
    predictions = []
    extended = values.copy()

    for _ in range(periods):
        recent = extended[-window:] if len(extended) >= window else extended
        n = len(recent)
        weights = list(range(1, n + 1))  # 1, 2, 3, ...
        weighted_sum = sum(v * w for v, w in zip(recent, weights))
        weight_total = sum(weights)
        pred = weighted_sum / weight_total
        predictions.append(pred)
        extended.append(pred)

    return predictions


def _linear_forecast(values: List[float], periods: int) -> List[float]:
    """线性回归预测"""
    n = len(values)
    x = list(range(n))

    # 计算斜率和截距
    x_mean = sum(x) / n
    y_mean = sum(values) / n

    numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
    denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

    slope = numerator / denominator if denominator != 0 else 0
    intercept = y_mean - slope * x_mean

    # 预测
    predictions = [slope * (n + i) + intercept for i in range(periods)]
    return predictions


def _growth_rate_forecast(values: List[float], periods: int) -> List[float]:
    """基于平均增长率预测"""
    if len(values) < 2:
        return [values[-1]] * periods

    # 计算平均增长率
    growth_rates = [(values[i] - values[i-1]) / values[i-1]
                   for i in range(1, len(values)) if values[i-1] != 0]
    avg_growth = statistics.mean(growth_rates) if growth_rates else 0

    predictions = []
    last_value = values[-1]
    for _ in range(periods):
        pred = last_value * (1 + avg_growth)
        predictions.append(pred)
        last_value = pred

    return predictions


# ============================================================
# 趋势分析
# ============================================================

def trend_analysis(
    periods_data: List[Dict[str, Any]],
    base_period: int = 0,
    metrics: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    多期趋势分析

    分析多期财务数据的变化趋势和增长率。

    Args:
        periods_data: 多期数据列表
            [{"period": "2022", "revenue": 1000}, {"period": "2023", "revenue": 1100}, ...]
        base_period: 基期索引，默认0（第一期）
        metrics: 要分析的指标列表（可选，默认分析所有数值型字段）

    Returns:
        {
            "analysis": {
                "revenue": {
                    "values": [1000, 1100, 1200],
                    "yoy_growth": [null, 0.10, 0.09],      # 同比增长
                    "indexed": [100, 110, 120],            # 以基期为100
                    "cagr": 0.095,                         # 复合增长率
                    "trend": "up",
                    "volatility": 0.01
                },
                ...
            },
            "periods": ["2022", "2023", "2024"],
            "base_period": "2022"
        }

    Example:
        >>> trend_analysis([
        ...     {"period": "2022", "revenue": 1000, "profit": 100},
        ...     {"period": "2023", "revenue": 1100, "profit": 120},
        ...     {"period": "2024", "revenue": 1200, "profit": 150}
        ... ])
    """
    if not periods_data:
        return {"error": "数据不能为空"}

    if len(periods_data) < 2:
        return {"error": "至少需要2期数据进行趋势分析"}

    # 识别要分析的指标
    sample = periods_data[0]
    if metrics is None:
        metrics = [k for k, v in sample.items() if isinstance(v, (int, float)) and k != "period"]

    periods = [d.get("period", f"T{i}") for i, d in enumerate(periods_data)]
    base_period_name = periods[base_period]

    analysis = {}

    for metric in metrics:
        values = [d.get(metric, 0) for d in periods_data]
        base_value = values[base_period]

        # 同比增长率
        yoy_growth = [None]  # 第一期无同比
        for i in range(1, len(values)):
            if values[i-1] != 0:
                yoy_growth.append((values[i] - values[i-1]) / values[i-1])
            else:
                yoy_growth.append(None)

        # 以基期为100的指数
        if base_value != 0:
            indexed = [v / base_value * 100 for v in values]
        else:
            indexed = [0] * len(values)

        # 复合增长率 CAGR
        n = len(values) - 1
        if n > 0 and values[0] != 0 and values[-1] > 0 and values[0] > 0:
            cagr = (values[-1] / values[0]) ** (1 / n) - 1
        else:
            cagr = None

        # 趋势方向
        valid_growth = [g for g in yoy_growth if g is not None]
        if valid_growth:
            avg_growth = statistics.mean(valid_growth)
            if avg_growth > 0.02:
                trend = "up"
            elif avg_growth < -0.02:
                trend = "down"
            else:
                trend = "stable"

            # 波动性（增长率的标准差）
            volatility = statistics.stdev(valid_growth) if len(valid_growth) > 1 else 0
        else:
            trend = "unknown"
            avg_growth = 0
            volatility = 0

        analysis[metric] = {
            "values": values,
            "yoy_growth": yoy_growth,
            "indexed": indexed,
            "cagr": cagr,
            "avg_growth": avg_growth,
            "trend": trend,
            "volatility": volatility,
            "min": min(values),
            "max": max(values)
        }

    return {
        "analysis": analysis,
        "periods": periods,
        "base_period": base_period_name,
        "num_periods": len(periods),
        "metrics_analyzed": metrics
    }


# ============================================================
# 工具注册（供 LLM 发现）
# ============================================================

BUDGET_TOOLS = {
    "variance_analysis": {
        "function": variance_analysis,
        "description": "预算 vs 实际差异分析，识别重大差异项",
        "parameters": ["budget", "actual", "threshold", "account_types"]
    },
    "flex_budget": {
        "function": flex_budget,
        "description": "弹性预算计算，根据业务量调整预算",
        "parameters": ["original_budget", "budget_volume", "actual_volume", "cost_behavior", "actual"]
    },
    "rolling_forecast": {
        "function": rolling_forecast,
        "description": "滚动预测，基于历史数据预测未来",
        "parameters": ["historical_data", "periods", "method", "window"]
    },
    "trend_analysis": {
        "function": trend_analysis,
        "description": "多期趋势分析，计算增长率和CAGR",
        "parameters": ["periods_data", "base_period", "metrics"]
    }
}
