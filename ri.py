#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ri - Risk CLI

风险管理命令行工具，提供信用评分、账龄分析、坏账计提、汇率风险等功能。

用法:
    ri <command> [options] < input.json

命令:
    credit      客户信用评分
    aging       应收账款账龄分析
    provision   坏账准备计算
    fx          汇率风险敞口
"""

import sys
import json
import argparse
from typing import Dict, Any, List

from fin_tools.tools.risk_tools import (
    credit_score,
    ar_aging,
    bad_debt_provision,
    fx_exposure
)


# ============================================================
# 输出格式化
# ============================================================

def load_json():
    """从 stdin 读取 JSON，接受对象或数组"""
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"ERROR: 无效的 JSON 输入 - {e}", file=sys.stderr)
        sys.exit(2)
    if not isinstance(data, (dict, list)):
        print("ERROR: 输入必须是 JSON 对象或数组", file=sys.stderr)
        sys.exit(2)
    return data

def format_number(value: float, style: str = "auto") -> str:
    """格式化数字"""
    if value is None:
        return "N/A"

    abs_val = abs(value)

    if style == "percent":
        return f"{value:.2%}"
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

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

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

def cmd_credit(args):
    """客户信用评分"""
    data = load_json()

    result = credit_score(
        customer_data=data,
        weights=data.get("weights")
    )

    if args.json:
        print_json(result)
    else:
        customer_name = result.get("customer_name", "未知客户")
        print(f"\n客户信用评分 - {customer_name}")
        print("─" * 60)

        # 评分结果
        print(f"\n综合评分: {result['score']}")
        print(f"信用等级: {result['grade']}")
        print(f"等级说明: {result['grade_desc']}")

        # 各维度得分
        print_table(
            headers=["评分维度", "得分", "权重"],
            rows=[
                [
                    dim.replace("_", " ").title(),
                    f"{score:.1f}",
                    f"{result['weights'].get(dim, 0):.0%}"
                ]
                for dim, score in result["dimension_scores"].items()
            ],
            title="维度得分"
        )

        # 风险因素
        if result["risk_factors"]:
            print("\n⚠ 风险因素:")
            for factor in result["risk_factors"]:
                print(f"  • {factor}")

        # 建议
        if result["recommendations"]:
            print("\n✓ 建议:")
            for rec in result["recommendations"]:
                print(f"  • {rec}")


def cmd_aging(args):
    """应收账款账龄分析"""
    data = load_json()

    receivables = data if isinstance(data, list) else data.get("receivables", [])

    result = ar_aging(
        receivables=receivables,
        as_of_date=data.get("as_of_date", args.date)
    )

    if args.json:
        print_json(result)
    else:
        print(f"\n应收账款账龄分析")
        print(f"截止日期: {result['as_of_date']}")
        print("─" * 60)

        print(f"\n应收总额: {format_number(result['total_ar'])}")
        print(f"发票笔数: {result['invoice_count']}")

        # 账龄分布
        print_table(
            headers=["账龄区间", "金额", "笔数", "占比"],
            rows=[
                [
                    bucket,
                    format_number(data["amount"]),
                    str(data["count"]),
                    format_number(data["pct"], "percent")
                ]
                for bucket, data in result["aging_summary"].items()
                if data["amount"] > 0
            ],
            title="账龄分布"
        )

        # 逾期汇总
        overdue = result["overdue_summary"]
        print(f"\n逾期情况:")
        print(f"  逾期总额: {format_number(overdue['total_overdue'])}")
        print(f"  逾期率: {format_number(overdue['overdue_rate'], 'percent')}")
        print(f"  平均逾期: {overdue['avg_days_overdue']:.0f}天")

        # 按客户汇总（前5名）
        if result["by_customer"]:
            print_table(
                headers=["客户", "应收金额", "逾期金额", "逾期率"],
                rows=[
                    [
                        c["customer_name"][:15],
                        format_number(c["total"]),
                        format_number(c["overdue"]),
                        format_number(c["overdue_rate"], "percent")
                    ]
                    for c in result["by_customer"][:5]
                ],
                title="客户应收（前5名）"
            )


def cmd_provision(args):
    """坏账准备计算"""
    data = load_json()

    # 支持直接传入账龄数据或ar_aging的输出
    aging_data = data.get("aging_data", data.get("aging_summary", data))

    result = bad_debt_provision(
        aging_data=aging_data,
        provision_rates=data.get("provision_rates"),
        specific_provisions=data.get("specific_provisions", [])
    )

    if args.json:
        print_json(result)
    else:
        print(f"\n坏账准备计算")
        print("─" * 60)

        print(f"\n应收总额: {format_number(result['total_ar'])}")

        # 按账龄计提
        print_table(
            headers=["账龄区间", "金额", "计提比例", "坏账准备"],
            rows=[
                [
                    item["aging_bucket"],
                    format_number(item["amount"]),
                    format_number(item["provision_rate"], "percent"),
                    format_number(item["provision"])
                ]
                for item in result["by_aging"]
                if item["amount"] > 0
            ],
            title="一般坏账准备"
        )

        print(f"\n一般坏账准备: {format_number(result['general_provision'])}")

        # 专项计提
        if result["by_specific"]:
            print_table(
                headers=["客户", "金额", "计提比例", "坏账准备", "原因"],
                rows=[
                    [
                        item["customer_name"][:10],
                        format_number(item["amount"]),
                        format_number(item["provision_rate"], "percent"),
                        format_number(item["provision"]),
                        item["reason"][:15]
                    ]
                    for item in result["by_specific"]
                ],
                title="专项坏账准备"
            )
            print(f"\n专项坏账准备: {format_number(result['specific_provision'])}")

        print(f"\n坏账准备合计: {format_number(result['total_provision'])}")
        print(f"综合计提比例: {format_number(result['provision_rate'], 'percent')}")


def cmd_fx(args):
    """汇率风险敞口"""
    data = load_json()

    result = fx_exposure(
        assets=data.get("assets", []),
        liabilities=data.get("liabilities", []),
        base_currency=data.get("base_currency", args.base),
        exchange_rates=data.get("exchange_rates")
    )

    if args.json:
        print_json(result)
    else:
        print(f"\n汇率风险敞口分析")
        print(f"本位币: {result['base_currency']}")
        print("─" * 60)

        # 各币种敞口
        if result["by_currency"]:
            print_table(
                headers=["币种", "资产", "负债", "净敞口", "方向", f"{result['base_currency']}价值"],
                rows=[
                    [
                        currency,
                        format_number(data["assets"]),
                        format_number(data["liabilities"]),
                        format_number(data["net_exposure"]),
                        "多头" if data["exposure_type"] == "long" else "空头" if data["exposure_type"] == "short" else "平衡",
                        format_number(data["base_value"])
                    ]
                    for currency, data in result["by_currency"].items()
                ],
                title="各币种敞口"
            )

        # 敞口汇总
        total = result["total_exposure"]
        print(f"\n敞口汇总:")
        print(f"  总敞口: {format_number(total['gross'])}")
        print(f"  净多头: {format_number(total['net_long'])}")
        print(f"  净空头: {format_number(total['net_short'])}")
        print(f"  净头寸: {format_number(total['net_position'])}")

        # 敏感性分析
        if result["by_currency"]:
            print("\n敏感性分析（汇率变动影响）:")
            for currency, data in result["by_currency"].items():
                sens = data["sensitivity"]
                print(f"  {currency}: ±1%={format_number(sens['1%'])}, ±5%={format_number(sens['5%'])}, ±10%={format_number(sens['10%'])}")

        # 风险评估
        risk = result["risk_assessment"]
        print(f"\n风险等级: {risk['risk_level']}")
        for rec in risk["recommendations"]:
            print(f"  • {rec}")


# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        prog="ri",
        description="Risk - 风险管理工具"
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # credit - 信用评分
    credit_parser = subparsers.add_parser("credit", help="客户信用评分")
    credit_parser.add_argument("--json", action="store_true")
    credit_parser.set_defaults(func=cmd_credit)

    # aging - 账龄分析
    aging_parser = subparsers.add_parser("aging", help="应收账款账龄分析")
    aging_parser.add_argument("--date", help="截止日期 (YYYY-MM-DD)")
    aging_parser.add_argument("--json", action="store_true")
    aging_parser.set_defaults(func=cmd_aging)

    # provision - 坏账准备
    provision_parser = subparsers.add_parser("provision", help="坏账准备计算")
    provision_parser.add_argument("--json", action="store_true")
    provision_parser.set_defaults(func=cmd_provision)

    # fx - 汇率风险
    fx_parser = subparsers.add_parser("fx", help="汇率风险敞口")
    fx_parser.add_argument("--base", default="CNY", help="本位币")
    fx_parser.add_argument("--json", action="store_true")
    fx_parser.set_defaults(func=cmd_fx)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
