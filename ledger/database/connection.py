#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQLite connection helper."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from ledger.database.migrations import run_migrations

@contextmanager
def get_db(db_path: str = "./ledger.db") -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        run_migrations(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
