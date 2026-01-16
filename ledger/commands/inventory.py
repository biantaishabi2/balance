#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger inventory command."""

from __future__ import annotations

from datetime import datetime

from ledger.database import get_db
from ledger.services import (
    inventory_balance,
    inventory_move_in,
    inventory_move_out,
    reconcile_inventory,
)
from ledger.utils import print_json


def _default_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def add_parser(subparsers, parents):
    parser = subparsers.add_parser("inventory", help="存货核算", parents=parents)
    sub = parser.add_subparsers(dest="inv_cmd")

    in_cmd = sub.add_parser("in", help="入库", parents=parents)
    in_cmd.add_argument("--sku", required=True, help="物料编码")
    in_cmd.add_argument("--qty", type=float, required=True, help="数量")
    in_cmd.add_argument("--unit-cost", type=float, required=True, help="单位成本")
    in_cmd.add_argument("--date", default=_default_date(), help="业务日期")
    in_cmd.add_argument("--name", help="物料名称")
    in_cmd.add_argument("--unit", help="单位")
    in_cmd.add_argument("--description", help="摘要")
    in_cmd.set_defaults(func=run_in)

    out_cmd = sub.add_parser("out", help="出库", parents=parents)
    out_cmd.add_argument("--sku", required=True, help="物料编码")
    out_cmd.add_argument("--qty", type=float, required=True, help="数量")
    out_cmd.add_argument("--date", default=_default_date(), help="业务日期")
    out_cmd.add_argument("--description", help="摘要")
    out_cmd.set_defaults(func=run_out)

    balance_cmd = sub.add_parser("balance", help="结存查询", parents=parents)
    balance_cmd.add_argument("--period", required=True, help="期间")
    balance_cmd.add_argument("--sku", help="物料编码")
    balance_cmd.set_defaults(func=run_balance)

    reconcile_cmd = sub.add_parser("reconcile", help="存货对平", parents=parents)
    reconcile_cmd.add_argument("--period", required=True, help="期间")
    reconcile_cmd.set_defaults(func=run_reconcile)

    return parser


def run_in(args):
    with get_db(args.db_path) as conn:
        result = inventory_move_in(
            conn,
            args.sku,
            args.qty,
            args.unit_cost,
            args.date,
            args.description,
            args.name,
            args.unit,
        )
    print_json({"status": "success", **result})


def run_out(args):
    with get_db(args.db_path) as conn:
        result = inventory_move_out(
            conn,
            args.sku,
            args.qty,
            args.date,
            args.description,
        )
    print_json({"status": "success", **result})


def run_balance(args):
    with get_db(args.db_path) as conn:
        rows = inventory_balance(conn, args.period, args.sku)
    print_json({"period": args.period, "balances": rows})


def run_reconcile(args):
    with get_db(args.db_path) as conn:
        result = reconcile_inventory(conn, args.period)
    print_json({"status": "success", **result})
