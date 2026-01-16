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
    create_cip_project,
    add_cip_cost,
    find_dimension,
    impair_fixed_asset,
    list_fixed_assets,
    set_fixed_asset_allocations,
    split_fixed_asset,
    transfer_cip_to_asset,
    transfer_fixed_asset,
    upgrade_fixed_asset,
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
    add_cmd.add_argument("--department", help="使用部门代码")
    add_cmd.add_argument("--project", help="项目代码")
    add_cmd.set_defaults(func=run_add)

    dep_cmd = sub.add_parser("depreciate", help="计提折旧", parents=parents)
    dep_cmd.add_argument("--period", required=True, help="期间")
    dep_cmd.set_defaults(func=run_depreciate)

    dispose_cmd = sub.add_parser("dispose", help="资产处置", parents=parents)
    dispose_cmd.add_argument("--asset-id", type=int, required=True, help="资产ID")
    dispose_cmd.add_argument("--date", default=_default_date(), help="处置日期")
    dispose_cmd.add_argument("--description", help="摘要")
    dispose_cmd.set_defaults(func=run_dispose)

    upgrade_cmd = sub.add_parser("upgrade", help="资产改扩建", parents=parents)
    upgrade_cmd.add_argument("--asset-id", type=int, required=True, help="资产ID")
    upgrade_cmd.add_argument("--amount", type=float, required=True, help="金额")
    upgrade_cmd.add_argument("--date", default=_default_date(), help="日期")
    upgrade_cmd.set_defaults(func=run_upgrade)

    split_cmd = sub.add_parser("split", help="资产拆分", parents=parents)
    split_cmd.add_argument("--asset-id", type=int, required=True, help="资产ID")
    split_cmd.add_argument("--ratios", required=True, help="比例列表，如 6,4")
    split_cmd.set_defaults(func=run_split)

    transfer_cmd = sub.add_parser("transfer", help="资产转移", parents=parents)
    transfer_cmd.add_argument("--asset-id", type=int, required=True, help="资产ID")
    transfer_cmd.add_argument("--department", help="使用部门代码")
    transfer_cmd.add_argument("--project", help="项目代码")
    transfer_cmd.add_argument("--date", default=_default_date(), help="日期")
    transfer_cmd.set_defaults(func=run_transfer)

    impair_cmd = sub.add_parser("impair", help="资产减值", parents=parents)
    impair_cmd.add_argument("--asset-id", type=int, required=True, help="资产ID")
    impair_cmd.add_argument("--period", required=True, help="期间")
    impair_cmd.add_argument("--amount", type=float, required=True, help="金额")
    impair_cmd.set_defaults(func=run_impair)

    cip_add_cmd = sub.add_parser("cip-add", help="新增在建工程", parents=parents)
    cip_add_cmd.add_argument("--name", required=True, help="项目名称")
    cip_add_cmd.set_defaults(func=run_cip_add)

    cip_cost_cmd = sub.add_parser("cip-cost", help="在建投入", parents=parents)
    cip_cost_cmd.add_argument("--project-id", type=int, required=True, help="项目ID")
    cip_cost_cmd.add_argument("--amount", type=float, required=True, help="金额")
    cip_cost_cmd.add_argument("--date", default=_default_date(), help="日期")
    cip_cost_cmd.set_defaults(func=run_cip_cost)

    cip_transfer_cmd = sub.add_parser("cip-transfer", help="转固", parents=parents)
    cip_transfer_cmd.add_argument("--project-id", type=int, required=True, help="项目ID")
    cip_transfer_cmd.add_argument("--asset-name", required=True, help="资产名称")
    cip_transfer_cmd.add_argument("--life", type=int, required=True, help="使用年限")
    cip_transfer_cmd.add_argument("--salvage", type=float, default=0, help="残值")
    cip_transfer_cmd.add_argument("--date", default=_default_date(), help="日期")
    cip_transfer_cmd.add_argument("--amount", type=float, help="转固金额")
    cip_transfer_cmd.set_defaults(func=run_cip_transfer)

    alloc_cmd = sub.add_parser("allocate", help="折旧分摊", parents=parents)
    alloc_cmd.add_argument("--asset-id", type=int, required=True, help="资产ID")
    alloc_cmd.add_argument(
        "--alloc",
        action="append",
        required=True,
        help="维度分摊，格式: dim_type:dim_code:ratio",
    )
    alloc_cmd.set_defaults(func=run_allocate)

    list_cmd = sub.add_parser("list", help="资产列表", parents=parents)
    list_cmd.add_argument("--status", default="active", help="状态: active/disposed/all")
    list_cmd.add_argument("--period", help="期间")
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
            args.department,
            args.project,
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
        rows = list_fixed_assets(conn, args.status, args.period)
    print_json({"items": rows})


def run_reconcile(args):
    with get_db(args.db_path) as conn:
        result = reconcile_fixed_assets(conn, args.period)
    print_json({"status": "success", **result})


def run_upgrade(args):
    with get_db(args.db_path) as conn:
        result = upgrade_fixed_asset(conn, args.asset_id, args.amount, args.date)
    print_json({"status": "success", **result})


def run_split(args):
    ratios = [float(r.strip()) for r in args.ratios.split(",") if r.strip()]
    with get_db(args.db_path) as conn:
        result = split_fixed_asset(conn, args.asset_id, ratios)
    print_json({"status": "success", **result})


def run_transfer(args):
    with get_db(args.db_path) as conn:
        result = transfer_fixed_asset(
            conn,
            args.asset_id,
            args.department,
            args.project,
            args.date,
        )
    print_json({"status": "success", **result})


def run_impair(args):
    with get_db(args.db_path) as conn:
        result = impair_fixed_asset(conn, args.asset_id, args.period, args.amount)
    print_json({"status": "success", **result})


def run_cip_add(args):
    with get_db(args.db_path) as conn:
        project_id = create_cip_project(conn, args.name)
    print_json({"status": "success", "project_id": project_id})


def run_cip_cost(args):
    with get_db(args.db_path) as conn:
        result = add_cip_cost(conn, args.project_id, args.amount, args.date)
    print_json({"status": "success", **result})


def run_cip_transfer(args):
    with get_db(args.db_path) as conn:
        result = transfer_cip_to_asset(
            conn,
            args.project_id,
            args.asset_name,
            args.life,
            args.salvage,
            args.date,
            args.amount,
        )
    print_json({"status": "success", **result})


def run_allocate(args):
    allocations = []
    with get_db(args.db_path) as conn:
        for item in args.alloc:
            dim_type, dim_code, ratio = item.split(":", 2)
            dim_id = find_dimension(conn, dim_type, dim_code)
            allocations.append((dim_type, dim_id, float(ratio)))
        set_fixed_asset_allocations(conn, args.asset_id, allocations)
    print_json({"status": "success", "asset_id": args.asset_id})
