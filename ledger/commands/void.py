#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger void command."""

from __future__ import annotations

from datetime import datetime

from ledger.database import get_db
from ledger.reporting import generate_statements
from ledger.services import (
    fetch_entries,
    fetch_voucher,
    insert_voucher,
    update_balance_for_voucher,
)
from ledger.utils import LedgerError, print_json


def add_parser(subparsers, parents):
    parser = subparsers.add_parser("void", help="作废凭证（红字冲销）", parents=parents)
    parser.add_argument("voucher_id", type=int, help="凭证ID")
    parser.add_argument("--reason", required=True, help="作废原因")
    parser.set_defaults(func=run)
    return parser


def run(args):
    with get_db(args.db_path) as conn:
        voucher = fetch_voucher(conn, args.voucher_id)
        if not voucher:
            raise LedgerError("VOUCHER_NOT_FOUND", f"凭证不存在: {args.voucher_id}")
        if voucher["status"] != "confirmed":
            raise LedgerError("VOUCHER_NOT_CONFIRMED", "仅已确认凭证可冲销")

        entries = fetch_entries(conn, args.voucher_id)
        reversed_entries = []
        for entry in entries:
            reversed_entries.append(
                {
                    "line_no": entry["line_no"],
                    "account_code": entry["account_code"],
                    "account_name": entry["account_name"],
                    "description": f"冲销:{entry.get('description') or ''}".strip(),
                    "debit_amount": entry["credit_amount"],
                    "credit_amount": entry["debit_amount"],
                    "dept_id": entry.get("dept_id"),
                    "project_id": entry.get("project_id"),
                    "customer_id": entry.get("customer_id"),
                    "supplier_id": entry.get("supplier_id"),
                    "employee_id": entry.get("employee_id"),
                }
            )

        void_data = {
            "date": voucher["date"],
            "description": f"冲销:{voucher.get('description') or ''}".strip(),
        }
        void_id, void_no, period, _ = insert_voucher(
            conn, void_data, reversed_entries, "confirmed"
        )
        update_balance_for_voucher(conn, void_id, period)

        conn.execute(
            """
            UPDATE vouchers
            SET status = 'voided', void_reason = ?, voided_at = ?
            WHERE id = ?
            """,
            (args.reason, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), args.voucher_id),
        )
        conn.execute(
            """
            INSERT INTO void_vouchers (original_voucher_id, void_voucher_id, void_reason)
            VALUES (?, ?, ?)
            """,
            (args.voucher_id, void_id, args.reason),
        )
        _ = generate_statements(conn, period)

    print_json(
        {
            "original_voucher_id": args.voucher_id,
            "void_voucher_id": void_id,
            "status": "voided",
            "message": "凭证已作废，红字冲销凭证已生成",
            "void_voucher_no": void_no,
        }
    )
