#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ledger domain services."""

from __future__ import annotations

from datetime import datetime
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
) -> Tuple[int, str, str, Optional[str]]:
    voucher_no = generate_voucher_no(conn, voucher_data["date"])
    period = parse_period(voucher_data["date"])
    ensure_period(conn, period)
    confirmed_at = None
    if status == "confirmed":
        confirmed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute(
        """
        INSERT INTO vouchers (voucher_no, date, period, description, status, confirmed_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            voucher_no,
            voucher_data["date"],
            period,
            voucher_data.get("description"),
            status,
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


def balances_for_period(conn, period: str) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT b.*, a.name AS account_name, a.type AS account_type, a.direction AS account_direction
        FROM balances b
        JOIN accounts a ON b.account_code = a.code
        WHERE b.period = ?
        """,
        (period,),
    ).fetchall()
    return [dict(r) for r in rows]


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
