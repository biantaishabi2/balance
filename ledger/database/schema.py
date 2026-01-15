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
  void_reason TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  reviewed_at TEXT,
  confirmed_at TEXT,
  voided_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_vouchers_period ON vouchers(period);
CREATE INDEX IF NOT EXISTS idx_vouchers_date ON vouchers(date);
CREATE INDEX IF NOT EXISTS idx_vouchers_status ON vouchers(status);

CREATE TABLE IF NOT EXISTS voucher_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
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

CREATE TABLE IF NOT EXISTS void_vouchers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  original_voucher_id INTEGER NOT NULL,
  void_voucher_id INTEGER NOT NULL,
  void_reason TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (original_voucher_id) REFERENCES vouchers(id),
  FOREIGN KEY (void_voucher_id) REFERENCES vouchers(id)
);

CREATE TABLE IF NOT EXISTS periods (
  period TEXT PRIMARY KEY,
  status TEXT NOT NULL DEFAULT 'open',
  opened_at TEXT,
  closed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_periods_status ON periods(status);
"""


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
