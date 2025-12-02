#!/usr/bin/env python3
"""
财务三表配平工具

用法:
    balance calc < input.json          # 计算配平（默认）
    balance check < input.json         # 校验输入数据
    balance diagnose < output.json     # 诊断结果问题
    balance scenario < input.json      # 场景分析
    balance explain < output.json      # 追溯解释
"""

import sys
import json
import argparse


# ============================================================
# 配平计算模块
# ============================================================
def step_finance(data: dict) -> dict:
    """融资现金流：利息、新增借款、期末现金"""
    opening_debt = data.get("opening_debt", 0)
    opening_cash = data.get("opening_cash", 0)
    interest_rate = data.get("interest_rate", 0.05)
    min_cash = data.get("min_cash", 0)
    repayment = data.get("repayment", 0)

    revenue = data.get("revenue", 0)
    cost = data.get("cost", 0)
    other_expense = data.get("other_expense", 0)
    delta_receivable = data.get("delta_receivable", 0)
    delta_payable = data.get("delta_payable", 0)

    interest = opening_debt * interest_rate

    estimated_depreciation = data.get("estimated_depreciation", 0)
    tax_rate = data.get("tax_rate", 0.25)
    estimated_ebt = revenue - cost - other_expense - interest - estimated_depreciation
    estimated_tax = max(estimated_ebt, 0) * tax_rate

    capex = data.get("capex", 0)
    operating_cf = revenue - cost - other_expense - estimated_tax - delta_receivable + delta_payable
    investing_cf = -capex
    cash_before_financing = opening_cash + operating_cf + investing_cf - interest - repayment

    gap = min_cash - cash_before_financing
    new_borrowing = max(gap, 0)

    closing_cash = cash_before_financing + new_borrowing
    closing_debt = opening_debt + new_borrowing - repayment

    data["interest"] = round(interest, 2)
    data["new_borrowing"] = round(new_borrowing, 2)
    data["closing_debt"] = round(closing_debt, 2)
    data["closing_cash"] = round(closing_cash, 2)
    data["operating_cashflow"] = round(operating_cf, 2)
    data["investing_cashflow"] = round(investing_cf, 2)
    data["financing_cashflow"] = round(new_borrowing - repayment - interest, 2)

    return data


def step_depreciation(data: dict) -> dict:
    """折旧计算"""
    fixed_asset_cost = data.get("fixed_asset_cost", 0)
    fixed_asset_life = data.get("fixed_asset_life", 5)
    fixed_asset_salvage = data.get("fixed_asset_salvage", 0)
    accum_depreciation = data.get("accum_depreciation", 0)
    capex = data.get("capex", 0)

    if fixed_asset_life > 0:
        annual_depreciation = (fixed_asset_cost - fixed_asset_salvage) / fixed_asset_life
    else:
        annual_depreciation = 0

    closing_accum_depreciation = accum_depreciation + annual_depreciation
    closing_fixed_asset_net = fixed_asset_cost + capex - closing_accum_depreciation

    data["depreciation"] = round(annual_depreciation, 2)
    data["closing_accum_depreciation"] = round(closing_accum_depreciation, 2)
    data["closing_fixed_asset_net"] = round(closing_fixed_asset_net, 2)

    return data


def step_profit(data: dict) -> dict:
    """损益表计算"""
    revenue = data.get("revenue", 0)
    cost = data.get("cost", 0)
    other_expense = data.get("other_expense", 0)
    interest = data.get("interest", 0)
    depreciation = data.get("depreciation", 0)
    tax_rate = data.get("tax_rate", 0.25)

    gross_profit = revenue - cost
    ebit = gross_profit - depreciation - other_expense
    ebt = ebit - interest
    tax = max(ebt, 0) * tax_rate
    net_income = ebt - tax

    data["gross_profit"] = round(gross_profit, 2)
    data["ebit"] = round(ebit, 2)
    data["ebt"] = round(ebt, 2)
    data["tax"] = round(tax, 2)
    data["net_income"] = round(net_income, 2)

    return data


def step_equity(data: dict) -> dict:
    """权益变动计算"""
    net_income = data.get("net_income", 0)
    dividend = data.get("dividend", 0)
    opening_retained = data.get("opening_retained", 0)
    opening_equity = data.get("opening_equity", 0)
    new_equity = data.get("new_equity", 0)

    retained_earnings_change = net_income - dividend
    closing_retained = opening_retained + retained_earnings_change
    closing_equity_capital = opening_equity + new_equity
    closing_total_equity = closing_equity_capital + closing_retained

    data["retained_earnings_change"] = round(retained_earnings_change, 2)
    data["closing_retained"] = round(closing_retained, 2)
    data["closing_equity_capital"] = round(closing_equity_capital, 2)
    data["closing_total_equity"] = round(closing_total_equity, 2)

    return data


def step_reconcile(data: dict) -> dict:
    """配平轧差"""
    closing_cash = data.get("closing_cash", 0)
    closing_receivable = data.get("closing_receivable", data.get("opening_receivable", 0))
    closing_inventory = data.get("closing_inventory", data.get("opening_inventory", 0))
    closing_fixed_asset_net = data.get("closing_fixed_asset_net", 0)

    closing_debt = data.get("closing_debt", 0)
    closing_payable = data.get("closing_payable", data.get("opening_payable", 0))
    closing_total_equity = data.get("closing_total_equity", 0)

    total_assets = closing_cash + closing_receivable + closing_inventory + closing_fixed_asset_net
    total_liabilities = closing_debt + closing_payable
    total_equity = closing_total_equity

    balance_diff = total_assets - total_liabilities - total_equity

    if abs(balance_diff) > 0.01:
        closing_payable += balance_diff
        total_liabilities = closing_debt + closing_payable
        balance_diff = total_assets - total_liabilities - total_equity

    is_balanced = abs(balance_diff) < 0.01

    data["closing_receivable"] = round(closing_receivable, 2)
    data["closing_payable"] = round(closing_payable, 2)
    data["total_assets"] = round(total_assets, 2)
    data["total_liabilities"] = round(total_liabilities, 2)
    data["total_equity"] = round(total_equity, 2)
    data["balance_diff"] = round(balance_diff, 2)
    data["is_balanced"] = is_balanced

    opening_cash = data.get("opening_cash", 0)
    operating_cf = data.get("operating_cashflow", 0)
    investing_cf = data.get("investing_cashflow", 0)
    financing_cf = data.get("financing_cashflow", 0)
    cash_check = opening_cash + operating_cf + investing_cf + financing_cf
    data["cash_flow_check"] = round(cash_check, 2)
    data["cash_balanced"] = abs(cash_check - closing_cash) < 0.01

    return data


CALC_STEPS = {
    "finance": step_finance,
    "depreciation": step_depreciation,
    "profit": step_profit,
    "equity": step_equity,
    "reconcile": step_reconcile,
}
CALC_STEP_ORDER = ["finance", "depreciation", "profit", "equity", "reconcile"]


def run_calc(data: dict, step: str = None) -> dict:
    """执行配平计算"""
    if step:
        return CALC_STEPS[step](data)
    for step_name in CALC_STEP_ORDER:
        data = CALC_STEPS[step_name](data)
    return data


# ============================================================
# 数据校验模块
# ============================================================
def run_check(data: dict) -> dict:
    """校验输入数据是否合理"""
    warnings = []
    errors = []

    # 必填字段检查
    required = ["revenue", "cost", "opening_cash"]
    for field in required:
        if field not in data:
            errors.append(f"缺少必填字段: {field}")

    # 数值合理性检查
    revenue = data.get("revenue", 0)
    cost = data.get("cost", 0)
    if cost > revenue * 1.5:
        warnings.append(f"成本({cost})远高于收入({revenue})，请确认是否正确")

    interest_rate = data.get("interest_rate", 0)
    if interest_rate > 0.3:
        warnings.append(f"利率({interest_rate*100}%)异常偏高，一般在3%-15%之间")
    if interest_rate < 0:
        errors.append(f"利率({interest_rate})不能为负数")

    tax_rate = data.get("tax_rate", 0)
    if tax_rate > 0.5:
        warnings.append(f"税率({tax_rate*100}%)异常偏高")
    if tax_rate < 0:
        errors.append(f"税率({tax_rate})不能为负数")

    fixed_asset_life = data.get("fixed_asset_life", 0)
    if fixed_asset_life < 0:
        errors.append(f"折旧年限({fixed_asset_life})不能为负数")

    opening_cash = data.get("opening_cash", 0)
    if opening_cash < 0:
        warnings.append(f"期初现金({opening_cash})为负数，请确认")

    # 负债率预估
    opening_debt = data.get("opening_debt", 0)
    opening_equity = data.get("opening_equity", 0)
    opening_retained = data.get("opening_retained", 0)
    total_equity = opening_equity + opening_retained
    if total_equity > 0:
        debt_ratio = opening_debt / (opening_debt + total_equity)
        if debt_ratio > 0.8:
            warnings.append(f"负债率({debt_ratio*100:.1f}%)偏高，超过80%")

    return {
        "status": "error" if errors else ("warning" if warnings else "ok"),
        "errors": errors,
        "warnings": warnings,
        "checked_fields": len(data),
    }


# ============================================================
# 问题诊断模块
# ============================================================
def run_diagnose(data: dict) -> dict:
    """诊断配平结果中的问题"""
    issues = []
    suggestions = []

    # 配平检查
    if not data.get("is_balanced", True):
        diff = data.get("balance_diff", 0)
        issues.append(f"资产负债表不平衡，差额: {diff}")
        suggestions.append("检查是否有遗漏的资产或负债项目")

    # 净利润分析
    net_income = data.get("net_income", 0)
    revenue = data.get("revenue", 0)
    if net_income < 0:
        issues.append(f"净利润为负: {net_income}")
        # 分析原因
        cost = data.get("cost", 0)
        interest = data.get("interest", 0)
        depreciation = data.get("depreciation", 0)
        if cost / revenue > 0.8 if revenue else False:
            suggestions.append(f"成本占收入比例过高({cost/revenue*100:.1f}%)，考虑降低成本")
        if interest / revenue > 0.1 if revenue else False:
            suggestions.append(f"利息费用占收入比例过高({interest/revenue*100:.1f}%)，考虑降低负债或利率")
        if depreciation / revenue > 0.2 if revenue else False:
            suggestions.append(f"折旧费用占收入比例过高({depreciation/revenue*100:.1f}%)")

    # 现金流分析
    closing_cash = data.get("closing_cash", 0)
    min_cash = data.get("min_cash", 0)
    if closing_cash < min_cash:
        issues.append(f"期末现金({closing_cash})低于最低要求({min_cash})")
        suggestions.append("需要增加借款或减少支出")

    # 新增借款分析
    new_borrowing = data.get("new_borrowing", 0)
    if new_borrowing > 0:
        issues.append(f"需要新增借款: {new_borrowing}")
        suggestions.append("现金流不足以支撑运营，自动借款补足")

    # 负债率分析
    total_liabilities = data.get("total_liabilities", 0)
    total_equity = data.get("total_equity", 0)
    if total_liabilities + total_equity > 0:
        debt_ratio = total_liabilities / (total_liabilities + total_equity)
        if debt_ratio > 0.7:
            issues.append(f"负债率偏高: {debt_ratio*100:.1f}%")
            suggestions.append("考虑增加股本或减少负债")

    return {
        "status": "ok" if not issues else "issues_found",
        "issues": issues,
        "suggestions": suggestions,
        "summary": {
            "net_income": data.get("net_income"),
            "closing_cash": data.get("closing_cash"),
            "is_balanced": data.get("is_balanced"),
        }
    }


# ============================================================
# 场景分析模块
# ============================================================
def run_scenario(data: dict, vary: str) -> dict:
    """场景分析：对比不同参数下的结果"""
    # 解析 vary 参数，格式: "field:val1,val2,val3"
    parts = vary.split(":")
    if len(parts) != 2:
        return {"error": "格式错误，应为 field:val1,val2,val3"}

    field = parts[0]
    values = [float(v.strip()) for v in parts[1].split(",")]

    results = []
    for val in values:
        scenario_data = data.copy()
        scenario_data[field] = val
        result = run_calc(scenario_data)
        results.append({
            field: val,
            "net_income": result.get("net_income"),
            "closing_cash": result.get("closing_cash"),
            "closing_debt": result.get("closing_debt"),
            "is_balanced": result.get("is_balanced"),
        })

    return {
        "vary_field": field,
        "scenarios": results,
    }


# ============================================================
# 追溯解释模块
# ============================================================
def run_explain(data: dict, field: str) -> dict:
    """追溯解释某个字段的计算过程"""
    explanations = {
        "net_income": {
            "formula": "净利润 = 收入 - 成本 - 折旧 - 其他费用 - 利息 - 税",
            "calc": f"净利润 = {data.get('revenue',0)} - {data.get('cost',0)} - {data.get('depreciation',0)} - {data.get('other_expense',0)} - {data.get('interest',0)} - {data.get('tax',0)} = {data.get('net_income',0)}",
            "components": {
                "revenue": data.get("revenue"),
                "cost": data.get("cost"),
                "depreciation": data.get("depreciation"),
                "other_expense": data.get("other_expense"),
                "interest": data.get("interest"),
                "tax": data.get("tax"),
            }
        },
        "closing_cash": {
            "formula": "期末现金 = 期初现金 + 经营现金流 + 投资现金流 + 筹资现金流",
            "calc": f"期末现金 = {data.get('opening_cash',0)} + {data.get('operating_cashflow',0)} + {data.get('investing_cashflow',0)} + {data.get('financing_cashflow',0)} = {data.get('closing_cash',0)}",
            "components": {
                "opening_cash": data.get("opening_cash"),
                "operating_cashflow": data.get("operating_cashflow"),
                "investing_cashflow": data.get("investing_cashflow"),
                "financing_cashflow": data.get("financing_cashflow"),
            }
        },
        "interest": {
            "formula": "利息 = 期初负债 × 利率",
            "calc": f"利息 = {data.get('opening_debt',0)} × {data.get('interest_rate',0)} = {data.get('interest',0)}",
            "components": {
                "opening_debt": data.get("opening_debt"),
                "interest_rate": data.get("interest_rate"),
            }
        },
        "depreciation": {
            "formula": "折旧 = (固定资产原值 - 残值) / 折旧年限",
            "calc": f"折旧 = ({data.get('fixed_asset_cost',0)} - {data.get('fixed_asset_salvage',0)}) / {data.get('fixed_asset_life',1)} = {data.get('depreciation',0)}",
            "components": {
                "fixed_asset_cost": data.get("fixed_asset_cost"),
                "fixed_asset_salvage": data.get("fixed_asset_salvage"),
                "fixed_asset_life": data.get("fixed_asset_life"),
            }
        },
        "closing_total_equity": {
            "formula": "期末权益 = 期初股本 + 期初留存收益 + 净利润 - 分红",
            "calc": f"期末权益 = {data.get('opening_equity',0)} + {data.get('opening_retained',0)} + {data.get('net_income',0)} - {data.get('dividend',0)} = {data.get('closing_total_equity',0)}",
            "components": {
                "opening_equity": data.get("opening_equity"),
                "opening_retained": data.get("opening_retained"),
                "net_income": data.get("net_income"),
                "dividend": data.get("dividend"),
            }
        },
    }

    if field in explanations:
        return explanations[field]
    else:
        return {
            "error": f"不支持的字段: {field}",
            "supported": list(explanations.keys()),
        }


# ============================================================
# 主函数
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="财务三表配平工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
子命令:
  calc       计算配平（默认）
  check      校验输入数据
  diagnose   诊断结果问题
  scenario   场景分析
  explain    追溯解释

示例:
  echo '{"revenue":10000,"cost":6000}' | balance calc
  balance check < input.json
  balance diagnose < output.json
  balance scenario --vary "interest_rate:0.05,0.08,0.10" < input.json
  balance explain --field net_income < output.json
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # calc 子命令
    calc_parser = subparsers.add_parser("calc", help="计算配平")
    calc_parser.add_argument("--step", "-s", choices=CALC_STEP_ORDER, help="只执行指定步骤")
    calc_parser.add_argument("--compact", "-c", action="store_true", help="紧凑输出")

    # check 子命令
    check_parser = subparsers.add_parser("check", help="校验输入数据")

    # diagnose 子命令
    diagnose_parser = subparsers.add_parser("diagnose", help="诊断结果问题")

    # scenario 子命令
    scenario_parser = subparsers.add_parser("scenario", help="场景分析")
    scenario_parser.add_argument("--vary", "-v", required=True, help="变量:值列表，如 interest_rate:0.05,0.08,0.10")

    # explain 子命令
    explain_parser = subparsers.add_parser("explain", help="追溯解释")
    explain_parser.add_argument("--field", "-f", required=True, help="要解释的字段")

    args = parser.parse_args()

    # 默认命令是 calc
    if args.command is None:
        args.command = "calc"
        args.step = None
        args.compact = False

    # 从 stdin 读取 JSON
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"错误: 无效的 JSON 输入 - {e}", file=sys.stderr)
        sys.exit(1)

    # 执行对应命令
    if args.command == "calc":
        result = run_calc(data, getattr(args, 'step', None))
    elif args.command == "check":
        result = run_check(data)
    elif args.command == "diagnose":
        result = run_diagnose(data)
    elif args.command == "scenario":
        result = run_scenario(data, args.vary)
    elif args.command == "explain":
        result = run_explain(data, args.field)
    else:
        result = run_calc(data)

    # 输出
    compact = getattr(args, 'compact', False)
    if compact:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
