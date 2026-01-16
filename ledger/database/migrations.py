#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Database migrations placeholder."""

from __future__ import annotations

import sqlite3


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

    for table in (
        "accounts",
        "dimensions",
        "vouchers",
        "voucher_entries",
        "balances",
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

    _ensure_column(conn, "vouchers", "archived_at", "archived_at TEXT")
    _ensure_column(conn, "voucher_entries", "archived_at", "archived_at TEXT")

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS tenants (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'active',
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS organizations (
          id TEXT NOT NULL,
          tenant_id TEXT NOT NULL,
          name TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'active',
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (tenant_id, id),
          FOREIGN KEY (tenant_id) REFERENCES tenants(id)
        );

        CREATE INDEX IF NOT EXISTS idx_organizations_tenant ON organizations(tenant_id);

        CREATE TABLE IF NOT EXISTS api_tokens (
          token TEXT PRIMARY KEY,
          tenant_id TEXT NOT NULL,
          org_id TEXT NOT NULL,
          name TEXT,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          revoked_at TEXT,
          FOREIGN KEY (tenant_id) REFERENCES tenants(id),
          FOREIGN KEY (tenant_id, org_id) REFERENCES organizations(tenant_id, id)
        );

        CREATE INDEX IF NOT EXISTS idx_api_tokens_tenant ON api_tokens(tenant_id, org_id);

        CREATE TABLE IF NOT EXISTS webhook_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          tenant_id TEXT NOT NULL,
          org_id TEXT NOT NULL,
          event_type TEXT NOT NULL,
          payload TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending',
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          delivered_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_webhook_events_tenant ON webhook_events(tenant_id, org_id);
        CREATE INDEX IF NOT EXISTS idx_webhook_events_status ON webhook_events(status);

        CREATE TABLE IF NOT EXISTS archive_runs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          tenant_id TEXT NOT NULL,
          org_id TEXT NOT NULL,
          cutoff_period TEXT NOT NULL,
          voucher_count INTEGER NOT NULL DEFAULT 0,
          entry_count INTEGER NOT NULL DEFAULT 0,
          archived_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_archive_runs_tenant ON archive_runs(tenant_id, org_id);

        CREATE INDEX IF NOT EXISTS idx_accounts_tenant ON accounts(tenant_id, org_id);
        CREATE INDEX IF NOT EXISTS idx_dimensions_tenant ON dimensions(tenant_id, org_id);
        CREATE INDEX IF NOT EXISTS idx_vouchers_tenant ON vouchers(tenant_id, org_id);
        CREATE INDEX IF NOT EXISTS idx_vouchers_archived ON vouchers(archived_at);
        CREATE INDEX IF NOT EXISTS idx_entries_tenant ON voucher_entries(tenant_id, org_id);
        CREATE INDEX IF NOT EXISTS idx_entries_archived ON voucher_entries(archived_at);
        CREATE INDEX IF NOT EXISTS idx_balances_tenant ON balances(tenant_id, org_id);
        CREATE INDEX IF NOT EXISTS idx_periods_tenant ON periods(tenant_id, org_id);
        CREATE INDEX IF NOT EXISTS idx_period_closings_tenant ON period_closings(tenant_id, org_id);
        CREATE INDEX IF NOT EXISTS idx_ar_items_tenant ON ar_items(tenant_id, org_id);
        CREATE INDEX IF NOT EXISTS idx_ap_items_tenant ON ap_items(tenant_id, org_id);
        CREATE INDEX IF NOT EXISTS idx_settlements_tenant ON settlements(tenant_id, org_id);
        CREATE INDEX IF NOT EXISTS idx_inventory_items_tenant ON inventory_items(tenant_id, org_id);
        CREATE INDEX IF NOT EXISTS idx_inventory_moves_tenant ON inventory_moves(tenant_id, org_id);
        CREATE INDEX IF NOT EXISTS idx_inventory_balances_tenant ON inventory_balances(tenant_id, org_id);
        CREATE INDEX IF NOT EXISTS idx_fixed_asset_depr_tenant ON fixed_asset_depreciations(tenant_id, org_id);
        """
    )
