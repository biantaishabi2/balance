#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger unreview command."""

from __future__ import annotations

from ledger.database import get_db
from ledger.services import unreview_voucher
from ledger.utils import print_json


def add_parser(subparsers, parents):
    parser = subparsers.add_parser("unreview", help="反审核凭证", parents=parents)
    parser.add_argument("voucher_id", type=int, help="凭证ID")
    parser.set_defaults(func=run)
    return parser


def run(args):
    with get_db(args.db_path) as conn:
        voucher = unreview_voucher(conn, args.voucher_id)

    print_json(
        {
            "voucher_id": args.voucher_id,
            "status": voucher["status"],
            "message": "凭证已反审核",
        }
    )
