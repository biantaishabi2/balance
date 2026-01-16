#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger approve command."""

from __future__ import annotations

from ledger.database import get_db
from ledger.services import approve_approval, reject_approval, request_approval
from ledger.utils import print_json


def add_parser(subparsers, parents):
    parser = subparsers.add_parser("approve", help="审批操作", parents=parents)
    parser.add_argument("--target-type", required=True, help="审批对象类型")
    parser.add_argument("--target-id", required=True, help="审批对象ID")
    parser.add_argument(
        "--action",
        choices=["request", "approve", "reject"],
        default="approve",
        help="操作类型",
    )
    parser.set_defaults(func=run)
    return parser


def run(args):
    with get_db(args.db_path) as conn:
        if args.action == "request":
            approval = request_approval(conn, args.target_type, args.target_id)
        elif args.action == "reject":
            approval = reject_approval(conn, args.target_type, args.target_id)
        else:
            approval = approve_approval(conn, args.target_type, args.target_id)

    print_json(
        {
            "target_type": args.target_type,
            "target_id": args.target_id,
            "status": approval["status"],
            "approval_id": approval["id"],
            "message": f"审批状态更新为 {approval['status']}",
        }
    )
