#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger review command."""

from __future__ import annotations

from ledger.database import get_db
from ledger.services import fetch_approval, review_voucher
from ledger.utils import print_json


def add_parser(subparsers, parents):
    parser = subparsers.add_parser("review", help="审核凭证", parents=parents)
    parser.add_argument("voucher_id", type=int, help="凭证ID")
    parser.set_defaults(func=run)
    return parser


def run(args):
    with get_db(args.db_path) as conn:
        voucher = review_voucher(conn, args.voucher_id)
        approval = fetch_approval(conn, "voucher", args.voucher_id)

    output = {
        "voucher_id": args.voucher_id,
        "status": voucher["status"],
        "reviewed_at": voucher.get("reviewed_at"),
        "approval": approval,
        "message": "凭证已审核",
    }
    if voucher.get("budget_warnings"):
        output["budget_warnings"] = voucher.get("budget_warnings", [])
    print_json(output)
