#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ac - Accounting/Audit CLI

会计审计命令行工具，提供试算平衡、调整分录、审计抽样、合并报表等功能。

用法:
    ac <command> [options] < input.json

命令:
    tb          试算平衡检查
    adj         调整分录建议
    sample      审计抽样
    consol      合并报表抵消
"""

import sys
import json
import argparse
from typing import Dict, Any, List

from fin_tools.tools.audit_tools import (
    trial_balance,
    adjusting_entries,
    audit_sampling,
    consolidation
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

def cmd_tb(args):
    """试算平衡检查"""
    data = json.load(sys.stdin)

    accounts = data if isinstance(data, list) else data.get("accounts", [])
    tolerance = data.get("tolerance", args.tolerance) if isinstance(data, dict) else args.tolerance

    result = trial_balance(accounts=accounts, tolerance=tolerance)

    if args.json:
        print_json(result)
    else:
        print(f"\n试算平衡检查")
        print("─" * 60)

        # 平衡状态
        status = "✓ 平衡" if result["balanced"] else "✗ 不平衡"
        print(f"\n状态: {status}")
        print(f"借方总额: {format_number(result['total_debit'])}")
        print(f"贷方总额: {format_number(result['total_credit'])}")
        if result["difference"] != 0:
            print(f"差额: {format_number(result['difference'])}")

        # 会计恒等式
        eq = result.get("equation", {})
        if eq:
            eq_status = "✓" if eq.get("balanced", True) else "✗"
            print(f"\n会计恒等式 {eq_status}")
            print(f"  资产: {format_number(eq.get('assets', 0))}")
            print(f"  负债: {format_number(eq.get('liabilities', 0))}")
            print(f"  权益: {format_number(eq.get('equity', 0))}")

        # 按类型汇总
        if result["by_type"]:
            print_table(
                headers=["科目类型", "借方", "贷方", "净额", "科目数"],
                rows=[
                    [
                        acc_type,
                        format_number(data["debit"]),
                        format_number(data["credit"]),
                        format_number(data["net"]),
                        str(data["count"])
                    ]
                    for acc_type, data in result["by_type"].items()
                ],
                title="按类型汇总"
            )

        # 问题
        if result["issues"]:
            print("\n⚠ 问题:")
            for issue in result["issues"]:
                print(f"  • [{issue['type']}] {issue['message']}")

        # 科目明细（有问题的）
        abnormal_accounts = [a for a in result["accounts"] if not a["is_normal"]]
        if abnormal_accounts and not args.brief:
            print_table(
                headers=["科目", "名称", "借方", "贷方", "净额", "警告"],
                rows=[
                    [
                        a["code"],
                        a["name"][:10],
                        format_number(a["debit"]),
                        format_number(a["credit"]),
                        format_number(a["net_balance"]),
                        a["warning"][:15] if a["warning"] else ""
                    ]
                    for a in abnormal_accounts
                ],
                title="异常科目"
            )


def cmd_adj(args):
    """调整分录建议"""
    data = json.load(sys.stdin)

    items = data if isinstance(data, list) else data.get("items", [])
    period_end = data.get("period_end", args.period) if isinstance(data, dict) else args.period

    result = adjusting_entries(items=items, period_end=period_end)

    if args.json:
        print_json(result)
    else:
        print(f"\n调整分录建议")
        if result["period_end"]:
            print(f"期末日期: {result['period_end']}")
        print("─" * 60)

        summary = result["summary"]
        print(f"\n分录数量: {summary['total_entries']}")
        print(f"借方总额: {format_number(summary['total_debit'])}")
        print(f"贷方总额: {format_number(summary['total_credit'])}")

        # 按类型统计
        if summary["by_type"]:
            print("\n按类型:")
            for adj_type, data in summary["by_type"].items():
                print(f"  • {adj_type}: {data['count']}笔, {format_number(data['amount'])}")

        # 分录明细
        for entry in result["entries"]:
            print(f"\n分录 #{entry['entry_no']}: {entry['description']}")
            print(f"  类型: {entry['type']} | 金额: {format_number(entry['amount'])}")

            for line in entry["lines"]:
                if line["debit"] > 0:
                    print(f"    借: {line['account']:<20} {format_number(line['debit'])}")
                if line["credit"] > 0:
                    print(f"    贷: {line['account']:<20} {format_number(line['credit'])}")

            if entry.get("note"):
                print(f"  备注: {entry['note']}")


def cmd_sample(args):
    """审计抽样"""
    data = json.load(sys.stdin)

    population = data if isinstance(data, list) else data.get("population", [])
    method = data.get("method", args.method) if isinstance(data, dict) else args.method
    sample_size = data.get("sample_size", args.size) if isinstance(data, dict) else args.size
    tolerable_error = data.get("tolerable_error", args.tolerable) if isinstance(data, dict) else args.tolerable
    confidence = data.get("confidence_level", args.confidence) if isinstance(data, dict) else args.confidence
    value_field = data.get("value_field", args.value_field) if isinstance(data, dict) else args.value_field
    seed = data.get("seed", args.seed) if isinstance(data, dict) else args.seed

    result = audit_sampling(
        population=population,
        method=method,
        sample_size=sample_size,
        confidence_level=confidence,
        tolerable_error=tolerable_error,
        value_field=value_field,
        seed=seed
    )

    if args.json:
        print_json(result)
    else:
        print(f"\n审计抽样")
        print(f"抽样方法: {result['method']}")
        print("─" * 60)

        print(f"\n总体规模: {result['population_size']}")
        print(f"总体金额: {format_number(result['population_value'])}")
        print(f"样本数量: {result['sample_size']}")
        print(f"样本金额: {format_number(result['sample_value'])}")
        print(f"金额覆盖率: {format_number(result['coverage'], 'percent')}")

        if result["sampling_interval"]:
            print(f"抽样间隔: {format_number(result['sampling_interval'])}")

        # 大额项目
        if result["high_value_items"]:
            print(f"\n大额项目（全部抽取）: {len(result['high_value_items'])}个")

        # 抽样结果
        if not args.brief:
            samples = result["samples"][:20]  # 最多显示20个
            if samples:
                print_table(
                    headers=["ID", "金额", "其他信息"],
                    rows=[
                        [
                            str(s.get("id", s.get("no", "")))[:10],
                            format_number(s.get(value_field, 0)),
                            str(list(s.keys())[:2])[:20]
                        ]
                        for s in samples
                    ],
                    title=f"抽样结果 (前{len(samples)}个)"
                )

            if len(result["samples"]) > 20:
                print(f"\n... 还有 {len(result['samples']) - 20} 个样本")


def cmd_consol(args):
    """合并报表抵消"""
    data = json.load(sys.stdin)

    parent = data.get("parent", {})
    subsidiaries = data.get("subsidiaries", [])
    intercompany = data.get("intercompany", [])
    investments = data.get("investments", [])

    result = consolidation(
        parent=parent,
        subsidiaries=subsidiaries,
        intercompany=intercompany,
        investments=investments
    )

    if args.json:
        print_json(result)
    else:
        print(f"\n合并报表抵消")
        print("─" * 60)

        summary = result["summary"]
        print(f"\n子公司数量: {summary['subsidiaries_count']}")
        print(f"抵消分录数: {summary['elimination_entries']}")
        print(f"内部交易抵消: {format_number(summary['intercompany_eliminated'])}")
        print(f"未实现利润抵消: {format_number(summary['unrealized_profit_eliminated'])}")

        # 合并后金额
        consol = result["consolidated"]
        print_table(
            headers=["项目", "合并金额"],
            rows=[
                ["资产总额", format_number(consol["assets"])],
                ["负债总额", format_number(consol["liabilities"])],
                ["归属母公司权益", format_number(consol["equity"])],
                ["营业收入", format_number(consol["revenue"])],
                ["营业费用", format_number(consol["expenses"])],
                ["归属母公司净利润", format_number(consol["net_income"])],
                ["商誉", format_number(consol["goodwill"])]
            ],
            title="合并后金额"
        )

        # 少数股东权益
        minority = result["minority_interest"]
        print(f"\n少数股东权益: {format_number(minority['equity'])}")
        print(f"少数股东损益: {format_number(minority['income'])}")

        # 抵消分录明细
        if not args.brief:
            for entry in result["eliminations"][:10]:  # 最多显示10个
                print(f"\n抵消分录 #{entry['entry_no']}: {entry['description']}")
                for line in entry["lines"]:
                    if line["debit"] > 0:
                        print(f"  借: {line['account']:<25} {format_number(line['debit'])}")
                    if line["credit"] > 0:
                        print(f"  贷: {line['account']:<25} {format_number(line['credit'])}")

            if len(result["eliminations"]) > 10:
                print(f"\n... 还有 {len(result['eliminations']) - 10} 个抵消分录")


# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        prog="ac",
        description="Accounting/Audit - 会计审计工具"
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # tb - 试算平衡
    tb_parser = subparsers.add_parser("tb", help="试算平衡检查")
    tb_parser.add_argument("--tolerance", type=float, default=0.01, help="允许误差 (默认0.01)")
    tb_parser.add_argument("--brief", action="store_true", help="简洁输出")
    tb_parser.add_argument("--json", action="store_true")
    tb_parser.set_defaults(func=cmd_tb)

    # adj - 调整分录
    adj_parser = subparsers.add_parser("adj", help="调整分录建议")
    adj_parser.add_argument("--period", default="", help="期末日期")
    adj_parser.add_argument("--json", action="store_true")
    adj_parser.set_defaults(func=cmd_adj)

    # sample - 审计抽样
    sample_parser = subparsers.add_parser("sample", help="审计抽样")
    sample_parser.add_argument("--method", default="random",
                               choices=["random", "systematic", "mus", "stratified"],
                               help="抽样方法")
    sample_parser.add_argument("--size", type=int, help="样本量")
    sample_parser.add_argument("--tolerable", type=float, help="可容忍错报")
    sample_parser.add_argument("--confidence", type=float, default=0.95, help="置信水平")
    sample_parser.add_argument("--value-field", default="amount", help="金额字段名")
    sample_parser.add_argument("--seed", type=int, help="随机种子")
    sample_parser.add_argument("--brief", action="store_true", help="简洁输出")
    sample_parser.add_argument("--json", action="store_true")
    sample_parser.set_defaults(func=cmd_sample)

    # consol - 合并报表
    consol_parser = subparsers.add_parser("consol", help="合并报表抵消")
    consol_parser.add_argument("--brief", action="store_true", help="简洁输出")
    consol_parser.add_argument("--json", action="store_true")
    consol_parser.set_defaults(func=cmd_consol)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
