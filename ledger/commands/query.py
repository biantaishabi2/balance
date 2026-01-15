#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger query command."""

from __future__ import annotations

from typing import Any, Dict, List

from fin_tools.tools.audit_tools import trial_balance

from ledger.database import get_db
from ledger.services import balances_for_period, fetch_entries, find_account
from ledger.utils import LedgerError, print_json


def add_parser(subparsers, parents):
    parser = subparsers.add_parser("query", help="查询凭证/余额", parents=parents)
    sub = parser.add_subparsers(dest="query_cmd")

    vouchers = sub.add_parser("vouchers", help="查询凭证", parents=parents)
    vouchers.add_argument("--period", help="期间")
    vouchers.add_argument("--status", help="状态")
    vouchers.add_argument("--account", help="科目")
    vouchers.add_argument("--voucher-no", dest="voucher_no", help="凭证号")
    vouchers.set_defaults(func=run_vouchers)

    balances = sub.add_parser("balances", help="查询余额", parents=parents)
    balances.add_argument("--period", help="期间")
    balances.add_argument("--account", help="科目")
    balances.add_argument("--dept-id", type=int)
    balances.add_argument("--project-id", type=int)
    balances.add_argument("--customer-id", type=int)
    balances.add_argument("--supplier-id", type=int)
    balances.add_argument("--employee-id", type=int)
    balances.set_defaults(func=run_balances)

    trial = sub.add_parser("trial-balance", help="试算平衡", parents=parents)
    trial.add_argument("--period", help="期间")
    trial.set_defaults(func=run_trial_balance)

    return parser


def run_vouchers(args):
    with get_db(args.db_path) as conn:
        conditions = ["1=1"]
        params: List[Any] = []
        if args.period:
            conditions.append("period = ?")
            params.append(args.period)
        if args.status:
            conditions.append("status = ?")
            params.append(args.status)
        if args.voucher_no:
            conditions.append("voucher_no = ?")
            params.append(args.voucher_no)

        if args.account:
            account = find_account(conn, args.account)
            rows = conn.execute(
                "SELECT DISTINCT voucher_id FROM voucher_entries WHERE account_code = ?",
                (account["code"],),
            ).fetchall()
            voucher_ids = [row["voucher_id"] for row in rows]
            if not voucher_ids:
                print_json({"vouchers": []})
                return
            conditions.append(f"id IN ({','.join('?' for _ in voucher_ids)})")
            params.extend(voucher_ids)

        sql = f"SELECT * FROM vouchers WHERE {' AND '.join(conditions)} ORDER BY date"
        vouchers = conn.execute(sql, params).fetchall()

        output = []
        for v in vouchers:
            entries = fetch_entries(conn, v["id"])
            output.append(
                {
                    "id": v["id"],
                    "voucher_no": v["voucher_no"],
                    "date": v["date"],
                    "description": v["description"],
                    "status": v["status"],
                    "entries": [
                        {
                            "account": e["account_name"],
                            "debit": e["debit_amount"],
                            "credit": e["credit_amount"],
                        }
                        for e in entries
                    ],
                }
            )

    print_json({"vouchers": output})


def _resolve_period(conn, period: str | None) -> str:
    if period:
        return period
    row = conn.execute("SELECT period FROM periods ORDER BY period DESC LIMIT 1").fetchone()
    if not row:
        raise LedgerError("PERIOD_CLOSED", "未找到可用期间")
    return row["period"]


def run_balances(args):
    with get_db(args.db_path) as conn:
        period = _resolve_period(conn, args.period)
        conditions = ["b.period = ?"]
        params: List[Any] = [period]

        if args.account:
            account = find_account(conn, args.account)
            conditions.append("b.account_code = ?")
            params.append(account["code"])
        if args.dept_id is not None:
            conditions.append("b.dept_id = ?")
            params.append(args.dept_id)
        if args.project_id is not None:
            conditions.append("b.project_id = ?")
            params.append(args.project_id)
        if args.customer_id is not None:
            conditions.append("b.customer_id = ?")
            params.append(args.customer_id)
        if args.supplier_id is not None:
            conditions.append("b.supplier_id = ?")
            params.append(args.supplier_id)
        if args.employee_id is not None:
            conditions.append("b.employee_id = ?")
            params.append(args.employee_id)

        rows = conn.execute(
            f"""
            SELECT b.*, a.name AS account_name
            FROM balances b
            JOIN accounts a ON b.account_code = a.code
            WHERE {' AND '.join(conditions)}
            ORDER BY b.account_code
            """,
            params,
        ).fetchall()

    balances = [
        {
            "account_code": row["account_code"],
            "account_name": row["account_name"],
            "opening_balance": row["opening_balance"],
            "debit_amount": row["debit_amount"],
            "credit_amount": row["credit_amount"],
            "closing_balance": row["closing_balance"],
            "dept_id": row["dept_id"],
            "project_id": row["project_id"],
            "customer_id": row["customer_id"],
            "supplier_id": row["supplier_id"],
            "employee_id": row["employee_id"],
        }
        for row in rows
    ]
    print_json({"period": period, "balances": balances})


def run_trial_balance(args):
    with get_db(args.db_path) as conn:
        period = _resolve_period(conn, args.period)
        balances = balances_for_period(conn, period)

    accounts: List[Dict[str, Any]] = []
    for b in balances:
        if b["account_direction"] == "debit":
            debit = max(b["closing_balance"], 0)
            credit = max(-b["closing_balance"], 0)
        else:
            credit = max(b["closing_balance"], 0)
            debit = max(-b["closing_balance"], 0)
        accounts.append(
            {
                "code": b["account_code"],
                "name": b["account_name"],
                "type": b["account_type"],
                "debit": round(debit, 2),
                "credit": round(credit, 2),
            }
        )

    result = trial_balance(accounts=accounts, tolerance=0.01)
    print_json({"period": period, **result})
