#!/usr/bin/env python3
"""
财务三表配平工具 - CLI 版本

用法:
    echo '{"revenue": 1000, ...}' | ./balance.py
    ./balance.py --step finance < input.json
    cat input.json | ./balance.py --step finance | ./balance.py --step profit
"""

import sys
import json
import argparse


# ============================================================
# 第一步：融资现金流
# ============================================================
def step_finance(data: dict) -> dict:
    """
    计算融资现金流：利息、新增借款、期末负债、期末现金

    解决循环依赖：利息按期初负债计算（简化模型）
    """
    # 取参数
    opening_debt = data.get("opening_debt", 0)
    opening_cash = data.get("opening_cash", 0)
    interest_rate = data.get("interest_rate", 0.05)
    min_cash = data.get("min_cash", 0)
    repayment = data.get("repayment", 0)

    # 经营现金流（简化：收入-成本-费用）
    revenue = data.get("revenue", 0)
    cost = data.get("cost", 0)
    other_expense = data.get("other_expense", 0)

    # 应收应付变动（影响现金）
    delta_receivable = data.get("delta_receivable", 0)  # 增加则现金减少
    delta_payable = data.get("delta_payable", 0)        # 增加则现金增加

    # 计算利息（按期初负债）
    interest = opening_debt * interest_rate

    # 预估税（需要先估算利润，这里简化处理）
    # 注意：精确计算需要折旧，但折旧在第二步，这里用预估值
    estimated_depreciation = data.get("estimated_depreciation", 0)
    tax_rate = data.get("tax_rate", 0.25)
    estimated_ebt = revenue - cost - other_expense - interest - estimated_depreciation
    estimated_tax = max(estimated_ebt, 0) * tax_rate

    # 资本支出
    capex = data.get("capex", 0)

    # 经营现金流（简化）
    operating_cf = revenue - cost - other_expense - estimated_tax - delta_receivable + delta_payable

    # 投资现金流
    investing_cf = -capex

    # 融资前现金
    cash_before_financing = opening_cash + operating_cf + investing_cf - interest - repayment

    # 现金缺口
    gap = min_cash - cash_before_financing

    # 新增借款
    new_borrowing = max(gap, 0)

    # 期末值
    closing_cash = cash_before_financing + new_borrowing
    closing_debt = opening_debt + new_borrowing - repayment

    # 写入结果
    data["interest"] = round(interest, 2)
    data["new_borrowing"] = round(new_borrowing, 2)
    data["closing_debt"] = round(closing_debt, 2)
    data["closing_cash"] = round(closing_cash, 2)
    data["operating_cashflow"] = round(operating_cf, 2)
    data["investing_cashflow"] = round(investing_cf, 2)
    data["financing_cashflow"] = round(new_borrowing - repayment - interest, 2)

    return data


# ============================================================
# 第二步：投资现金流 / 折旧
# ============================================================
def step_depreciation(data: dict) -> dict:
    """
    计算折旧费用、期末固定资产净值

    默认使用直线法
    """
    # 取参数
    fixed_asset_cost = data.get("fixed_asset_cost", 0)
    fixed_asset_life = data.get("fixed_asset_life", 5)
    fixed_asset_salvage = data.get("fixed_asset_salvage", 0)
    accum_depreciation = data.get("accum_depreciation", 0)
    capex = data.get("capex", 0)
    depreciation_method = data.get("depreciation_method", "straight_line")

    # 直线法折旧
    if fixed_asset_life > 0:
        if depreciation_method == "straight_line":
            # 直线法
            annual_depreciation = (fixed_asset_cost - fixed_asset_salvage) / fixed_asset_life
        elif depreciation_method == "double_declining":
            # 双倍余额递减法
            rate = 2 / fixed_asset_life
            net_value = fixed_asset_cost - accum_depreciation
            annual_depreciation = net_value * rate
        else:
            annual_depreciation = (fixed_asset_cost - fixed_asset_salvage) / fixed_asset_life
    else:
        annual_depreciation = 0

    # 期末累计折旧
    closing_accum_depreciation = accum_depreciation + annual_depreciation

    # 期末固定资产净值（含本期资本支出）
    closing_fixed_asset_net = fixed_asset_cost + capex - closing_accum_depreciation

    # 写入结果
    data["depreciation"] = round(annual_depreciation, 2)
    data["closing_accum_depreciation"] = round(closing_accum_depreciation, 2)
    data["closing_fixed_asset_net"] = round(closing_fixed_asset_net, 2)

    return data


# ============================================================
# 第三步：损益表
# ============================================================
def step_profit(data: dict) -> dict:
    """
    计算损益表：毛利、EBIT、EBT、所得税、净利润
    """
    # 取参数
    revenue = data.get("revenue", 0)
    cost = data.get("cost", 0)
    other_expense = data.get("other_expense", 0)
    interest = data.get("interest", 0)
    depreciation = data.get("depreciation", 0)
    tax_rate = data.get("tax_rate", 0.25)

    # 毛利
    gross_profit = revenue - cost

    # 营业利润（EBIT）
    ebit = gross_profit - depreciation - other_expense

    # 利润总额（EBT）
    ebt = ebit - interest

    # 所得税（亏损不交税）
    tax = max(ebt, 0) * tax_rate

    # 净利润
    net_income = ebt - tax

    # 写入结果
    data["gross_profit"] = round(gross_profit, 2)
    data["ebit"] = round(ebit, 2)
    data["ebt"] = round(ebt, 2)
    data["tax"] = round(tax, 2)
    data["net_income"] = round(net_income, 2)

    return data


# ============================================================
# 第四步：权益变动
# ============================================================
def step_equity(data: dict) -> dict:
    """
    计算权益变动：留存收益变动、期末权益
    """
    # 取参数
    net_income = data.get("net_income", 0)
    dividend = data.get("dividend", 0)
    opening_retained = data.get("opening_retained", 0)
    opening_equity = data.get("opening_equity", 0)
    new_equity = data.get("new_equity", 0)

    # 留存收益变动
    retained_earnings_change = net_income - dividend

    # 期末留存收益
    closing_retained = opening_retained + retained_earnings_change

    # 期末股本
    closing_equity_capital = opening_equity + new_equity

    # 期末所有者权益合计
    closing_total_equity = closing_equity_capital + closing_retained

    # 写入结果
    data["retained_earnings_change"] = round(retained_earnings_change, 2)
    data["closing_retained"] = round(closing_retained, 2)
    data["closing_equity_capital"] = round(closing_equity_capital, 2)
    data["closing_total_equity"] = round(closing_total_equity, 2)

    return data


# ============================================================
# 第五步：配平轧差
# ============================================================
def step_reconcile(data: dict) -> dict:
    """
    验证资产=负债+权益，必要时调整应收应付
    """
    # 取期末资产
    closing_cash = data.get("closing_cash", 0)
    closing_receivable = data.get("closing_receivable", data.get("opening_receivable", 0))
    closing_inventory = data.get("closing_inventory", data.get("opening_inventory", 0))
    closing_fixed_asset_net = data.get("closing_fixed_asset_net", 0)

    # 取期末负债
    closing_debt = data.get("closing_debt", 0)
    closing_payable = data.get("closing_payable", data.get("opening_payable", 0))

    # 取期末权益
    closing_total_equity = data.get("closing_total_equity", 0)

    # 计算合计
    total_assets = closing_cash + closing_receivable + closing_inventory + closing_fixed_asset_net
    total_liabilities = closing_debt + closing_payable
    total_equity = closing_total_equity

    # 检查差额
    balance_diff = total_assets - total_liabilities - total_equity

    # 调整（如果需要）
    adjustment_target = data.get("adjustment_target", "payable")  # 默认调应付

    if abs(balance_diff) > 0.01:  # 允许1分钱误差
        if adjustment_target == "payable":
            closing_payable += balance_diff
            total_liabilities = closing_debt + closing_payable
        elif adjustment_target == "receivable":
            closing_receivable -= balance_diff
            total_assets = closing_cash + closing_receivable + closing_inventory + closing_fixed_asset_net

        # 重新计算差额
        balance_diff = total_assets - total_liabilities - total_equity

    # 是否平衡
    is_balanced = abs(balance_diff) < 0.01

    # 写入结果
    data["closing_receivable"] = round(closing_receivable, 2)
    data["closing_payable"] = round(closing_payable, 2)
    data["total_assets"] = round(total_assets, 2)
    data["total_liabilities"] = round(total_liabilities, 2)
    data["total_equity"] = round(total_equity, 2)
    data["balance_diff"] = round(balance_diff, 2)
    data["is_balanced"] = is_balanced

    # 现金流勾稽检查
    opening_cash = data.get("opening_cash", 0)
    operating_cf = data.get("operating_cashflow", 0)
    investing_cf = data.get("investing_cashflow", 0)
    financing_cf = data.get("financing_cashflow", 0)

    cash_check = opening_cash + operating_cf + investing_cf + financing_cf
    data["cash_flow_check"] = round(cash_check, 2)
    data["cash_balanced"] = abs(cash_check - closing_cash) < 0.01

    return data


# ============================================================
# 主函数：执行全部或指定步骤
# ============================================================
STEPS = {
    "finance": step_finance,
    "depreciation": step_depreciation,
    "profit": step_profit,
    "equity": step_equity,
    "reconcile": step_reconcile,
}

STEP_ORDER = ["finance", "depreciation", "profit", "equity", "reconcile"]


def run_all(data: dict) -> dict:
    """按顺序执行全部五步"""
    for step_name in STEP_ORDER:
        data = STEPS[step_name](data)
    return data


def main():
    parser = argparse.ArgumentParser(
        description="财务三表配平工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  echo '{"revenue":10000,"cost":6000}' | ./balance.py
  ./balance.py --step finance < input.json
  cat input.json | ./balance.py --step finance | ./balance.py --step profit
        """
    )
    parser.add_argument(
        "--step", "-s",
        choices=list(STEPS.keys()),
        help="只执行指定步骤: finance, depreciation, profit, equity, reconcile"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="执行全部五步（默认）"
    )
    parser.add_argument(
        "--compact", "-c",
        action="store_true",
        help="输出紧凑 JSON（不格式化）"
    )
    parser.add_argument(
        "--list-steps", "-l",
        action="store_true",
        help="列出所有步骤"
    )

    args = parser.parse_args()

    # 列出步骤
    if args.list_steps:
        print("可用步骤（按执行顺序）:")
        for i, name in enumerate(STEP_ORDER, 1):
            print(f"  {i}. {name}")
        return

    # 从 stdin 读取 JSON
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"错误: 无效的 JSON 输入 - {e}", file=sys.stderr)
        sys.exit(1)

    # 执行
    if args.step:
        data = STEPS[args.step](data)
    else:
        data = run_all(data)

    # 输出
    if args.compact:
        print(json.dumps(data, ensure_ascii=False))
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
