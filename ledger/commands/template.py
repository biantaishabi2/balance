#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger template command."""

from __future__ import annotations

import json

from ledger.database import get_db
from ledger.services import add_voucher_template, disable_voucher_template, list_voucher_templates
from ledger.utils import load_json_input, print_json


def add_parser(subparsers, parents):
    parser = subparsers.add_parser("template", help="凭证模板", parents=parents)
    sub = parser.add_subparsers(dest="tpl_cmd")

    add_cmd = sub.add_parser("add", help="新增模板", parents=parents)
    add_cmd.set_defaults(func=run_add)

    list_cmd = sub.add_parser("list", help="模板列表", parents=parents)
    list_cmd.set_defaults(func=run_list)

    disable_cmd = sub.add_parser("disable", help="禁用模板", parents=parents)
    disable_cmd.add_argument("--code", required=True, help="模板代码")
    disable_cmd.set_defaults(func=run_disable)

    return parser


def run_add(args):
    data = load_json_input()
    code = data.get("code")
    name = data.get("name")
    rule_json = data.get("rule_json")
    if isinstance(rule_json, str):
        rule_json = json.loads(rule_json)
    with get_db(args.db_path) as conn:
        add_voucher_template(conn, code, name, rule_json)
    print_json({"status": "success", "code": code})


def run_list(args):
    with get_db(args.db_path) as conn:
        rows = list_voucher_templates(conn)
    print_json({"templates": rows})


def run_disable(args):
    with get_db(args.db_path) as conn:
        disable_voucher_template(conn, args.code)
    print_json({"status": "success", "code": args.code})
