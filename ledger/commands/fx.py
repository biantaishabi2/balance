#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger fx command."""

from __future__ import annotations

from ledger.database import get_db
from ledger.services import (
    add_currency,
    add_fx_rate,
    fx_balance,
    list_currencies,
    list_fx_rates,
    revalue_forex,
)
from ledger.utils import print_json


def add_parser(subparsers, parents):
    parser = subparsers.add_parser("fx", help="外汇管理", parents=parents)
    sub = parser.add_subparsers(dest="fx_cmd")

    cur_cmd = sub.add_parser("currency", help="币种管理", parents=parents)
    cur_sub = cur_cmd.add_subparsers(dest="currency_cmd")

    cur_add = cur_sub.add_parser("add", help="新增币种", parents=parents)
    cur_add.add_argument("--code", required=True, help="币种代码")
    cur_add.add_argument("--name", required=True, help="币种名称")
    cur_add.add_argument("--symbol", help="符号")
    cur_add.add_argument("--precision", type=int, default=2, help="精度")
    cur_add.set_defaults(func=run_currency_add)

    cur_list = cur_sub.add_parser("list", help="币种列表", parents=parents)
    cur_list.set_defaults(func=run_currency_list)

    rate_cmd = sub.add_parser("rate", help="汇率管理", parents=parents)
    rate_sub = rate_cmd.add_subparsers(dest="rate_cmd")

    rate_add = rate_sub.add_parser("add", help="新增汇率", parents=parents)
    rate_add.add_argument("--currency", required=True, help="币种代码")
    rate_add.add_argument("--date", required=True, help="日期")
    rate_add.add_argument("--rate", type=float, required=True, help="汇率")
    rate_add.add_argument("--rate-type", default="spot", help="汇率类型")
    rate_add.add_argument("--source", help="来源")
    rate_add.set_defaults(func=run_rate_add)

    rate_list = rate_sub.add_parser("list", help="汇率列表", parents=parents)
    rate_list.add_argument("--currency", help="币种代码")
    rate_list.add_argument("--date", help="日期")
    rate_list.add_argument("--rate-type", help="汇率类型")
    rate_list.set_defaults(func=run_rate_list)

    balance_cmd = sub.add_parser("balance", help="外币余额", parents=parents)
    balance_cmd.add_argument("--period", required=True, help="期间")
    balance_cmd.add_argument("--currency", help="币种代码")
    balance_cmd.set_defaults(func=run_balance)

    revalue_cmd = sub.add_parser("revalue", help="汇兑重估", parents=parents)
    revalue_cmd.add_argument("--period", required=True, help="期间")
    revalue_cmd.add_argument("--rate-type", default="closing", help="汇率类型")
    revalue_cmd.set_defaults(func=run_revalue)

    return parser


def run_currency_add(args):
    with get_db(args.db_path) as conn:
        add_currency(conn, args.code, args.name, args.symbol, args.precision)
    print_json({"status": "success"})


def run_currency_list(args):
    with get_db(args.db_path) as conn:
        rows = list_currencies(conn)
    print_json({"currencies": rows})


def run_rate_add(args):
    with get_db(args.db_path) as conn:
        add_fx_rate(conn, args.currency, args.date, args.rate, args.rate_type, args.source)
    print_json({"status": "success"})


def run_rate_list(args):
    with get_db(args.db_path) as conn:
        rows = list_fx_rates(conn, args.currency, args.date, args.rate_type)
    print_json({"rates": rows})


def run_balance(args):
    with get_db(args.db_path) as conn:
        rows = fx_balance(conn, args.period, args.currency)
    print_json({"period": args.period, "balances": rows})


def run_revalue(args):
    with get_db(args.db_path) as conn:
        result = revalue_forex(conn, args.period, args.rate_type)
    print_json({"status": "success", **result})
