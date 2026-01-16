#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ledger domain services."""

from __future__ import annotations

from datetime import datetime
import ast
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
        "bill_account": "1123",
        "bad_debt_expense_account": "6702",
        "bad_debt_reserve_account": "1231",
    },
    "ap": {
        "ap_account": "2202",
        "inventory_account": "1403",
        "bank_account": "1002",
        "bill_account": "2203",
    },
    "inventory": {
        "inventory_account": "1403",
        "cost_account": "6401",
        "offset_account": "1002",
        "variance_account": "6403",
        "inventory_gain_account": "6051",
        "inventory_loss_account": "6605",
    },
    "fixed_asset": {
        "asset_account": "1601",
        "accum_depreciation_account": "1602",
        "depreciation_expense_account": "6602",
        "bank_account": "1002",
        "cip_account": "1604",
        "impairment_loss_account": "6701",
        "impairment_reserve_account": "1603",
    },
}


DEFAULT_FOREX_CONFIG = {
    "base_currency": "CNY",
    "fx_gain_account": "6051",
    "fx_loss_account": "6603",
    "revaluable_accounts": [],
}


DEFAULT_INVENTORY_CONFIG = {
    "cost_method": "avg",
    "negative_policy": "reject",
}


DEFAULT_CREDIT_CONFIG = {
    "block_on_exceed": False,
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


def assert_period_writable(conn, period: str, entry_type: str) -> None:
    status = get_period_status(conn, period)
    if status == "closed":
        raise LedgerError("PERIOD_CLOSED", f"期间已结账: {period}")
    if status == "adjustment" and entry_type != "adjustment":
        raise LedgerError("PERIOD_ADJUSTMENT_ONLY", f"期间仅允许调整凭证: {period}")


def set_period_status(conn, period: str, status: str) -> Dict[str, Any]:
    if status not in {"open", "closed", "adjustment"}:
        raise LedgerError("PERIOD_STATUS_INVALID", f"无效期间状态: {status}")
    ensure_period(conn, period)
    conn.execute(
        "UPDATE periods SET status = ? WHERE period = ?",
        (status, period),
    )
    return {"period": period, "status": status}


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


def set_credit_profile(
    conn,
    dim_type: str,
    code: str,
    credit_limit: float,
    credit_days: int = 0,
) -> Dict[str, Any]:
    dim_id = find_dimension(conn, dim_type, code)
    conn.execute(
        """
        UPDATE dimensions
        SET credit_limit = ?, credit_days = ?
        WHERE id = ?
        """,
        (round(credit_limit, 2), credit_days, dim_id),
    )
    return {
        "dim_id": dim_id,
        "credit_limit": round(credit_limit, 2),
        "credit_days": credit_days,
    }


def _apply_credit_usage(
    conn,
    dim_id: int,
    amount: float,
) -> None:
    row = conn.execute(
        "SELECT credit_limit, credit_used FROM dimensions WHERE id = ?",
        (dim_id,),
    ).fetchone()
    if not row:
        return
    credit_limit = float(row["credit_limit"] or 0)
    credit_used = float(row["credit_used"] or 0)
    new_used = round(credit_used + amount, 2)
    config = _load_credit_config()
    if credit_limit > 0 and new_used - credit_limit > 0.01:
        if config.get("block_on_exceed"):
            raise LedgerError("CREDIT_LIMIT_EXCEEDED", "信用额度不足")
    conn.execute(
        "UPDATE dimensions SET credit_used = ? WHERE id = ?",
        (new_used, dim_id),
    )


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
    date: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], float, float]:
    entries: List[Dict[str, Any]] = []
    total_debit = 0.0
    total_credit = 0.0
    forex_config = _load_forex_config()
    base_currency = forex_config["base_currency"]

    for idx, entry in enumerate(entries_data, start=1):
        account_token = entry.get("account") or entry.get("account_code")
        if not account_token:
            raise LedgerError("ACCOUNT_NOT_FOUND", "分录缺少科目(account)")
        account = find_account(conn, account_token)
        debit = float(entry.get("debit", entry.get("debit_amount", 0)) or 0)
        credit = float(entry.get("credit", entry.get("credit_amount", 0)) or 0)
        currency_code = (entry.get("currency") or entry.get("currency_code") or base_currency).upper()
        rate_type = entry.get("rate_type") or "spot"
        foreign_debit = entry.get("foreign_debit_amount")
        foreign_credit = entry.get("foreign_credit_amount")
        if foreign_debit is None:
            foreign_debit = entry.get("foreign_debit")
        if foreign_credit is None:
            foreign_credit = entry.get("foreign_credit")
        fx_rate = entry.get("fx_rate")
        if currency_code != base_currency:
            if foreign_debit is None and foreign_credit is None:
                foreign_debit = debit
                foreign_credit = credit
            if fx_rate is None:
                fx_rate = get_fx_rate(conn, currency_code, date or "", rate_type)
            if fx_rate is None:
                raise LedgerError("FX_RATE_NOT_FOUND", f"未找到汇率: {currency_code}")
            debit = round(float(foreign_debit or 0) * float(fx_rate), 2)
            credit = round(float(foreign_credit or 0) * float(fx_rate), 2)
        else:
            fx_rate = float(fx_rate or 1)
            if foreign_debit is None and foreign_credit is None:
                foreign_debit = debit
                foreign_credit = credit

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
                "currency_code": currency_code,
                "fx_rate": float(fx_rate or 1),
                "foreign_debit_amount": float(foreign_debit or 0),
                "foreign_credit_amount": float(foreign_credit or 0),
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
        entry_type = voucher_data.get("entry_type", "normal")
        assert_period_writable(conn, period, entry_type)
    confirmed_at = None
    reviewed_at = None
    if status == "reviewed":
        reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if status == "confirmed":
        confirmed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute(
        """
        INSERT INTO vouchers (
          voucher_no, date, period, description, status, entry_type, source_template, reviewed_at, confirmed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            voucher_no,
            voucher_data["date"],
            period,
            voucher_data.get("description"),
            status,
            voucher_data.get("entry_type", "normal"),
            voucher_data.get("source_template"),
            reviewed_at,
            confirmed_at,
        ),
    )
    voucher_id = cur.lastrowid
    forex_config = _load_forex_config()
    base_currency = forex_config["base_currency"]
    for entry in entries:
        currency_code = entry.get("currency_code") or base_currency
        fx_rate = entry.get("fx_rate") or 1
        foreign_debit = entry.get("foreign_debit_amount")
        foreign_credit = entry.get("foreign_credit_amount")
        if foreign_debit is None:
            foreign_debit = entry.get("debit_amount") if currency_code == base_currency else 0
        if foreign_credit is None:
            foreign_credit = entry.get("credit_amount") if currency_code == base_currency else 0
        conn.execute(
            """
            INSERT INTO voucher_entries (
              voucher_id, line_no, account_code, account_name, description,
              debit_amount, credit_amount, currency_code, fx_rate, foreign_debit_amount, foreign_credit_amount,
              dept_id, project_id, customer_id, supplier_id, employee_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                voucher_id,
                entry["line_no"],
                entry["account_code"],
                entry["account_name"],
                entry.get("description"),
                entry["debit_amount"],
                entry["credit_amount"],
                currency_code,
                fx_rate,
                foreign_debit,
                foreign_credit,
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


def _get_opening_balance_fx(
    conn,
    period: str,
    account_code: str,
    currency_code: str,
    dims: Tuple[int, int, int, int, int],
) -> float:
    prev = _prev_period(period)
    if not prev:
        return 0.0
    row = conn.execute(
        """
        SELECT foreign_closing FROM balances_fx
        WHERE period = ? AND account_code = ? AND currency_code = ?
          AND dept_id = ? AND project_id = ? AND customer_id = ? AND supplier_id = ? AND employee_id = ?
        """,
        (prev, account_code, currency_code, *dims),
    ).fetchone()
    return float(row["foreign_closing"]) if row else 0.0


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
    forex_config = _load_forex_config()
    base_currency = forex_config["base_currency"]
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

        currency_code = row["currency_code"] or base_currency
        foreign_debit = float(row["foreign_debit_amount"] or 0)
        foreign_credit = float(row["foreign_credit_amount"] or 0)
        if currency_code == base_currency and foreign_debit == 0 and foreign_credit == 0:
            foreign_debit = float(row["debit_amount"] or 0)
            foreign_credit = float(row["credit_amount"] or 0)
        fx_key = (
            row["account_code"],
            period,
            currency_code,
            dept_id,
            project_id,
            customer_id,
            supplier_id,
            employee_id,
        )
        fx_row = conn.execute(
            """
            SELECT * FROM balances_fx
            WHERE account_code = ? AND period = ? AND currency_code = ?
              AND dept_id = ? AND project_id = ? AND customer_id = ? AND supplier_id = ? AND employee_id = ?
            """,
            fx_key,
        ).fetchone()
        if not fx_row:
            opening_fx = _get_opening_balance_fx(
                conn,
                period,
                row["account_code"],
                currency_code,
                (dept_id, project_id, customer_id, supplier_id, employee_id),
            )
            conn.execute(
                """
                INSERT INTO balances_fx (
                  account_code, period, currency_code, dept_id, project_id, customer_id, supplier_id, employee_id,
                  foreign_opening, foreign_debit, foreign_credit, foreign_closing
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?)
                """,
                (
                    row["account_code"],
                    period,
                    currency_code,
                    dept_id,
                    project_id,
                    customer_id,
                    supplier_id,
                    employee_id,
                    opening_fx,
                    opening_fx,
                ),
            )
            fx_row = conn.execute(
                """
                SELECT * FROM balances_fx
                WHERE account_code = ? AND period = ? AND currency_code = ?
                  AND dept_id = ? AND project_id = ? AND customer_id = ? AND supplier_id = ? AND employee_id = ?
                """,
                fx_key,
            ).fetchone()

        fx_debit = float(fx_row["foreign_debit"]) + foreign_debit
        fx_credit = float(fx_row["foreign_credit"]) + foreign_credit
        fx_opening = float(fx_row["foreign_opening"] or 0)
        if row["direction"] == "debit":
            fx_closing = fx_opening + fx_debit - fx_credit
        else:
            fx_closing = fx_opening - fx_debit + fx_credit
        conn.execute(
            """
            UPDATE balances_fx
            SET foreign_debit = ?, foreign_credit = ?, foreign_closing = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (fx_debit, fx_credit, fx_closing, fx_row["id"]),
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
    assert_period_writable(conn, voucher["period"], voucher.get("entry_type", "normal"))

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
    if voucher.get("entry_type") == "adjustment":
        _apply_adjustment_rollforward(conn, voucher["period"])
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


def add_currency(
    conn,
    code: str,
    name: str,
    symbol: Optional[str] = None,
    precision: int = 2,
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO currencies (code, name, symbol, precision, is_active)
        VALUES (?, ?, ?, ?, 1)
        """,
        (code.upper(), name, symbol, precision),
    )


def list_currencies(conn) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM currencies WHERE is_active = 1 ORDER BY code").fetchall()
    return [dict(row) for row in rows]


def add_fx_rate(
    conn,
    currency_code: str,
    date: str,
    rate: float,
    rate_type: str = "spot",
    source: Optional[str] = None,
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO exchange_rates (currency_code, date, rate, rate_type, source)
        VALUES (?, ?, ?, ?, ?)
        """,
        (currency_code.upper(), date, round(rate, 6), rate_type, source),
    )


def list_fx_rates(
    conn,
    currency_code: Optional[str] = None,
    date: Optional[str] = None,
    rate_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    conditions: List[str] = []
    params: List[Any] = []
    if currency_code:
        conditions.append("currency_code = ?")
        params.append(currency_code.upper())
    if date:
        conditions.append("date = ?")
        params.append(date)
    if rate_type:
        conditions.append("rate_type = ?")
        params.append(rate_type)
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = conn.execute(
        f"SELECT * FROM exchange_rates {where_clause} ORDER BY date DESC, currency_code",
        params,
    ).fetchall()
    return [dict(row) for row in rows]


def get_fx_rate(conn, currency_code: str, date: str, rate_type: str = "spot") -> Optional[float]:
    if not date:
        return None
    row = conn.execute(
        """
        SELECT rate FROM exchange_rates
        WHERE currency_code = ? AND date = ? AND rate_type = ?
        """,
        (currency_code.upper(), date, rate_type),
    ).fetchone()
    if row:
        return float(row["rate"])
    return None


def fx_balance(
    conn,
    period: str,
    currency_code: Optional[str] = None,
) -> List[Dict[str, Any]]:
    conditions = ["period = ?"]
    params: List[Any] = [period]
    if currency_code:
        conditions.append("currency_code = ?")
        params.append(currency_code.upper())
    rows = conn.execute(
        f"""
        SELECT * FROM balances_fx
        WHERE {' AND '.join(conditions)}
        ORDER BY account_code, currency_code
        """,
        params,
    ).fetchall()
    return [dict(row) for row in rows]


def revalue_forex(conn, period: str, rate_type: str = "closing") -> Dict[str, Any]:
    forex_config = _load_forex_config()
    base_currency = forex_config["base_currency"]
    revaluable_accounts = forex_config.get("revaluable_accounts") or []
    if not revaluable_accounts:
        return {"period": period, "voucher_id": None, "lines": 0}

    fx_rows = conn.execute(
        """
        SELECT fx.*, a.direction
        FROM balances_fx fx
        JOIN accounts a ON fx.account_code = a.code
        WHERE fx.period = ? AND fx.currency_code != ?
        """,
        (period, base_currency),
    ).fetchall()

    entries: List[Dict[str, Any]] = []
    gain_total = 0.0
    loss_total = 0.0

    def _match_revaluable(code: str) -> bool:
        return any(code.startswith(prefix) for prefix in revaluable_accounts)

    for row in fx_rows:
        if not _match_revaluable(row["account_code"]):
            continue
        rate = get_fx_rate(conn, row["currency_code"], _period_end_date(period), rate_type)
        if rate is None:
            continue
        foreign_closing = float(row["foreign_closing"] or 0)
        revalued = round(foreign_closing * rate, 2)
        base_row = conn.execute(
            """
            SELECT closing_balance FROM balances
            WHERE period = ? AND account_code = ?
              AND dept_id = ? AND project_id = ? AND customer_id = ? AND supplier_id = ? AND employee_id = ?
            """,
            (
                period,
                row["account_code"],
                row["dept_id"],
                row["project_id"],
                row["customer_id"],
                row["supplier_id"],
                row["employee_id"],
            ),
        ).fetchone()
        base_closing = float(base_row["closing_balance"] or 0) if base_row else 0.0
        diff = round(revalued - base_closing, 2)
        if abs(diff) < 0.01:
            continue
        dims = (
            row["dept_id"] or 0,
            row["project_id"] or 0,
            row["customer_id"] or 0,
            row["supplier_id"] or 0,
            row["employee_id"] or 0,
        )
        debit = 0.0
        credit = 0.0
        if row["direction"] == "debit":
            if diff > 0:
                debit = diff
                gain_total += diff
            else:
                credit = abs(diff)
                loss_total += abs(diff)
        else:
            if diff > 0:
                credit = diff
                loss_total += diff
            else:
                debit = abs(diff)
                gain_total += abs(diff)
        entries.append(
            _build_entry_for_account(
                conn,
                row["account_code"],
                debit,
                credit,
                dims={
                    "dept_id": dims[0],
                    "project_id": dims[1],
                    "customer_id": dims[2],
                    "supplier_id": dims[3],
                    "employee_id": dims[4],
                },
                description="期末汇兑重估",
            )
        )

    fx_gain = forex_config["fx_gain_account"]
    fx_loss = forex_config["fx_loss_account"]
    if gain_total > 0:
        entries.extend(
            _build_entries(
                conn,
                [(fx_gain, 0.0, gain_total)],
                description="期末汇兑收益",
            )
        )
    if loss_total > 0:
        entries.extend(
            _build_entries(
                conn,
                [(fx_loss, loss_total, 0.0)],
                description="期末汇兑损失",
            )
        )

    if not entries:
        return {"period": period, "voucher_id": None, "lines": 0}

    voucher_id, voucher_no, _, _ = insert_voucher(
        conn,
        {"date": _period_end_date(period), "description": f"{period} 汇兑重估"},
        entries,
        "reviewed",
    )
    confirm_voucher(conn, voucher_id)
    return {"period": period, "voucher_id": voucher_id, "voucher_no": voucher_no, "lines": len(entries)}


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


def close_period(conn, period: str, template_code: Optional[str] = None) -> Dict[str, Any]:
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

    net_by_dims: Dict[Tuple[int, int, int, int, int], float] = {}
    if template_code:
        template = _load_closing_template(conn, template_code)
        closing_entries = _build_template_close_entries(conn, balances, template)
    else:
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
    if not template_code and retain_account and retain_account != profit_account:
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
        "template": template_code,
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


def _period_has_activity(conn, period: str) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM vouchers WHERE period = ?",
        (period,),
    ).fetchone()
    if row and row["cnt"] > 0:
        return True
    row = conn.execute(
        """
        SELECT COUNT(*) AS cnt FROM balances
        WHERE period = ? AND (debit_amount != 0 OR credit_amount != 0)
        """,
        (period,),
    ).fetchone()
    return bool(row and row["cnt"] > 0)


def _apply_adjustment_rollforward(conn, period: str) -> None:
    status = get_period_status(conn, period)
    if status != "adjustment":
        return
    next_period = _next_period(period)
    if not next_period:
        return
    if not _period_has_activity(conn, next_period):
        _roll_forward_balances(conn, period, next_period)
        return

    closing_rows = conn.execute(
        """
        SELECT account_code, dept_id, project_id, customer_id, supplier_id, employee_id, closing_balance
        FROM balances WHERE period = ?
        """,
        (period,),
    ).fetchall()
    opening_rows = conn.execute(
        """
        SELECT account_code, dept_id, project_id, customer_id, supplier_id, employee_id, opening_balance
        FROM balances WHERE period = ?
        """,
        (next_period,),
    ).fetchall()

    closing_map = {
        (
            row["account_code"],
            row["dept_id"] or 0,
            row["project_id"] or 0,
            row["customer_id"] or 0,
            row["supplier_id"] or 0,
            row["employee_id"] or 0,
        ): float(row["closing_balance"] or 0)
        for row in closing_rows
    }
    opening_map = {
        (
            row["account_code"],
            row["dept_id"] or 0,
            row["project_id"] or 0,
            row["customer_id"] or 0,
            row["supplier_id"] or 0,
            row["employee_id"] or 0,
        ): float(row["opening_balance"] or 0)
        for row in opening_rows
    }
    keys = set(closing_map) | set(opening_map)
    entries: List[Dict[str, Any]] = []
    for key in keys:
        closing = closing_map.get(key, 0.0)
        opening = opening_map.get(key, 0.0)
        delta = round(closing - opening, 2)
        if abs(delta) < 0.01:
            continue
        account_code = key[0]
        account = find_account(conn, account_code)
        if account["direction"] == "debit":
            debit = delta if delta > 0 else 0.0
            credit = abs(delta) if delta < 0 else 0.0
        else:
            debit = abs(delta) if delta < 0 else 0.0
            credit = delta if delta > 0 else 0.0
        entries.append(
            _build_entry_for_account(
                conn,
                account_code,
                debit,
                credit,
                dims={
                    "dept_id": key[1],
                    "project_id": key[2],
                    "customer_id": key[3],
                    "supplier_id": key[4],
                    "employee_id": key[5],
                },
                description=f"{period} 调整结转",
            )
        )

    if not entries:
        return

    total_debit = sum(e["debit_amount"] for e in entries)
    total_credit = sum(e["credit_amount"] for e in entries)
    if abs(total_debit - total_credit) >= 0.01:
        raise LedgerError("ADJUSTMENT_NOT_BALANCED", "调整结转凭证不平衡")

    voucher_id, _, _, _ = insert_voucher(
        conn,
        {
            "date": f"{next_period}-01",
            "description": f"{period} 调整结转",
            "entry_type": "adjustment",
            "source_template": "period_adjustment",
        },
        entries,
        "reviewed",
    )
    confirm_voucher(conn, voucher_id)


def add_voucher_template(conn, code: str, name: str, rule_json: Dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO voucher_templates (code, name, rule_json, is_active)
        VALUES (?, ?, ?, 1)
        """,
        (code, name, json.dumps(rule_json, ensure_ascii=False)),
    )


def list_voucher_templates(conn) -> List[Dict[str, Any]]:
    rows = conn.execute(
        "SELECT code, name, is_active, created_at FROM voucher_templates ORDER BY code"
    ).fetchall()
    return [dict(row) for row in rows]


def disable_voucher_template(conn, code: str) -> None:
    row = conn.execute(
        "SELECT 1 FROM voucher_templates WHERE code = ?",
        (code,),
    ).fetchone()
    if not row:
        raise LedgerError("TEMPLATE_NOT_FOUND", f"模板不存在: {code}")
    conn.execute("UPDATE voucher_templates SET is_active = 0 WHERE code = ?", (code,))


def _eval_expr(expr: str, context: Dict[str, Any]) -> float:
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise LedgerError("TEMPLATE_EXPR_INVALID", f"表达式错误: {exc}") from exc
    allowed_nodes = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Constant,
        ast.Name,
        ast.Load,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.USub,
        ast.UAdd,
        ast.Call,
        ast.Mod,
        ast.Pow,
    )
    allowed_funcs = {"round": round, "abs": abs}
    for node in ast.walk(tree):
        if not isinstance(node, allowed_nodes):
            raise LedgerError("TEMPLATE_EXPR_INVALID", "表达式包含不允许的语法")
        if isinstance(node, ast.Name) and node.id not in context:
            raise LedgerError("TEMPLATE_EXPR_INVALID", f"变量未定义: {node.id}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in allowed_funcs:
                raise LedgerError("TEMPLATE_EXPR_INVALID", "表达式函数不允许")
    value = eval(compile(tree, "<expr>", "eval"), {"__builtins__": {}}, {**allowed_funcs, **context})
    return float(value)


def generate_voucher_from_template(
    conn,
    code: str,
    payload: Dict[str, Any],
    date: Optional[str] = None,
) -> Dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM voucher_templates WHERE code = ?",
        (code,),
    ).fetchone()
    if not row:
        raise LedgerError("TEMPLATE_NOT_FOUND", f"模板不存在: {code}")
    if not row["is_active"]:
        raise LedgerError("TEMPLATE_DISABLED", f"模板已禁用: {code}")
    try:
        rule = json.loads(row["rule_json"])
    except json.JSONDecodeError as exc:
        raise LedgerError("TEMPLATE_INVALID", f"模板JSON错误: {exc}") from exc
    if not isinstance(rule, dict):
        raise LedgerError("TEMPLATE_INVALID", "模板规则必须是对象")

    header = rule.get("header") or {}
    description = header.get("description") or payload.get("description") or code
    date_field = header.get("date_field")
    voucher_date = date or payload.get(date_field) or payload.get("date")
    if not voucher_date:
        raise LedgerError("TEMPLATE_DATE_REQUIRED", "缺少凭证日期")

    lines = rule.get("lines")
    if not isinstance(lines, list) or not lines:
        raise LedgerError("TEMPLATE_INVALID", "模板缺少分录")

    entries_data: List[Dict[str, Any]] = []
    for line in lines:
        if not isinstance(line, dict):
            continue
        account = line.get("account")
        if not account:
            raise LedgerError("TEMPLATE_INVALID", "模板分录缺少科目")
        debit_expr = line.get("debit") or "0"
        credit_expr = line.get("credit") or "0"
        debit_value = _eval_expr(str(debit_expr), payload)
        credit_value = _eval_expr(str(credit_expr), payload)
        dims_payload: Dict[str, Any] = {}
        dims = line.get("dims") or {}
        if isinstance(dims, dict):
            for key, val in dims.items():
                if isinstance(val, str) and val in payload:
                    dims_payload[key] = payload[val]
                else:
                    dims_payload[key] = val
        entry_desc = line.get("description") or description
        entries_data.append(
            {
                "account": account,
                "debit": debit_value,
                "credit": credit_value,
                "description": entry_desc,
                **dims_payload,
            }
        )

    entries, total_debit, total_credit = build_entries(conn, entries_data, voucher_date)
    if abs(total_debit - total_credit) >= 0.01:
        raise LedgerError("NOT_BALANCED", "模板生成凭证不平衡")
    voucher_id, voucher_no, period, _ = insert_voucher(
        conn,
        {
            "date": voucher_date,
            "description": description,
            "source_template": code,
        },
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


def _load_closing_template(conn, code: str) -> Dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM closing_templates WHERE code = ?",
        (code,),
    ).fetchone()
    if not row:
        raise LedgerError("CLOSE_TEMPLATE_NOT_FOUND", f"结转模板不存在: {code}")
    if not row["is_active"]:
        raise LedgerError("CLOSE_TEMPLATE_DISABLED", f"结转模板已禁用: {code}")
    try:
        rule_json = json.loads(row["rule_json"])
    except json.JSONDecodeError as exc:
        raise LedgerError("CLOSE_TEMPLATE_INVALID", f"结转模板JSON错误: {exc}") from exc
    return {"code": row["code"], "name": row["name"], "rules": rule_json}


def _build_template_close_entries(
    conn, balances: List[Dict[str, Any]], template: Dict[str, Any]
) -> List[Dict[str, Any]]:
    rules = template.get("rules")
    if isinstance(rules, dict):
        rules_list = [rules]
    elif isinstance(rules, list):
        rules_list = rules
    else:
        raise LedgerError("CLOSE_TEMPLATE_INVALID", "结转模板规则必须是对象或数组")

    entries: List[Dict[str, Any]] = []
    for rule in rules_list:
        if not isinstance(rule, dict):
            continue
        prefixes = rule.get("source_prefixes") or []
        types = rule.get("source_types") or []
        target_account = rule.get("target_account")
        description = rule.get("description") or "期末结转"
        if not target_account:
            raise LedgerError("CLOSE_TEMPLATE_INVALID", "结转模板缺少 target_account")

        net_by_dims: Dict[Tuple[int, int, int, int, int], float] = {}
        for balance in balances:
            if prefixes and not any(balance["account_code"].startswith(p) for p in prefixes):
                continue
            if types and balance.get("account_type") not in types:
                continue
            if not prefixes and not types:
                continue
            _append_reverse_entry(entries, balance)
            dims = _dims_from_balance(balance)
            last_entry = entries[-1]
            net_by_dims[dims] = net_by_dims.get(dims, 0.0) + (
                last_entry["debit_amount"] - last_entry["credit_amount"]
            )

        for dims, net in net_by_dims.items():
            if abs(net) < 0.01:
                continue
            debit = 0.0
            credit = 0.0
            if net > 0:
                credit = net
            else:
                debit = abs(net)
            _append_entry(
                entries,
                target_account,
                find_account(conn, target_account)["name"],
                debit,
                credit,
                dims,
                description,
            )
    return entries


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
        "dept_id": payload.get("dept_id") or None,
        "project_id": payload.get("project_id") or None,
        "customer_id": payload.get("customer_id") or None,
        "supplier_id": payload.get("supplier_id") or None,
        "employee_id": payload.get("employee_id") or None,
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
    base_currency = _load_forex_config()["base_currency"]
    entry = {
        "line_no": 0,
        "account_code": account["code"],
        "account_name": account["name"],
        "description": description,
        "debit_amount": round(debit_amount, 2),
        "credit_amount": round(credit_amount, 2),
        "currency_code": base_currency,
        "fx_rate": 1.0,
        "foreign_debit_amount": round(debit_amount, 2),
        "foreign_credit_amount": round(credit_amount, 2),
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
    _apply_credit_usage(conn, customer_id, amount)
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
    _apply_credit_usage(conn, int(row["customer_id"]), -amount)
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
    _apply_credit_usage(conn, supplier_id, amount)
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
    _apply_credit_usage(conn, int(row["supplier_id"]), -amount)
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


def create_payment_plan(
    conn,
    item_type: str,
    item_id: int,
    due_date: str,
    amount: float,
) -> Dict[str, Any]:
    if amount <= 0:
        raise LedgerError("PAYMENT_PLAN_AMOUNT_INVALID", "计划金额必须大于 0")
    cur = conn.execute(
        """
        INSERT INTO payment_plans (item_type, item_id, due_date, amount, status)
        VALUES (?, ?, ?, ?, 'pending')
        """,
        (item_type, item_id, due_date, round(amount, 2)),
    )
    return {
        "plan_id": cur.lastrowid,
        "item_type": item_type,
        "item_id": item_id,
        "due_date": due_date,
        "amount": round(amount, 2),
        "status": "pending",
    }


def settle_payment_plan(conn, plan_id: int, date: str) -> Dict[str, Any]:
    plan = conn.execute("SELECT * FROM payment_plans WHERE id = ?", (plan_id,)).fetchone()
    if not plan:
        raise LedgerError("PAYMENT_PLAN_NOT_FOUND", f"计划不存在: {plan_id}")
    if plan["status"] != "pending":
        raise LedgerError("PAYMENT_PLAN_STATUS_INVALID", "计划已处理")
    voucher_id = None
    if plan["item_type"] == "ar":
        result = settle_ar_item(conn, plan["item_id"], plan["amount"], date, "plan settle")
        voucher_id = result["voucher_id"]
    elif plan["item_type"] == "ap":
        result = settle_ap_item(conn, plan["item_id"], plan["amount"], date, "plan settle")
        voucher_id = result["voucher_id"]
    else:
        raise LedgerError("PAYMENT_PLAN_TYPE_INVALID", "不支持的计划类型")
    conn.execute(
        "UPDATE payment_plans SET status = 'settled', voucher_id = ? WHERE id = ?",
        (voucher_id, plan_id),
    )
    return {"plan_id": plan_id, "status": "settled", "voucher_id": voucher_id}


def add_bill(
    conn,
    bill_no: str,
    bill_type: str,
    amount: float,
    date: str,
    maturity_date: Optional[str] = None,
    item_type: Optional[str] = None,
    item_id: Optional[int] = None,
) -> Dict[str, Any]:
    if amount <= 0:
        raise LedgerError("BILL_AMOUNT_INVALID", "票据金额必须大于 0")
    if bill_type not in {"ar", "ap"}:
        raise LedgerError("BILL_TYPE_INVALID", "票据类型无效")
    mapping = _load_subledger_mapping()[bill_type]
    description = f"Bill {bill_no}"
    if bill_type == "ar":
        lines = [
            (mapping["bill_account"], amount, 0.0),
            (mapping["ar_account"], 0.0, amount),
        ]
    else:
        lines = [
            (mapping["ap_account"], amount, 0.0),
            (mapping["bill_account"], 0.0, amount),
        ]
    entries = _build_entries(conn, lines, description=description)
    voucher = _create_posted_voucher(conn, date, description, entries)
    cur = conn.execute(
        """
        INSERT INTO bills (bill_no, bill_type, amount, status, maturity_date, item_type, item_id, voucher_id)
        VALUES (?, ?, ?, 'holding', ?, ?, ?, ?)
        """,
        (bill_no, bill_type, round(amount, 2), maturity_date, item_type, item_id, voucher["voucher_id"]),
    )
    return {"bill_id": cur.lastrowid, "voucher_id": voucher["voucher_id"], "status": "holding"}


def update_bill_status(
    conn,
    bill_no: str,
    status: str,
    date: str,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    bill = conn.execute("SELECT * FROM bills WHERE bill_no = ?", (bill_no,)).fetchone()
    if not bill:
        raise LedgerError("BILL_NOT_FOUND", f"票据不存在: {bill_no}")
    if status not in {"endorsed", "discounted", "settled"}:
        raise LedgerError("BILL_STATUS_INVALID", f"无效票据状态: {status}")
    mapping = _load_subledger_mapping()[bill["bill_type"]]
    voucher_id = None
    if status == "settled":
        description = description or f"Bill settle {bill_no}"
        if bill["bill_type"] == "ar":
            lines = [
                (mapping["bank_account"], bill["amount"], 0.0),
                (mapping["bill_account"], 0.0, bill["amount"]),
            ]
        else:
            lines = [
                (mapping["bill_account"], bill["amount"], 0.0),
                (mapping["bank_account"], 0.0, bill["amount"]),
            ]
        entries = _build_entries(conn, lines, description=description)
        voucher = _create_posted_voucher(conn, date, description, entries)
        voucher_id = voucher["voucher_id"]
    conn.execute(
        "UPDATE bills SET status = ?, voucher_id = ? WHERE id = ?",
        (status, voucher_id, bill["id"]),
    )
    return {"bill_id": bill["id"], "status": status, "voucher_id": voucher_id}


def provision_bad_debt(
    conn, period: str, customer_code: str, amount: float
) -> Dict[str, Any]:
    if amount <= 0:
        raise LedgerError("BAD_DEBT_AMOUNT_INVALID", "计提金额必须大于 0")
    customer_id = find_dimension(conn, "customer", customer_code)
    mapping = _load_subledger_mapping()["ar"]
    description = f"Bad debt {period}"
    entries = _build_entries(
        conn,
        [
            (mapping["bad_debt_expense_account"], amount, 0.0),
            (mapping["bad_debt_reserve_account"], 0.0, amount),
        ],
        dims={"customer_id": customer_id},
        description=description,
    )
    voucher = _create_posted_voucher(conn, f"{period}-01", description, entries)
    cur = conn.execute(
        """
        INSERT INTO bad_debt_provisions (period, customer_id, amount, voucher_id)
        VALUES (?, ?, ?, ?)
        """,
        (period, customer_id, round(amount, 2), voucher["voucher_id"]),
    )
    return {"provision_id": cur.lastrowid, "voucher_id": voucher["voucher_id"]}


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


def _get_inventory_balance(
    conn,
    sku: str,
    period: str,
    warehouse_id: int = 0,
    location_id: int = 0,
) -> Tuple[float, float]:
    row = conn.execute(
        """
        SELECT qty, amount FROM inventory_balances
        WHERE sku = ? AND period = ? AND warehouse_id = ? AND location_id = ?
        """,
        (sku, period, warehouse_id, location_id),
    ).fetchone()
    if row:
        return float(row["qty"]), float(row["amount"])
    prev = conn.execute(
        """
        SELECT qty, amount FROM inventory_balances
        WHERE sku = ? AND period < ? AND warehouse_id = ? AND location_id = ?
        ORDER BY period DESC
        LIMIT 1
        """,
        (sku, period, warehouse_id, location_id),
    ).fetchone()
    if prev:
        return float(prev["qty"]), float(prev["amount"])
    return 0.0, 0.0


def _upsert_inventory_balance(
    conn,
    sku: str,
    period: str,
    qty: float,
    amount: float,
    warehouse_id: int = 0,
    location_id: int = 0,
) -> None:
    conn.execute(
        """
        INSERT INTO inventory_balances (sku, period, warehouse_id, location_id, qty, amount, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(sku, period, warehouse_id, location_id) DO UPDATE SET
          qty = excluded.qty,
          amount = excluded.amount,
          updated_at = CURRENT_TIMESTAMP
        """,
        (sku, period, warehouse_id, location_id, round(qty, 2), round(amount, 2)),
    )


def create_warehouse(conn, code: str, name: str) -> int:
    cur = conn.execute(
        "INSERT OR IGNORE INTO warehouses (code, name) VALUES (?, ?)",
        (code, name),
    )
    if cur.lastrowid:
        return cur.lastrowid
    row = conn.execute("SELECT id FROM warehouses WHERE code = ?", (code,)).fetchone()
    return int(row["id"]) if row else 0


def create_location(conn, warehouse_id: int, code: str, name: str) -> int:
    cur = conn.execute(
        "INSERT OR IGNORE INTO locations (warehouse_id, code, name) VALUES (?, ?, ?)",
        (warehouse_id, code, name),
    )
    if cur.lastrowid:
        return cur.lastrowid
    row = conn.execute(
        "SELECT id FROM locations WHERE warehouse_id = ? AND code = ?",
        (warehouse_id, code),
    ).fetchone()
    return int(row["id"]) if row else 0


def _resolve_warehouse_location(
    conn, warehouse_code: Optional[str], location_code: Optional[str]
) -> Tuple[int, int]:
    if not warehouse_code:
        return 0, 0
    warehouse_id = create_warehouse(conn, warehouse_code, warehouse_code)
    if not location_code:
        return warehouse_id, 0
    location_id = create_location(conn, warehouse_id, location_code, location_code)
    return warehouse_id, location_id


def set_standard_cost(conn, sku: str, period: str, cost: float, variance_account: str) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO standard_costs (sku, period, cost, variance_account)
        VALUES (?, ?, ?, ?)
        """,
        (sku, period, round(cost, 2), variance_account),
    )


def _get_standard_cost(conn, sku: str, period: str) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT cost, variance_account FROM standard_costs WHERE sku = ? AND period = ?",
        (sku, period),
    ).fetchone()
    return dict(row) if row else None


def _latest_inventory_cost(conn, sku: str) -> float:
    row = conn.execute(
        """
        SELECT unit_cost FROM inventory_moves
        WHERE sku = ? AND direction = 'in'
        ORDER BY date DESC, id DESC
        LIMIT 1
        """,
        (sku,),
    ).fetchone()
    return float(row["unit_cost"]) if row else 0.0


def _consume_fifo_batches(
    conn, sku: str, qty: float, warehouse_id: int, location_id: int
) -> Tuple[List[Dict[str, Any]], float]:
    remaining = qty
    lines: List[Dict[str, Any]] = []
    batches = conn.execute(
        """
        SELECT * FROM inventory_batches
        WHERE sku = ? AND status = 'open'
          AND (warehouse_id IS NULL OR warehouse_id = ?)
          AND (location_id IS NULL OR location_id = ?)
        ORDER BY created_at, id
        """,
        (sku, warehouse_id if warehouse_id else None, location_id if location_id else None),
    ).fetchall()
    for batch in batches:
        if remaining <= 0:
            break
        available = float(batch["remaining_qty"] or 0)
        if available <= 0:
            continue
        use_qty = available if available <= remaining else remaining
        total_cost = round(use_qty * float(batch["unit_cost"]), 2)
        lines.append(
            {
                "batch_id": batch["id"],
                "qty": round(use_qty, 2),
                "unit_cost": float(batch["unit_cost"]),
                "total_cost": total_cost,
            }
        )
        remaining = round(remaining - use_qty, 2)
        new_remaining = round(available - use_qty, 2)
        status = "closed" if new_remaining <= 0 else "open"
        conn.execute(
            "UPDATE inventory_batches SET remaining_qty = ?, status = ? WHERE id = ?",
            (new_remaining, status, batch["id"]),
        )
    if remaining > 0.01:
        raise LedgerError("INVENTORY_INSUFFICIENT", "库存数量不足")
    total = round(sum(line["total_cost"] for line in lines), 2)
    return lines, total


def inventory_move_in(
    conn,
    sku: str,
    qty: float,
    unit_cost: float,
    date: str,
    description: Optional[str] = None,
    name: Optional[str] = None,
    unit: Optional[str] = None,
    warehouse_code: Optional[str] = None,
    location_code: Optional[str] = None,
    batch_no: Optional[str] = None,
    cost_method: Optional[str] = None,
) -> Dict[str, Any]:
    if qty <= 0 or unit_cost < 0:
        raise LedgerError("INVENTORY_AMOUNT_INVALID", "入库数量或成本无效")
    _ensure_inventory_item(conn, sku, name, unit)
    warehouse_id, location_id = _resolve_warehouse_location(
        conn, warehouse_code, location_code
    )
    config = _load_inventory_config()
    method = (cost_method or config.get("cost_method") or "avg").lower()
    mapping = _load_subledger_mapping()["inventory"]
    description = description or "Inventory in"
    actual_total = round(qty * unit_cost, 2)
    total_cost = actual_total
    lines = []
    if method == "standard":
        period = parse_period(date)
        std = _get_standard_cost(conn, sku, period)
        if not std:
            raise LedgerError("STANDARD_COST_MISSING", "标准成本未设置")
        standard_total = round(qty * float(std["cost"]), 2)
        variance = round(actual_total - standard_total, 2)
        total_cost = standard_total
        lines.append((mapping["inventory_account"], standard_total, 0.0))
        if abs(variance) >= 0.01:
            if variance > 0:
                lines.append((std["variance_account"] or mapping["variance_account"], variance, 0.0))
            else:
                lines.append((std["variance_account"] or mapping["variance_account"], 0.0, abs(variance)))
        lines.append((mapping["offset_account"], 0.0, actual_total))
    else:
        lines = [
            (mapping["inventory_account"], total_cost, 0.0),
            (mapping["offset_account"], 0.0, total_cost),
        ]
    entries = _build_entries(conn, lines, description=description)
    voucher = _create_posted_voucher(conn, date, description, entries)
    conn.execute(
        """
        INSERT INTO inventory_moves (
          sku, direction, qty, unit_cost, total_cost, voucher_id, date, warehouse_id, location_id, batch_id
        )
        VALUES (?, 'in', ?, ?, ?, ?, ?, ?, ?, NULL)
        """,
        (
            sku,
            round(qty, 2),
            round(unit_cost, 2),
            total_cost,
            voucher["voucher_id"],
            date,
            warehouse_id if warehouse_id else None,
            location_id if location_id else None,
        ),
    )
    move_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    if method == "fifo":
        batch_qty = round(qty, 2)
        batch_total = round(qty * unit_cost, 2)
        cur = conn.execute(
            """
            INSERT INTO inventory_batches (
              sku, batch_no, qty, remaining_qty, unit_cost, total_cost, warehouse_id, location_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sku,
                batch_no,
                batch_qty,
                batch_qty,
                round(unit_cost, 2),
                batch_total,
                warehouse_id if warehouse_id else None,
                location_id if location_id else None,
            ),
        )
        batch_id = cur.lastrowid
        conn.execute(
            """
            INSERT INTO inventory_move_lines (move_id, batch_id, qty, unit_cost, total_cost)
            VALUES (?, ?, ?, ?, ?)
            """,
            (move_id, batch_id, batch_qty, round(unit_cost, 2), batch_total),
        )
    period = parse_period(date)
    current_qty, current_amount = _get_inventory_balance(
        conn, sku, period, warehouse_id or 0, location_id or 0
    )
    new_qty = round(current_qty + qty, 2)
    new_amount = round(current_amount + total_cost, 2)
    _upsert_inventory_balance(
        conn, sku, period, new_qty, new_amount, warehouse_id or 0, location_id or 0
    )
    return {
        "sku": sku,
        "voucher_id": voucher["voucher_id"],
        "qty": round(qty, 2),
        "unit_cost": round(unit_cost, 2),
        "total_cost": total_cost,
        "period": period,
        "warehouse_id": warehouse_id,
        "location_id": location_id,
    }


def inventory_move_out(
    conn,
    sku: str,
    qty: float,
    date: str,
    description: Optional[str] = None,
    warehouse_code: Optional[str] = None,
    location_code: Optional[str] = None,
    cost_method: Optional[str] = None,
) -> Dict[str, Any]:
    if qty <= 0:
        raise LedgerError("INVENTORY_AMOUNT_INVALID", "出库数量无效")
    mapping = _load_subledger_mapping()["inventory"]
    description = description or "Inventory out"
    period = parse_period(date)
    warehouse_id, location_id = _resolve_warehouse_location(
        conn, warehouse_code, location_code
    )
    config = _load_inventory_config()
    method = (cost_method or config.get("cost_method") or "avg").lower()
    negative_policy = config.get("negative_policy", "reject")
    current_qty, current_amount = _get_inventory_balance(
        conn, sku, period, warehouse_id or 0, location_id or 0
    )
    if qty - current_qty > 0.01 and negative_policy == "reject":
        raise LedgerError("INVENTORY_INSUFFICIENT", "库存数量不足")

    move_lines: List[Dict[str, Any]] = []
    total_cost = 0.0
    unit_cost = 0.0
    if method == "fifo":
        move_lines, total_cost = _consume_fifo_batches(
            conn, sku, qty, warehouse_id or 0, location_id or 0
        )
        unit_cost = round(total_cost / qty, 2) if qty else 0.0
    elif method == "standard":
        std = _get_standard_cost(conn, sku, period)
        if not std:
            raise LedgerError("STANDARD_COST_MISSING", "标准成本未设置")
        unit_cost = round(float(std["cost"]), 2)
        total_cost = round(unit_cost * qty, 2)
    else:
        avg_cost = current_amount / current_qty if current_qty else _latest_inventory_cost(conn, sku)
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
        INSERT INTO inventory_moves (
          sku, direction, qty, unit_cost, total_cost, voucher_id, date, warehouse_id, location_id, batch_id,
          pending_cost_adjustment
        )
        VALUES (?, 'out', ?, ?, ?, ?, ?, ?, ?, NULL, ?)
        """,
        (
            sku,
            round(qty, 2),
            unit_cost,
            total_cost,
            voucher["voucher_id"],
            date,
            warehouse_id if warehouse_id else None,
            location_id if location_id else None,
            0 if qty - current_qty <= 0.01 else total_cost,
        ),
    )
    move_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    if move_lines:
        for line in move_lines:
            conn.execute(
                """
                INSERT INTO inventory_move_lines (move_id, batch_id, qty, unit_cost, total_cost)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    move_id,
                    line["batch_id"],
                    line["qty"],
                    line["unit_cost"],
                    line["total_cost"],
                ),
            )
    new_qty = round(current_qty - qty, 2)
    new_amount = round(current_amount - total_cost, 2)
    _upsert_inventory_balance(
        conn, sku, period, new_qty, new_amount, warehouse_id or 0, location_id or 0
    )
    return {
        "sku": sku,
        "voucher_id": voucher["voucher_id"],
        "qty": round(qty, 2),
        "unit_cost": unit_cost,
        "total_cost": total_cost,
        "period": period,
        "warehouse_id": warehouse_id,
        "location_id": location_id,
    }


def inventory_balance(
    conn,
    period: str,
    sku: Optional[str] = None,
    warehouse_id: Optional[int] = None,
    location_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    conditions = ["period = ?"]
    params: List[Any] = [period]
    if sku:
        conditions.append("sku = ?")
        params.append(sku)
    if warehouse_id is not None:
        conditions.append("warehouse_id = ?")
        params.append(warehouse_id)
    if location_id is not None:
        conditions.append("location_id = ?")
        params.append(location_id)
    rows = conn.execute(
        f"SELECT * FROM inventory_balances WHERE {' AND '.join(conditions)} ORDER BY sku",
        params,
    ).fetchall()
    return [dict(row) for row in rows]


def inventory_count(
    conn,
    sku: str,
    counted_qty: float,
    date: str,
    warehouse_code: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    if counted_qty < 0:
        raise LedgerError("INVENTORY_COUNT_INVALID", "盘点数量无效")
    warehouse_id, _ = _resolve_warehouse_location(conn, warehouse_code, None)
    period = parse_period(date)
    current_qty, current_amount = _get_inventory_balance(
        conn, sku, period, warehouse_id or 0, 0
    )
    diff_qty = round(counted_qty - current_qty, 2)
    if abs(diff_qty) < 0.01:
        return {"sku": sku, "diff_qty": 0.0, "voucher_id": None}
    avg_cost = current_amount / current_qty if current_qty else _latest_inventory_cost(conn, sku)
    diff_amount = round(diff_qty * avg_cost, 2)
    mapping = _load_subledger_mapping()["inventory"]
    description = description or "Inventory count"
    if diff_qty > 0:
        lines = [
            (mapping["inventory_account"], diff_amount, 0.0),
            (mapping["inventory_gain_account"], 0.0, diff_amount),
        ]
    else:
        lines = [
            (mapping["inventory_loss_account"], abs(diff_amount), 0.0),
            (mapping["inventory_account"], 0.0, abs(diff_amount)),
        ]
    entries = _build_entries(conn, lines, description=description)
    voucher = _create_posted_voucher(conn, date, description, entries)
    conn.execute(
        """
        INSERT INTO inventory_counts (sku, warehouse_id, counted_qty, book_qty, diff_qty, date, voucher_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            sku,
            warehouse_id if warehouse_id else None,
            round(counted_qty, 2),
            round(current_qty, 2),
            diff_qty,
            date,
            voucher["voucher_id"],
        ),
    )
    new_qty = round(current_qty + diff_qty, 2)
    new_amount = round(current_amount + diff_amount, 2)
    _upsert_inventory_balance(
        conn, sku, period, new_qty, new_amount, warehouse_id or 0, 0
    )
    return {"sku": sku, "diff_qty": diff_qty, "voucher_id": voucher["voucher_id"]}


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
    voucher_entries: List[Dict[str, Any]] = []
    for asset_id, amount in entries:
        allocations = conn.execute(
            "SELECT * FROM fixed_asset_allocations WHERE asset_id = ?",
            (asset_id,),
        ).fetchall()
        if allocations:
            for alloc in allocations:
                dims: Dict[str, Optional[int]] = {}
                dim_type = alloc["dim_type"]
                if dim_type == "department":
                    dims["dept_id"] = alloc["dim_id"]
                elif dim_type == "project":
                    dims["project_id"] = alloc["dim_id"]
                elif dim_type == "customer":
                    dims["customer_id"] = alloc["dim_id"]
                elif dim_type == "supplier":
                    dims["supplier_id"] = alloc["dim_id"]
                elif dim_type == "employee":
                    dims["employee_id"] = alloc["dim_id"]
                alloc_amount = round(amount * float(alloc["ratio"]), 2)
                voucher_entries.append(
                    _build_entry_for_account(
                        conn,
                        mapping["depreciation_expense_account"],
                        alloc_amount,
                        0.0,
                        dims=dims,
                        description=description,
                    )
                )
        else:
            voucher_entries.append(
                _build_entry_for_account(
                    conn,
                    mapping["depreciation_expense_account"],
                    amount,
                    0.0,
                    description=description,
                )
            )
    voucher_entries.append(
        _build_entry_for_account(
            conn,
            mapping["accum_depreciation_account"],
            0.0,
            total_amount,
            description=description,
        )
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


def upgrade_fixed_asset(conn, asset_id: int, amount: float, date: str) -> Dict[str, Any]:
    if amount <= 0:
        raise LedgerError("ASSET_UPGRADE_INVALID", "改扩建金额必须大于 0")
    asset = conn.execute(
        "SELECT * FROM fixed_assets WHERE id = ?",
        (asset_id,),
    ).fetchone()
    if not asset:
        raise LedgerError("ASSET_NOT_FOUND", f"固定资产不存在: {asset_id}")
    mapping = _load_subledger_mapping()["fixed_asset"]
    description = f"Upgrade asset {asset_id}"
    entries = _build_entries(
        conn,
        [
            (mapping["asset_account"], amount, 0.0),
            (mapping["bank_account"], 0.0, amount),
        ],
        description=description,
    )
    voucher = _create_posted_voucher(conn, date, description, entries)
    conn.execute(
        "UPDATE fixed_assets SET cost = ? WHERE id = ?",
        (round(float(asset["cost"]) + amount, 2), asset_id),
    )
    cur = conn.execute(
        """
        INSERT INTO fixed_asset_changes (asset_id, change_type, amount, date, voucher_id)
        VALUES (?, 'upgrade', ?, ?, ?)
        """,
        (asset_id, round(amount, 2), date, voucher["voucher_id"]),
    )
    return {"change_id": cur.lastrowid, "voucher_id": voucher["voucher_id"]}


def split_fixed_asset(conn, asset_id: int, ratios: List[float]) -> Dict[str, Any]:
    asset = conn.execute(
        "SELECT * FROM fixed_assets WHERE id = ?",
        (asset_id,),
    ).fetchone()
    if not asset:
        raise LedgerError("ASSET_NOT_FOUND", f"固定资产不存在: {asset_id}")
    if not ratios or sum(ratios) <= 0:
        raise LedgerError("ASSET_SPLIT_INVALID", "拆分比例无效")
    total_ratio = sum(ratios)
    new_assets = []
    original_cost = float(asset["cost"])
    original_salvage = float(asset["salvage_value"] or 0)
    for idx, ratio in enumerate(ratios[1:], start=1):
        new_cost = round(original_cost * ratio / total_ratio, 2)
        new_salvage = round(original_salvage * ratio / total_ratio, 2)
        cur = conn.execute(
            """
            INSERT INTO fixed_assets (name, cost, acquired_at, life_years, salvage_value, status)
            VALUES (?, ?, ?, ?, ?, 'active')
            """,
            (
                f"{asset['name']}-S{idx}",
                new_cost,
                asset["acquired_at"],
                asset["life_years"],
                new_salvage,
            ),
        )
        new_assets.append(cur.lastrowid)
    conn.execute(
        "UPDATE fixed_assets SET cost = ?, salvage_value = ? WHERE id = ?",
        (
            round(original_cost * ratios[0] / total_ratio, 2),
            round(original_salvage * ratios[0] / total_ratio, 2),
            asset_id,
        ),
    )
    return {"asset_id": asset_id, "new_asset_ids": new_assets}


def impair_fixed_asset(conn, asset_id: int, period: str, amount: float) -> Dict[str, Any]:
    if amount <= 0:
        raise LedgerError("ASSET_IMPAIRMENT_INVALID", "减值金额必须大于 0")
    asset = conn.execute(
        "SELECT * FROM fixed_assets WHERE id = ?",
        (asset_id,),
    ).fetchone()
    if not asset:
        raise LedgerError("ASSET_NOT_FOUND", f"固定资产不存在: {asset_id}")
    mapping = _load_subledger_mapping()["fixed_asset"]
    description = f"Impairment {period}"
    entries = _build_entries(
        conn,
        [
            (mapping["impairment_loss_account"], amount, 0.0),
            (mapping["impairment_reserve_account"], 0.0, amount),
        ],
        description=description,
    )
    voucher = _create_posted_voucher(conn, f"{period}-01", description, entries)
    cur = conn.execute(
        """
        INSERT INTO fixed_asset_impairments (asset_id, period, amount, voucher_id)
        VALUES (?, ?, ?, ?)
        """,
        (asset_id, period, round(amount, 2), voucher["voucher_id"]),
    )
    return {"impairment_id": cur.lastrowid, "voucher_id": voucher["voucher_id"]}


def create_cip_project(conn, name: str) -> int:
    cur = conn.execute(
        "INSERT INTO cip_projects (name, cost, status) VALUES (?, 0, 'ongoing')",
        (name,),
    )
    return cur.lastrowid


def add_cip_cost(conn, project_id: int, amount: float, date: str) -> Dict[str, Any]:
    if amount <= 0:
        raise LedgerError("CIP_AMOUNT_INVALID", "在建工程金额必须大于 0")
    mapping = _load_subledger_mapping()["fixed_asset"]
    description = f"CIP cost {project_id}"
    entries = _build_entries(
        conn,
        [
            (mapping["cip_account"], amount, 0.0),
            (mapping["bank_account"], 0.0, amount),
        ],
        description=description,
    )
    voucher = _create_posted_voucher(conn, date, description, entries)
    conn.execute(
        "UPDATE cip_projects SET cost = cost + ? WHERE id = ?",
        (round(amount, 2), project_id),
    )
    return {"project_id": project_id, "voucher_id": voucher["voucher_id"]}


def transfer_cip_to_asset(
    conn,
    project_id: int,
    asset_name: str,
    life_years: int,
    salvage_value: float,
    date: str,
    amount: Optional[float] = None,
) -> Dict[str, Any]:
    project = conn.execute(
        "SELECT * FROM cip_projects WHERE id = ?",
        (project_id,),
    ).fetchone()
    if not project:
        raise LedgerError("CIP_NOT_FOUND", f"CIP 不存在: {project_id}")
    total_cost = float(project["cost"] or 0)
    transfer_amount = round(amount if amount is not None else total_cost, 2)
    if transfer_amount <= 0:
        raise LedgerError("CIP_AMOUNT_INVALID", "转固金额必须大于 0")
    mapping = _load_subledger_mapping()["fixed_asset"]
    description = f"CIP transfer {project_id}"
    entries = _build_entries(
        conn,
        [
            (mapping["asset_account"], transfer_amount, 0.0),
            (mapping["cip_account"], 0.0, transfer_amount),
        ],
        description=description,
    )
    voucher = _create_posted_voucher(conn, date, description, entries)
    cur = conn.execute(
        """
        INSERT INTO fixed_assets (name, cost, acquired_at, life_years, salvage_value, status)
        VALUES (?, ?, ?, ?, ?, 'active')
        """,
        (asset_name, transfer_amount, date, life_years, round(salvage_value, 2)),
    )
    asset_id = cur.lastrowid
    conn.execute(
        "UPDATE cip_projects SET status = 'converted' WHERE id = ?",
        (project_id,),
    )
    conn.execute(
        """
        INSERT INTO cip_transfers (project_id, asset_id, amount, date, voucher_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (project_id, asset_id, transfer_amount, date, voucher["voucher_id"]),
    )
    return {"project_id": project_id, "asset_id": asset_id, "voucher_id": voucher["voucher_id"]}


def set_fixed_asset_allocations(
    conn, asset_id: int, allocations: List[Tuple[str, int, float]]
) -> None:
    conn.execute("DELETE FROM fixed_asset_allocations WHERE asset_id = ?", (asset_id,))
    for dim_type, dim_id, ratio in allocations:
        conn.execute(
            """
            INSERT INTO fixed_asset_allocations (asset_id, dim_type, dim_id, ratio)
            VALUES (?, ?, ?, ?)
            """,
            (asset_id, dim_type, dim_id, ratio),
        )


def list_fixed_assets(
    conn, status: Optional[str] = None, period: Optional[str] = None
) -> List[Dict[str, Any]]:
    conditions: List[str] = []
    params: List[Any] = []
    if status and status != "all":
        conditions.append("status = ?")
        params.append(status)
    if period:
        conditions.append("acquired_at <= ?")
        params.append(_period_end_date(period))
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
    ledger_accum_value = abs(ledger_accum)

    return {
        "period": period,
        "asset_total": round(expected_asset, 2),
        "ledger_asset": round(ledger_asset, 2),
        "asset_difference": round(ledger_asset - expected_asset, 2),
        "accum_depreciation": round(expected_accum, 2),
        "ledger_accum": round(ledger_accum_value, 2),
        "accum_difference": round(ledger_accum_value - expected_accum, 2),
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


def _load_forex_config() -> Dict[str, Any]:
    config_path = Path(__file__).resolve().parents[1] / "data" / "forex_config.json"
    if not config_path.exists():
        return dict(DEFAULT_FOREX_CONFIG)
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LedgerError("FOREX_CONFIG_INVALID", f"外汇配置JSON错误: {exc}") from exc
    if not isinstance(data, dict):
        raise LedgerError("FOREX_CONFIG_INVALID", "外汇配置必须为对象")
    merged = dict(DEFAULT_FOREX_CONFIG)
    merged.update(data)
    merged["revaluable_accounts"] = list(merged.get("revaluable_accounts") or [])
    return merged


def _load_inventory_config() -> Dict[str, Any]:
    config_path = Path(__file__).resolve().parents[1] / "data" / "inventory_config.json"
    if not config_path.exists():
        return dict(DEFAULT_INVENTORY_CONFIG)
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LedgerError("INVENTORY_CONFIG_INVALID", f"存货配置JSON错误: {exc}") from exc
    if not isinstance(data, dict):
        raise LedgerError("INVENTORY_CONFIG_INVALID", "存货配置必须为对象")
    merged = dict(DEFAULT_INVENTORY_CONFIG)
    merged.update(data)
    return merged


def _load_credit_config() -> Dict[str, Any]:
    config_path = Path(__file__).resolve().parents[1] / "data" / "credit_config.json"
    if not config_path.exists():
        return dict(DEFAULT_CREDIT_CONFIG)
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LedgerError("CREDIT_CONFIG_INVALID", f"信用配置JSON错误: {exc}") from exc
    if not isinstance(data, dict):
        raise LedgerError("CREDIT_CONFIG_INVALID", "信用配置必须为对象")
    merged = dict(DEFAULT_CREDIT_CONFIG)
    merged.update(data)
    return merged


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
