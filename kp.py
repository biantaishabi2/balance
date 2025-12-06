#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kp - KPI/Performance CLI

绩效考核命令行工具，提供KPI仪表盘、EVA计算、平衡计分卡、OKR追踪等功能。

用法:
    kp <command> [options] < input.json

命令:
    kpi         KPI仪表盘
    eva         经济增加值计算
    bsc         平衡计分卡
    okr         OKR进度追踪
"""

import sys
import json
import argparse
from typing import Dict, Any, List

from fin_tools.tools.performance_tools import (
    kpi_dashboard,
    eva_calc,
    balanced_scorecard,
    okr_progress
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
        return f"{value:.1%}"
    elif style == "score":
        return f"{value:.1f}"
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


def status_icon(status: str) -> str:
    """状态图标"""
    icons = {
        "exceeded": "★",
        "on_target": "✓",
        "at_risk": "△",
        "behind": "✗",
        "on_track": "✓"
    }
    return icons.get(status, "○")


# ============================================================
# 命令处理
# ============================================================

def cmd_kpi(args):
    """KPI仪表盘"""
    data = load_json()

    kpis = data if isinstance(data, list) else data.get("kpis", [])
    period = data.get("period", args.period) if isinstance(data, dict) else args.period

    result = kpi_dashboard(kpis=kpis, period=period)

    if args.json:
        print_json(result)
    else:
        print(f"\nKPI 仪表盘")
        if result["period"]:
            print(f"考核期间: {result['period']}")
        print("─" * 60)

        summary = result["summary"]
        print(f"\n综合得分: {format_number(summary['overall_score'], 'score')}")
        print(f"加权得分: {format_number(summary['weighted_score'], 'score')}")
        print(f"\n状态分布: ★超额{summary['exceeded']} ✓达标{summary['on_target']} △风险{summary['at_risk']} ✗落后{summary['behind']}")

        # KPI明细
        print_table(
            headers=["KPI", "目标", "实际", "完成率", "得分", "状态"],
            rows=[
                [
                    kpi["name"][:12],
                    format_number(kpi["target"]),
                    format_number(kpi["actual"]),
                    format_number(kpi["completion_rate"], "percent"),
                    format_number(kpi["score"], "score"),
                    status_icon(kpi["status"])
                ]
                for kpi in result["kpis"]
            ],
            title="KPI明细"
        )

        # 亮点和关注
        if result["highlights"]:
            print("\n★ 亮点:")
            for h in result["highlights"]:
                print(f"  • {h}")

        if result["concerns"]:
            print("\n△ 关注项:")
            for c in result["concerns"]:
                print(f"  • {c}")


def cmd_eva(args):
    """经济增加值计算"""
    data = load_json()

    result = eva_calc(
        nopat=data.get("nopat", 0),
        invested_capital=data.get("invested_capital", data.get("capital", 0)),
        wacc=data.get("wacc", args.wacc),
        adjustments=data.get("adjustments")
    )

    if args.json:
        print_json(result)
    else:
        print(f"\n经济增加值 (EVA) 计算")
        print("─" * 60)

        print(f"\n税后净营业利润 (NOPAT): {format_number(result['nopat'])}")
        if result["adjustments"]:
            print(f"调整后 NOPAT: {format_number(result['adjusted_nopat'])}")

        print(f"\n投入资本: {format_number(result['invested_capital'])}")
        if result["adjusted_capital"] != result["invested_capital"]:
            print(f"调整后资本: {format_number(result['adjusted_capital'])}")

        print(f"\nWACC: {format_number(result['wacc'], 'percent')}")
        print(f"资本费用: {format_number(result['capital_charge'])}")

        print(f"\n{'='*40}")
        eva_value = result["eva"]
        eva_sign = "+" if eva_value >= 0 else ""
        print(f"EVA = {eva_sign}{format_number(eva_value)}")
        print(f"{'='*40}")

        print(f"\nROIC: {format_number(result['roic'], 'percent')}")
        print(f"EVA利差: {format_number(result['eva_spread'], 'percent')}")
        print(f"价值创造: {'是 ✓' if result['value_created'] else '否 ✗'}")

        print(f"\n分析: {result['analysis']}")


def cmd_bsc(args):
    """平衡计分卡"""
    data = load_json()

    perspectives = data.get("perspectives", data)
    weights = data.get("weights")

    result = balanced_scorecard(perspectives=perspectives, weights=weights)

    if args.json:
        print_json(result)
    else:
        print(f"\n平衡计分卡 (BSC)")
        print("─" * 60)

        print(f"\n综合得分: {format_number(result['overall_score'], 'score')}")

        # 各维度得分
        print_table(
            headers=["维度", "得分", "权重", "加权得分", "状态"],
            rows=[
                [
                    perspective,
                    format_number(data["score"], "score"),
                    format_number(data["weight"], "percent"),
                    format_number(data["weighted_score"], "score"),
                    data["status"]
                ]
                for perspective, data in result["perspectives"].items()
            ],
            title="维度得分"
        )

        # 各维度指标明细
        for perspective, data in result["perspectives"].items():
            if data["metrics"]:
                print_table(
                    headers=["指标", "目标", "实际", "完成率", "得分"],
                    rows=[
                        [
                            m["name"][:15],
                            format_number(m["target"]),
                            format_number(m["actual"]),
                            format_number(m["completion"], "percent"),
                            format_number(m["score"], "score")
                        ]
                        for m in data["metrics"]
                    ],
                    title=f"{perspective}维度"
                )

        # 优势和劣势
        if result["strengths"]:
            print(f"\n✓ 优势维度: {', '.join(result['strengths'])}")
        if result["weaknesses"]:
            print(f"△ 待改进维度: {', '.join(result['weaknesses'])}")

        # 建议
        if result["recommendations"]:
            print("\n建议:")
            for rec in result["recommendations"]:
                print(f"  • {rec}")


def cmd_okr(args):
    """OKR进度追踪"""
    data = load_json()

    objectives = data if isinstance(data, list) else data.get("objectives", [])
    method = data.get("scoring_method", args.method) if isinstance(data, dict) else args.method

    result = okr_progress(objectives=objectives, scoring_method=method)

    if args.json:
        print_json(result)
    else:
        print(f"\nOKR 进度追踪")
        print(f"评分方法: {result['scoring_method']}")
        print("─" * 60)

        summary = result["summary"]
        print(f"\n目标总数: {summary['total_objectives']}")
        print(f"KR总数: {summary['total_krs']}")
        print(f"平均进度: {format_number(summary['avg_progress'], 'percent')}")
        print(f"状态: ✓正常{summary['on_track']} △风险{summary['at_risk']} ✗落后{summary['behind']}")

        # 目标明细
        for obj in result["objectives"]:
            print(f"\n{status_icon(obj['status'])} {obj['objective']}")
            print(f"  负责人: {obj['owner']} | 进度: {format_number(obj['progress'], 'percent')} | 得分: {format_number(obj['score'], 'percent')}")

            for kr in obj["key_results"]:
                kr_status = "✓" if kr["progress"] >= 0.9 else "△" if kr["progress"] >= 0.7 else "○"
                print(f"    {kr_status} {kr['kr']}: {kr['actual']}/{kr['target']} ({format_number(kr['progress'], 'percent')})")

        # 按负责人
        if len(result["by_owner"]) > 1:
            print_table(
                headers=["负责人", "目标数", "平均进度"],
                rows=[
                    [owner, str(data["count"]), format_number(data["avg_progress"], "percent")]
                    for owner, data in result["by_owner"].items()
                ],
                title="按负责人汇总"
            )

        # 建议
        if result["recommendations"]:
            print("\n建议:")
            for rec in result["recommendations"]:
                print(f"  • {rec}")


# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        prog="kp",
        description="KPI/Performance - 绩效考核工具"
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # kpi - KPI仪表盘
    kpi_parser = subparsers.add_parser("kpi", help="KPI仪表盘")
    kpi_parser.add_argument("--period", default="", help="考核期间")
    kpi_parser.add_argument("--json", action="store_true")
    kpi_parser.set_defaults(func=cmd_kpi)

    # eva - 经济增加值
    eva_parser = subparsers.add_parser("eva", help="经济增加值计算")
    eva_parser.add_argument("--wacc", type=float, default=0.10, help="WACC (默认10%%)")
    eva_parser.add_argument("--json", action="store_true")
    eva_parser.set_defaults(func=cmd_eva)

    # bsc - 平衡计分卡
    bsc_parser = subparsers.add_parser("bsc", help="平衡计分卡")
    bsc_parser.add_argument("--json", action="store_true")
    bsc_parser.set_defaults(func=cmd_bsc)

    # okr - OKR进度
    okr_parser = subparsers.add_parser("okr", help="OKR进度追踪")
    okr_parser.add_argument("--method", default="average",
                           choices=["average", "google"],
                           help="评分方法")
    okr_parser.add_argument("--json", action="store_true")
    okr_parser.set_defaults(func=cmd_okr)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
