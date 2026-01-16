#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Database schema for ledger."""

from __future__ import annotations

import sqlite3


SCHEMA_SQL = """
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

CREATE TABLE IF NOT EXISTS accounts (
  tenant_id TEXT NOT NULL DEFAULT 'default',
  org_id TEXT NOT NULL DEFAULT 'default',
  code TEXT NOT NULL,
  name TEXT NOT NULL,
  level INTEGER NOT NULL,
  parent_code TEXT,
  type TEXT NOT NULL,
  direction TEXT NOT NULL,
  cash_flow TEXT,
  is_enabled INTEGER DEFAULT 1,
  is_system INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (tenant_id, org_id, code),
  FOREIGN KEY (tenant_id, org_id, parent_code) REFERENCES accounts(tenant_id, org_id, code)
);

CREATE INDEX IF NOT EXISTS idx_accounts_tenant ON accounts(tenant_id, org_id);
CREATE INDEX IF NOT EXISTS idx_accounts_type ON accounts(type);
CREATE INDEX IF NOT EXISTS idx_accounts_level ON accounts(level);

CREATE TABLE IF NOT EXISTS dimensions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id TEXT NOT NULL DEFAULT 'default',
  org_id TEXT NOT NULL DEFAULT 'default',
  type TEXT NOT NULL,
  code TEXT NOT NULL,
  name TEXT NOT NULL,
  parent_id INTEGER,
  extra TEXT,
  is_enabled INTEGER DEFAULT 1,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(tenant_id, org_id, type, code)
);

CREATE INDEX IF NOT EXISTS idx_dimensions_tenant ON dimensions(tenant_id, org_id);
CREATE INDEX IF NOT EXISTS idx_dimensions_type ON dimensions(type);

CREATE TABLE IF NOT EXISTS vouchers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id TEXT NOT NULL DEFAULT 'default',
  org_id TEXT NOT NULL DEFAULT 'default',
  voucher_no TEXT NOT NULL,
  date TEXT NOT NULL,
  period TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'draft',
  void_reason TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  reviewed_at TEXT,
  confirmed_at TEXT,
  voided_at TEXT,
  archived_at TEXT,
  UNIQUE(tenant_id, org_id, voucher_no)
);

CREATE INDEX IF NOT EXISTS idx_vouchers_tenant ON vouchers(tenant_id, org_id);
CREATE INDEX IF NOT EXISTS idx_vouchers_period ON vouchers(period);
CREATE INDEX IF NOT EXISTS idx_vouchers_date ON vouchers(date);
CREATE INDEX IF NOT EXISTS idx_vouchers_status ON vouchers(status);
CREATE INDEX IF NOT EXISTS idx_vouchers_archived ON vouchers(archived_at);

CREATE TABLE IF NOT EXISTS voucher_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id TEXT NOT NULL DEFAULT 'default',
  org_id TEXT NOT NULL DEFAULT 'default',
  voucher_id INTEGER NOT NULL,
  line_no INTEGER NOT NULL,
  account_code TEXT NOT NULL,
  account_name TEXT,
  description TEXT,
  debit_amount REAL DEFAULT 0,
  credit_amount REAL DEFAULT 0,
  dept_id INTEGER,
  project_id INTEGER,
  customer_id INTEGER,
  supplier_id INTEGER,
  employee_id INTEGER,
  archived_at TEXT,
  FOREIGN KEY (voucher_id) REFERENCES vouchers(id) ON DELETE CASCADE,
  FOREIGN KEY (dept_id) REFERENCES dimensions(id),
  FOREIGN KEY (project_id) REFERENCES dimensions(id),
  FOREIGN KEY (customer_id) REFERENCES dimensions(id),
  FOREIGN KEY (supplier_id) REFERENCES dimensions(id),
  FOREIGN KEY (employee_id) REFERENCES dimensions(id),
  FOREIGN KEY (tenant_id, org_id, account_code) REFERENCES accounts(tenant_id, org_id, code)
);

CREATE INDEX IF NOT EXISTS idx_entries_tenant ON voucher_entries(tenant_id, org_id);
CREATE INDEX IF NOT EXISTS idx_entries_voucher ON voucher_entries(voucher_id);
CREATE INDEX IF NOT EXISTS idx_entries_account ON voucher_entries(account_code);
CREATE INDEX IF NOT EXISTS idx_entries_archived ON voucher_entries(archived_at);

CREATE TABLE IF NOT EXISTS balances (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id TEXT NOT NULL DEFAULT 'default',
  org_id TEXT NOT NULL DEFAULT 'default',
  account_code TEXT NOT NULL,
  period TEXT NOT NULL,
  dept_id INTEGER NOT NULL DEFAULT 0,
  project_id INTEGER NOT NULL DEFAULT 0,
  customer_id INTEGER NOT NULL DEFAULT 0,
  supplier_id INTEGER NOT NULL DEFAULT 0,
  employee_id INTEGER NOT NULL DEFAULT 0,
  opening_balance REAL DEFAULT 0,
  debit_amount REAL DEFAULT 0,
  credit_amount REAL DEFAULT 0,
  closing_balance REAL DEFAULT 0,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(
    tenant_id,
    org_id,
    account_code,
    period,
    dept_id,
    project_id,
    customer_id,
    supplier_id,
    employee_id
  )
);

CREATE INDEX IF NOT EXISTS idx_balances_tenant ON balances(tenant_id, org_id);
CREATE INDEX IF NOT EXISTS idx_balances_account ON balances(account_code);
CREATE INDEX IF NOT EXISTS idx_balances_period ON balances(period);
CREATE INDEX IF NOT EXISTS idx_balances_dept ON balances(dept_id);
CREATE INDEX IF NOT EXISTS idx_balances_project ON balances(project_id);
CREATE INDEX IF NOT EXISTS idx_balances_customer ON balances(customer_id);
CREATE INDEX IF NOT EXISTS idx_balances_supplier ON balances(supplier_id);
CREATE INDEX IF NOT EXISTS idx_balances_employee ON balances(employee_id);

CREATE TABLE IF NOT EXISTS void_vouchers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id TEXT NOT NULL DEFAULT 'default',
  org_id TEXT NOT NULL DEFAULT 'default',
  original_voucher_id INTEGER NOT NULL,
  void_voucher_id INTEGER NOT NULL,
  void_reason TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (original_voucher_id) REFERENCES vouchers(id),
  FOREIGN KEY (void_voucher_id) REFERENCES vouchers(id)
);

CREATE TABLE IF NOT EXISTS period_closings (
  tenant_id TEXT NOT NULL DEFAULT 'default',
  org_id TEXT NOT NULL DEFAULT 'default',
  period TEXT NOT NULL,
  closing_voucher_id INTEGER,
  transfer_voucher_id INTEGER,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  reopened_at TEXT,
  PRIMARY KEY (tenant_id, org_id, period),
  FOREIGN KEY (closing_voucher_id) REFERENCES vouchers(id),
  FOREIGN KEY (transfer_voucher_id) REFERENCES vouchers(id)
);

CREATE INDEX IF NOT EXISTS idx_period_closings_tenant ON period_closings(tenant_id, org_id);

CREATE TABLE IF NOT EXISTS ar_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id TEXT NOT NULL DEFAULT 'default',
  org_id TEXT NOT NULL DEFAULT 'default',
  customer_id INTEGER NOT NULL,
  voucher_id INTEGER NOT NULL,
  amount REAL NOT NULL,
  settled_amount REAL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'open',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (customer_id) REFERENCES dimensions(id),
  FOREIGN KEY (voucher_id) REFERENCES vouchers(id)
);

CREATE INDEX IF NOT EXISTS idx_ar_items_tenant ON ar_items(tenant_id, org_id);
CREATE INDEX IF NOT EXISTS idx_ar_items_customer ON ar_items(customer_id);

CREATE TABLE IF NOT EXISTS ap_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id TEXT NOT NULL DEFAULT 'default',
  org_id TEXT NOT NULL DEFAULT 'default',
  supplier_id INTEGER NOT NULL,
  voucher_id INTEGER NOT NULL,
  amount REAL NOT NULL,
  settled_amount REAL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'open',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (supplier_id) REFERENCES dimensions(id),
  FOREIGN KEY (voucher_id) REFERENCES vouchers(id)
);

CREATE INDEX IF NOT EXISTS idx_ap_items_tenant ON ap_items(tenant_id, org_id);
CREATE INDEX IF NOT EXISTS idx_ap_items_supplier ON ap_items(supplier_id);

CREATE TABLE IF NOT EXISTS settlements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id TEXT NOT NULL DEFAULT 'default',
  org_id TEXT NOT NULL DEFAULT 'default',
  item_type TEXT NOT NULL,
  item_id INTEGER NOT NULL,
  amount REAL NOT NULL,
  voucher_id INTEGER NOT NULL,
  date TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (voucher_id) REFERENCES vouchers(id)
);

CREATE INDEX IF NOT EXISTS idx_settlements_tenant ON settlements(tenant_id, org_id);
CREATE INDEX IF NOT EXISTS idx_settlements_item ON settlements(item_type, item_id);

CREATE TABLE IF NOT EXISTS inventory_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id TEXT NOT NULL DEFAULT 'default',
  org_id TEXT NOT NULL DEFAULT 'default',
  sku TEXT NOT NULL,
  name TEXT NOT NULL,
  unit TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(tenant_id, org_id, sku)
);

CREATE INDEX IF NOT EXISTS idx_inventory_items_tenant ON inventory_items(tenant_id, org_id);

CREATE TABLE IF NOT EXISTS inventory_moves (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id TEXT NOT NULL DEFAULT 'default',
  org_id TEXT NOT NULL DEFAULT 'default',
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

CREATE INDEX IF NOT EXISTS idx_inventory_moves_tenant ON inventory_moves(tenant_id, org_id);
CREATE INDEX IF NOT EXISTS idx_inventory_moves_sku ON inventory_moves(sku);
CREATE INDEX IF NOT EXISTS idx_inventory_moves_date ON inventory_moves(date);

CREATE TABLE IF NOT EXISTS inventory_balances (
  tenant_id TEXT NOT NULL DEFAULT 'default',
  org_id TEXT NOT NULL DEFAULT 'default',
  sku TEXT NOT NULL,
  period TEXT NOT NULL,
  qty REAL NOT NULL,
  amount REAL NOT NULL,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(tenant_id, org_id, sku, period)
);

CREATE INDEX IF NOT EXISTS idx_inventory_balances_tenant ON inventory_balances(tenant_id, org_id);
CREATE INDEX IF NOT EXISTS idx_inventory_balances_sku ON inventory_balances(sku);

CREATE TABLE IF NOT EXISTS fixed_assets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id TEXT NOT NULL DEFAULT 'default',
  org_id TEXT NOT NULL DEFAULT 'default',
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
  tenant_id TEXT NOT NULL DEFAULT 'default',
  org_id TEXT NOT NULL DEFAULT 'default',
  asset_id INTEGER NOT NULL,
  period TEXT NOT NULL,
  amount REAL NOT NULL,
  voucher_id INTEGER NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (asset_id) REFERENCES fixed_assets(id),
  FOREIGN KEY (voucher_id) REFERENCES vouchers(id)
);

CREATE INDEX IF NOT EXISTS idx_fixed_asset_depr_tenant ON fixed_asset_depreciations(tenant_id, org_id);
CREATE INDEX IF NOT EXISTS idx_fixed_asset_depr_asset ON fixed_asset_depreciations(asset_id);

CREATE TABLE IF NOT EXISTS periods (
  tenant_id TEXT NOT NULL DEFAULT 'default',
  org_id TEXT NOT NULL DEFAULT 'default',
  period TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  opened_at TEXT,
  closed_at TEXT,
  PRIMARY KEY (tenant_id, org_id, period)
);

CREATE INDEX IF NOT EXISTS idx_periods_tenant ON periods(tenant_id, org_id);
CREATE INDEX IF NOT EXISTS idx_periods_status ON periods(status);
"""


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
