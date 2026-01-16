#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger allocation command."""

from __future__ import annotations

from ledger.database import get_db
from ledger.services import (
    create_allocation_rule,
    find_dimension,
    list_allocation_rules,
    run_allocation,
    set_allocation_rule_lines,
)
from ledger.utils import LedgerError, print_json


def add_parser(subparsers, parents):
    parser = subparsers.add_parser("allocation", help="成本分摊", parents=parents)
    sub = parser.add_subparsers(dest="alloc_cmd")

    add_cmd = sub.add_parser("add", help="新增分摊规则", parents=parents)
    add_cmd.add_argument("--name", required=True, help="规则名称")
    add_cmd.add_argument("--source-accounts", required=True, help="来源科目(逗号分隔)")
    add_cmd.add_argument("--target-dim", required=True, help="目标维度 department/project")
    add_cmd.add_argument("--basis", required=True, help="分摊口径 revenue/headcount/area/fixed")
    add_cmd.add_argument("--period", help="期间")
    add_cmd.add_argument("--ratios", help="固定比例: 维度代码:比例,维度代码:比例")
    add_cmd.set_defaults(func=run_add)

    list_cmd = sub.add_parser("list", help="规则列表", parents=parents)
    list_cmd.set_defaults(func=run_list)

    run_cmd = sub.add_parser("run", help="执行分摊", parents=parents)
    run_cmd.add_argument("--rule-id", type=int, required=True, help="规则ID")
    run_cmd.add_argument("--period", required=True, help="期间")
    run_cmd.add_argument("--date", help="凭证日期")
    run_cmd.add_argument("--description", help="摘要")
    run_cmd.set_defaults(func=run_run)

    return parser


def run_add(args):
    source_accounts = [acc.strip() for acc in args.source_accounts.split(",") if acc.strip()]
    with get_db(args.db_path) as conn:
        result = create_allocation_rule(
            conn,
            args.name,
            source_accounts,
            args.target_dim,
            args.basis,
            args.period,
        )
        if args.basis == "fixed":
            if not args.ratios:
                raise LedgerError("ALLOCATION_RATIO_REQUIRED", "固定比例必须提供 ratios")
            lines = []
            for item in args.ratios.split(","):
                if not item.strip():
                    continue
                parts = item.split(":")
                if len(parts) != 2:
                    raise LedgerError("ALLOCATION_RATIO_INVALID", "固定比例格式错误")
                dim_code, ratio = parts[0].strip(), float(parts[1])
                dim_id = find_dimension(conn, args.target_dim, dim_code)
                lines.append((dim_id, ratio))
            set_allocation_rule_lines(conn, result["rule_id"], lines)
        elif args.ratios:
            raise LedgerError("ALLOCATION_RATIO_INVALID", "仅固定比例支持 ratios")
    print_json({"status": "success", **result})


def run_list(args):
    with get_db(args.db_path) as conn:
        rows = list_allocation_rules(conn)
    print_json({"rules": rows})


def run_run(args):
    with get_db(args.db_path) as conn:
        result = run_allocation(conn, args.rule_id, args.period, args.date, args.description)
    print_json({"status": "success", **result})
