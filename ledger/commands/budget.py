#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger budget command."""

from __future__ import annotations

from ledger.database import get_db
from ledger.services import budget_variance, list_budgets, set_budget
from ledger.utils import print_json


def add_parser(subparsers, parents):
    parser = subparsers.add_parser("budget", help="预算管理", parents=parents)
    sub = parser.add_subparsers(dest="budget_cmd")

    set_cmd = sub.add_parser("set", help="设置预算", parents=parents)
    set_cmd.add_argument("--period", required=True, help="期间")
    set_cmd.add_argument("--dim-type", required=True, help="维度类型 department/project")
    set_cmd.add_argument("--dim-code", required=True, help="维度代码")
    set_cmd.add_argument("--amount", type=float, required=True, help="预算金额")
    set_cmd.set_defaults(func=run_set)

    list_cmd = sub.add_parser("list", help="预算列表", parents=parents)
    list_cmd.add_argument("--period", help="期间")
    list_cmd.add_argument("--dim-type", help="维度类型")
    list_cmd.set_defaults(func=run_list)

    variance_cmd = sub.add_parser("variance", help="预算差异", parents=parents)
    variance_cmd.add_argument("--period", required=True, help="期间")
    variance_cmd.add_argument("--dim-type", required=True, help="维度类型 department/project")
    variance_cmd.add_argument("--dim-code", help="维度代码")
    variance_cmd.set_defaults(func=run_variance)

    return parser


def run_set(args):
    with get_db(args.db_path) as conn:
        result = set_budget(conn, args.period, args.dim_type, args.dim_code, args.amount)
    print_json({"status": "success", **result})


def run_list(args):
    with get_db(args.db_path) as conn:
        rows = list_budgets(conn, args.period, args.dim_type)
    print_json({"budgets": rows})


def run_variance(args):
    with get_db(args.db_path) as conn:
        result = budget_variance(conn, args.period, args.dim_type, args.dim_code)
    print_json({"status": "success", **result})
