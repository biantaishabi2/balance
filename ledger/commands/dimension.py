#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger dimensions command."""

from __future__ import annotations

from ledger.database import get_db
from ledger.utils import LedgerError, load_json_input, print_json


def add_parser(subparsers, parents):
    parser = subparsers.add_parser("dimensions", help="辅助核算管理", parents=parents)
    sub = parser.add_subparsers(dest="dim_cmd")

    list_parser = sub.add_parser("list", help="列出维度", parents=parents)
    list_parser.add_argument("--type", dest="type", help="维度类型")
    list_parser.set_defaults(func=run_list)

    add_parser = sub.add_parser("add", help="添加维度", parents=parents)
    add_parser.set_defaults(func=run_add)

    return parser


def run_list(args):
    sql = "SELECT id, type, code, name, parent_id FROM dimensions WHERE 1=1"
    params = []
    if args.type:
        sql += " AND type = ?"
        params.append(args.type)
    sql += " ORDER BY id"

    with get_db(args.db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
    dimensions = [
        {
            "id": row["id"],
            "type": row["type"],
            "code": row["code"],
            "name": row["name"],
            "parent_id": row["parent_id"],
        }
        for row in rows
    ]
    print_json({"dimensions": dimensions})


def run_add(args):
    data = load_json_input()
    required = ["type", "code", "name"]
    for field in required:
        if field not in data:
            raise LedgerError("DIMENSION_NOT_FOUND", f"缺少字段: {field}")

    with get_db(args.db_path) as conn:
        conn.execute(
            """
            INSERT INTO dimensions (type, code, name, parent_id, extra, is_enabled)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (
                data["type"],
                data["code"],
                data["name"],
                data.get("parent_id"),
                data.get("extra"),
            ),
        )
    print_json({"status": "success", "message": "维度已添加", "code": data["code"]})
