#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger init command."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ledger.database import get_db, init_db
from ledger.services import ensure_period, load_standard_accounts
from ledger.utils import LedgerError, print_json


def add_parser(subparsers, parents):
    parser = subparsers.add_parser("init", help="初始化账套", parents=parents)
    parser.set_defaults(func=run)
    return parser


def run(args):
    accounts_path = Path("data/standard_accounts.json")
    if not accounts_path.exists():
        raise LedgerError("ACCOUNT_NOT_FOUND", "标准科目文件不存在")
    accounts = json.loads(accounts_path.read_text(encoding="utf-8"))

    current_period = datetime.now().strftime("%Y-%m")
    with get_db(args.db_path) as conn:
        init_db(conn)
        loaded = load_standard_accounts(conn, accounts)
        ensure_period(conn, current_period)

    print_json(
        {
            "status": "success",
            "message": "账套初始化完成",
            "accounts_loaded": loaded,
            "current_period": current_period,
        }
    )
