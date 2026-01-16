#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ledger domain services."""

from __future__ import annotations

from datetime import datetime
import calendar
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ledger.utils import LedgerError


DIMENSION_FIELDS = {
    "department": "department",
    "project": "project",
    "customer": "customer",
    "supplier": "supplier",
    "employee": "employee",
}


DEFAULT_BALANCE_MAPPING = {
    "revenue": {"account_types": ["revenue"], "source": "credit_amount"},
    "cost": {"account_types": ["expense"], "source": "debit_amount"},
    "opening_cash": {"prefixes": ["1001", "1002"], "source": "opening_balance"},
    "opening_debt": {"account_types": ["liability"], "source": "opening_balance"},
    "opening_equity": {
        "prefixes": ["4001", "4002", "4101", "4102", "4201"],
        "source": "opening_balance",
    },
    "closing_receivable": {"prefixes": ["1122"], "source": "closing_balance"},
    "closing_payable": {"prefixes": ["2202"], "source": "closing_balance"},
    "closing_inventory": {"prefixes": ["1403"], "source": "closing_balance"},
    "fixed_asset_cost": {"prefixes": ["1601"], "source": "closing_balance"},
    "accum_depreciation": {"prefixes": ["1602"], "source": "closing_balance"},
}


DEFAULT_CLOSE_CONFIG = {
    "profit_account": "4103",
    "retain_account": "4104",
}


DEFAULT_SUBLEDGER_MAPPING = {
    "ar": {
        "ar_account": "1122",
        "revenue_account": "6001",
        "bank_account": "1002",
    },
    "ap": {
        "ap_account": "2202",
        "inventory_account": "1403",
        "bank_account": "1002",
    },
    "inventory": {
        "inventory_account": "1403",
        "cost_account": "6401",
        "offset_account": "1002",
    },
    "fixed_asset": {
        "asset_account": "1601",
        "accum_depreciation_account": "1602",
        "depreciation_expense_account": "6602",
        "bank_account": "1002",
    },
}


def parse_period(date_str: str) -> str:
    return date_str[:7]


def _prev_period(period: str) -> Optional[str]:
    try:
        year, month = period.split("-")
        year_i = int(year)
        month_i = int(month)
    except ValueError:
        return None
    if month_i == 1:
        return f"{year_i - 1:04d}-12"
    return f"{year_i:04d}-{month_i - 1:02d}"


def _next_period(period: str) -> Optional[str]:
    try:
        year, month = period.split("-")
        year_i = int(year)
        month_i = int(month)
    except ValueError:
        return None
    if month_i == 12:
        return f"{year_i + 1:04d}-01"
    return f"{year_i:04d}-{month_i + 1:02d}"


def _period_end_date(period: str) -> str:
    year, month = period.split("-")
    year_i = int(year)
    month_i = int(month)
    last_day = calendar.monthrange(year_i, month_i)[1]
    return f"{year_i:04d}-{month_i:02d}-{last_day:02d}"


def ensure_period(conn, period: str) -> None:
    row = conn.execute("SELECT period FROM periods WHERE period = ?", (period,)).fetchone()
    if row:
        return
    conn.execute(
        "INSERT INTO periods (period, status, opened_at) VALUES (?, 'open', CURRENT_TIMESTAMP)",
        (period,),
    )

    prev = _prev_period(period)
    if not prev:
        return
    existing = conn.execute(
        "SELECT 1 FROM balances WHERE period = ? LIMIT 1", (period,)
    ).fetchone()
    if existing:
        return
    prev_rows = conn.execute(
        """
        SELECT account_code, dept_id, project_id, customer_id, supplier_id, employee_id, closing_balance
        FROM balances
        WHERE period = ?
        """,
        (prev,),
    ).fetchall()
    for row in prev_rows:
        conn.execute(
            """
            INSERT OR IGNORE INTO balances (
              account_code, period, dept_id, project_id, customer_id, supplier_id, employee_id,
              opening_balance, debit_amount, credit_amount, closing_balance
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?)
            """,
            (
                row["account_code"],
                period,
                row["dept_id"],
                row["project_id"],
                row["customer_id"],
                row["supplier_id"],
                row["employee_id"],
                row["closing_balance"],
                row["closing_balance"],
            ),
        )


def get_period_status(conn, period: str) -> Optional[str]:
    row = conn.execute("SELECT status FROM periods WHERE period = ?", (period,)).fetchone()
    return row["status"] if row else None


def assert_period_open(conn, period: str) -> None:
    status = get_period_status(conn, period)
    if status == "closed":
        raise LedgerError("PERIOD_CLOSED", f"期间已结账: {period}")


def load_standard_accounts(conn, accounts: List[Dict[str, Any]]) -> int:
    loaded = 0
    for acc in accounts:
        conn.execute(
            """
            INSERT OR IGNORE INTO accounts (
              code, name, level, parent_code, type, direction, cash_flow, is_enabled, is_system
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                acc["code"],
                acc["name"],
                acc.get("level", 1),
                acc.get("parent_code"),
                acc.get("type", "asset"),
                acc.get("direction", "debit"),
                acc.get("cash_flow"),
                acc.get("is_enabled", 1),
                acc.get("is_system", 1),
            ),
        )
        loaded += 1
    return loaded


def find_account(conn, identifier: str) -> Dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM accounts WHERE code = ? OR name = ?",
        (identifier, identifier),
    ).fetchone()
    if not row:
        raise LedgerError("ACCOUNT_NOT_FOUND", f"科目不存在: {identifier}")
    if not row["is_enabled"]:
        raise LedgerError("ACCOUNT_DISABLED", f"科目已停用: {identifier}")
    return dict(row)


def find_dimension(conn, dim_type: str, code: str) -> int:
    row = conn.execute(
        "SELECT id FROM dimensions WHERE type = ? AND code = ? AND is_enabled = 1",
        (dim_type, code),
    ).fetchone()
    if not row:
        raise LedgerError("DIMENSION_NOT_FOUND", f"维度不存在: {dim_type}:{code}")
    return int(row["id"])


def generate_voucher_no(conn, date_str: str) -> str:
    prefix = "V" + date_str.replace("-", "")
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM vouchers WHERE voucher_no LIKE ?",
        (f"{prefix}%",),
    ).fetchone()
    seq = int(row["cnt"]) + 1
    return f"{prefix}{seq:03d}"


def build_entries(
    conn,
    entries_data: Iterable[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], float, float]:
    entries: List[Dict[str, Any]] = []
    total_debit = 0.0
    total_credit = 0.0

    for idx, entry in enumerate(entries_data, start=1):
        account_token = entry.get("account") or entry.get("account_code")
        if not account_token:
            raise LedgerError("ACCOUNT_NOT_FOUND", "分录缺少科目(account)")
        account = find_account(conn, account_token)
        debit = float(entry.get("debit", entry.get("debit_amount", 0)) or 0)
        credit = float(entry.get("credit", entry.get("credit_amount", 0)) or 0)

        dims: Dict[str, Optional[int]] = {
            "dept_id": None,
            "project_id": None,
            "customer_id": None,
            "supplier_id": None,
            "employee_id": None,
        }
        for key, dim_type in DIMENSION_FIELDS.items():
            code = entry.get(key)
            if code:
                dim_id = find_dimension(conn, dim_type, code)
                dims[f"{key}_id" if key != "department" else "dept_id"] = dim_id

        entries.append(
            {
                "line_no": idx,
                "account_code": account["code"],
                "account_name": account["name"],
                "description": entry.get("description"),
                "debit_amount": debit,
                "credit_amount": credit,
                **dims,
            }
        )
        total_debit += debit
        total_credit += credit

    return entries, total_debit, total_credit


def insert_voucher(
    conn,
    voucher_data: Dict[str, Any],
    entries: List[Dict[str, Any]],
    status: str,
    enforce_open: bool = True,
) -> Tuple[int, str, str, Optional[str]]:
    voucher_no = generate_voucher_no(conn, voucher_data["date"])
    period = parse_period(voucher_data["date"])
    ensure_period(conn, period)
    if enforce_open:
        assert_period_open(conn, period)
    confirmed_at = None
    reviewed_at = None
    if status == "reviewed":
        reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if status == "confirmed":
        confirmed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute(
        """
        INSERT INTO vouchers (voucher_no, date, period, description, status, reviewed_at, confirmed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            voucher_no,
            voucher_data["date"],
            period,
            voucher_data.get("description"),
            status,
            reviewed_at,
            confirmed_at,
        ),
    )
    voucher_id = cur.lastrowid
    for entry in entries:
        conn.execute(
            """
            INSERT INTO voucher_entries (
              voucher_id, line_no, account_code, account_name, description,
              debit_amount, credit_amount, dept_id, project_id, customer_id, supplier_id, employee_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                voucher_id,
                entry["line_no"],
                entry["account_code"],
                entry["account_name"],
                entry.get("description"),
                entry["debit_amount"],
                entry["credit_amount"],
                entry.get("dept_id"),
                entry.get("project_id"),
                entry.get("customer_id"),
                entry.get("supplier_id"),
                entry.get("employee_id"),
            ),
        )
    return voucher_id, voucher_no, period, confirmed_at


def _balance_key(entry: Dict[str, Any]) -> Tuple[Any, ...]:
    return (
        entry["account_code"],
        entry.get("dept_id") or 0,
        entry.get("project_id") or 0,
        entry.get("customer_id") or 0,
        entry.get("supplier_id") or 0,
        entry.get("employee_id") or 0,
    )


def _get_opening_balance(
    conn, period: str, account_code: str, dims: Tuple[int, int, int, int, int]
) -> float:
    prev = _prev_period(period)
    if not prev:
        return 0.0
    row = conn.execute(
        """
        SELECT closing_balance FROM balances
        WHERE period = ? AND account_code = ?
          AND dept_id = ? AND project_id = ? AND customer_id = ? AND supplier_id = ? AND employee_id = ?
        """,
        (prev, account_code, *dims),
    ).fetchone()
    return float(row["closing_balance"]) if row else 0.0


def update_balance_for_voucher(conn, voucher_id: int, period: str) -> int:
    entries = conn.execute(
        """
        SELECT ve.*, a.direction
        FROM voucher_entries ve
        JOIN accounts a ON ve.account_code = a.code
        WHERE ve.voucher_id = ?
        """,
        (voucher_id,),
    ).fetchall()

    updated_keys = set()
    for row in entries:
        dept_id = row["dept_id"] or 0
        project_id = row["project_id"] or 0
        customer_id = row["customer_id"] or 0
        supplier_id = row["supplier_id"] or 0
        employee_id = row["employee_id"] or 0
        key = (
            row["account_code"],
            period,
            dept_id,
            project_id,
            customer_id,
            supplier_id,
            employee_id,
        )
        updated_keys.add(key)
        balance_row = conn.execute(
            """
            SELECT * FROM balances
            WHERE account_code = ? AND period = ?
              AND dept_id = ? AND project_id = ? AND customer_id = ? AND supplier_id = ? AND employee_id = ?
            """,
            key,
        ).fetchone()
        if not balance_row:
            opening = _get_opening_balance(
                conn,
                period,
                row["account_code"],
                (dept_id, project_id, customer_id, supplier_id, employee_id),
            )
            conn.execute(
                """
                INSERT INTO balances (
                  account_code, period, dept_id, project_id, customer_id, supplier_id, employee_id,
                  opening_balance, debit_amount, credit_amount, closing_balance
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?)
                """,
                (
                    row["account_code"],
                    period,
                    dept_id,
                    project_id,
                    customer_id,
                    supplier_id,
                    employee_id,
                    opening,
                    opening,
                ),
            )
            balance_row = conn.execute(
                """
                SELECT * FROM balances
                WHERE account_code = ? AND period = ?
                  AND dept_id = ? AND project_id = ? AND customer_id = ? AND supplier_id = ? AND employee_id = ?
                """,
                key,
            ).fetchone()

        debit = float(balance_row["debit_amount"]) + float(row["debit_amount"] or 0)
        credit = float(balance_row["credit_amount"]) + float(row["credit_amount"] or 0)
        opening_balance = float(balance_row["opening_balance"] or 0)
        if row["direction"] == "debit":
            closing = opening_balance + debit - credit
        else:
            closing = opening_balance - debit + credit
        conn.execute(
            """
            UPDATE balances
            SET debit_amount = ?, credit_amount = ?, closing_balance = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (debit, credit, closing, balance_row["id"]),
        )

    return len(updated_keys)


def fetch_voucher(conn, voucher_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM vouchers WHERE id = ?", (voucher_id,)).fetchone()
    return dict(row) if row else None


def fetch_entries(conn, voucher_id: int) -> List[Dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM voucher_entries WHERE voucher_id = ? ORDER BY line_no",
        (voucher_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def review_voucher(conn, voucher_id: int) -> Dict[str, Any]:
    voucher = fetch_voucher(conn, voucher_id)
    if not voucher:
        raise LedgerError("VOUCHER_NOT_FOUND", f"凭证不存在: {voucher_id}")
    if voucher["status"] != "draft":
        raise LedgerError("VOUCHER_STATUS_INVALID", "仅草稿凭证可审核")
    reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "UPDATE vouchers SET status = 'reviewed', reviewed_at = ? WHERE id = ?",
        (reviewed_at, voucher_id),
    )
    voucher["status"] = "reviewed"
    voucher["reviewed_at"] = reviewed_at
    return voucher


def unreview_voucher(conn, voucher_id: int) -> Dict[str, Any]:
    voucher = fetch_voucher(conn, voucher_id)
    if not voucher:
        raise LedgerError("VOUCHER_NOT_FOUND", f"凭证不存在: {voucher_id}")
    if voucher["status"] != "reviewed":
        raise LedgerError("VOUCHER_STATUS_INVALID", "仅已审核凭证可反审核")
    conn.execute(
        "UPDATE vouchers SET status = 'draft', reviewed_at = NULL WHERE id = ?",
        (voucher_id,),
    )
    voucher["status"] = "draft"
    voucher["reviewed_at"] = None
    return voucher


def confirm_voucher(conn, voucher_id: int) -> Dict[str, Any]:
    voucher = fetch_voucher(conn, voucher_id)
    if not voucher:
        raise LedgerError("VOUCHER_NOT_FOUND", f"凭证不存在: {voucher_id}")
    if voucher["status"] != "reviewed":
        raise LedgerError("VOUCHER_NOT_REVIEWED", "未审核凭证不能记账")
    assert_period_open(conn, voucher["period"])

    entries = fetch_entries(conn, voucher_id)
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
        (confirmed_at, voucher_id),
    )
    balances_updated = update_balance_for_voucher(conn, voucher_id, voucher["period"])
    voucher["status"] = "confirmed"
    voucher["confirmed_at"] = confirmed_at
    voucher["balances_updated"] = balances_updated
    return voucher


def void_voucher(conn, voucher_id: int, reason: str) -> Dict[str, Any]:
    voucher = fetch_voucher(conn, voucher_id)
    if not voucher:
        raise LedgerError("VOUCHER_NOT_FOUND", f"凭证不存在: {voucher_id}")
    if voucher["status"] != "confirmed":
        raise LedgerError("VOUCHER_NOT_CONFIRMED", "仅已确认凭证可冲销")

    entries = fetch_entries(conn, voucher_id)
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
        conn, void_data, reversed_entries, "confirmed", enforce_open=False
    )
    update_balance_for_voucher(conn, void_id, period)

    conn.execute(
        """
        UPDATE vouchers
        SET status = 'voided', void_reason = ?, voided_at = ?
        WHERE id = ?
        """,
        (reason, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), voucher_id),
    )
    conn.execute(
        """
        INSERT INTO void_vouchers (original_voucher_id, void_voucher_id, void_reason)
        VALUES (?, ?, ?)
        """,
        (voucher_id, void_id, reason),
    )
    return {
        "original_voucher_id": voucher_id,
        "void_voucher_id": void_id,
        "void_voucher_no": void_no,
        "period": period,
    }


def balances_for_period(
    conn, period: str, dims: Optional[Dict[str, int]] = None
) -> List[Dict[str, Any]]:
    conditions = ["b.period = ?"]
    params: List[Any] = [period]
    if dims:
        for field in ("dept_id", "project_id", "customer_id", "supplier_id", "employee_id"):
            value = dims.get(field)
            if value is not None:
                conditions.append(f"b.{field} = ?")
                params.append(value)
    rows = conn.execute(
        f"""
        SELECT b.*, a.name AS account_name, a.type AS account_type, a.direction AS account_direction
        FROM balances b
        JOIN accounts a ON b.account_code = a.code
        WHERE {' AND '.join(conditions)}
        """,
        params,
    ).fetchall()
    return [dict(r) for r in rows]


def close_period(conn, period: str) -> Dict[str, Any]:
    ensure_period(conn, period)
    assert_period_open(conn, period)

    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM vouchers WHERE period = ? AND status IN ('draft', 'reviewed')",
        (period,),
    ).fetchone()
    if row and row["cnt"] > 0:
        raise LedgerError("PERIOD_HAS_UNPOSTED", "期间存在未记账凭证")

    balances = balances_for_period(conn, period)
    config = _load_close_config()
    profit_account = config["profit_account"]
    retain_account = config.get("retain_account")

    closing_entries, net_by_dims = _build_income_close_entries(
        conn, balances, profit_account
    )

    closing_voucher_id = None
    if closing_entries:
        close_data = {
            "date": _period_end_date(period),
            "description": f"{period} 期末结转",
        }
        closing_voucher_id, _, _, _ = insert_voucher(
            conn, close_data, closing_entries, "confirmed"
        )
        update_balance_for_voucher(conn, closing_voucher_id, period)

    transfer_voucher_id = None
    if retain_account and retain_account != profit_account:
        transfer_entries = _build_profit_transfer_entries(
            conn, period, profit_account, retain_account
        )
        if transfer_entries:
            transfer_data = {
                "date": _period_end_date(period),
                "description": f"{period} 本年利润结转",
            }
            transfer_voucher_id, _, _, _ = insert_voucher(
                conn, transfer_data, transfer_entries, "confirmed"
            )
            update_balance_for_voucher(conn, transfer_voucher_id, period)

    conn.execute(
        "UPDATE periods SET status = 'closed', closed_at = CURRENT_TIMESTAMP WHERE period = ?",
        (period,),
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO period_closings (
          period, closing_voucher_id, transfer_voucher_id, created_at, reopened_at
        )
        VALUES (?, ?, ?, CURRENT_TIMESTAMP, NULL)
        """,
        (period, closing_voucher_id, transfer_voucher_id),
    )

    next_period = _next_period(period)
    if next_period:
        _roll_forward_balances(conn, period, next_period)

    net_total = round(sum(net_by_dims.values()), 2)
    return {
        "period": period,
        "next_period": next_period,
        "closing_voucher_id": closing_voucher_id,
        "transfer_voucher_id": transfer_voucher_id,
        "net_income": net_total,
    }


def _roll_forward_balances(conn, period: str, next_period: str) -> None:
    ensure_period(conn, next_period)
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM vouchers WHERE period = ?",
        (next_period,),
    ).fetchone()
    if row and row["cnt"] > 0:
        raise LedgerError("NEXT_PERIOD_HAS_VOUCHERS", f"下期已有凭证: {next_period}")
    row = conn.execute(
        """
        SELECT COUNT(*) AS cnt FROM balances
        WHERE period = ? AND (debit_amount != 0 OR credit_amount != 0)
        """,
        (next_period,),
    ).fetchone()
    if row and row["cnt"] > 0:
        raise LedgerError("NEXT_PERIOD_HAS_BALANCES", f"下期已有发生额: {next_period}")

    balances = balances_for_period(conn, period)
    conn.execute("DELETE FROM balances WHERE period = ?", (next_period,))
    for balance in balances:
        closing = float(balance.get("closing_balance") or 0)
        conn.execute(
            """
            INSERT INTO balances (
              account_code, period, dept_id, project_id, customer_id, supplier_id, employee_id,
              opening_balance, debit_amount, credit_amount, closing_balance
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?)
            """,
            (
                balance["account_code"],
                next_period,
                balance.get("dept_id") or 0,
                balance.get("project_id") or 0,
                balance.get("customer_id") or 0,
                balance.get("supplier_id") or 0,
                balance.get("employee_id") or 0,
                closing,
                closing,
            ),
        )


def _fetch_closing_voucher_ids(conn, period: str) -> Tuple[Optional[int], Optional[int]]:
    row = conn.execute(
        "SELECT closing_voucher_id, transfer_voucher_id FROM period_closings WHERE period = ?",
        (period,),
    ).fetchone()
    if row:
        return row["closing_voucher_id"], row["transfer_voucher_id"]
    closing_row = conn.execute(
        """
        SELECT id FROM vouchers
        WHERE period = ? AND description = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (period, f"{period} 期末结转"),
    ).fetchone()
    transfer_row = conn.execute(
        """
        SELECT id FROM vouchers
        WHERE period = ? AND description = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (period, f"{period} 本年利润结转"),
    ).fetchone()
    return (
        closing_row["id"] if closing_row else None,
        transfer_row["id"] if transfer_row else None,
    )


def reopen_period(conn, period: str) -> Dict[str, Any]:
    status = get_period_status(conn, period)
    if status != "closed":
        raise LedgerError("PERIOD_NOT_CLOSED", f"期间未结账: {period}")
    next_period = _next_period(period)
    if next_period:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM vouchers WHERE period = ?",
            (next_period,),
        ).fetchone()
        if row and row["cnt"] > 0:
            raise LedgerError("NEXT_PERIOD_HAS_VOUCHERS", f"下期已有凭证: {next_period}")
        row = conn.execute(
            """
            SELECT COUNT(*) AS cnt FROM balances
            WHERE period = ? AND (debit_amount != 0 OR credit_amount != 0)
            """,
            (next_period,),
        ).fetchone()
        if row and row["cnt"] > 0:
            raise LedgerError("NEXT_PERIOD_HAS_BALANCES", f"下期已有发生额: {next_period}")

    closing_id, transfer_id = _fetch_closing_voucher_ids(conn, period)
    voided_ids: List[int] = []
    for voucher_id in (closing_id, transfer_id):
        if not voucher_id:
            continue
        voucher = fetch_voucher(conn, voucher_id)
        if voucher and voucher["status"] == "confirmed":
            result = void_voucher(conn, voucher_id, f"reopen {period}")
            voided_ids.append(result["void_voucher_id"])

    conn.execute(
        "UPDATE periods SET status = 'open', closed_at = NULL WHERE period = ?",
        (period,),
    )
    if next_period:
        conn.execute("DELETE FROM balances WHERE period = ?", (next_period,))
    conn.execute(
        "UPDATE period_closings SET reopened_at = CURRENT_TIMESTAMP WHERE period = ?",
        (period,),
    )
    return {
        "period": period,
        "status": "open",
        "void_voucher_ids": voided_ids,
        "next_period": next_period,
    }


def _build_income_close_entries(
    conn, balances: List[Dict[str, Any]], profit_account: str
) -> Tuple[List[Dict[str, Any]], Dict[Tuple[int, int, int, int, int], float]]:
    profit = find_account(conn, profit_account)
    entries: List[Dict[str, Any]] = []
    net_by_dims: Dict[Tuple[int, int, int, int, int], float] = {}

    for balance in balances:
        if balance.get("account_type") not in ("revenue", "expense"):
            continue
        closing = float(balance.get("closing_balance") or 0)
        if abs(closing) < 0.01:
            continue
        _append_reverse_entry(entries, balance)
        dims = _dims_from_balance(balance)
        if balance.get("account_type") == "revenue":
            net_by_dims[dims] = net_by_dims.get(dims, 0.0) + closing
        else:
            net_by_dims[dims] = net_by_dims.get(dims, 0.0) - closing

    for dims, net in net_by_dims.items():
        if abs(net) < 0.01:
            continue
        debit = abs(net) if net < 0 else 0.0
        credit = net if net > 0 else 0.0
        _append_entry(
            entries,
            profit["code"],
            profit["name"],
            debit,
            credit,
            dims,
            "期末结转",
        )

    return entries, net_by_dims


def _build_profit_transfer_entries(
    conn, period: str, profit_account: str, retain_account: str
) -> List[Dict[str, Any]]:
    profit = find_account(conn, profit_account)
    retain = find_account(conn, retain_account)
    balances = balances_for_period(conn, period)
    entries: List[Dict[str, Any]] = []

    for balance in balances:
        if balance.get("account_code") != profit_account:
            continue
        closing = float(balance.get("closing_balance") or 0)
        if abs(closing) < 0.01:
            continue
        dims = _dims_from_balance(balance)
        if closing > 0:
            _append_entry(
                entries,
                profit["code"],
                profit["name"],
                closing,
                0.0,
                dims,
                "本年利润结转",
            )
            _append_entry(
                entries,
                retain["code"],
                retain["name"],
                0.0,
                closing,
                dims,
                "本年利润结转",
            )
        else:
            amount = abs(closing)
            _append_entry(
                entries,
                profit["code"],
                profit["name"],
                0.0,
                amount,
                dims,
                "本年利润结转",
            )
            _append_entry(
                entries,
                retain["code"],
                retain["name"],
                amount,
                0.0,
                dims,
                "本年利润结转",
            )

    return entries


def _dims_from_balance(balance: Dict[str, Any]) -> Tuple[int, int, int, int, int]:
    return (
        balance.get("dept_id") or 0,
        balance.get("project_id") or 0,
        balance.get("customer_id") or 0,
        balance.get("supplier_id") or 0,
        balance.get("employee_id") or 0,
    )


def _append_reverse_entry(entries: List[Dict[str, Any]], balance: Dict[str, Any]) -> None:
    closing = float(balance.get("closing_balance") or 0)
    if balance.get("account_direction") == "debit":
        debit = abs(closing) if closing < 0 else 0.0
        credit = closing if closing > 0 else 0.0
    else:
        debit = closing if closing > 0 else 0.0
        credit = abs(closing) if closing < 0 else 0.0
    _append_entry(
        entries,
        balance["account_code"],
        balance.get("account_name"),
        debit,
        credit,
        _dims_from_balance(balance),
        "期末结转",
    )


def _append_entry(
    entries: List[Dict[str, Any]],
    account_code: str,
    account_name: str,
    debit_amount: float,
    credit_amount: float,
    dims: Tuple[int, int, int, int, int],
    description: str,
) -> None:
    entries.append(
        {
            "line_no": len(entries) + 1,
            "account_code": account_code,
            "account_name": account_name,
            "description": description,
            "debit_amount": debit_amount,
            "credit_amount": credit_amount,
            "dept_id": dims[0] or None,
            "project_id": dims[1] or None,
            "customer_id": dims[2] or None,
            "supplier_id": dims[3] or None,
            "employee_id": dims[4] or None,
        }
    )


def _normalize_dims(dims: Optional[Dict[str, Optional[int]]] = None) -> Dict[str, Optional[int]]:
    payload = dims or {}
    return {
        "dept_id": payload.get("dept_id"),
        "project_id": payload.get("project_id"),
        "customer_id": payload.get("customer_id"),
        "supplier_id": payload.get("supplier_id"),
        "employee_id": payload.get("employee_id"),
    }


def _build_entry_for_account(
    conn,
    account_code: str,
    debit_amount: float,
    credit_amount: float,
    dims: Optional[Dict[str, Optional[int]]] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    account = find_account(conn, account_code)
    entry = {
        "line_no": 0,
        "account_code": account["code"],
        "account_name": account["name"],
        "description": description,
        "debit_amount": round(debit_amount, 2),
        "credit_amount": round(credit_amount, 2),
    }
    entry.update(_normalize_dims(dims))
    return entry


def _build_entries(
    conn,
    lines: List[Tuple[str, float, float]],
    dims: Optional[Dict[str, Optional[int]]] = None,
    description: Optional[str] = None,
) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    for account_code, debit_amount, credit_amount in lines:
        entry = _build_entry_for_account(
            conn,
            account_code,
            debit_amount,
            credit_amount,
            dims=dims,
            description=description,
        )
        entry["line_no"] = len(entries) + 1
        entries.append(entry)
    return entries


def _create_posted_voucher(
    conn, date: str, description: str, entries: List[Dict[str, Any]]
) -> Dict[str, Any]:
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
    voucher_id, voucher_no, period, _ = insert_voucher(
        conn,
        {"date": date, "description": description},
        entries,
        "reviewed",
    )
    voucher = confirm_voucher(conn, voucher_id)
    return {
        "voucher_id": voucher_id,
        "voucher_no": voucher_no,
        "period": period,
        "confirmed_at": voucher.get("confirmed_at"),
    }


def add_ar_item(
    conn, customer_code: str, amount: float, date: str, description: Optional[str] = None
) -> Dict[str, Any]:
    if amount <= 0:
        raise LedgerError("AR_AMOUNT_INVALID", "应收金额必须大于 0")
    customer_id = find_dimension(conn, "customer", customer_code)
    mapping = _load_subledger_mapping()["ar"]
    description = description or "AR item"
    dims = {"customer_id": customer_id}
    entries = _build_entries(
        conn,
        [
            (mapping["ar_account"], amount, 0.0),
            (mapping["revenue_account"], 0.0, amount),
        ],
        dims=dims,
        description=description,
    )
    voucher = _create_posted_voucher(conn, date, description, entries)
    cur = conn.execute(
        """
        INSERT INTO ar_items (customer_id, voucher_id, amount, settled_amount, status)
        VALUES (?, ?, ?, 0, 'open')
        """,
        (customer_id, voucher["voucher_id"], round(amount, 2)),
    )
    return {
        "item_id": cur.lastrowid,
        "voucher_id": voucher["voucher_id"],
        "amount": round(amount, 2),
        "status": "open",
    }


def settle_ar_item(
    conn, item_id: int, amount: float, date: str, description: Optional[str] = None
) -> Dict[str, Any]:
    row = conn.execute("SELECT * FROM ar_items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        raise LedgerError("AR_ITEM_NOT_FOUND", f"应收不存在: {item_id}")
    if amount <= 0:
        raise LedgerError("AR_AMOUNT_INVALID", "核销金额必须大于 0")
    remaining = float(row["amount"]) - float(row["settled_amount"] or 0)
    if amount - remaining > 0.01:
        raise LedgerError("AR_AMOUNT_EXCEED", "核销金额超过剩余应收")

    mapping = _load_subledger_mapping()["ar"]
    description = description or "AR settlement"
    dims = {"customer_id": row["customer_id"]}
    entries = _build_entries(
        conn,
        [
            (mapping["bank_account"], amount, 0.0),
            (mapping["ar_account"], 0.0, amount),
        ],
        dims=dims,
        description=description,
    )
    voucher = _create_posted_voucher(conn, date, description, entries)
    conn.execute(
        """
        INSERT INTO settlements (item_type, item_id, amount, voucher_id, date)
        VALUES ('ar', ?, ?, ?, ?)
        """,
        (item_id, round(amount, 2), voucher["voucher_id"], date),
    )
    new_settled = round(float(row["settled_amount"] or 0) + amount, 2)
    status = "settled" if new_settled >= float(row["amount"]) - 0.01 else "open"
    conn.execute(
        "UPDATE ar_items SET settled_amount = ?, status = ? WHERE id = ?",
        (new_settled, status, item_id),
    )
    return {
        "item_id": item_id,
        "voucher_id": voucher["voucher_id"],
        "settled_amount": new_settled,
        "status": status,
    }


def list_ar_items(
    conn,
    status: Optional[str] = None,
    period: Optional[str] = None,
    customer_code: Optional[str] = None,
) -> List[Dict[str, Any]]:
    conditions: List[str] = []
    params: List[Any] = []
    if status and status != "all":
        conditions.append("ai.status = ?")
        params.append(status)
    if period:
        conditions.append("v.period = ?")
        params.append(period)
    if customer_code:
        customer_id = find_dimension(conn, "customer", customer_code)
        conditions.append("ai.customer_id = ?")
        params.append(customer_id)
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = conn.execute(
        f"""
        SELECT ai.*, v.date AS voucher_date, v.period AS period
        FROM ar_items ai
        JOIN vouchers v ON ai.voucher_id = v.id
        {where_clause}
        ORDER BY ai.id
        """,
        params,
    ).fetchall()
    return [dict(row) for row in rows]


def ar_aging(conn, as_of: str) -> Dict[str, float]:
    rows = conn.execute(
        """
        SELECT ai.amount, ai.settled_amount, v.date
        FROM ar_items ai
        JOIN vouchers v ON ai.voucher_id = v.id
        WHERE ai.status = 'open'
        """
    ).fetchall()
    buckets = {"0_30": 0.0, "31_60": 0.0, "61_90": 0.0, "90_plus": 0.0}
    as_of_date = datetime.strptime(as_of, "%Y-%m-%d")
    for row in rows:
        remaining = float(row["amount"]) - float(row["settled_amount"] or 0)
        if remaining <= 0:
            continue
        delta = (as_of_date - datetime.strptime(row["date"], "%Y-%m-%d")).days
        if delta <= 30:
            buckets["0_30"] += remaining
        elif delta <= 60:
            buckets["31_60"] += remaining
        elif delta <= 90:
            buckets["61_90"] += remaining
        else:
            buckets["90_plus"] += remaining
    return {k: round(v, 2) for k, v in buckets.items()}


def reconcile_ar(
    conn, period: str, customer_code: Optional[str] = None
) -> Dict[str, Any]:
    mapping = _load_subledger_mapping()["ar"]
    cutoff = _period_end_date(period)
    conditions = ["v.date <= ?"]
    params: List[Any] = [cutoff]
    if customer_code:
        customer_id = find_dimension(conn, "customer", customer_code)
        conditions.append("ai.customer_id = ?")
        params.append(customer_id)
    where_clause = f"WHERE {' AND '.join(conditions)}"
    rows = conn.execute(
        f"""
        SELECT ai.id, ai.amount, COALESCE(SUM(s.amount), 0) AS settled
        FROM ar_items ai
        JOIN vouchers v ON ai.voucher_id = v.id
        LEFT JOIN settlements s
          ON s.item_type = 'ar'
         AND s.item_id = ai.id
         AND s.date <= ?
        {where_clause}
        GROUP BY ai.id
        """,
        [cutoff, *params],
    ).fetchall()
    outstanding = sum(float(row["amount"]) - float(row["settled"]) for row in rows)

    balance_row = conn.execute(
        """
        SELECT COALESCE(SUM(closing_balance), 0) AS total
        FROM balances
        WHERE period = ? AND account_code = ?
        """,
        (period, mapping["ar_account"]),
    ).fetchone()
    ledger_balance = float(balance_row["total"] or 0)
    if customer_code:
        balance_row = conn.execute(
            """
            SELECT COALESCE(SUM(closing_balance), 0) AS total
            FROM balances
            WHERE period = ? AND account_code = ? AND customer_id = ?
            """,
            (period, mapping["ar_account"], customer_id),
        ).fetchone()
        ledger_balance = float(balance_row["total"] or 0)

    return {
        "period": period,
        "outstanding": round(outstanding, 2),
        "ledger_balance": round(ledger_balance, 2),
        "difference": round(ledger_balance - outstanding, 2),
    }


def add_ap_item(
    conn, supplier_code: str, amount: float, date: str, description: Optional[str] = None
) -> Dict[str, Any]:
    if amount <= 0:
        raise LedgerError("AP_AMOUNT_INVALID", "应付金额必须大于 0")
    supplier_id = find_dimension(conn, "supplier", supplier_code)
    mapping = _load_subledger_mapping()["ap"]
    description = description or "AP item"
    dims = {"supplier_id": supplier_id}
    entries = _build_entries(
        conn,
        [
            (mapping["inventory_account"], amount, 0.0),
            (mapping["ap_account"], 0.0, amount),
        ],
        dims=dims,
        description=description,
    )
    voucher = _create_posted_voucher(conn, date, description, entries)
    cur = conn.execute(
        """
        INSERT INTO ap_items (supplier_id, voucher_id, amount, settled_amount, status)
        VALUES (?, ?, ?, 0, 'open')
        """,
        (supplier_id, voucher["voucher_id"], round(amount, 2)),
    )
    return {
        "item_id": cur.lastrowid,
        "voucher_id": voucher["voucher_id"],
        "amount": round(amount, 2),
        "status": "open",
    }


def settle_ap_item(
    conn, item_id: int, amount: float, date: str, description: Optional[str] = None
) -> Dict[str, Any]:
    row = conn.execute("SELECT * FROM ap_items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        raise LedgerError("AP_ITEM_NOT_FOUND", f"应付不存在: {item_id}")
    if amount <= 0:
        raise LedgerError("AP_AMOUNT_INVALID", "核销金额必须大于 0")
    remaining = float(row["amount"]) - float(row["settled_amount"] or 0)
    if amount - remaining > 0.01:
        raise LedgerError("AP_AMOUNT_EXCEED", "核销金额超过剩余应付")

    mapping = _load_subledger_mapping()["ap"]
    description = description or "AP settlement"
    dims = {"supplier_id": row["supplier_id"]}
    entries = _build_entries(
        conn,
        [
            (mapping["ap_account"], amount, 0.0),
            (mapping["bank_account"], 0.0, amount),
        ],
        dims=dims,
        description=description,
    )
    voucher = _create_posted_voucher(conn, date, description, entries)
    conn.execute(
        """
        INSERT INTO settlements (item_type, item_id, amount, voucher_id, date)
        VALUES ('ap', ?, ?, ?, ?)
        """,
        (item_id, round(amount, 2), voucher["voucher_id"], date),
    )
    new_settled = round(float(row["settled_amount"] or 0) + amount, 2)
    status = "settled" if new_settled >= float(row["amount"]) - 0.01 else "open"
    conn.execute(
        "UPDATE ap_items SET settled_amount = ?, status = ? WHERE id = ?",
        (new_settled, status, item_id),
    )
    return {
        "item_id": item_id,
        "voucher_id": voucher["voucher_id"],
        "settled_amount": new_settled,
        "status": status,
    }


def list_ap_items(
    conn,
    status: Optional[str] = None,
    period: Optional[str] = None,
    supplier_code: Optional[str] = None,
) -> List[Dict[str, Any]]:
    conditions: List[str] = []
    params: List[Any] = []
    if status and status != "all":
        conditions.append("ai.status = ?")
        params.append(status)
    if period:
        conditions.append("v.period = ?")
        params.append(period)
    if supplier_code:
        supplier_id = find_dimension(conn, "supplier", supplier_code)
        conditions.append("ai.supplier_id = ?")
        params.append(supplier_id)
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = conn.execute(
        f"""
        SELECT ai.*, v.date AS voucher_date, v.period AS period
        FROM ap_items ai
        JOIN vouchers v ON ai.voucher_id = v.id
        {where_clause}
        ORDER BY ai.id
        """,
        params,
    ).fetchall()
    return [dict(row) for row in rows]


def ap_aging(conn, as_of: str) -> Dict[str, float]:
    rows = conn.execute(
        """
        SELECT ai.amount, ai.settled_amount, v.date
        FROM ap_items ai
        JOIN vouchers v ON ai.voucher_id = v.id
        WHERE ai.status = 'open'
        """
    ).fetchall()
    buckets = {"0_30": 0.0, "31_60": 0.0, "61_90": 0.0, "90_plus": 0.0}
    as_of_date = datetime.strptime(as_of, "%Y-%m-%d")
    for row in rows:
        remaining = float(row["amount"]) - float(row["settled_amount"] or 0)
        if remaining <= 0:
            continue
        delta = (as_of_date - datetime.strptime(row["date"], "%Y-%m-%d")).days
        if delta <= 30:
            buckets["0_30"] += remaining
        elif delta <= 60:
            buckets["31_60"] += remaining
        elif delta <= 90:
            buckets["61_90"] += remaining
        else:
            buckets["90_plus"] += remaining
    return {k: round(v, 2) for k, v in buckets.items()}


def reconcile_ap(
    conn, period: str, supplier_code: Optional[str] = None
) -> Dict[str, Any]:
    mapping = _load_subledger_mapping()["ap"]
    cutoff = _period_end_date(period)
    conditions = ["v.date <= ?"]
    params: List[Any] = [cutoff]
    if supplier_code:
        supplier_id = find_dimension(conn, "supplier", supplier_code)
        conditions.append("ai.supplier_id = ?")
        params.append(supplier_id)
    where_clause = f"WHERE {' AND '.join(conditions)}"
    rows = conn.execute(
        f"""
        SELECT ai.id, ai.amount, COALESCE(SUM(s.amount), 0) AS settled
        FROM ap_items ai
        JOIN vouchers v ON ai.voucher_id = v.id
        LEFT JOIN settlements s
          ON s.item_type = 'ap'
         AND s.item_id = ai.id
         AND s.date <= ?
        {where_clause}
        GROUP BY ai.id
        """,
        [cutoff, *params],
    ).fetchall()
    outstanding = sum(float(row["amount"]) - float(row["settled"]) for row in rows)

    balance_row = conn.execute(
        """
        SELECT COALESCE(SUM(closing_balance), 0) AS total
        FROM balances
        WHERE period = ? AND account_code = ?
        """,
        (period, mapping["ap_account"]),
    ).fetchone()
    ledger_balance = float(balance_row["total"] or 0)
    if supplier_code:
        balance_row = conn.execute(
            """
            SELECT COALESCE(SUM(closing_balance), 0) AS total
            FROM balances
            WHERE period = ? AND account_code = ? AND supplier_id = ?
            """,
            (period, mapping["ap_account"], supplier_id),
        ).fetchone()
        ledger_balance = float(balance_row["total"] or 0)

    return {
        "period": period,
        "outstanding": round(outstanding, 2),
        "ledger_balance": round(ledger_balance, 2),
        "difference": round(ledger_balance - outstanding, 2),
    }


def _get_inventory_item(conn, sku: str) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT * FROM inventory_items WHERE sku = ?",
        (sku,),
    ).fetchone()
    return dict(row) if row else None


def _ensure_inventory_item(
    conn, sku: str, name: Optional[str] = None, unit: Optional[str] = None
) -> Dict[str, Any]:
    existing = _get_inventory_item(conn, sku)
    if existing:
        return existing
    final_name = name or sku
    final_unit = unit or "unit"
    conn.execute(
        "INSERT INTO inventory_items (sku, name, unit) VALUES (?, ?, ?)",
        (sku, final_name, final_unit),
    )
    return {"sku": sku, "name": final_name, "unit": final_unit}


def _get_inventory_balance(conn, sku: str, period: str) -> Tuple[float, float]:
    row = conn.execute(
        "SELECT qty, amount FROM inventory_balances WHERE sku = ? AND period = ?",
        (sku, period),
    ).fetchone()
    if row:
        return float(row["qty"]), float(row["amount"])
    prev = conn.execute(
        """
        SELECT qty, amount FROM inventory_balances
        WHERE sku = ? AND period < ?
        ORDER BY period DESC
        LIMIT 1
        """,
        (sku, period),
    ).fetchone()
    if prev:
        return float(prev["qty"]), float(prev["amount"])
    return 0.0, 0.0


def _upsert_inventory_balance(conn, sku: str, period: str, qty: float, amount: float) -> None:
    conn.execute(
        """
        INSERT INTO inventory_balances (sku, period, qty, amount, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(sku, period) DO UPDATE SET
          qty = excluded.qty,
          amount = excluded.amount,
          updated_at = CURRENT_TIMESTAMP
        """,
        (sku, period, round(qty, 2), round(amount, 2)),
    )


def inventory_move_in(
    conn,
    sku: str,
    qty: float,
    unit_cost: float,
    date: str,
    description: Optional[str] = None,
    name: Optional[str] = None,
    unit: Optional[str] = None,
) -> Dict[str, Any]:
    if qty <= 0 or unit_cost < 0:
        raise LedgerError("INVENTORY_AMOUNT_INVALID", "入库数量或成本无效")
    _ensure_inventory_item(conn, sku, name, unit)
    mapping = _load_subledger_mapping()["inventory"]
    description = description or "Inventory in"
    total_cost = round(qty * unit_cost, 2)
    entries = _build_entries(
        conn,
        [
            (mapping["inventory_account"], total_cost, 0.0),
            (mapping["offset_account"], 0.0, total_cost),
        ],
        description=description,
    )
    voucher = _create_posted_voucher(conn, date, description, entries)
    conn.execute(
        """
        INSERT INTO inventory_moves (sku, direction, qty, unit_cost, total_cost, voucher_id, date)
        VALUES (?, 'in', ?, ?, ?, ?, ?)
        """,
        (sku, round(qty, 2), round(unit_cost, 2), total_cost, voucher["voucher_id"], date),
    )
    period = parse_period(date)
    current_qty, current_amount = _get_inventory_balance(conn, sku, period)
    new_qty = round(current_qty + qty, 2)
    new_amount = round(current_amount + total_cost, 2)
    _upsert_inventory_balance(conn, sku, period, new_qty, new_amount)
    return {
        "sku": sku,
        "voucher_id": voucher["voucher_id"],
        "qty": round(qty, 2),
        "unit_cost": round(unit_cost, 2),
        "total_cost": total_cost,
        "period": period,
    }


def inventory_move_out(
    conn,
    sku: str,
    qty: float,
    date: str,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    if qty <= 0:
        raise LedgerError("INVENTORY_AMOUNT_INVALID", "出库数量无效")
    mapping = _load_subledger_mapping()["inventory"]
    description = description or "Inventory out"
    period = parse_period(date)
    current_qty, current_amount = _get_inventory_balance(conn, sku, period)
    if current_qty <= 0 or qty - current_qty > 0.01:
        raise LedgerError("INVENTORY_INSUFFICIENT", "库存数量不足")
    avg_cost = current_amount / current_qty if current_qty else 0.0
    unit_cost = round(avg_cost, 2)
    total_cost = round(unit_cost * qty, 2)
    entries = _build_entries(
        conn,
        [
            (mapping["cost_account"], total_cost, 0.0),
            (mapping["inventory_account"], 0.0, total_cost),
        ],
        description=description,
    )
    voucher = _create_posted_voucher(conn, date, description, entries)
    conn.execute(
        """
        INSERT INTO inventory_moves (sku, direction, qty, unit_cost, total_cost, voucher_id, date)
        VALUES (?, 'out', ?, ?, ?, ?, ?)
        """,
        (sku, round(qty, 2), unit_cost, total_cost, voucher["voucher_id"], date),
    )
    new_qty = round(current_qty - qty, 2)
    new_amount = round(current_amount - total_cost, 2)
    _upsert_inventory_balance(conn, sku, period, new_qty, new_amount)
    return {
        "sku": sku,
        "voucher_id": voucher["voucher_id"],
        "qty": round(qty, 2),
        "unit_cost": unit_cost,
        "total_cost": total_cost,
        "period": period,
    }


def inventory_balance(conn, period: str, sku: Optional[str] = None) -> List[Dict[str, Any]]:
    conditions = ["period = ?"]
    params: List[Any] = [period]
    if sku:
        conditions.append("sku = ?")
        params.append(sku)
    rows = conn.execute(
        f"SELECT * FROM inventory_balances WHERE {' AND '.join(conditions)} ORDER BY sku",
        params,
    ).fetchall()
    return [dict(row) for row in rows]


def reconcile_inventory(conn, period: str) -> Dict[str, Any]:
    mapping = _load_subledger_mapping()["inventory"]
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM inventory_balances WHERE period = ?",
        (period,),
    ).fetchone()
    inventory_total = float(row["total"] or 0)
    balance_row = conn.execute(
        """
        SELECT COALESCE(SUM(closing_balance), 0) AS total
        FROM balances
        WHERE period = ? AND account_code = ?
        """,
        (period, mapping["inventory_account"]),
    ).fetchone()
    ledger_balance = float(balance_row["total"] or 0)
    return {
        "period": period,
        "inventory_total": round(inventory_total, 2),
        "ledger_balance": round(ledger_balance, 2),
        "difference": round(ledger_balance - inventory_total, 2),
    }


def add_fixed_asset(
    conn,
    name: str,
    cost: float,
    life_years: int,
    salvage_value: float,
    acquired_at: str,
) -> Dict[str, Any]:
    if cost <= 0:
        raise LedgerError("ASSET_COST_INVALID", "固定资产成本必须大于 0")
    if life_years <= 0:
        raise LedgerError("ASSET_LIFE_INVALID", "固定资产年限必须大于 0")
    mapping = _load_subledger_mapping()["fixed_asset"]
    description = f"Fixed asset: {name}"
    entries = _build_entries(
        conn,
        [
            (mapping["asset_account"], cost, 0.0),
            (mapping["bank_account"], 0.0, cost),
        ],
        description=description,
    )
    voucher = _create_posted_voucher(conn, acquired_at, description, entries)
    cur = conn.execute(
        """
        INSERT INTO fixed_assets (name, cost, acquired_at, life_years, salvage_value, status)
        VALUES (?, ?, ?, ?, ?, 'active')
        """,
        (name, round(cost, 2), acquired_at, life_years, round(salvage_value, 2)),
    )
    return {"asset_id": cur.lastrowid, "voucher_id": voucher["voucher_id"]}


def depreciate_assets(conn, period: str) -> Dict[str, Any]:
    mapping = _load_subledger_mapping()["fixed_asset"]
    assets = conn.execute(
        "SELECT * FROM fixed_assets WHERE status = 'active' ORDER BY id"
    ).fetchall()
    entries: List[Tuple[int, float]] = []
    for asset in assets:
        existing = conn.execute(
            "SELECT 1 FROM fixed_asset_depreciations WHERE asset_id = ? AND period = ?",
            (asset["id"], period),
        ).fetchone()
        if existing:
            continue
        total_depr_row = conn.execute(
            "SELECT SUM(amount) AS total FROM fixed_asset_depreciations WHERE asset_id = ?",
            (asset["id"],),
        ).fetchone()
        total_depr = float(total_depr_row["total"] or 0)
        depreciable = float(asset["cost"]) - float(asset["salvage_value"] or 0)
        remaining = depreciable - total_depr
        if remaining <= 0:
            continue
        months = int(asset["life_years"]) * 12
        monthly = round(depreciable / months, 2)
        amount = monthly if remaining > monthly else round(remaining, 2)
        if amount <= 0:
            continue
        entries.append((int(asset["id"]), amount))

    if not entries:
        raise LedgerError("DEPRECIATION_EMPTY", "没有可计提的资产")

    total_amount = round(sum(amount for _, amount in entries), 2)
    description = f"Depreciation {period}"
    voucher_entries = _build_entries(
        conn,
        [
            (mapping["depreciation_expense_account"], total_amount, 0.0),
            (mapping["accum_depreciation_account"], 0.0, total_amount),
        ],
        description=description,
    )
    voucher = _create_posted_voucher(
        conn,
        f"{period}-01",
        description,
        voucher_entries,
    )
    for asset_id, amount in entries:
        conn.execute(
            """
            INSERT INTO fixed_asset_depreciations (asset_id, period, amount, voucher_id)
            VALUES (?, ?, ?, ?)
            """,
            (asset_id, period, amount, voucher["voucher_id"]),
        )
    return {
        "voucher_id": voucher["voucher_id"],
        "total_amount": total_amount,
        "assets_count": len(entries),
    }


def dispose_fixed_asset(
    conn, asset_id: int, date: str, description: Optional[str] = None
) -> Dict[str, Any]:
    asset = conn.execute(
        "SELECT * FROM fixed_assets WHERE id = ?",
        (asset_id,),
    ).fetchone()
    if not asset:
        raise LedgerError("ASSET_NOT_FOUND", f"固定资产不存在: {asset_id}")
    if asset["status"] != "active":
        raise LedgerError("ASSET_STATUS_INVALID", "固定资产已处置")
    mapping = _load_subledger_mapping()["fixed_asset"]
    total_depr_row = conn.execute(
        "SELECT SUM(amount) AS total FROM fixed_asset_depreciations WHERE asset_id = ?",
        (asset_id,),
    ).fetchone()
    accumulated = round(float(total_depr_row["total"] or 0), 2)
    cost = round(float(asset["cost"]), 2)
    net_value = round(cost - accumulated, 2)
    description = description or f"Dispose asset {asset_id}"
    lines = []
    if accumulated > 0:
        lines.append((mapping["accum_depreciation_account"], accumulated, 0.0))
    if net_value >= 0:
        lines.append((mapping["depreciation_expense_account"], net_value, 0.0))
    else:
        lines.append((mapping["depreciation_expense_account"], 0.0, abs(net_value)))
    lines.append((mapping["asset_account"], 0.0, cost))
    entries = _build_entries(conn, lines, description=description)
    voucher = _create_posted_voucher(conn, date, description, entries)
    conn.execute(
        "UPDATE fixed_assets SET status = 'disposed' WHERE id = ?",
        (asset_id,),
    )
    return {"asset_id": asset_id, "voucher_id": voucher["voucher_id"], "status": "disposed"}


def list_fixed_assets(conn, status: Optional[str] = None) -> List[Dict[str, Any]]:
    conditions: List[str] = []
    params: List[Any] = []
    if status and status != "all":
        conditions.append("status = ?")
        params.append(status)
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = conn.execute(
        f"SELECT * FROM fixed_assets {where_clause} ORDER BY id",
        params,
    ).fetchall()
    return [dict(row) for row in rows]


def reconcile_fixed_assets(conn, period: str) -> Dict[str, Any]:
    mapping = _load_subledger_mapping()["fixed_asset"]
    cutoff = _period_end_date(period)
    assets_row = conn.execute(
        """
        SELECT COALESCE(SUM(cost), 0) AS total
        FROM fixed_assets
        WHERE status = 'active' AND acquired_at <= ?
        """,
        (cutoff,),
    ).fetchone()
    expected_asset = float(assets_row["total"] or 0)
    depr_row = conn.execute(
        """
        SELECT COALESCE(SUM(d.amount), 0) AS total
        FROM fixed_asset_depreciations d
        JOIN fixed_assets a ON a.id = d.asset_id
        WHERE a.status = 'active' AND d.period <= ?
        """,
        (period,),
    ).fetchone()
    expected_accum = float(depr_row["total"] or 0)

    asset_balance_row = conn.execute(
        """
        SELECT COALESCE(SUM(closing_balance), 0) AS total
        FROM balances
        WHERE period = ? AND account_code = ?
        """,
        (period, mapping["asset_account"]),
    ).fetchone()
    ledger_asset = float(asset_balance_row["total"] or 0)
    accum_balance_row = conn.execute(
        """
        SELECT COALESCE(SUM(closing_balance), 0) AS total
        FROM balances
        WHERE period = ? AND account_code = ?
        """,
        (period, mapping["accum_depreciation_account"]),
    ).fetchone()
    ledger_accum = float(accum_balance_row["total"] or 0)

    return {
        "period": period,
        "asset_total": round(expected_asset, 2),
        "ledger_asset": round(ledger_asset, 2),
        "asset_difference": round(ledger_asset - expected_asset, 2),
        "accum_depreciation": round(expected_accum, 2),
        "ledger_accum": round(ledger_accum, 2),
        "accum_difference": round(ledger_accum - expected_accum, 2),
    }


def build_balance_input(balances: List[Dict[str, Any]]) -> Dict[str, Any]:
    mapping = _load_balance_mapping()
    mapped = _apply_balance_mapping(balances, mapping)

    def sum_opening(filter_fn):
        return sum(b["opening_balance"] for b in balances if filter_fn(b))

    def sum_debit(filter_fn):
        return sum(b["debit_amount"] for b in balances if filter_fn(b))

    def sum_credit(filter_fn):
        return sum(b["credit_amount"] for b in balances if filter_fn(b))

    cash_codes = {"1001", "1002"}
    revenue = mapped.get("revenue", sum_credit(lambda b: b["account_type"] == "revenue"))
    cost = mapped.get("cost", sum_debit(lambda b: b["account_type"] == "expense"))
    other_expense = mapped.get("other_expense", 0.0)

    opening_cash = mapped.get(
        "opening_cash", sum_opening(lambda b: b["account_code"] in cash_codes)
    )
    opening_debt = mapped.get(
        "opening_debt", sum_opening(lambda b: b["account_type"] == "liability")
    )
    opening_equity = mapped.get(
        "opening_equity", sum_opening(lambda b: b["account_type"] == "equity")
    )
    opening_retained = mapped.get("opening_retained", 0.0)

    def sum_closing_by_prefix(prefixes: Tuple[str, ...]):
        return sum(
            b["closing_balance"]
            for b in balances
            if b["account_code"].startswith(prefixes)
        )

    closing_receivable = mapped.get(
        "closing_receivable", sum_closing_by_prefix(("1122",))
    )
    closing_payable = mapped.get("closing_payable", sum_closing_by_prefix(("2202",)))
    closing_inventory = mapped.get("closing_inventory", sum_closing_by_prefix(("1403",)))
    opening_receivable = mapped.get(
        "opening_receivable",
        sum_opening(lambda b: b["account_code"].startswith("1122")),
    )
    opening_payable = mapped.get(
        "opening_payable",
        sum_opening(lambda b: b["account_code"].startswith("2202")),
    )
    opening_inventory = mapped.get(
        "opening_inventory",
        sum_opening(lambda b: b["account_code"].startswith("1403")),
    )
    fixed_asset_cost = mapped.get("fixed_asset_cost", sum_closing_by_prefix(("1601",)))
    accum_depreciation = mapped.get("accum_depreciation", 0.0)

    delta_receivable = mapped.get(
        "delta_receivable", closing_receivable - opening_receivable
    )
    delta_payable = mapped.get("delta_payable", closing_payable - opening_payable)

    input_data = dict(mapped)
    input_data.update(
        {
            "revenue": round(revenue, 2),
            "cost": round(cost, 2),
            "other_expense": round(other_expense, 2),
            "opening_cash": round(opening_cash, 2),
            "opening_debt": round(opening_debt, 2),
            "opening_equity": round(opening_equity, 2),
            "opening_retained": round(opening_retained, 2),
            "opening_receivable": round(opening_receivable, 2),
            "opening_payable": round(opening_payable, 2),
            "opening_inventory": round(opening_inventory, 2),
            "closing_receivable": round(closing_receivable, 2),
            "closing_payable": round(closing_payable, 2),
            "closing_inventory": round(closing_inventory, 2),
            "fixed_asset_cost": round(fixed_asset_cost, 2),
            "accum_depreciation": round(accum_depreciation, 2),
            "delta_receivable": round(delta_receivable, 2),
            "delta_payable": round(delta_payable, 2),
        }
    )
    return input_data


def _load_close_config() -> Dict[str, str]:
    config_path = Path(__file__).resolve().parents[1] / "data" / "close_config.json"
    if not config_path.exists():
        return dict(DEFAULT_CLOSE_CONFIG)
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LedgerError("CLOSE_CONFIG_INVALID", f"结账配置JSON错误: {exc}") from exc
    if not isinstance(data, dict):
        raise LedgerError("CLOSE_CONFIG_INVALID", "结账配置必须为对象")
    return {
        "profit_account": data.get("profit_account", DEFAULT_CLOSE_CONFIG["profit_account"]),
        "retain_account": data.get("retain_account", DEFAULT_CLOSE_CONFIG["retain_account"]),
    }


def _load_subledger_mapping() -> Dict[str, Dict[str, str]]:
    mapping_path = Path(__file__).resolve().parents[1] / "data" / "subledger_mapping.json"
    if not mapping_path.exists():
        return DEFAULT_SUBLEDGER_MAPPING
    try:
        data = json.loads(mapping_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LedgerError("SUBLEDGER_MAPPING_INVALID", f"子账映射JSON错误: {exc}") from exc
    if not isinstance(data, dict):
        raise LedgerError("SUBLEDGER_MAPPING_INVALID", "子账映射必须为对象")
    mapping = dict(DEFAULT_SUBLEDGER_MAPPING)
    for key, value in data.items():
        if isinstance(value, dict):
            current = dict(mapping.get(key, {}))
            current.update(value)
            mapping[key] = current
    return mapping


def _load_balance_mapping() -> Dict[str, Any]:
    mapping_path = Path(__file__).resolve().parents[1] / "data" / "balance_mapping.json"
    if not mapping_path.exists():
        return DEFAULT_BALANCE_MAPPING
    try:
        raw = json.loads(mapping_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LedgerError("BALANCE_MAPPING_INVALID", f"映射文件JSON错误: {exc}") from exc
    fields = raw.get("fields") if isinstance(raw, dict) else None
    if not isinstance(fields, dict):
        raise LedgerError("BALANCE_MAPPING_INVALID", "映射文件缺少 fields")
    return fields


def _apply_balance_mapping(
    balances: List[Dict[str, Any]], mapping: Dict[str, Any]
) -> Dict[str, float]:
    result: Dict[str, float] = {}
    for field, rule in mapping.items():
        if not isinstance(rule, dict):
            continue
        source = rule.get("source")
        if source not in {"opening_balance", "closing_balance", "debit_amount", "credit_amount"}:
            raise LedgerError("BALANCE_MAPPING_INVALID", f"无效的source: {source}")
        total = 0.0
        for balance in balances:
            if _matches_balance(balance, rule):
                total += float(balance.get(source) or 0)
        result[field] = total
    return result


def _matches_balance(balance: Dict[str, Any], rule: Dict[str, Any]) -> bool:
    prefixes = rule.get("prefixes") or []
    account_types = rule.get("account_types") or []
    matched = False
    if prefixes:
        matched = any(balance["account_code"].startswith(p) for p in prefixes)
    if account_types:
        matched = matched or balance.get("account_type") in account_types
    return matched
