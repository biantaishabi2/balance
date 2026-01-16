#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Database schema for ledger."""

from __future__ import annotations

import sqlite3


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS accounts (
  code TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  level INTEGER NOT NULL,
  parent_code TEXT,
  type TEXT NOT NULL,
  direction TEXT NOT NULL,
  cash_flow TEXT,
  is_enabled INTEGER DEFAULT 1,
  is_system INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (parent_code) REFERENCES accounts(code)
);

CREATE INDEX IF NOT EXISTS idx_accounts_type ON accounts(type);
CREATE INDEX IF NOT EXISTS idx_accounts_level ON accounts(level);

CREATE TABLE IF NOT EXISTS dimensions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT NOT NULL,
  code TEXT NOT NULL,
  name TEXT NOT NULL,
  parent_id INTEGER,
  extra TEXT,
  credit_limit REAL DEFAULT 0,
  credit_used REAL DEFAULT 0,
  credit_days INTEGER DEFAULT 0,
  is_enabled INTEGER DEFAULT 1,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(type, code)
);

CREATE INDEX IF NOT EXISTS idx_dimensions_type ON dimensions(type);

CREATE TABLE IF NOT EXISTS vouchers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  voucher_no TEXT UNIQUE NOT NULL,
  date TEXT NOT NULL,
  period TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'draft',
  entry_type TEXT NOT NULL DEFAULT 'normal',
  source_template TEXT,
  source_event_id TEXT,
  void_reason TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  reviewed_at TEXT,
  confirmed_at TEXT,
  voided_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_vouchers_period ON vouchers(period);
CREATE INDEX IF NOT EXISTS idx_vouchers_date ON vouchers(date);
CREATE INDEX IF NOT EXISTS idx_vouchers_status ON vouchers(status);

CREATE TABLE IF NOT EXISTS invoices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT NOT NULL,
  code TEXT,
  number TEXT NOT NULL,
  date TEXT NOT NULL,
  period TEXT NOT NULL,
  amount REAL NOT NULL,
  tax_rate REAL NOT NULL DEFAULT 0,
  tax_amount REAL NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'issued',
  voucher_id INTEGER,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(code, number),
  FOREIGN KEY (voucher_id) REFERENCES vouchers(id)
);

CREATE INDEX IF NOT EXISTS idx_invoices_period ON invoices(period);
CREATE INDEX IF NOT EXISTS idx_invoices_type ON invoices(type);
CREATE INDEX IF NOT EXISTS idx_invoices_voucher ON invoices(voucher_id);

CREATE TABLE IF NOT EXISTS voucher_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  voucher_id INTEGER NOT NULL,
  line_no INTEGER NOT NULL,
  account_code TEXT NOT NULL,
  account_name TEXT,
  description TEXT,
  debit_amount REAL DEFAULT 0,
  credit_amount REAL DEFAULT 0,
  currency_code TEXT DEFAULT 'CNY',
  fx_rate REAL DEFAULT 1,
  foreign_debit_amount REAL DEFAULT 0,
  foreign_credit_amount REAL DEFAULT 0,
  dept_id INTEGER,
  project_id INTEGER,
  customer_id INTEGER,
  supplier_id INTEGER,
  employee_id INTEGER,
  FOREIGN KEY (voucher_id) REFERENCES vouchers(id) ON DELETE CASCADE,
  FOREIGN KEY (dept_id) REFERENCES dimensions(id),
  FOREIGN KEY (project_id) REFERENCES dimensions(id),
  FOREIGN KEY (customer_id) REFERENCES dimensions(id),
  FOREIGN KEY (supplier_id) REFERENCES dimensions(id),
  FOREIGN KEY (employee_id) REFERENCES dimensions(id),
  FOREIGN KEY (account_code) REFERENCES accounts(code)
);

CREATE INDEX IF NOT EXISTS idx_entries_voucher ON voucher_entries(voucher_id);
CREATE INDEX IF NOT EXISTS idx_entries_account ON voucher_entries(account_code);

CREATE TABLE IF NOT EXISTS balances (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    account_code,
    period,
    dept_id,
    project_id,
    customer_id,
    supplier_id,
    employee_id
  )
);

CREATE INDEX IF NOT EXISTS idx_balances_account ON balances(account_code);
CREATE INDEX IF NOT EXISTS idx_balances_period ON balances(period);
CREATE INDEX IF NOT EXISTS idx_balances_dept ON balances(dept_id);
CREATE INDEX IF NOT EXISTS idx_balances_project ON balances(project_id);
CREATE INDEX IF NOT EXISTS idx_balances_customer ON balances(customer_id);
CREATE INDEX IF NOT EXISTS idx_balances_supplier ON balances(supplier_id);
CREATE INDEX IF NOT EXISTS idx_balances_employee ON balances(employee_id);

CREATE TABLE IF NOT EXISTS tax_adjustments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  period TEXT NOT NULL,
  adjustment_type TEXT NOT NULL,
  amount REAL NOT NULL,
  description TEXT,
  voucher_id INTEGER,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (voucher_id) REFERENCES vouchers(id)
);

CREATE INDEX IF NOT EXISTS idx_tax_adjustments_period ON tax_adjustments(period);
CREATE INDEX IF NOT EXISTS idx_tax_adjustments_type ON tax_adjustments(adjustment_type);

CREATE TABLE IF NOT EXISTS void_vouchers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  original_voucher_id INTEGER NOT NULL,
  void_voucher_id INTEGER NOT NULL,
  void_reason TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (original_voucher_id) REFERENCES vouchers(id),
  FOREIGN KEY (void_voucher_id) REFERENCES vouchers(id)
);

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
  warehouse_id INTEGER,
  location_id INTEGER,
  batch_id INTEGER,
  pending_cost_adjustment REAL DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (voucher_id) REFERENCES vouchers(id)
);

CREATE INDEX IF NOT EXISTS idx_inventory_moves_sku ON inventory_moves(sku);
CREATE INDEX IF NOT EXISTS idx_inventory_moves_date ON inventory_moves(date);

CREATE TABLE IF NOT EXISTS inventory_balances (
  sku TEXT NOT NULL,
  period TEXT NOT NULL,
  warehouse_id INTEGER NOT NULL DEFAULT 0,
  location_id INTEGER NOT NULL DEFAULT 0,
  qty REAL NOT NULL,
  amount REAL NOT NULL,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(sku, period, warehouse_id, location_id)
);

CREATE INDEX IF NOT EXISTS idx_inventory_balances_sku ON inventory_balances(sku);

CREATE TABLE IF NOT EXISTS fixed_assets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  cost REAL NOT NULL,
  acquired_at TEXT NOT NULL,
  life_years INTEGER NOT NULL,
  salvage_value REAL NOT NULL DEFAULT 0,
  dept_id INTEGER,
  project_id INTEGER,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

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

CREATE TABLE IF NOT EXISTS allocation_rules (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  source_accounts TEXT NOT NULL,
  target_dim TEXT NOT NULL,
  basis TEXT NOT NULL,
  period TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS allocation_rule_lines (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  rule_id INTEGER NOT NULL,
  target_dim_id INTEGER NOT NULL,
  ratio REAL NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (rule_id) REFERENCES allocation_rules(id)
);

CREATE INDEX IF NOT EXISTS idx_allocation_rule_lines_rule ON allocation_rule_lines(rule_id);

CREATE TABLE IF NOT EXISTS budgets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  period TEXT NOT NULL,
  dim_type TEXT NOT NULL,
  dim_id INTEGER NOT NULL,
  amount REAL NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(period, dim_type, dim_id)
);

CREATE TABLE IF NOT EXISTS budget_controls (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  period TEXT NOT NULL,
  dim_type TEXT NOT NULL,
  dim_id INTEGER NOT NULL,
  used_amount REAL NOT NULL DEFAULT 0,
  locked_amount REAL NOT NULL DEFAULT 0,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(period, dim_type, dim_id)
);

CREATE TABLE IF NOT EXISTS voucher_events (
  event_id TEXT PRIMARY KEY,
  template_code TEXT NOT NULL,
  voucher_id INTEGER NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (voucher_id) REFERENCES vouchers(id)
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

CREATE TABLE IF NOT EXISTS inventory_serials (
  serial_no TEXT PRIMARY KEY,
  sku TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'in',
  move_in_id INTEGER,
  move_out_id INTEGER,
  warehouse_id INTEGER,
  location_id INTEGER,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT,
  FOREIGN KEY (move_in_id) REFERENCES inventory_moves(id),
  FOREIGN KEY (move_out_id) REFERENCES inventory_moves(id)
);

CREATE INDEX IF NOT EXISTS idx_inventory_serials_sku ON inventory_serials(sku);

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

CREATE TABLE IF NOT EXISTS periods (
  period TEXT PRIMARY KEY,
  status TEXT NOT NULL DEFAULT 'open',
  opened_at TEXT,
  closed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_periods_status ON periods(status);

CREATE TABLE IF NOT EXISTS audit_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor_type TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  action TEXT NOT NULL,
  target_type TEXT,
  target_id TEXT,
  detail TEXT,
  tenant_id TEXT NOT NULL,
  org_id TEXT,
  ip TEXT,
  user_agent TEXT,
  request_id TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_target ON audit_logs(target_type, target_id);

CREATE TABLE IF NOT EXISTS approvals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(target_type, target_id)
);

CREATE TABLE IF NOT EXISTS audit_rules (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  rule_json TEXT NOT NULL
);
"""


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
