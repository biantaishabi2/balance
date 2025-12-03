#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fa - Financial Analysis CLI

财务分析命令行工具，提供预算分析、趋势分析等功能。

用法:
    fa <command> [options] < input.json

命令:
    variance    预算差异分析
    flex        弹性预算
    forecast    滚动预测
    trend       趋势分析
"""

import sys
import json
import argparse
from typing import Dict, Any, List

from fin_tools.tools.budget_tools import (
    variance_analysis,
    flex_budget,
    rolling_forecast,
    trend_analysis
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

def cmd_variance(args):
    """预算差异分析"""
    data = json.load(sys.stdin)

    budget = data.get("budget", {})
    actual = data.get("actual", {})
    threshold = data.get("threshold", args.threshold)
    account_types = data.get("account_types")

    result = variance_analysis(
        budget=budget,
        actual=actual,
        threshold=threshold,
        account_types=account_types
    )

    if args.json:
        print_json(result)
    else:
        # 表格输出
        print_table(
            headers=["科目", "预算", "实际", "差异", "差异%", "状态"],
            rows=[
                [
                    v["account"],
                    format_number(v["budget"]),
                    format_number(v["actual"]),
                    format_number(v["variance"]),
                    format_number(v["variance_pct"], "percent") if v["variance_pct"] else "N/A",
                    "✓ 有利" if v["is_favorable"] else "✗ 不利"
                ]
                for v in result["variances"]
            ],
            title="预算差异分析"
        )

        # 汇总
        summary = result["summary"]
        print(f"\n汇总:")
        print(f"  预算合计: {format_number(summary['total_budget'])}")
        print(f"  实际合计: {format_number(summary['total_actual'])}")
        print(f"  总差异: {format_number(summary['total_variance'])} ({format_number(summary['total_variance_pct'], 'percent')})")
        print(f"  重大差异项: {len(result['significant_items'])} 项 (阈值: {threshold:.0%})")


def cmd_flex(args):
    """弹性预算"""
    data = json.load(sys.stdin)

    original_budget = data.get("original_budget", data.get("budget", {}))
    budget_volume = data.get("budget_volume", 0)
    actual_volume = data.get("actual_volume", 0)
    cost_behavior = data.get("cost_behavior", {})
    actual = data.get("actual")

    result = flex_budget(
        original_budget=original_budget,
        budget_volume=budget_volume,
        actual_volume=actual_volume,
        cost_behavior=cost_behavior,
        actual=actual
    )

    if args.json:
        print_json(result)
    else:
        print(f"\n弹性预算分析")
        print("─" * 60)
        print(f"预算业务量: {budget_volume:,.0f}")
        print(f"实际业务量: {actual_volume:,.0f}")
        print(f"业务量比率: {result['volume_ratio']:.2%}")

        # 调整明细
        print_table(
            headers=["科目", "原预算", "弹性预算", "调整额", "成本性态"],
            rows=[
                [
                    a["account"],
                    format_number(a["original"]),
                    format_number(a["flexed"]),
                    format_number(a["adjustment"]),
                    a["behavior"]
                ]
                for a in result["adjustments"]
            ],
            title="弹性预算调整"
        )

        print(f"\n合计: {format_number(result['total_original'])} → {format_number(result['total_flexed'])}")

        if "variances" in result:
            v = result["variances"]
            print(f"\n差异分解:")
            print(f"  业务量差异: {format_number(v['volume_variance'])}")
            print(f"  效率差异: {format_number(v['efficiency_variance'])}")
            print(f"  总差异: {format_number(v['total_variance'])}")


def cmd_forecast(args):
    """滚动预测"""
    data = json.load(sys.stdin)

    historical_data = data.get("historical_data", data.get("data", []))
    periods = data.get("periods", args.periods)
    method = data.get("method", args.method)
    window = data.get("window", args.window)

    result = rolling_forecast(
        historical_data=historical_data,
        periods=periods,
        method=method,
        window=window
    )

    if "error" in result:
        print(f"错误: {result['error']}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print_json(result)
    else:
        print(f"\n滚动预测 (方法: {method}, 预测期数: {periods})")
        print("─" * 60)

        # 历史+预测数据表格
        metrics = result["metrics"]
        headers = ["期间"] + metrics
        rows = []

        # 添加历史数据
        for d in historical_data:
            row = [d.get("period", "")]
            for m in metrics:
                row.append(format_number(d.get(m, 0)))
            rows.append(row)

        # 添加预测数据（带标记）
        for f in result["forecast"]:
            row = [f"→ {f['period']}"]
            for m in metrics:
                row.append(format_number(f.get(m, 0)))
            rows.append(row)

        print_table(headers, rows, "历史数据 + 预测")

        # 趋势信息
        if result.get("trend"):
            print("\n趋势分析:")
            for m, t in result.get("trend", {}).items():
                direction_icon = {"up": "↑", "down": "↓", "stable": "→"}.get(t["direction"], "?")
                avg_growth = t.get('avg_growth', 0)
                print(f"  {m}: {direction_icon} {t['direction']} (平均增长: {avg_growth:.1%})")


def cmd_trend(args):
    """趋势分析"""
    data = json.load(sys.stdin)

    periods_data = data.get("periods_data", data.get("data", []))
    base_period = data.get("base_period", args.base)
    metrics = data.get("metrics")

    result = trend_analysis(
        periods_data=periods_data,
        base_period=base_period,
        metrics=metrics
    )

    if "error" in result:
        print(f"错误: {result['error']}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print_json(result)
    else:
        print(f"\n趋势分析 (基期: {result['base_period']})")
        print("─" * 60)

        for metric, analysis in result["analysis"].items():
            print(f"\n【{metric}】")

            # 数值和指数表
            headers = ["期间"] + result["periods"]
            rows = [
                ["数值"] + [format_number(v) for v in analysis["values"]],
                ["同比"] + [format_number(g, "percent") if g else "-" for g in analysis["yoy_growth"]],
                ["指数"] + [f"{v:.1f}" for v in analysis["indexed"]]
            ]

            for row in rows:
                print("  " + "  ".join(str(c).rjust(10) for c in row))

            # 趋势汇总
            direction_icon = {"up": "↑", "down": "↓", "stable": "→"}.get(analysis["trend"], "?")
            print(f"\n  趋势: {direction_icon} {analysis['trend']}")
            if analysis["cagr"] is not None:
                print(f"  CAGR: {analysis['cagr']:.1%}")
            print(f"  波动性: {analysis['volatility']:.2%}")
            print(f"  区间: {format_number(analysis['min'])} ~ {format_number(analysis['max'])}")


# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        prog="fa",
        description="Financial Analysis - 财务分析工具"
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # variance - 预算差异
    variance_parser = subparsers.add_parser("variance", help="预算差异分析")
    variance_parser.add_argument("--threshold", type=float, default=0.10,
                                help="重大差异阈值 (默认: 0.10)")
    variance_parser.add_argument("--json", action="store_true",
                                help="JSON格式输出")
    variance_parser.set_defaults(func=cmd_variance)

    # flex - 弹性预算
    flex_parser = subparsers.add_parser("flex", help="弹性预算")
    flex_parser.add_argument("--json", action="store_true",
                            help="JSON格式输出")
    flex_parser.set_defaults(func=cmd_flex)

    # forecast - 滚动预测
    forecast_parser = subparsers.add_parser("forecast", help="滚动预测")
    forecast_parser.add_argument("--periods", type=int, default=3,
                                help="预测期数 (默认: 3)")
    forecast_parser.add_argument("--method", default="moving_avg",
                                choices=["moving_avg", "weighted_avg", "linear", "growth_rate"],
                                help="预测方法")
    forecast_parser.add_argument("--window", type=int, default=3,
                                help="移动平均窗口 (默认: 3)")
    forecast_parser.add_argument("--json", action="store_true",
                                help="JSON格式输出")
    forecast_parser.set_defaults(func=cmd_forecast)

    # trend - 趋势分析
    trend_parser = subparsers.add_parser("trend", help="趋势分析")
    trend_parser.add_argument("--base", type=int, default=0,
                             help="基期索引 (默认: 0)")
    trend_parser.add_argument("--json", action="store_true",
                             help="JSON格式输出")
    trend_parser.set_defaults(func=cmd_trend)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
