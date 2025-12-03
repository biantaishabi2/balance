# -*- coding: utf-8 -*-
"""
DCF 原子工具

独立的、可组合的DCF估值计算工具，供LLM灵活调用。

设计原则:
1. 每个工具独立运行，不依赖类状态
2. 输入输出清晰（dict格式，可序列化为JSON）
3. 可自由组合，LLM可以跳过、替换、插入任何步骤
4. 保留计算追溯信息

工具清单:
- calc_capm: CAPM计算股权成本
- calc_wacc: 加权平均资本成本
- calc_fcff: 企业自由现金流
- calc_terminal_value: 终值计算（支持永续增长法和退出倍数法）
- calc_enterprise_value: 企业价值
- calc_equity_value: 股权价值
- calc_per_share_value: 每股价值
- dcf_sensitivity: 敏感性分析矩阵
- dcf_quick_valuate: 快捷估值入口
"""

from typing import Dict, List, Any, Optional, Union


def calc_capm(
    risk_free_rate: float,
    beta: float,
    market_risk_premium: float,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具1: CAPM计算股权成本

    公式: Re = Rf + β × MRP

    Args:
        risk_free_rate: 无风险利率（如10年期国债收益率）
        beta: 贝塔系数（系统性风险）
        market_risk_premium: 市场风险溢价 (Rm - Rf)
        source: 计算来源标记 ("tool" 或 "llm_override")

    Returns:
        dict: {
            "value": 股权成本,
            "formula": 公式说明,
            "inputs": 输入参数,
            "source": 计算来源
        }

    示例:
        >>> result = calc_capm(0.03, 1.2, 0.06)
        >>> round(result["value"], 3)
        0.102
    """
    value = risk_free_rate + beta * market_risk_premium

    return {
        "value": value,
        "formula": "Rf + β × MRP",
        "inputs": {
            "risk_free_rate": risk_free_rate,
            "beta": beta,
            "market_risk_premium": market_risk_premium
        },
        "source": source
    }


def calc_wacc(
    cost_of_equity: float,
    cost_of_debt: float,
    tax_rate: float,
    debt_ratio: float,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具2: 加权平均资本成本 (WACC)

    公式: WACC = E/(D+E) × Re + D/(D+E) × Rd × (1-t)

    Args:
        cost_of_equity: 股权成本 (Re)
        cost_of_debt: 债务成本 (Rd)
        tax_rate: 税率
        debt_ratio: 负债率 D/(D+E)
        source: 计算来源标记

    Returns:
        dict: {
            "value": WACC,
            "formula": 公式说明,
            "inputs": 输入参数,
            "source": 计算来源
        }

    示例:
        >>> result = calc_wacc(0.102, 0.05, 0.25, 0.30)
        >>> round(result["value"], 4)
        0.0826
    """
    equity_ratio = 1 - debt_ratio
    after_tax_debt_cost = cost_of_debt * (1 - tax_rate)
    value = equity_ratio * cost_of_equity + debt_ratio * after_tax_debt_cost

    return {
        "value": value,
        "formula": "E/(D+E) × Re + D/(D+E) × Rd × (1-t)",
        "inputs": {
            "cost_of_equity": cost_of_equity,
            "cost_of_debt": cost_of_debt,
            "tax_rate": tax_rate,
            "debt_ratio": debt_ratio,
            "equity_ratio": equity_ratio,
            "after_tax_debt_cost": after_tax_debt_cost
        },
        "source": source
    }


def calc_fcff(
    ebit: float,
    tax_rate: float,
    depreciation: float,
    capex: float,
    delta_nwc: float,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具3: 企业自由现金流 (FCFF)

    公式: FCFF = EBIT × (1-t) + D&A - CapEx - ΔNWC

    Args:
        ebit: 息税前利润
        tax_rate: 税率
        depreciation: 折旧与摊销
        capex: 资本支出
        delta_nwc: 净营运资本变动
        source: 计算来源标记

    Returns:
        dict: {
            "value": FCFF,
            "formula": 公式说明,
            "inputs": 输入参数,
            "source": 计算来源
        }

    示例:
        >>> result = calc_fcff(100_000_000, 0.25, 15_000_000, 20_000_000, 5_000_000)
        >>> result["value"]
        65000000.0
    """
    nopat = ebit * (1 - tax_rate)
    value = nopat + depreciation - capex - delta_nwc

    return {
        "value": value,
        "formula": "EBIT × (1-t) + D&A - CapEx - ΔNWC",
        "inputs": {
            "ebit": ebit,
            "tax_rate": tax_rate,
            "nopat": nopat,
            "depreciation": depreciation,
            "capex": capex,
            "delta_nwc": delta_nwc
        },
        "source": source
    }


def calc_terminal_value(
    method: str,
    final_fcf: Optional[float] = None,
    wacc: Optional[float] = None,
    terminal_growth: Optional[float] = None,
    final_ebitda: Optional[float] = None,
    exit_multiple: Optional[float] = None,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具4: 终值计算（支持两种方法）

    方法1 - 永续增长法:
        公式: TV = FCF × (1+g) / (WACC - g)
        需要: final_fcf, wacc, terminal_growth

    方法2 - 退出倍数法:
        公式: TV = EBITDA × Exit Multiple
        需要: final_ebitda, exit_multiple

    Args:
        method: 计算方法 ("perpetual" 或 "multiple")
        final_fcf: 预测期最后一年的FCF
        wacc: 加权平均资本成本
        terminal_growth: 永续增长率
        final_ebitda: 预测期最后一年的EBITDA
        exit_multiple: 退出倍数
        source: 计算来源标记

    Returns:
        dict: {
            "value": 终值,
            "formula": 公式说明,
            "inputs": 输入参数,
            "source": 计算来源
        }

    示例:
        >>> # 永续增长法
        >>> result = calc_terminal_value("perpetual", final_fcf=80_000_000, wacc=0.09, terminal_growth=0.02)
        >>> result["value"]
        1165714285.7142856

        >>> # 退出倍数法
        >>> result = calc_terminal_value("multiple", final_ebitda=120_000_000, exit_multiple=8.0)
        >>> result["value"]
        960000000
    """
    if method == "perpetual":
        if final_fcf is None or wacc is None or terminal_growth is None:
            raise ValueError("永续增长法需要: final_fcf, wacc, terminal_growth")
        if terminal_growth >= wacc:
            raise ValueError(f"Terminal growth ({terminal_growth}) must be less than WACC ({wacc})")

        value = final_fcf * (1 + terminal_growth) / (wacc - terminal_growth)

        return {
            "value": value,
            "formula": "FCF × (1+g) / (WACC - g)",
            "inputs": {
                "method": "perpetual_growth",
                "final_fcf": final_fcf,
                "terminal_growth": terminal_growth,
                "wacc": wacc
            },
            "source": source
        }

    elif method == "multiple":
        if final_ebitda is None or exit_multiple is None:
            raise ValueError("退出倍数法需要: final_ebitda, exit_multiple")

        value = final_ebitda * exit_multiple

        return {
            "value": value,
            "formula": "EBITDA × Exit Multiple",
            "inputs": {
                "method": "exit_multiple",
                "final_ebitda": final_ebitda,
                "exit_multiple": exit_multiple
            },
            "source": source
        }

    else:
        raise ValueError(f"Unknown method: {method}. Use 'perpetual' or 'multiple'")


def calc_enterprise_value(
    fcf_list: List[float],
    wacc: float,
    terminal_value: float,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具5: 计算企业价值

    公式: EV = Σ FCF/(1+WACC)^t + TV/(1+WACC)^n

    Args:
        fcf_list: 各年FCF列表
        wacc: 折现率
        terminal_value: 终值
        source: 计算来源标记

    Returns:
        dict: {
            "value": 企业价值,
            "formula": 公式说明,
            "inputs": 输入参数（包括各期折现明细）,
            "source": 计算来源
        }

    示例:
        >>> fcf_list = [50_000_000, 55_000_000, 60_000_000, 65_000_000, 70_000_000]
        >>> result = calc_enterprise_value(fcf_list, 0.09, 1_000_000_000)
        >>> result["value"] > 800_000_000
        True
    """
    # 计算各期FCF现值
    pv_fcf_list = []
    for t, fcf in enumerate(fcf_list):
        discount_factor = 1 / (1 + wacc) ** (t + 1)
        pv = fcf * discount_factor
        pv_fcf_list.append({
            "year": t + 1,
            "fcf": fcf,
            "discount_factor": round(discount_factor, 6),
            "present_value": round(pv, 2)
        })

    pv_fcf_total = sum(item["present_value"] for item in pv_fcf_list)

    # 计算终值现值
    n = len(fcf_list)
    pv_terminal = terminal_value / (1 + wacc) ** n

    # 企业价值
    value = pv_fcf_total + pv_terminal

    return {
        "value": value,
        "formula": "Σ FCF/(1+WACC)^t + TV/(1+WACC)^n",
        "inputs": {
            "pv_of_fcf": pv_fcf_total,
            "pv_of_terminal": pv_terminal,
            "terminal_value": terminal_value,
            "wacc": wacc,
            "projection_years": n,
            "fcf_details": pv_fcf_list
        },
        "source": source
    }


def calc_equity_value(
    enterprise_value: float,
    debt: float,
    cash: float,
    minority_interest: float = 0,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具6: 计算股权价值

    公式: Equity = EV - Debt + Cash - Minority Interest

    Args:
        enterprise_value: 企业价值
        debt: 有息负债
        cash: 现金及等价物
        minority_interest: 少数股东权益
        source: 计算来源标记

    Returns:
        dict: {
            "value": 股权价值,
            "formula": 公式说明,
            "inputs": 输入参数,
            "source": 计算来源
        }

    示例:
        >>> result = calc_equity_value(893_000_000, 200_000_000, 50_000_000)
        >>> result["value"]
        743000000
    """
    value = enterprise_value - debt + cash - minority_interest

    return {
        "value": value,
        "formula": "EV - Debt + Cash - Minority",
        "inputs": {
            "enterprise_value": enterprise_value,
            "debt": debt,
            "cash": cash,
            "minority_interest": minority_interest
        },
        "source": source
    }


def calc_per_share_value(
    equity_value: float,
    shares_outstanding: float,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具7: 计算每股价值

    公式: Per Share Value = Equity Value / Shares Outstanding

    Args:
        equity_value: 股权价值
        shares_outstanding: 流通股数
        source: 计算来源标记

    Returns:
        dict: {
            "value": 每股价值,
            "formula": 公式说明,
            "inputs": 输入参数,
            "source": 计算来源
        }

    示例:
        >>> result = calc_per_share_value(743_000_000, 100_000_000)
        >>> result["value"]
        7.43
    """
    value = equity_value / shares_outstanding if shares_outstanding > 0 else 0

    return {
        "value": value,
        "formula": "Equity Value / Shares Outstanding",
        "inputs": {
            "equity_value": equity_value,
            "shares_outstanding": shares_outstanding
        },
        "source": source
    }


def dcf_sensitivity(
    fcf_list: List[float],
    wacc_range: List[float],
    growth_range: List[float],
    debt: float,
    cash: float,
    shares: float,
    source: str = "tool"
) -> Dict[str, Any]:
    """
    工具8: 敏感性分析矩阵

    生成 WACC × Terminal Growth 的每股价值矩阵

    Args:
        fcf_list: 各年FCF
        wacc_range: WACC范围 [0.08, 0.09, 0.10, ...]
        growth_range: 永续增长率范围 [0.01, 0.02, ...]
        debt: 负债
        cash: 现金
        shares: 股数
        source: 计算来源标记

    Returns:
        dict: {
            "matrix": 敏感性矩阵数据,
            "headers": 表头说明,
            "source": 计算来源
        }

    示例:
        >>> fcf_list = [50_000_000, 55_000_000, 60_000_000, 65_000_000, 70_000_000]
        >>> result = dcf_sensitivity(fcf_list, [0.08, 0.09, 0.10], [0.01, 0.02, 0.03], 200_000_000, 50_000_000, 100_000_000)
        >>> len(result["matrix"])
        3
    """
    matrix = []

    for wacc in wacc_range:
        row = {"wacc": f"{wacc:.1%}"}
        for g in growth_range:
            try:
                if g >= wacc:
                    row[f"g={g:.1%}"] = "N/A"
                    continue

                # 终值
                tv = calc_terminal_value("perpetual", final_fcf=fcf_list[-1], wacc=wacc, terminal_growth=g)
                # 企业价值
                ev = calc_enterprise_value(fcf_list, wacc, tv["value"])
                # 股权价值
                eq = calc_equity_value(ev["value"], debt, cash)
                # 每股价值
                per_share = eq["value"] / shares if shares > 0 else 0
                row[f"g={g:.1%}"] = round(per_share, 2)
            except (ValueError, ZeroDivisionError):
                row[f"g={g:.1%}"] = "N/A"

        matrix.append(row)

    return {
        "headers": {
            "rows": "WACC",
            "columns": "Terminal Growth"
        },
        "matrix": matrix,
        "source": source
    }


def dcf_quick_valuate(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    工具9: 快捷估值入口

    一键完成DCF估值，内部依次调用所有原子工具。
    当需要自定义某个步骤时，可以单独调用原子工具替代。

    Args:
        inputs: DCF输入参数，包含:
            - wacc_inputs: WACC计算参数（可选，也可直接提供wacc）
                - risk_free_rate: 无风险利率
                - beta: 贝塔系数
                - market_risk_premium: 市场风险溢价
                - cost_of_debt: 债务成本
                - debt_ratio: 负债率
                - tax_rate: 税率
            - wacc: 直接提供的WACC值（如果提供则跳过calc_wacc）
            - fcf_list: 各年FCF列表
            - terminal_method: 终值计算方法 ("perpetual" 或 "multiple")
            - terminal_growth: 永续增长率（perpetual方法需要）
            - exit_multiple: 退出倍数（multiple方法需要）
            - final_ebitda: 最后一年EBITDA（multiple方法需要）
            - debt: 有息负债
            - cash: 现金
            - shares_outstanding: 流通股数
            - sensitivity_config: 敏感性分析配置（可选）
                - wacc_range: WACC范围
                - growth_range: 增长率范围

    Returns:
        dict: 完整DCF估值结果

    示例:
        >>> inputs = {
        ...     "wacc": 0.09,
        ...     "fcf_list": [50_000_000, 55_000_000, 60_000_000, 65_000_000, 70_000_000],
        ...     "terminal_method": "perpetual",
        ...     "terminal_growth": 0.02,
        ...     "debt": 200_000_000,
        ...     "cash": 50_000_000,
        ...     "shares_outstanding": 100_000_000
        ... }
        >>> result = dcf_quick_valuate(inputs)
        >>> result["per_share_value"]["value"] > 0
        True
    """
    # 1. WACC计算（如果没有直接提供）
    if "wacc" in inputs:
        wacc_value = inputs["wacc"]
        wacc_result = {
            "value": wacc_value,
            "formula": "user_provided",
            "inputs": {"wacc": wacc_value},
            "source": "llm_override"
        }
        cost_of_equity_result = None
    else:
        wacc_inputs = inputs["wacc_inputs"]
        cost_of_equity_result = calc_capm(
            wacc_inputs["risk_free_rate"],
            wacc_inputs["beta"],
            wacc_inputs["market_risk_premium"]
        )
        wacc_result = calc_wacc(
            cost_of_equity_result["value"],
            wacc_inputs["cost_of_debt"],
            wacc_inputs.get("tax_rate", 0.25),
            wacc_inputs["debt_ratio"]
        )
        wacc_value = wacc_result["value"]

    # 2. FCF列表
    fcf_list = inputs["fcf_list"]

    # 3. 终值计算
    terminal_method = inputs.get("terminal_method", "perpetual")
    if terminal_method == "perpetual":
        terminal_value_result = calc_terminal_value(
            "perpetual",
            final_fcf=fcf_list[-1],
            wacc=wacc_value,
            terminal_growth=inputs["terminal_growth"]
        )
    else:
        final_ebitda = inputs.get("final_ebitda", fcf_list[-1] * 1.2)  # 默认假设EBITDA约为FCF的1.2倍
        terminal_value_result = calc_terminal_value(
            "multiple",
            final_ebitda=final_ebitda,
            exit_multiple=inputs.get("exit_multiple", 10)
        )

    # 4. 企业价值
    enterprise_value_result = calc_enterprise_value(
        fcf_list,
        wacc_value,
        terminal_value_result["value"]
    )

    # 5. 股权价值
    equity_value_result = calc_equity_value(
        enterprise_value_result["value"],
        inputs["debt"],
        inputs["cash"]
    )

    # 6. 每股价值
    per_share_result = calc_per_share_value(
        equity_value_result["value"],
        inputs["shares_outstanding"]
    )

    # 7. 敏感性分析（可选）
    sensitivity_result = None
    sens_config = inputs.get("sensitivity_config")
    if sens_config:
        sensitivity_result = dcf_sensitivity(
            fcf_list,
            sens_config["wacc_range"],
            sens_config["growth_range"],
            inputs["debt"],
            inputs["cash"],
            inputs["shares_outstanding"]
        )

    # 组装结果
    result = {
        "_meta": {
            "model_type": "dcf",
            "method": terminal_method,
            "projection_years": len(fcf_list),
            "built_with": "atomic_tools"
        },
        "wacc": wacc_result,
        "terminal_value": terminal_value_result,
        "enterprise_value": enterprise_value_result,
        "equity_value": equity_value_result,
        "per_share_value": per_share_result
    }

    if cost_of_equity_result:
        result["cost_of_equity"] = cost_of_equity_result

    if sensitivity_result:
        result["sensitivity_matrix"] = sensitivity_result

    return result
