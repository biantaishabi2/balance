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
