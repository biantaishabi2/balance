#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger auto command."""

from __future__ import annotations

from ledger.database import get_db
from ledger.services import generate_voucher_from_template
from ledger.utils import load_json_input, print_json


def add_parser(subparsers, parents):
    parser = subparsers.add_parser("auto", help="模板自动凭证", parents=parents)
    parser.add_argument("--template", required=True, help="模板代码")
    parser.add_argument("--date", help="凭证日期")
    parser.set_defaults(func=run)
    return parser


def run(args):
    payload = load_json_input()
    with get_db(args.db_path) as conn:
        result = generate_voucher_from_template(conn, args.template, payload, args.date)
    print_json({"status": "success", **result})
