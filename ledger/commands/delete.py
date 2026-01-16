#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger delete command."""

from __future__ import annotations

from ledger.database import get_db
from ledger.services import fetch_voucher, log_audit_event
from ledger.utils import LedgerError, print_json


def add_parser(subparsers, parents):
    parser = subparsers.add_parser("delete", help="删除草稿凭证", parents=parents)
    parser.add_argument("voucher_id", type=int, help="凭证ID")
    parser.set_defaults(func=run)
    return parser


def run(args):
    with get_db(args.db_path) as conn:
        voucher = fetch_voucher(conn, args.voucher_id)
        if not voucher:
            raise LedgerError("VOUCHER_NOT_FOUND", f"凭证不存在: {args.voucher_id}")
        if voucher["status"] != "draft":
            raise LedgerError("VOID_CONFIRMED", "已确认凭证不能删除，只能冲销")
        log_audit_event(
            conn,
            "ledger.delete",
            target_type="voucher",
            target_id=args.voucher_id,
            detail={"voucher_no": voucher.get("voucher_no")},
        )
        conn.execute("DELETE FROM vouchers WHERE id = ?", (args.voucher_id,))

    print_json(
        {
            "voucher_id": args.voucher_id,
            "deleted": True,
            "message": "草稿已删除",
        }
    )
