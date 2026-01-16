#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger report command."""

from __future__ import annotations

from pathlib import Path

from ledger.database import get_db
from ledger.reporting import generate_statements
from ledger.utils import LedgerError, print_json


def add_parser(subparsers, parents):
    parser = subparsers.add_parser("report", help="生成三表", parents=parents)
    parser.add_argument("--period", required=True, help="期间")
    parser.add_argument("--output", help="输出路径")
    parser.add_argument(
        "--engine",
        choices=["balance", "ledger"],
        default="balance",
        help="报表引擎",
    )
    parser.add_argument("--dept-id", type=int)
    parser.add_argument("--project-id", type=int)
    parser.add_argument("--customer-id", type=int)
    parser.add_argument("--supplier-id", type=int)
    parser.add_argument("--employee-id", type=int)
    parser.add_argument(
        "--scope",
        choices=["all", "normal", "adjustment"],
        default="all",
        help="口径: all/normal/adjustment",
    )
    parser.add_argument(
        "--budget-dim-type",
        choices=["department", "project"],
        help="预算维度类型",
    )
    parser.add_argument("--budget-dim-code", help="预算维度代码")
    parser.add_argument("--interest-rate", type=float, default=0.0, help="利率假设")
    parser.add_argument("--tax-rate", type=float, default=0.0, help="税率假设")
    parser.add_argument("--fixed-asset-life", type=float, default=0.0, help="折旧年限(年)")
    parser.add_argument("--fixed-asset-salvage", type=float, default=0.0, help="固定资产残值")
    parser.set_defaults(func=run)
    return parser


def run(args):
    assumptions = {
        "interest_rate": args.interest_rate,
        "tax_rate": args.tax_rate,
        "fixed_asset_life": args.fixed_asset_life,
        "fixed_asset_salvage": args.fixed_asset_salvage,
    }
    dims = {
        "dept_id": args.dept_id,
        "project_id": args.project_id,
        "customer_id": args.customer_id,
        "supplier_id": args.supplier_id,
        "employee_id": args.employee_id,
    }
    budget = None
    if args.budget_dim_type or args.budget_dim_code:
        budget = {
            "dim_type": args.budget_dim_type,
            "dim_code": args.budget_dim_code,
        }
    with get_db(args.db_path) as conn:
        report = generate_statements(
            conn,
            args.period,
            assumptions=assumptions,
            dims=dims,
            engine=args.engine,
            scope=args.scope,
            budget=budget,
        )

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(
            print_json_to_string(report),
            encoding="utf-8",
        )
        print_json({"status": "success", "output": str(out_path)})
        return

    print_json(report)


def print_json_to_string(data):
    import json

    return json.dumps(data, ensure_ascii=False, indent=2)
