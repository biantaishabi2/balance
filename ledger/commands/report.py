#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger report command."""

from __future__ import annotations

from pathlib import Path

from ledger.database import get_db
from ledger.reporting import generate_group_statements, generate_statements
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
    parser.add_argument("--consolidate", action="store_true", help="生成合并报表")
    parser.add_argument("--ledger-codes", help="账套代码列表，逗号分隔")
    parser.add_argument("--rule", dest="rule_name", help="合并规则名称")
    parser.add_argument("--template", dest="template_code", help="报表模板代码")
    parser.add_argument("--group-currency", help="集团本位币")
    parser.add_argument("--rate-date", help="汇率日期(YYYY-MM-DD)")
    parser.add_argument("--dept-id", type=int)
    parser.add_argument("--project-id", type=int)
    parser.add_argument("--customer-id", type=int)
    parser.add_argument("--supplier-id", type=int)
    parser.add_argument("--employee-id", type=int)
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
    with get_db(args.db_path) as conn:
        if args.consolidate:
            ledger_codes = None
            if args.ledger_codes:
                ledger_codes = [
                    code.strip()
                    for code in args.ledger_codes.split(",")
                    if code.strip()
                ]
            report = generate_group_statements(
                conn,
                args.period,
                ledger_codes=ledger_codes,
                rule_name=args.rule_name,
                template_code=args.template_code,
                group_currency=args.group_currency,
                rate_date=args.rate_date,
            )
        else:
            report = generate_statements(
                conn,
                args.period,
                assumptions=assumptions,
                dims=dims,
                engine=args.engine,
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
