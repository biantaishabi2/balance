#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger record command."""

from __future__ import annotations

from ledger.database import get_db
from ledger.reporting import generate_statements
from ledger.services import build_entries, insert_voucher, update_balance_for_voucher
from ledger.utils import LedgerError, load_json_input, print_json


def add_parser(subparsers, parents):
    parser = subparsers.add_parser("record", help="录入凭证", parents=parents)
    parser.add_argument("--auto", action="store_true", help="自动确认并更新余额")
    parser.set_defaults(func=run)
    return parser


def run(args):
    data = load_json_input()
    date = data.get("date")
    entries_data = data.get("entries")
    if not date:
        raise LedgerError("VOUCHER_NOT_FOUND", "缺少凭证日期")
    if not entries_data:
        raise LedgerError("VOUCHER_NOT_FOUND", "缺少分录")

    with get_db(args.db_path) as conn:
        entries, total_debit, total_credit = build_entries(conn, entries_data)
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

        status = "confirmed" if args.auto else "draft"
        voucher_id, voucher_no, period, confirmed_at = insert_voucher(
            conn, data, entries, status
        )

        if status == "confirmed":
            balances_updated = update_balance_for_voucher(conn, voucher_id, period)
            _ = generate_statements(conn, period)
            output = {
                "voucher_id": voucher_id,
                "voucher_no": voucher_no,
                "status": "confirmed",
                "message": "凭证已确认，余额已更新，三表已生成",
                "confirmed_at": confirmed_at,
                "balances_updated": balances_updated,
                "reports_generated": True,
            }
        else:
            output = {
                "voucher_id": voucher_id,
                "voucher_no": voucher_no,
                "status": "draft",
                "message": "草稿已保存，使用 ledger confirm 确认",
                "voucher": {
                    "date": date,
                    "description": data.get("description"),
                    "entries": [
                        {
                            "account": e["account_code"],
                            "account_name": e["account_name"],
                            "debit": e["debit_amount"],
                            "credit": e["credit_amount"],
                        }
                        for e in entries
                    ],
                    "debit_total": round(total_debit, 2),
                    "credit_total": round(total_credit, 2),
                    "is_balanced": True,
                },
            }

    print_json(output)
