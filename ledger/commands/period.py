#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger period command."""

from __future__ import annotations

from ledger.database import get_db
from ledger.services import set_period_status
from ledger.utils import print_json


def add_parser(subparsers, parents):
    parser = subparsers.add_parser("period", help="期间管理", parents=parents)
    sub = parser.add_subparsers(dest="period_cmd")

    status_cmd = sub.add_parser("set-status", help="设置期间状态", parents=parents)
    status_cmd.add_argument("--period", required=True, help="期间")
    status_cmd.add_argument("--status", required=True, help="open/closed/adjustment")
    status_cmd.set_defaults(func=run_set_status)

    return parser


def run_set_status(args):
    with get_db(args.db_path) as conn:
        result = set_period_status(conn, args.period, args.status)
    print_json({"status": "success", **result})
