#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger report command."""

from __future__ import annotations

from pathlib import Path

from ledger.database import get_db
from ledger.reporting import generate_statements
from ledger.utils import LedgerError, print_json


def add_parser(subparsers, parents):
    parser = subparsers.add_parser("report", help="生成三表", parents=parents)
    parser.add_argument("--period", required=True, help="期间")
    parser.add_argument("--output", help="输出路径")
    parser.set_defaults(func=run)
    return parser


def run(args):
    with get_db(args.db_path) as conn:
        report = generate_statements(conn, args.period)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(
            print_json_to_string(report),
            encoding="utf-8",
        )
        print_json({"status": "success", "output": str(out_path)})
        return

    print_json(report)


def print_json_to_string(data):
    import json

    return json.dumps(data, ensure_ascii=False, indent=2)
