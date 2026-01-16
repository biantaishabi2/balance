#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger confirm command."""

from __future__ import annotations

from ledger.database import get_db
from ledger.reporting import generate_statements
from ledger.services import confirm_voucher
from ledger.utils import LedgerError, print_json


def add_parser(subparsers, parents):
    parser = subparsers.add_parser("confirm", help="确认已审核凭证", parents=parents)
    parser.add_argument("voucher_id", type=int, help="凭证ID")
    parser.set_defaults(func=run)
    return parser


def run(args):
    with get_db(args.db_path) as conn:
        voucher = confirm_voucher(conn, args.voucher_id)
        _ = generate_statements(conn, voucher["period"])

    print_json(
        {
            "voucher_id": args.voucher_id,
            "status": "confirmed",
            "message": "凭证已确认，余额已更新，三表已生成",
            "confirmed_at": voucher.get("confirmed_at"),
            "balances_updated": voucher.get("balances_updated"),
            "reports_generated": True,
        }
    )
