#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger invoice command."""

from __future__ import annotations

from datetime import datetime

from ledger.database import get_db
from ledger.services import (
    add_invoice,
    link_invoice,
    list_invoices,
    post_vat_summary,
    vat_summary,
)
from ledger.utils import print_json


def _default_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def add_parser(subparsers, parents):
    parser = subparsers.add_parser("invoice", help="发票管理", parents=parents)
    sub = parser.add_subparsers(dest="invoice_cmd")

    add_cmd = sub.add_parser("add", help="新增发票", parents=parents)
    add_cmd.add_argument(
        "--type",
        required=True,
        choices=["output", "input", "sales", "purchase"],
        help="发票类型",
    )
    add_cmd.add_argument("--code", help="发票代码")
    add_cmd.add_argument("--number", required=True, help="发票号码")
    add_cmd.add_argument("--date", default=_default_date(), help="开票日期")
    add_cmd.add_argument("--amount", type=float, required=True, help="不含税金额")
    add_cmd.add_argument("--tax-rate", type=float, default=0.0, help="税率")
    add_cmd.add_argument("--tax-amount", type=float, help="税额")
    add_cmd.add_argument("--status", default="issued", help="状态")
    add_cmd.add_argument("--voucher-id", type=int, help="关联凭证ID")
    add_cmd.set_defaults(func=run_add)

    list_cmd = sub.add_parser("list", help="发票列表", parents=parents)
    list_cmd.add_argument("--type", dest="invoice_type", help="发票类型")
    list_cmd.add_argument("--period", help="期间")
    list_cmd.add_argument("--status", default="issued", help="状态")
    list_cmd.add_argument("--voucher-id", type=int, help="凭证ID")
    list_cmd.add_argument("--code", help="发票代码")
    list_cmd.add_argument("--number", help="发票号码")
    list_cmd.set_defaults(func=run_list)

    link_cmd = sub.add_parser("link", help="关联凭证", parents=parents)
    link_cmd.add_argument("--invoice-id", type=int, required=True, help="发票ID")
    link_cmd.add_argument("--voucher-id", type=int, required=True, help="凭证ID")
    link_cmd.set_defaults(func=run_link)

    vat_cmd = sub.add_parser("vat", help="增值税汇总", parents=parents)
    vat_cmd.add_argument("--period", required=True, help="期间")
    vat_cmd.add_argument(
        "--taxpayer-type",
        choices=["general", "small_scale"],
        default="general",
        help="纳税人类型",
    )
    vat_cmd.add_argument("--post", action="store_true", help="生成结转凭证")
    vat_cmd.add_argument("--date", help="凭证日期")
    vat_cmd.add_argument("--description", help="凭证摘要")
    vat_cmd.set_defaults(func=run_vat)

    return parser


def run_add(args):
    with get_db(args.db_path) as conn:
        result = add_invoice(
            conn,
            args.type,
            args.code,
            args.number,
            args.date,
            args.amount,
            args.tax_rate,
            args.tax_amount,
            args.status,
            args.voucher_id,
        )
    print_json({"status": "success", **result})


def run_list(args):
    with get_db(args.db_path) as conn:
        rows = list_invoices(
            conn,
            args.invoice_type,
            args.period,
            args.status,
            args.voucher_id,
            args.code,
            args.number,
        )
    print_json({"items": rows})


def run_link(args):
    with get_db(args.db_path) as conn:
        result = link_invoice(conn, args.invoice_id, args.voucher_id)
    print_json({"status": "success", **result})


def run_vat(args):
    with get_db(args.db_path) as conn:
        if args.post:
            result = post_vat_summary(
                conn,
                args.period,
                date=args.date,
                description=args.description,
                taxpayer_type=args.taxpayer_type,
            )
        else:
            result = vat_summary(conn, args.period, taxpayer_type=args.taxpayer_type)
    print_json(result)
