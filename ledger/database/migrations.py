#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Database migrations placeholder."""

from __future__ import annotations

import sqlite3


def run_migrations(conn: sqlite3.Connection) -> None:
    """Apply minimal schema migrations."""
    columns = [row[1] for row in conn.execute("PRAGMA table_info(vouchers)").fetchall()]
    if not columns:
        return
    if "reviewed_at" not in columns:
        conn.execute("ALTER TABLE vouchers ADD COLUMN reviewed_at TEXT")
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

        CREATE TABLE IF NOT EXISTS companies (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          code TEXT NOT NULL UNIQUE,
          name TEXT NOT NULL,
          base_currency TEXT NOT NULL,
          is_enabled INTEGER DEFAULT 1,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS ledgers (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          company_id INTEGER NOT NULL,
          code TEXT NOT NULL,
          name TEXT NOT NULL,
          base_currency TEXT NOT NULL,
          db_path TEXT,
          is_enabled INTEGER DEFAULT 1,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(company_id, code),
          FOREIGN KEY (company_id) REFERENCES companies(id)
        );

        CREATE INDEX IF NOT EXISTS idx_ledgers_company ON ledgers(company_id);

        CREATE TABLE IF NOT EXISTS consolidation_rules (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL UNIQUE,
          group_currency TEXT,
          elimination_accounts TEXT,
          ownership TEXT,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS report_templates (
          code TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          fields TEXT NOT NULL,
          formula TEXT
        );

        CREATE TABLE IF NOT EXISTS fx_rates (
          date TEXT NOT NULL,
          base_currency TEXT NOT NULL,
          quote_currency TEXT NOT NULL,
          rate REAL NOT NULL,
          rate_type TEXT NOT NULL,
          PRIMARY KEY (date, base_currency, quote_currency, rate_type)
        );
        """
    )
