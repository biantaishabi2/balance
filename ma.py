#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ma - Management Accounting CLI

管理会计命令行工具，提供部门损益、产品盈利分析、成本分摊、本量利分析等功能。

用法:
    ma <command> [options] < input.json

命令:
    dept        部门损益表
    product     产品盈利分析
    allocate    成本分摊
    cvp         本量利分析
    breakeven   盈亏平衡点计算
"""

import sys
import json
import argparse
from typing import Dict, Any, List

from fin_tools.tools.management_tools import (
    dept_pnl,
    product_profitability,
    cost_allocation,
    cvp_analysis,
    breakeven
)


# ============================================================
# 输出格式化
# ============================================================

def format_number(value: float, style: str = "auto") -> str:
    """格式化数字"""
    if value is None:
        return "N/A"

    if isinstance(value, float) and (value == float('inf') or value == float('-inf')):
        return "∞"

    abs_val = abs(value)

    if style == "percent":
        return f"{value:.1%}"
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

def cmd_dept(args):
    """部门损益表"""
    data = json.load(sys.stdin)

    result = dept_pnl(
        revenues=data.get("revenues", []),
        direct_costs=data.get("direct_costs", []),
        allocated_costs=data.get("allocated_costs", []),
        departments=data.get("departments")
    )

    if args.json:
        print_json(result, args.compact)
    else:
        # 表格输出
        print_table(
            ["部门", "收入", "直接成本", "贡献毛利", "毛利率", "分摊成本", "营业利润"],
            [
                [
                    dept,
                    format_number(info["revenue"]),
                    format_number(info["direct_costs"]),
                    format_number(info["contribution_margin"]),
                    format_number(info["contribution_margin_rate"], "percent"),
                    format_number(info["allocated_costs"]),
                    format_number(info["operating_profit"])
                ]
                for dept, info in result["by_department"].items()
            ],
            title="📊 部门损益表"
        )

        print(f"\n合计: 收入 {format_number(result['summary']['total_revenue'])} | "
              f"贡献毛利 {format_number(result['summary']['total_contribution'])} | "
              f"营业利润 {format_number(result['summary']['total_operating_profit'])}")
        print(f"贡献排名: {' > '.join(result['ranking'])}")


def cmd_product(args):
    """产品盈利分析"""
    data = json.load(sys.stdin)

    result = product_profitability(
        products=data.get("products", []),
        include_abc=not args.no_abc
    )

    if args.json:
        print_json(result, args.compact)
    else:
        # 表格输出
        rows = []
        for p in result["products"]:
            row = [
                p["name"],
                format_number(p["revenue"]),
                format_number(p["contribution_margin"]),
                format_number(p["cm_ratio"], "percent"),
                format_number(p["net_profit"]),
                p.get("abc_class", "-")
            ]
            rows.append(row)

        print_table(
            ["产品", "收入", "贡献毛利", "毛利率", "净利润", "ABC"],
            rows,
            title="📦 产品盈利分析"
        )

        summary = result["summary"]
        print(f"\n汇总: 总收入 {format_number(summary['total_revenue'])} | "
              f"总贡献毛利 {format_number(summary['total_cm'])} | "
              f"平均毛利率 {format_number(summary['avg_cm_ratio'], 'percent')}")
        print(f"盈利产品: {summary['profitable_count']} | "
              f"亏损产品: {summary['loss_count']} | "
              f"盈亏平衡: {summary['breakeven_count']}")

        if "abc_analysis" in result:
            abc = result["abc_analysis"]
            print(f"\nABC分类: A类({len(abc['A'])}个) B类({len(abc['B'])}个) C类({len(abc['C'])}个)")


def cmd_allocate(args):
    """成本分摊"""
    data = json.load(sys.stdin)

    result = cost_allocation(
        total_cost=data.get("total_cost", 0),
        cost_objects=data.get("cost_objects", []),
        method=args.method,
        drivers=data.get("drivers")
    )

    if args.json:
        print_json(result, args.compact)
    else:
        print(f"\n💰 成本分摊 - {result['method_name']}")
        print("─" * 60)

        print_table(
            ["对象", "分摊金额", "占比"],
            [
                [
                    a["name"],
                    format_number(a["allocated_cost"]),
                    format_number(a["percentage"], "percent")
                ]
                for a in result["allocations"]
            ]
        )

        print(f"\n总分摊: {format_number(result['total_allocated'])}")

        if args.method == "abc" and "variance" in result.get("details", {}):
            variance = result["details"]["variance"]
            if abs(variance) > 0.01:
                print(f"差异: {format_number(variance)} (总成本与分摊总额的差异)")


def cmd_cvp(args):
    """本量利分析"""
    data = json.load(sys.stdin)

    result = cvp_analysis(
        selling_price=data.get("selling_price", 0),
        variable_cost=data.get("variable_cost", 0),
        fixed_costs=data.get("fixed_costs", 0),
        current_volume=data.get("current_volume"),
        target_profit=data.get("target_profit"),
        tax_rate=data.get("tax_rate", 0)
    )

    if args.json:
        print_json(result, args.compact)
    else:
        print("\n📈 本量利分析 (CVP)")
        print("─" * 60)

        # 基本指标
        print(f"单位贡献毛利: {format_number(result['unit_contribution_margin'])}")
        print(f"贡献毛利率: {format_number(result['cm_ratio'], 'percent')}")
        print(f"盈亏平衡销量: {format_number(result['breakeven_units'])} 单位")
        print(f"盈亏平衡销售额: {format_number(result['breakeven_sales'])}")

        # 当前分析
        if "current_analysis" in result:
            ca = result["current_analysis"]
            print(f"\n当前状况 (销量 {ca['volume']:,}):")
            print(f"  收入: {format_number(ca['revenue'])}")
            print(f"  贡献毛利: {format_number(ca['contribution_margin'])}")
            print(f"  营业利润: {format_number(ca['operating_profit'])}")
            print(f"  安全边际: {format_number(ca['margin_of_safety'])} 单位 "
                  f"({format_number(ca['margin_of_safety_rate'], 'percent')})")
            print(f"  经营杠杆: {ca['operating_leverage']:.2f}x")

        # 敏感性分析
        if "sensitivity" in result:
            sens = result["sensitivity"]
            print("\n敏感性分析:")
            for key in ["price", "volume", "variable_cost"]:
                if key in sens.get("interpretation", {}):
                    print(f"  • {sens['interpretation'][key]}")

        # 目标利润
        if "target_analysis" in result:
            ta = result["target_analysis"]
            if "error" not in ta:
                print(f"\n目标利润 {format_number(ta['target_profit'])}:")
                print(f"  需要销量: {format_number(ta['required_volume'])} 单位")
                print(f"  需要销售额: {format_number(ta['required_sales'])}")
                if ta.get("additional_volume") is not None:
                    print(f"  需增加销量: {format_number(ta['additional_volume'])} 单位")


def cmd_breakeven(args):
    """盈亏平衡点计算"""
    data = json.load(sys.stdin)

    result = breakeven(
        products=data.get("products", []),
        fixed_costs=data.get("fixed_costs", 0),
        method=args.method
    )

    if args.json:
        print_json(result, args.compact)
    else:
        print(f"\n⚖️ 盈亏平衡分析 - {result['method_name']}")
        print("─" * 60)

        print_table(
            ["产品", "单位毛利", "毛利率", "平衡销量", "平衡销售额"],
            [
                [
                    p["name"],
                    format_number(p["unit_cm"]),
                    format_number(p["cm_ratio"], "percent"),
                    format_number(p["breakeven_units"]),
                    format_number(p["breakeven_sales"])
                ]
                for p in result["by_product"]
            ]
        )

        print(f"\n固定成本: {format_number(result['fixed_costs'])}")
        print(f"综合盈亏平衡销售额: {format_number(result['breakeven_sales'])}")

        if "weighted_avg_cm_ratio" in result:
            print(f"加权平均贡献毛利率: {format_number(result['weighted_avg_cm_ratio'], 'percent')}")

        print(f"\n{result['analysis']}")


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        prog="ma",
        description="管理会计命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  echo '{"revenues":[{"dept":"销售部","amount":1000000}],...}' | ma dept
  echo '{"products":[{"name":"A","revenue":100000,"variable_costs":40000}]}' | ma product
  echo '{"total_cost":100000,"cost_objects":[...]}' | ma allocate --method abc
  echo '{"selling_price":100,"variable_cost":60,"fixed_costs":200000}' | ma cvp
  echo '{"products":[...],"fixed_costs":200000}' | ma breakeven
        """
    )
    parser.add_argument("--json", action="store_true", help="输出JSON格式")
    parser.add_argument("--compact", action="store_true", help="紧凑JSON输出")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # dept - 部门损益表
    p_dept = subparsers.add_parser("dept", help="部门损益表")
    p_dept.add_argument("--json", action="store_true", help="输出JSON格式")
    p_dept.add_argument("--compact", action="store_true", help="紧凑JSON输出")
    p_dept.set_defaults(func=cmd_dept)

    # product - 产品盈利分析
    p_product = subparsers.add_parser("product", help="产品盈利分析")
    p_product.add_argument("--json", action="store_true", help="输出JSON格式")
    p_product.add_argument("--compact", action="store_true", help="紧凑JSON输出")
    p_product.add_argument("--no-abc", action="store_true", help="不进行ABC分类")
    p_product.set_defaults(func=cmd_product)

    # allocate - 成本分摊
    p_allocate = subparsers.add_parser("allocate", help="成本分摊")
    p_allocate.add_argument("--method", choices=["direct", "step", "abc"],
                            default="direct", help="分摊方法")
    p_allocate.add_argument("--json", action="store_true", help="输出JSON格式")
    p_allocate.add_argument("--compact", action="store_true", help="紧凑JSON输出")
    p_allocate.set_defaults(func=cmd_allocate)

    # cvp - 本量利分析
    p_cvp = subparsers.add_parser("cvp", help="本量利分析")
    p_cvp.add_argument("--json", action="store_true", help="输出JSON格式")
    p_cvp.add_argument("--compact", action="store_true", help="紧凑JSON输出")
    p_cvp.set_defaults(func=cmd_cvp)

    # breakeven - 盈亏平衡点
    p_breakeven = subparsers.add_parser("breakeven", help="盈亏平衡点计算")
    p_breakeven.add_argument("--method", choices=["weighted_avg", "sequential"],
                             default="weighted_avg", help="计算方法")
    p_breakeven.add_argument("--json", action="store_true", help="输出JSON格式")
    p_breakeven.add_argument("--compact", action="store_true", help="紧凑JSON输出")
    p_breakeven.set_defaults(func=cmd_breakeven)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    try:
        args.func(args)
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyError as e:
        print(f"缺少必要字段: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
