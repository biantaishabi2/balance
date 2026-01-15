#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger confirm command."""

from __future__ import annotations

from datetime import datetime

from ledger.database import get_db
from ledger.reporting import generate_statements
from ledger.services import fetch_entries, fetch_voucher, update_balance_for_voucher
from ledger.utils import LedgerError, print_json


def add_parser(subparsers, parents):
    parser = subparsers.add_parser("confirm", help="确认草稿凭证", parents=parents)
    parser.add_argument("voucher_id", type=int, help="凭证ID")
    parser.set_defaults(func=run)
    return parser


def run(args):
    with get_db(args.db_path) as conn:
        voucher = fetch_voucher(conn, args.voucher_id)
        if not voucher:
            raise LedgerError("VOUCHER_NOT_FOUND", f"凭证不存在: {args.voucher_id}")
        if voucher["status"] != "draft":
            raise LedgerError("VOID_CONFIRMED", "非草稿凭证不能确认")

        entries = fetch_entries(conn, args.voucher_id)
        total_debit = sum(e["debit_amount"] for e in entries)
        total_credit = sum(e["credit_amount"] for e in entries)
        if abs(total_debit - total_credit) >= 0.01:
            raise LedgerError(
                "NOT_BALANCED",
                f"借贷不相等：借方{total_debit}，贷方{total_credit}",
                {
                    "debit_total": round(total_debit, 2),
                    "credit_total": round(total_credit, 2),
                    "difference": round(total_debit - total_credit, 2),
                },
            )

        confirmed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "UPDATE vouchers SET status = 'confirmed', confirmed_at = ? WHERE id = ?",
            (confirmed_at, args.voucher_id),
        )
        balances_updated = update_balance_for_voucher(conn, args.voucher_id, voucher["period"])
        _ = generate_statements(conn, voucher["period"])

    print_json(
        {
            "voucher_id": args.voucher_id,
            "status": "confirmed",
            "message": "凭证已确认，余额已更新，三表已生成",
            "confirmed_at": confirmed_at,
            "balances_updated": balances_updated,
            "reports_generated": True,
        }
    )
