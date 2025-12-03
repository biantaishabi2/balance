#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tx - Tax CLI

税务筹划命令行工具，提供增值税、所得税计算及优化功能。

用法:
    tx <command> [options] < input.json

命令:
    vat         增值税计算
    cit         企业所得税计算
    iit         个人所得税计算
    bonus       年终奖优化
    rd          研发加计扣除
    burden      综合税负分析
"""

import sys
import json
import argparse
from typing import Dict, Any, List

from fin_tools.tools.tax_tools import (
    vat_calc,
    cit_calc,
    iit_calc,
    bonus_optimize,
    rd_deduction,
    tax_burden
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

def cmd_vat(args):
    """增值税计算"""
    data = json.load(sys.stdin)

    result = vat_calc(
        sales=data.get("sales", []),
        purchases=data.get("purchases", []),
        taxpayer_type=data.get("taxpayer_type", args.type)
    )

    if args.json:
        print_json(result)
    else:
        print(f"\n增值税计算 ({result['taxpayer_type']})")
        print("─" * 60)

        print(f"\n销项税额: {format_number(result['output_tax'])}")
        print(f"进项税额: {format_number(result['input_tax'])}")
        print(f"应纳税额: {format_number(result['tax_payable'])}")
        print(f"税负率: {format_number(result['tax_burden_rate'], 'percent')}")


def cmd_cit(args):
    """企业所得税计算"""
    data = json.load(sys.stdin)

    result = cit_calc(
        accounting_profit=data.get("accounting_profit", data.get("profit", 0)),
        adjustments=data.get("adjustments"),
        preference=data.get("preference", args.preference),
        prior_year_loss=data.get("prior_year_loss", 0)
    )

    if args.json:
        print_json(result)
    else:
        print(f"\n企业所得税计算")
        print("─" * 60)

        print(f"\n会计利润: {format_number(result['accounting_profit'])}")

        if result["adjustments"]["add_total"] > 0 or result["adjustments"]["subtract_total"] > 0:
            print(f"纳税调增: {format_number(result['adjustments']['add_total'])}")
            print(f"纳税调减: {format_number(result['adjustments']['subtract_total'])}")

        if result["prior_year_loss"] > 0:
            print(f"弥补亏损: {format_number(result['prior_year_loss'])}")

        print(f"\n应纳税所得额: {format_number(result['taxable_income'])}")
        print(f"优惠政策: {result['preference']}")
        print(f"适用税率: {format_number(result['tax_rate'], 'percent')}")
        print(f"应纳税额: {format_number(result['tax_payable'])}")
        print(f"实际税负: {format_number(result['effective_rate'], 'percent')}")


def cmd_iit(args):
    """个人所得税计算"""
    data = json.load(sys.stdin)

    result = iit_calc(
        annual_salary=data.get("annual_salary", data.get("salary", 0)),
        social_insurance=data.get("social_insurance", 0),
        housing_fund=data.get("housing_fund", 0),
        special_deductions=data.get("special_deductions", 0),
        other_deductions=data.get("other_deductions", 0)
    )

    if args.json:
        print_json(result)
    else:
        print(f"\n个人所得税计算（综合所得）")
        print("─" * 60)

        print(f"\n年收入: {format_number(result['gross_income'])}")
        print(f"\n扣除项:")
        print(f"  基本扣除: {format_number(result['deductions']['basic'])}")
        print(f"  社保: {format_number(result['deductions']['social_insurance'])}")
        print(f"  公积金: {format_number(result['deductions']['housing_fund'])}")
        print(f"  专项附加: {format_number(result['deductions']['special'])}")
        print(f"  扣除合计: {format_number(result['deductions']['total'])}")

        print(f"\n应纳税所得额: {format_number(result['taxable_income'])}")
        print(f"适用税率: {format_number(result['tax_rate'], 'percent')}")
        print(f"速算扣除: {format_number(result['quick_deduction'])}")
        print(f"应纳税额: {format_number(result['tax_payable'])}")
        print(f"税后收入: {format_number(result['net_income'])}")
        print(f"实际税率: {format_number(result['effective_rate'], 'percent')}")


def cmd_bonus(args):
    """年终奖优化"""
    data = json.load(sys.stdin)

    result = bonus_optimize(
        annual_salary=data.get("annual_salary", data.get("salary", 0)),
        total_bonus=data.get("total_bonus", data.get("bonus", 0)),
        social_insurance=data.get("social_insurance", 0),
        housing_fund=data.get("housing_fund", 0),
        special_deductions=data.get("special_deductions", 0)
    )

    if args.json:
        print_json(result)
    else:
        print(f"\n年终奖优化方案")
        print("─" * 60)

        print(f"\n年薪: {format_number(result['inputs']['annual_salary'])}")
        print(f"年终奖: {format_number(result['inputs']['total_bonus'])}")

        # 方案对比
        print_table(
            headers=["方案", "工资税", "年终奖税", "总税负"],
            rows=[
                [
                    s["method"],
                    format_number(s["salary_tax"]),
                    format_number(s.get("bonus_tax", 0)),
                    format_number(s["total_tax"])
                ]
                for s in result["scenarios"]
            ],
            title="方案对比"
        )

        # 推荐
        print(f"\n✓ 推荐方案: {result['recommendation']}")
        print(f"  最低税负: {format_number(result['optimal']['total_tax'])}")
        print(f"  可节税: {format_number(result['tax_saved'])}")

        if result["optimal"].get("bonus_separate"):
            print(f"  年终奖单独计税: {format_number(result['optimal']['bonus_separate'])}")
            print(f"  并入综合所得: {format_number(result['optimal']['bonus_combined'])}")


def cmd_rd(args):
    """研发加计扣除"""
    data = json.load(sys.stdin)

    result = rd_deduction(
        rd_expenses=data.get("rd_expenses", data.get("expenses", {})),
        industry=data.get("industry", args.industry)
    )

    if args.json:
        print_json(result)
    else:
        print(f"\n研发加计扣除计算")
        print("─" * 60)

        print(f"\n研发费用合计: {format_number(result['total_rd_expense'])}")
        print(f"可加计金额: {format_number(result['eligible_expense'])}")
        print(f"加计比例: {format_number(result['deduction_rate'], 'percent')}")
        print(f"加计扣除额: {format_number(result['additional_deduction'])}")
        print(f"\n节税金额:")
        print(f"  按25%税率: {format_number(result['tax_saving_25'])}")
        print(f"  按15%税率: {format_number(result['tax_saving_15'])} (高新技术企业)")


def cmd_burden(args):
    """综合税负分析"""
    data = json.load(sys.stdin)

    result = tax_burden(
        revenue=data.get("revenue", 0),
        vat_payable=data.get("vat", data.get("vat_payable", 0)),
        cit_payable=data.get("cit", data.get("cit_payable", 0)),
        other_taxes=data.get("other_taxes", {})
    )

    if args.json:
        print_json(result)
    else:
        print(f"\n综合税负分析")
        print("─" * 60)

        print(f"\n营业收入: {format_number(result['revenue'])}")
        print(f"税费总额: {format_number(result['total_tax'])}")
        print(f"综合税负率: {format_number(result['burden_rate'], 'percent')}")

        # 税种构成
        print_table(
            headers=["税种", "金额", "占比"],
            rows=[
                [k, format_number(v), format_number(result["composition"].get(k, 0), "percent")]
                for k, v in result["breakdown"].items()
            ],
            title="税费构成"
        )

        print(f"\n分析: {result['analysis']}")


# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        prog="tx",
        description="Tax - 税务筹划工具"
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # vat - 增值税
    vat_parser = subparsers.add_parser("vat", help="增值税计算")
    vat_parser.add_argument("--type", default="general",
                           choices=["general", "small_scale"],
                           help="纳税人类型")
    vat_parser.add_argument("--json", action="store_true")
    vat_parser.set_defaults(func=cmd_vat)

    # cit - 企业所得税
    cit_parser = subparsers.add_parser("cit", help="企业所得税计算")
    cit_parser.add_argument("--preference", default="standard",
                           choices=["standard", "high_tech", "small_low_profit", "western"],
                           help="优惠政策")
    cit_parser.add_argument("--json", action="store_true")
    cit_parser.set_defaults(func=cmd_cit)

    # iit - 个人所得税
    iit_parser = subparsers.add_parser("iit", help="个人所得税计算")
    iit_parser.add_argument("--json", action="store_true")
    iit_parser.set_defaults(func=cmd_iit)

    # bonus - 年终奖优化
    bonus_parser = subparsers.add_parser("bonus", help="年终奖优化")
    bonus_parser.add_argument("--json", action="store_true")
    bonus_parser.set_defaults(func=cmd_bonus)

    # rd - 研发加计扣除
    rd_parser = subparsers.add_parser("rd", help="研发加计扣除")
    rd_parser.add_argument("--industry", default="manufacturing",
                          choices=["manufacturing", "other"],
                          help="行业")
    rd_parser.add_argument("--json", action="store_true")
    rd_parser.set_defaults(func=cmd_rd)

    # burden - 综合税负
    burden_parser = subparsers.add_parser("burden", help="综合税负分析")
    burden_parser.add_argument("--json", action="store_true")
    burden_parser.set_defaults(func=cmd_burden)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
