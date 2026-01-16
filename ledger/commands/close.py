#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger close command."""

from __future__ import annotations

from ledger.database import get_db
from ledger.services import close_period
from ledger.utils import print_json


def add_parser(subparsers, parents):
    parser = subparsers.add_parser("close", help="期末结账", parents=parents)
    parser.add_argument("--period", required=True, help="期间")
    parser.set_defaults(func=run)
    return parser


def run(args):
    with get_db(args.db_path) as conn:
        result = close_period(conn, args.period)

    print_json(
        {
            "status": "closed",
            **result,
        }
    )
