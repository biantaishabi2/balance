#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Database migrations placeholder."""

from __future__ import annotations

import sqlite3


def run_migrations(conn: sqlite3.Connection) -> None:
    """Apply minimal schema migrations."""
    def _ensure_column(table: str, column: str, ddl: str) -> None:
        columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")

    columns = [row[1] for row in conn.execute("PRAGMA table_info(vouchers)").fetchall()]
    if not columns:
        return
    if "reviewed_at" not in columns:
        conn.execute("ALTER TABLE vouchers ADD COLUMN reviewed_at TEXT")
    _ensure_column("vouchers", "entry_type", "entry_type TEXT NOT NULL DEFAULT 'normal'")
    _ensure_column("vouchers", "source_template", "source_template TEXT")
    _ensure_column("dimensions", "credit_limit", "credit_limit REAL DEFAULT 0")
    _ensure_column("dimensions", "credit_used", "credit_used REAL DEFAULT 0")
    _ensure_column("dimensions", "credit_days", "credit_days INTEGER DEFAULT 0")
    _ensure_column("voucher_entries", "currency_code", "currency_code TEXT DEFAULT 'CNY'")
    _ensure_column("voucher_entries", "fx_rate", "fx_rate REAL DEFAULT 1")
    _ensure_column(
        "voucher_entries", "foreign_debit_amount", "foreign_debit_amount REAL DEFAULT 0"
    )
    _ensure_column(
        "voucher_entries", "foreign_credit_amount", "foreign_credit_amount REAL DEFAULT 0"
    )
    _ensure_column("inventory_moves", "warehouse_id", "warehouse_id INTEGER")
    _ensure_column("inventory_moves", "location_id", "location_id INTEGER")
    _ensure_column("inventory_moves", "batch_id", "batch_id INTEGER")
    _ensure_column(
        "inventory_moves", "pending_cost_adjustment", "pending_cost_adjustment REAL DEFAULT 0"
    )
    _ensure_column("inventory_balances", "warehouse_id", "warehouse_id INTEGER DEFAULT 0")
    _ensure_column("inventory_balances", "location_id", "location_id INTEGER DEFAULT 0")
    _ensure_column("fixed_assets", "dept_id", "dept_id INTEGER")
    _ensure_column("fixed_assets", "project_id", "project_id INTEGER")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS period_closings (
          period TEXT PRIMARY KEY,
          closing_voucher_id INTEGER,
          transfer_voucher_id INTEGER,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          reopened_at TEXT,
          FOREIGN KEY (closing_voucher_id) REFERENCES vouchers(id),
          FOREIGN KEY (transfer_voucher_id) REFERENCES vouchers(id)
        );

        CREATE TABLE IF NOT EXISTS ar_items (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          customer_id INTEGER NOT NULL,
          voucher_id INTEGER NOT NULL,
          amount REAL NOT NULL,
          settled_amount REAL DEFAULT 0,
          status TEXT NOT NULL DEFAULT 'open',
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (customer_id) REFERENCES dimensions(id),
          FOREIGN KEY (voucher_id) REFERENCES vouchers(id)
        );

        CREATE INDEX IF NOT EXISTS idx_ar_items_customer ON ar_items(customer_id);

        CREATE TABLE IF NOT EXISTS ap_items (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          supplier_id INTEGER NOT NULL,
          voucher_id INTEGER NOT NULL,
          amount REAL NOT NULL,
          settled_amount REAL DEFAULT 0,
          status TEXT NOT NULL DEFAULT 'open',
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (supplier_id) REFERENCES dimensions(id),
          FOREIGN KEY (voucher_id) REFERENCES vouchers(id)
        );

        CREATE INDEX IF NOT EXISTS idx_ap_items_supplier ON ap_items(supplier_id);

        CREATE TABLE IF NOT EXISTS settlements (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          item_type TEXT NOT NULL,
          item_id INTEGER NOT NULL,
          amount REAL NOT NULL,
          voucher_id INTEGER NOT NULL,
          date TEXT NOT NULL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (voucher_id) REFERENCES vouchers(id)
        );

        CREATE INDEX IF NOT EXISTS idx_settlements_item ON settlements(item_type, item_id);

        CREATE TABLE IF NOT EXISTS inventory_items (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          sku TEXT NOT NULL UNIQUE,
          name TEXT NOT NULL,
          unit TEXT NOT NULL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS inventory_moves (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          sku TEXT NOT NULL,
          direction TEXT NOT NULL,
          qty REAL NOT NULL,
          unit_cost REAL NOT NULL,
          total_cost REAL NOT NULL,
          voucher_id INTEGER NOT NULL,
          date TEXT NOT NULL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (voucher_id) REFERENCES vouchers(id)
        );

        CREATE INDEX IF NOT EXISTS idx_inventory_moves_sku ON inventory_moves(sku);
        CREATE INDEX IF NOT EXISTS idx_inventory_moves_date ON inventory_moves(date);

        CREATE TABLE IF NOT EXISTS inventory_balances (
          sku TEXT NOT NULL,
          period TEXT NOT NULL,
          qty REAL NOT NULL,
          amount REAL NOT NULL,
          updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(sku, period)
        );

        CREATE INDEX IF NOT EXISTS idx_inventory_balances_sku ON inventory_balances(sku);

        CREATE TABLE IF NOT EXISTS fixed_assets (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          cost REAL NOT NULL,
          acquired_at TEXT NOT NULL,
          life_years INTEGER NOT NULL,
          salvage_value REAL NOT NULL DEFAULT 0,
          status TEXT NOT NULL DEFAULT 'active',
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS fixed_asset_depreciations (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          asset_id INTEGER NOT NULL,
          period TEXT NOT NULL,
          amount REAL NOT NULL,
          voucher_id INTEGER NOT NULL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (asset_id) REFERENCES fixed_assets(id),
          FOREIGN KEY (voucher_id) REFERENCES vouchers(id)
        );

        CREATE INDEX IF NOT EXISTS idx_fixed_asset_depr_asset ON fixed_asset_depreciations(asset_id);

        CREATE TABLE IF NOT EXISTS currencies (
          code TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          symbol TEXT,
          precision INTEGER NOT NULL DEFAULT 2,
          is_active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS exchange_rates (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          currency_code TEXT NOT NULL,
          date TEXT NOT NULL,
          rate REAL NOT NULL,
          rate_type TEXT NOT NULL DEFAULT 'spot',
          source TEXT,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(currency_code, date, rate_type),
          FOREIGN KEY (currency_code) REFERENCES currencies(code)
        );

        CREATE TABLE IF NOT EXISTS balances_fx (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          account_code TEXT NOT NULL,
          period TEXT NOT NULL,
          currency_code TEXT NOT NULL,
          dept_id INTEGER NOT NULL DEFAULT 0,
          project_id INTEGER NOT NULL DEFAULT 0,
          customer_id INTEGER NOT NULL DEFAULT 0,
          supplier_id INTEGER NOT NULL DEFAULT 0,
          employee_id INTEGER NOT NULL DEFAULT 0,
          foreign_opening REAL DEFAULT 0,
          foreign_debit REAL DEFAULT 0,
          foreign_credit REAL DEFAULT 0,
          foreign_closing REAL DEFAULT 0,
          updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(
            account_code,
            period,
            currency_code,
            dept_id,
            project_id,
            customer_id,
            supplier_id,
            employee_id
          )
        );

        CREATE TABLE IF NOT EXISTS closing_templates (
          code TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          rule_json TEXT NOT NULL,
          is_active INTEGER DEFAULT 1,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS voucher_templates (
          code TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          rule_json TEXT NOT NULL,
          is_active INTEGER DEFAULT 1,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS payment_plans (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          item_type TEXT NOT NULL,
          item_id INTEGER NOT NULL,
          due_date TEXT NOT NULL,
          amount REAL NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending',
          voucher_id INTEGER,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS bills (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          bill_no TEXT NOT NULL,
          bill_type TEXT NOT NULL,
          amount REAL NOT NULL,
          status TEXT NOT NULL DEFAULT 'holding',
          maturity_date TEXT,
          item_type TEXT,
          item_id INTEGER,
          voucher_id INTEGER,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(bill_no)
        );

        CREATE TABLE IF NOT EXISTS bad_debt_provisions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          period TEXT NOT NULL,
          customer_id INTEGER NOT NULL,
          amount REAL NOT NULL,
          voucher_id INTEGER NOT NULL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (customer_id) REFERENCES dimensions(id),
          FOREIGN KEY (voucher_id) REFERENCES vouchers(id)
        );

        CREATE TABLE IF NOT EXISTS warehouses (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          code TEXT NOT NULL,
          name TEXT NOT NULL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(code)
        );

        CREATE TABLE IF NOT EXISTS locations (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          warehouse_id INTEGER NOT NULL,
          code TEXT NOT NULL,
          name TEXT NOT NULL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(warehouse_id, code),
          FOREIGN KEY (warehouse_id) REFERENCES warehouses(id)
        );

        CREATE TABLE IF NOT EXISTS inventory_batches (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          sku TEXT NOT NULL,
          batch_no TEXT,
          qty REAL NOT NULL,
          remaining_qty REAL NOT NULL,
          unit_cost REAL NOT NULL,
          total_cost REAL NOT NULL,
          warehouse_id INTEGER,
          location_id INTEGER,
          status TEXT NOT NULL DEFAULT 'open',
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_inventory_batches_sku ON inventory_batches(sku);

        CREATE TABLE IF NOT EXISTS inventory_move_lines (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          move_id INTEGER NOT NULL,
          batch_id INTEGER,
          qty REAL NOT NULL,
          unit_cost REAL NOT NULL,
          total_cost REAL NOT NULL,
          FOREIGN KEY (move_id) REFERENCES inventory_moves(id),
          FOREIGN KEY (batch_id) REFERENCES inventory_batches(id)
        );

        CREATE TABLE IF NOT EXISTS inventory_counts (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          sku TEXT NOT NULL,
          warehouse_id INTEGER,
          counted_qty REAL NOT NULL,
          book_qty REAL NOT NULL,
          diff_qty REAL NOT NULL,
          date TEXT NOT NULL,
          voucher_id INTEGER,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS standard_costs (
          sku TEXT NOT NULL,
          period TEXT NOT NULL,
          cost REAL NOT NULL,
          variance_account TEXT,
          UNIQUE(sku, period)
        );

        CREATE TABLE IF NOT EXISTS fixed_asset_changes (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          asset_id INTEGER NOT NULL,
          change_type TEXT NOT NULL,
          amount REAL NOT NULL,
          date TEXT NOT NULL,
          voucher_id INTEGER,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (asset_id) REFERENCES fixed_assets(id)
        );

        CREATE TABLE IF NOT EXISTS fixed_asset_impairments (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          asset_id INTEGER NOT NULL,
          period TEXT NOT NULL,
          amount REAL NOT NULL,
          voucher_id INTEGER NOT NULL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (asset_id) REFERENCES fixed_assets(id),
          FOREIGN KEY (voucher_id) REFERENCES vouchers(id)
        );

        CREATE TABLE IF NOT EXISTS cip_projects (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          cost REAL NOT NULL DEFAULT 0,
          status TEXT NOT NULL DEFAULT 'ongoing',
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS cip_transfers (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id INTEGER NOT NULL,
          asset_id INTEGER NOT NULL,
          amount REAL NOT NULL,
          date TEXT NOT NULL,
          voucher_id INTEGER,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (project_id) REFERENCES cip_projects(id),
          FOREIGN KEY (asset_id) REFERENCES fixed_assets(id)
        );

        CREATE TABLE IF NOT EXISTS fixed_asset_allocations (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          asset_id INTEGER NOT NULL,
          dim_type TEXT NOT NULL,
          dim_id INTEGER NOT NULL,
          ratio REAL NOT NULL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(asset_id, dim_type, dim_id),
          FOREIGN KEY (asset_id) REFERENCES fixed_assets(id)
        );

        CREATE TABLE IF NOT EXISTS allocation_basis_values (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          period TEXT NOT NULL,
          dim_type TEXT NOT NULL,
          dim_id INTEGER NOT NULL,
          value REAL NOT NULL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(period, dim_type, dim_id)
        );
        """
    )
