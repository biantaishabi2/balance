#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger ar command."""

from __future__ import annotations

from datetime import datetime

from ledger.database import get_db
from ledger.services import add_ar_item, ar_aging, list_ar_items, settle_ar_item
from ledger.utils import print_json


def _default_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def add_parser(subparsers, parents):
    parser = subparsers.add_parser("ar", help="应收管理", parents=parents)
    sub = parser.add_subparsers(dest="ar_cmd")

    add_cmd = sub.add_parser("add", help="新增应收", parents=parents)
    add_cmd.add_argument("--customer", required=True, help="客户维度代码")
    add_cmd.add_argument("--amount", type=float, required=True, help="应收金额")
    add_cmd.add_argument("--date", default=_default_date(), help="业务日期")
    add_cmd.add_argument("--description", help="摘要")
    add_cmd.set_defaults(func=run_add)

    settle_cmd = sub.add_parser("settle", help="应收核销", parents=parents)
    settle_cmd.add_argument("--item-id", type=int, required=True, help="应收ID")
    settle_cmd.add_argument("--amount", type=float, required=True, help="核销金额")
    settle_cmd.add_argument("--date", default=_default_date(), help="核销日期")
    settle_cmd.add_argument("--description", help="摘要")
    settle_cmd.set_defaults(func=run_settle)

    list_cmd = sub.add_parser("list", help="应收列表", parents=parents)
    list_cmd.add_argument("--status", default="open", help="状态: open/settled/all")
    list_cmd.set_defaults(func=run_list)

    aging_cmd = sub.add_parser("aging", help="应收账龄", parents=parents)
    aging_cmd.add_argument("--as-of", default=_default_date(), help="截止日期")
    aging_cmd.set_defaults(func=run_aging)

    return parser


def run_add(args):
    with get_db(args.db_path) as conn:
        result = add_ar_item(
            conn,
            args.customer,
            args.amount,
            args.date,
            args.description,
        )
    print_json({"status": "success", **result})


def run_settle(args):
    with get_db(args.db_path) as conn:
        result = settle_ar_item(
            conn,
            args.item_id,
            args.amount,
            args.date,
            args.description,
        )
    print_json({"status": "success", **result})


def run_list(args):
    with get_db(args.db_path) as conn:
        rows = list_ar_items(conn, args.status)
    print_json({"items": rows})


def run_aging(args):
    with get_db(args.db_path) as conn:
        buckets = ar_aging(conn, args.as_of)
    print_json({"as_of": args.as_of, "aging": buckets})
