#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger ar command."""

from __future__ import annotations

from datetime import datetime

from ledger.database import get_db
from ledger.services import (
    add_ar_item,
    ar_aging,
    add_bill,
    create_payment_plan,
    provision_bad_debt,
    provision_bad_debt_auto,
    reverse_bad_debt,
    set_credit_profile,
    settle_payment_plan,
    update_bill_status,
    list_ar_items,
    reconcile_ar,
    settle_ar_item,
)
from ledger.utils import print_json


def _default_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def add_parser(subparsers, parents):
    parser = subparsers.add_parser("ar", help="应收管理", parents=parents)
    sub = parser.add_subparsers(dest="ar_cmd")

    add_cmd = sub.add_parser("add", help="新增应收", parents=parents)
    add_cmd.add_argument("--customer", required=True, help="客户维度代码")
    add_cmd.add_argument("--amount", type=float, required=True, help="应收金额")
    add_cmd.add_argument("--date", default=_default_date(), help="业务日期")
    add_cmd.add_argument("--description", help="摘要")
    add_cmd.set_defaults(func=run_add)

    settle_cmd = sub.add_parser("settle", help="应收核销", parents=parents)
    settle_cmd.add_argument("--item-id", type=int, required=True, help="应收ID")
    settle_cmd.add_argument("--amount", type=float, required=True, help="核销金额")
    settle_cmd.add_argument("--date", default=_default_date(), help="核销日期")
    settle_cmd.add_argument("--description", help="摘要")
    settle_cmd.set_defaults(func=run_settle)

    list_cmd = sub.add_parser("list", help="应收列表", parents=parents)
    list_cmd.add_argument("--status", default="open", help="状态: open/settled/all")
    list_cmd.add_argument("--period", help="期间")
    list_cmd.add_argument("--customer", help="客户维度代码")
    list_cmd.set_defaults(func=run_list)

    aging_cmd = sub.add_parser("aging", help="应收账龄", parents=parents)
    aging_cmd.add_argument("--as-of", default=_default_date(), help="截止日期")
    aging_cmd.add_argument("--customer", help="客户维度代码")
    aging_cmd.set_defaults(func=run_aging)

    reconcile_cmd = sub.add_parser("reconcile", help="应收对平", parents=parents)
    reconcile_cmd.add_argument("--period", required=True, help="期间")
    reconcile_cmd.add_argument("--customer", help="客户维度代码")
    reconcile_cmd.set_defaults(func=run_reconcile)

    credit_cmd = sub.add_parser("credit", help="信用额度", parents=parents)
    credit_cmd.add_argument("--customer", required=True, help="客户维度代码")
    credit_cmd.add_argument("--limit", type=float, required=True, help="信用额度")
    credit_cmd.add_argument("--days", type=int, default=0, help="账期天数")
    credit_cmd.set_defaults(func=run_credit)

    plan_cmd = sub.add_parser("plan", help="收款计划", parents=parents)
    plan_cmd.add_argument("--item-id", type=int, required=True, help="应收ID")
    plan_cmd.add_argument("--due-date", required=True, help="到期日")
    plan_cmd.add_argument("--amount", type=float, required=True, help="金额")
    plan_cmd.set_defaults(func=run_plan_add)

    plan_settle_cmd = sub.add_parser("plan-settle", help="计划回款", parents=parents)
    plan_settle_cmd.add_argument("--plan-id", type=int, required=True, help="计划ID")
    plan_settle_cmd.add_argument("--date", default=_default_date(), help="回款日期")
    plan_settle_cmd.set_defaults(func=run_plan_settle)

    bill_cmd = sub.add_parser("bill", help="票据", parents=parents)
    bill_cmd.add_argument("--bill-no", required=True, help="票据号")
    bill_cmd.add_argument("--amount", type=float, required=True, help="金额")
    bill_cmd.add_argument("--date", default=_default_date(), help="日期")
    bill_cmd.add_argument("--maturity-date", help="到期日")
    bill_cmd.add_argument("--item-id", type=int, help="应收ID")
    bill_cmd.set_defaults(func=run_bill_add)

    bill_status_cmd = sub.add_parser("bill-status", help="票据状态", parents=parents)
    bill_status_cmd.add_argument("--bill-no", required=True, help="票据号")
    bill_status_cmd.add_argument("--status", required=True, help="endorsed/discounted/settled")
    bill_status_cmd.add_argument("--date", default=_default_date(), help="日期")
    bill_status_cmd.set_defaults(func=run_bill_status)

    bad_debt_cmd = sub.add_parser("bad-debt", help="坏账计提", parents=parents)
    bad_debt_cmd.add_argument("--period", required=True, help="期间")
    bad_debt_cmd.add_argument("--customer", required=True, help="客户维度代码")
    bad_debt_cmd.add_argument("--amount", type=float, required=True, help="金额")
    bad_debt_cmd.set_defaults(func=run_bad_debt)

    bad_debt_auto_cmd = sub.add_parser("bad-debt-auto", help="坏账自动计提", parents=parents)
    bad_debt_auto_cmd.add_argument("--period", required=True, help="期间")
    bad_debt_auto_cmd.add_argument("--customer", required=True, help="客户维度代码")
    bad_debt_auto_cmd.set_defaults(func=run_bad_debt_auto)

    bad_debt_rev_cmd = sub.add_parser("bad-debt-reverse", help="坏账冲回", parents=parents)
    bad_debt_rev_cmd.add_argument("--period", required=True, help="期间")
    bad_debt_rev_cmd.add_argument("--customer", required=True, help="客户维度代码")
    bad_debt_rev_cmd.add_argument("--amount", type=float, required=True, help="金额")
    bad_debt_rev_cmd.set_defaults(func=run_bad_debt_reverse)

    return parser


def run_add(args):
    with get_db(args.db_path) as conn:
        result = add_ar_item(
            conn,
            args.customer,
            args.amount,
            args.date,
            args.description,
        )
    print_json({"status": "success", **result})


def run_settle(args):
    with get_db(args.db_path) as conn:
        result = settle_ar_item(
            conn,
            args.item_id,
            args.amount,
            args.date,
            args.description,
        )
    print_json({"status": "success", **result})


def run_list(args):
    with get_db(args.db_path) as conn:
        rows = list_ar_items(conn, args.status, args.period, args.customer)
    print_json({"items": rows})


def run_aging(args):
    with get_db(args.db_path) as conn:
        buckets = ar_aging(conn, args.as_of, args.customer)
    print_json({"as_of": args.as_of, "aging": buckets})


def run_reconcile(args):
    with get_db(args.db_path) as conn:
        result = reconcile_ar(conn, args.period, args.customer)
    print_json({"status": "success", **result})


def run_credit(args):
    with get_db(args.db_path) as conn:
        result = set_credit_profile(conn, "customer", args.customer, args.limit, args.days)
    print_json({"status": "success", **result})


def run_plan_add(args):
    with get_db(args.db_path) as conn:
        result = create_payment_plan(conn, "ar", args.item_id, args.due_date, args.amount)
    print_json({"status": "success", **result})


def run_plan_settle(args):
    with get_db(args.db_path) as conn:
        result = settle_payment_plan(conn, args.plan_id, args.date)
    print_json({"status": "success", **result})


def run_bill_add(args):
    with get_db(args.db_path) as conn:
        result = add_bill(
            conn,
            args.bill_no,
            "ar",
            args.amount,
            args.date,
            args.maturity_date,
            "ar" if args.item_id else None,
            args.item_id,
        )
    print_json({"status": "success", **result})


def run_bill_status(args):
    with get_db(args.db_path) as conn:
        result = update_bill_status(conn, args.bill_no, args.status, args.date)
    print_json({"status": "success", **result})


def run_bad_debt(args):
    with get_db(args.db_path) as conn:
        result = provision_bad_debt(conn, args.period, args.customer, args.amount)
    print_json({"status": "success", **result})


def run_bad_debt_reverse(args):
    with get_db(args.db_path) as conn:
        result = reverse_bad_debt(conn, args.period, args.customer, args.amount)
    print_json({"status": "success", **result})


def run_bad_debt_auto(args):
    with get_db(args.db_path) as conn:
        result = provision_bad_debt_auto(conn, args.period, args.customer)
    print_json({"status": "success", **result})
