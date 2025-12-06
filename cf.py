#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cf - Cash Flow CLI

资金管理命令行工具，提供现金流预测、营运资金分析等功能。

用法:
    cf <command> [options] < input.json

命令:
    forecast    13周现金流预测
    wcc         营运资金周期分析
    drivers     现金流驱动因素分解
"""

import sys
import json
import argparse
from typing import Dict, Any, List

from fin_tools.tools.cash_tools import (
    cash_forecast_13w,
    working_capital_cycle,
    cash_drivers
)


# ============================================================
# 输出格式化
# ============================================================

def format_number(value: float, style: str = "auto") -> str:
    """格式化数字"""
    if value is None:
        return "N/A"

    abs_val = abs(value)

    if style == "percent":
        return f"{value:.1%}"
    elif style == "days":
        return f"{value:.1f}天"
    elif style == "currency" or (style == "auto" and abs_val >= 1000):
        if abs_val >= 1e9:
            return f"{value/1e9:,.2f}B"
        elif abs_val >= 1e6:
            return f"{value/1e6:,.2f}M"
        elif abs_val >= 1e3:
            return f"{value/1e3:,.2f}K"
        else:
            return f"{value:,.2f}"
    else:
        return f"{value:.2f}"


def print_json(data: Dict, compact: bool = False):
    """输出JSON"""
    if compact:
        print(json.dumps(data, ensure_ascii=False))
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))


def print_table(headers: List[str], rows: List[List[str]], title: str = None):
    """输出表格"""
    if title:
        print(f"\n{title}")
        print("─" * 60)

    # 计算列宽
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    # 打印表头
    header_line = "│ " + " │ ".join(h.ljust(widths[i]) for i, h in enumerate(headers)) + " │"
    separator = "├─" + "─┼─".join("─" * w for w in widths) + "─┤"
    top_border = "┌─" + "─┬─".join("─" * w for w in widths) + "─┐"
    bottom_border = "└─" + "─┴─".join("─" * w for w in widths) + "─┘"

    print(top_border)
    print(header_line)
    print(separator)
    for row in rows:
        row_line = "│ " + " │ ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)) + " │"
        print(row_line)
    print(bottom_border)


# ============================================================
# 命令处理
# ============================================================

def cmd_forecast(args):
    """13周现金流预测"""
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"ERROR: 无效的 JSON 输入 - {e}", file=sys.stderr)
        sys.exit(2)

    if not isinstance(data, dict):
        print("ERROR: 输入必须是 JSON 对象（键值对）", file=sys.stderr)
        sys.exit(2)

    opening_cash = data.get("opening_cash", 0)
    weeks = data.get("weeks", args.weeks)
    if weeks <= 0:
        print("ERROR: weeks 必须为正整数", file=sys.stderr)
        sys.exit(2)
    try:
        opening_cash = float(opening_cash)
    except (TypeError, ValueError):
        print("ERROR: opening_cash 必须是数值", file=sys.stderr)
        sys.exit(2)

    result = cash_forecast_13w(
        opening_cash=opening_cash,
        receivables_schedule=data.get("receivables_schedule", []),
        payables_schedule=data.get("payables_schedule", []),
        recurring_inflows=data.get("recurring_inflows"),
        recurring_outflows=data.get("recurring_outflows"),
        weeks=weeks
    )

    if args.json:
        print_json(result)
    else:
        print(f"\n13周现金流预测")
        print("─" * 70)

        # 周度预测表
        print_table(
            headers=["周", "期初", "流入", "流出", "净流量", "期末"],
            rows=[
                [
                    f"W{w['week']}",
                    format_number(w["opening_balance"]),
                    format_number(w["inflow_total"]),
                    format_number(w["outflow_total"]),
                    format_number(w["net_flow"]),
                    format_number(w["ending_balance"])
                ]
                for w in result["weekly_forecast"]
            ],
            title="周度现金预测"
        )

        # 汇总
        summary = result["summary"]
        print(f"\n汇总:")
        print(f"  期初现金: {format_number(summary['opening_cash'])}")
        print(f"  总流入: {format_number(summary['total_inflows'])}")
        print(f"  总流出: {format_number(summary['total_outflows'])}")
        print(f"  净现金流: {format_number(summary['net_cash_flow'])}")
        print(f"  期末现金: {format_number(summary['ending_cash'])}")

        # 资金缺口预警
        if result["has_funding_gap"]:
            print(f"\n⚠️  资金缺口预警:")
            for gap in result["funding_gaps"]:
                print(f"  第{gap['week']}周: 缺口 {format_number(gap['shortfall'])}")
        else:
            print(f"\n✓ 无资金缺口")

        # 最低余额
        min_bal = result["min_balance"]
        print(f"\n最低余额: 第{min_bal['week']}周 {format_number(min_bal['balance'])}")


def cmd_wcc(args):
    """营运资金周期分析"""
    data = json.load(sys.stdin)

    result = working_capital_cycle(
        accounts_receivable=data.get("accounts_receivable", data.get("ar", 0)),
        inventory=data.get("inventory", 0),
        accounts_payable=data.get("accounts_payable", data.get("ap", 0)),
        revenue=data.get("revenue", 0),
        cogs=data.get("cogs", data.get("cost_of_goods_sold", 0)),
        period_days=data.get("period_days", 365)
    )

    if args.json:
        print_json(result)
    else:
        print(f"\n营运资金周期分析")
        print("─" * 60)

        # 周转天数
        print_table(
            headers=["指标", "天数", "周转率"],
            rows=[
                ["应收周转天数 (DSO)", f"{result['dso']:.1f}", f"{result['analysis']['ar_turnover']:.2f}x"],
                ["存货周转天数 (DIO)", f"{result['dio']:.1f}", f"{result['analysis']['inventory_turnover']:.2f}x"],
                ["应付周转天数 (DPO)", f"{result['dpo']:.1f}", f"{result['analysis']['ap_turnover']:.2f}x"],
            ],
            title="周转分析"
        )

        # CCC
        print(f"\n现金转换周期 (CCC): {result['ccc']:.1f} 天")
        print(f"  = DSO ({result['dso']:.1f}) + DIO ({result['dio']:.1f}) - DPO ({result['dpo']:.1f})")

        # 营运资金
        print(f"\n营运资金需求: {format_number(result['working_capital'])}")
        print(f"营运资金/收入: {result['wc_revenue_ratio']:.1%}")

        # 解读
        print(f"\n解读: {result['interpretation']}")


def cmd_drivers(args):
    """现金流驱动因素分解"""
    data = json.load(sys.stdin)

    period1 = data.get("period1", {})
    period2 = data.get("period2", {})

    result = cash_drivers(period1=period1, period2=period2)

    if args.json:
        print_json(result)
    else:
        print(f"\n现金流驱动因素分析")
        print("─" * 60)

        # 变动汇总
        print_table(
            headers=["活动", "期初", "期末", "变动"],
            rows=[
                [
                    "经营活动",
                    format_number(result["period1_totals"]["operating"]),
                    format_number(result["period2_totals"]["operating"]),
                    format_number(result["changes"]["operating"])
                ],
                [
                    "投资活动",
                    format_number(result["period1_totals"]["investing"]),
                    format_number(result["period2_totals"]["investing"]),
                    format_number(result["changes"]["investing"])
                ],
                [
                    "筹资活动",
                    format_number(result["period1_totals"]["financing"]),
                    format_number(result["period2_totals"]["financing"]),
                    format_number(result["changes"]["financing"])
                ],
                [
                    "合计",
                    format_number(result["period1_totals"]["total"]),
                    format_number(result["period2_totals"]["total"]),
                    format_number(result["changes"]["total"])
                ]
            ],
            title="现金流变动"
        )

        # 影响排名
        print("\n主要驱动因素:")
        for i, driver in enumerate(result["impact_ranking"], 1):
            sign = "+" if driver["amount"] >= 0 else ""
            print(f"  {i}. {driver['factor']}: {sign}{format_number(driver['amount'])}")

        # 分析结论
        print(f"\n分析: {result['analysis']}")


# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        prog="cf",
        description="Cash Flow - 资金管理工具"
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # forecast - 13周现金预测
    forecast_parser = subparsers.add_parser("forecast", help="13周现金流预测")
    forecast_parser.add_argument("--weeks", type=int, default=13,
                                help="预测周数 (默认: 13)")
    forecast_parser.add_argument("--json", action="store_true",
                                help="JSON格式输出")
    forecast_parser.set_defaults(func=cmd_forecast)

    # wcc - 营运资金周期
    wcc_parser = subparsers.add_parser("wcc", help="营运资金周期分析")
    wcc_parser.add_argument("--json", action="store_true",
                           help="JSON格式输出")
    wcc_parser.set_defaults(func=cmd_wcc)

    # drivers - 驱动因素
    drivers_parser = subparsers.add_parser("drivers", help="现金流驱动因素分解")
    drivers_parser.add_argument("--json", action="store_true",
                               help="JSON格式输出")
    drivers_parser.set_defaults(func=cmd_drivers)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
