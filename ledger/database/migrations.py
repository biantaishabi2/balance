#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Database migrations placeholder."""

from __future__ import annotations

import sqlite3

from .schema import SCHEMA_SQL


_DEFAULT_TENANT_COLUMN = "tenant_id TEXT NOT NULL DEFAULT 'default'"
_DEFAULT_ORG_COLUMN = "org_id TEXT NOT NULL DEFAULT 'default'"


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    if not _table_exists(conn, table):
        return
    columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def run_migrations(conn: sqlite3.Connection) -> None:
    """Apply minimal schema migrations."""
    if not _table_exists(conn, "vouchers"):
        return

    _ensure_column(conn, "vouchers", "reviewed_at", "reviewed_at TEXT")
    _ensure_column(
        conn, "vouchers", "entry_type", "entry_type TEXT NOT NULL DEFAULT 'normal'"
    )
    _ensure_column(conn, "vouchers", "source_template", "source_template TEXT")
    _ensure_column(conn, "vouchers", "source_event_id", "source_event_id TEXT")
    _ensure_column(conn, "vouchers", "archived_at", "archived_at TEXT")

    _ensure_column(conn, "dimensions", "credit_limit", "credit_limit REAL DEFAULT 0")
    _ensure_column(conn, "dimensions", "credit_used", "credit_used REAL DEFAULT 0")
    _ensure_column(conn, "dimensions", "credit_days", "credit_days INTEGER DEFAULT 0")

    _ensure_column(conn, "voucher_entries", "currency_code", "currency_code TEXT DEFAULT 'CNY'")
    _ensure_column(conn, "voucher_entries", "fx_rate", "fx_rate REAL DEFAULT 1")
    _ensure_column(
        conn,
        "voucher_entries",
        "foreign_debit_amount",
        "foreign_debit_amount REAL DEFAULT 0",
    )
    _ensure_column(
        conn,
        "voucher_entries",
        "foreign_credit_amount",
        "foreign_credit_amount REAL DEFAULT 0",
    )
    _ensure_column(conn, "voucher_entries", "archived_at", "archived_at TEXT")

    _ensure_column(conn, "inventory_moves", "warehouse_id", "warehouse_id INTEGER")
    _ensure_column(conn, "inventory_moves", "location_id", "location_id INTEGER")
    _ensure_column(conn, "inventory_moves", "batch_id", "batch_id INTEGER")
    _ensure_column(
        conn,
        "inventory_moves",
        "pending_cost_adjustment",
        "pending_cost_adjustment REAL DEFAULT 0",
    )
    _ensure_column(conn, "inventory_balances", "warehouse_id", "warehouse_id INTEGER DEFAULT 0")
    _ensure_column(conn, "inventory_balances", "location_id", "location_id INTEGER DEFAULT 0")

    _ensure_column(conn, "fixed_assets", "dept_id", "dept_id INTEGER")
    _ensure_column(conn, "fixed_assets", "project_id", "project_id INTEGER")

    for table in (
        "accounts",
        "dimensions",
        "vouchers",
        "voucher_entries",
        "balances",
        "balances_fx",
        "void_vouchers",
        "period_closings",
        "ar_items",
        "ap_items",
        "settlements",
        "inventory_items",
        "inventory_moves",
        "inventory_balances",
        "fixed_assets",
        "fixed_asset_depreciations",
        "periods",
    ):
        _ensure_column(conn, table, "tenant_id", _DEFAULT_TENANT_COLUMN)
        _ensure_column(conn, table, "org_id", _DEFAULT_ORG_COLUMN)

    conn.executescript(SCHEMA_SQL)
