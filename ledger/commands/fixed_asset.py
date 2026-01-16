#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger fixed asset command."""

from __future__ import annotations

from datetime import datetime

from ledger.database import get_db
from ledger.services import (
    add_fixed_asset,
    depreciate_assets,
    dispose_fixed_asset,
    list_fixed_assets,
    reconcile_fixed_assets,
)
from ledger.utils import print_json


def _default_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def add_parser(subparsers, parents):
    parser = subparsers.add_parser("fixed-asset", help="固定资产", parents=parents)
    sub = parser.add_subparsers(dest="fa_cmd")

    add_cmd = sub.add_parser("add", help="新增资产", parents=parents)
    add_cmd.add_argument("--name", required=True, help="资产名称")
    add_cmd.add_argument("--cost", type=float, required=True, help="入账成本")
    add_cmd.add_argument("--life", type=int, required=True, help="使用年限")
    add_cmd.add_argument("--salvage", type=float, default=0, help="残值")
    add_cmd.add_argument("--date", default=_default_date(), help="购置日期")
    add_cmd.set_defaults(func=run_add)

    dep_cmd = sub.add_parser("depreciate", help="计提折旧", parents=parents)
    dep_cmd.add_argument("--period", required=True, help="期间")
    dep_cmd.set_defaults(func=run_depreciate)

    dispose_cmd = sub.add_parser("dispose", help="资产处置", parents=parents)
    dispose_cmd.add_argument("--asset-id", type=int, required=True, help="资产ID")
    dispose_cmd.add_argument("--date", default=_default_date(), help="处置日期")
    dispose_cmd.add_argument("--description", help="摘要")
    dispose_cmd.set_defaults(func=run_dispose)

    list_cmd = sub.add_parser("list", help="资产列表", parents=parents)
    list_cmd.add_argument("--status", default="active", help="状态: active/disposed/all")
    list_cmd.set_defaults(func=run_list)

    reconcile_cmd = sub.add_parser("reconcile", help="固定资产对平", parents=parents)
    reconcile_cmd.add_argument("--period", required=True, help="期间")
    reconcile_cmd.set_defaults(func=run_reconcile)

    return parser


def run_add(args):
    with get_db(args.db_path) as conn:
        result = add_fixed_asset(
            conn,
            args.name,
            args.cost,
            args.life,
            args.salvage,
            args.date,
        )
    print_json({"status": "success", **result})


def run_depreciate(args):
    with get_db(args.db_path) as conn:
        result = depreciate_assets(conn, args.period)
    print_json({"status": "success", **result})


def run_dispose(args):
    with get_db(args.db_path) as conn:
        result = dispose_fixed_asset(conn, args.asset_id, args.date, args.description)
    print_json({"status": "success", **result})


def run_list(args):
    with get_db(args.db_path) as conn:
        rows = list_fixed_assets(conn, args.status)
    print_json({"items": rows})


def run_reconcile(args):
    with get_db(args.db_path) as conn:
        result = reconcile_fixed_assets(conn, args.period)
    print_json({"status": "success", **result})
