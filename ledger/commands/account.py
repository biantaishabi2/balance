#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger account command."""

from __future__ import annotations

from ledger.database import get_db
from ledger.services import find_account
from ledger.utils import LedgerError, load_json_input, print_json


def add_parser(subparsers, parents):
    parser = subparsers.add_parser("account", help="科目管理", parents=parents)
    sub = parser.add_subparsers(dest="account_cmd")

    list_parser = sub.add_parser("list", help="列出科目", parents=parents)
    list_parser.add_argument("--type", dest="type", help="科目类型")
    list_parser.add_argument("--level", dest="level", type=int, help="科目级别")
    list_parser.set_defaults(func=run_list)

    add_parser = sub.add_parser("add", help="添加科目", parents=parents)
    add_parser.set_defaults(func=run_add)

    disable_parser = sub.add_parser("disable", help="停用科目", parents=parents)
    disable_parser.add_argument("code", help="科目代码")
    disable_parser.set_defaults(func=run_disable)

    return parser


def run_list(args):
    sql = "SELECT * FROM accounts WHERE 1=1"
    params = []
    if args.type:
        sql += " AND type = ?"
        params.append(args.type)
    if args.level:
        sql += " AND level = ?"
        params.append(args.level)
    sql += " ORDER BY code"

    with get_db(args.db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
    accounts = [
        {
            "code": row["code"],
            "name": row["name"],
            "level": row["level"],
            "type": row["type"],
            "direction": row["direction"],
            "is_enabled": bool(row["is_enabled"]),
        }
        for row in rows
    ]
    print_json({"accounts": accounts})


def run_add(args):
    data = load_json_input()
    required = ["code", "name", "type", "direction"]
    for field in required:
        if field not in data:
            raise LedgerError("ACCOUNT_NOT_FOUND", f"缺少字段: {field}")

    with get_db(args.db_path) as conn:
        level = data.get("level")
        parent_code = data.get("parent_code")
        if level is None:
            if parent_code:
                parent = conn.execute(
                    "SELECT level FROM accounts WHERE code = ?", (parent_code,)
                ).fetchone()
                if not parent:
                    raise LedgerError("ACCOUNT_NOT_FOUND", f"上级科目不存在: {parent_code}")
                level = int(parent["level"]) + 1
            else:
                level = 1
        conn.execute(
            """
            INSERT INTO accounts (code, name, level, parent_code, type, direction, cash_flow, is_enabled, is_system)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, 0)
            """,
            (
                data["code"],
                data["name"],
                level,
                parent_code,
                data["type"],
                data["direction"],
                data.get("cash_flow"),
            ),
        )

    print_json(
        {"status": "success", "message": "科目已添加", "code": data["code"]}
    )


def run_disable(args):
    with get_db(args.db_path) as conn:
        find_account(conn, args.code)
        conn.execute(
            "UPDATE accounts SET is_enabled = 0 WHERE code = ?", (args.code,)
        )
    print_json({"status": "success", "message": "科目已停用", "code": args.code})
