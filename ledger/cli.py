#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Main CLI for ledger."""

from __future__ import annotations

import argparse

from ledger import commands
from ledger.utils import LedgerError, handle_error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ledger",
        description="记账系统 CLI",
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db-path", default="./ledger.db", help="数据库路径")

    subparsers = parser.add_subparsers(dest="command")

    commands.add_init_parser(subparsers, [common])
    commands.add_record_parser(subparsers, [common])
    commands.add_review_parser(subparsers, [common])
    commands.add_unreview_parser(subparsers, [common])
    commands.add_confirm_parser(subparsers, [common])
    commands.add_close_parser(subparsers, [common])
    commands.add_reopen_parser(subparsers, [common])
    commands.add_delete_parser(subparsers, [common])
    commands.add_void_parser(subparsers, [common])
    commands.add_query_parser(subparsers, [common])
    commands.add_report_parser(subparsers, [common])
    commands.add_account_parser(subparsers, [common])
    commands.add_dimension_parser(subparsers, [common])
    commands.add_ar_parser(subparsers, [common])
    commands.add_ap_parser(subparsers, [common])
    commands.add_inventory_parser(subparsers, [common])
    commands.add_fixed_asset_parser(subparsers, [common])

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return
    try:
        args.func(args)
    except LedgerError as exc:
        handle_error(exc)


if __name__ == "__main__":
    main()
