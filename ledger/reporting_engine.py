#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ledger-native reporting engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ledger.services import balances_for_period
from ledger.utils import LedgerError


_VALID_SOURCES = {
    "opening_balance",
    "closing_balance",
    "debit_amount",
    "credit_amount",
    "net_change",
}


def generate_ledger_statements(
    conn, period: str, dims: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    mapping = _load_report_mapping()
    balances = balances_for_period(conn, period, dims=dims)

    balance_sheet = mapping.get("balance_sheet", {})
    income_statement = mapping.get("income_statement", {})
    cash_flow = mapping.get("cash_flow", {})

    total_assets = _sum_rule(balances, balance_sheet.get("assets", {}))
    total_liabilities = _sum_rule(balances, balance_sheet.get("liabilities", {}))
    equity_base = _sum_rule(balances, balance_sheet.get("equity", {}))

    revenue = _sum_rule(balances, income_statement.get("revenue", {}))
    cost = _sum_rule(balances, income_statement.get("cost", {}))
    expense = _sum_rule(balances, income_statement.get("expense", {}))
    gross_profit = revenue - cost
    net_income = gross_profit - expense
    total_equity = equity_base + net_income

    operating_adjust = _sum_rule(
        balances,
        cash_flow.get("operating", {}),
        net_change_mode="signed",
    )
    investing_cf = _sum_rule(
        balances,
        cash_flow.get("investing", {}),
        net_change_mode="signed",
    )
    financing_cf = _sum_rule(
        balances,
        cash_flow.get("financing", {}),
        net_change_mode="signed",
    )
    operating_cf = net_income + operating_adjust
    net_change = operating_cf + investing_cf + financing_cf

    cash_rule = cash_flow.get("cash_accounts")
    if not cash_rule:
        cash_rule = {
            "prefixes": ["1001", "1002"],
            "source": "net_change",
            "direction": "debit",
        }
    cash_change = _sum_rule(balances, cash_rule, net_change_mode="cash")

    is_balanced = (
        abs(total_assets - total_liabilities - total_equity) < 0.01
        and abs(net_change - cash_change) < 0.01
    )

    return {
        "period": period,
        "income_statement": {
            "revenue": round(revenue, 2),
            "cost": round(cost, 2),
            "gross_profit": round(gross_profit, 2),
            "net_income": round(net_income, 2),
        },
        "balance_sheet": {
            "total_assets": round(total_assets, 2),
            "total_liabilities": round(total_liabilities, 2),
            "total_equity": round(total_equity, 2),
        },
        "cash_flow_statement": {
            "operating_cf": round(operating_cf, 2),
            "investing_cf": round(investing_cf, 2),
            "financing_cf": round(financing_cf, 2),
            "net_change": round(net_change, 2),
        },
        "is_balanced": is_balanced,
    }


def _load_report_mapping() -> Dict[str, Any]:
    mapping_path = Path(__file__).resolve().parents[1] / "data" / "report_mapping.json"
    if not mapping_path.exists():
        raise LedgerError("REPORT_MAPPING_NOT_FOUND", "缺少报表映射配置")
    try:
        data = json.loads(mapping_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LedgerError("REPORT_MAPPING_INVALID", f"报表映射JSON错误: {exc}") from exc
    if not isinstance(data, dict):
        raise LedgerError("REPORT_MAPPING_INVALID", "报表映射必须为对象")
    return data


def _sum_rule(
    balances: List[Dict[str, Any]],
    rule: Dict[str, Any],
    *,
    net_change_mode: str | None = None,
) -> float:
    if not rule:
        return 0.0
    source = rule.get("source")
    if source not in _VALID_SOURCES:
        raise LedgerError("REPORT_MAPPING_INVALID", f"无效source: {source}")
    direction = rule.get("direction")
    if direction not in {"debit", "credit"}:
        raise LedgerError("REPORT_MAPPING_INVALID", f"无效direction: {direction}")

    total = 0.0
    for balance in balances:
        if not _match_balance(balance, rule):
            continue
        if source == "net_change":
            delta = float(balance.get("closing_balance") or 0) - float(
                balance.get("opening_balance") or 0
            )
            if net_change_mode == "signed":
                delta = delta if direction == "credit" else -delta
            total += delta
        else:
            total += float(balance.get(source) or 0)
    return total


def _match_balance(balance: Dict[str, Any], rule: Dict[str, Any]) -> bool:
    prefixes = rule.get("prefixes") or []
    account_types = rule.get("account_types") or []
    if not prefixes and not account_types:
        raise LedgerError("REPORT_MAPPING_INVALID", "映射缺少prefixes/account_types")

    matched = False
    if prefixes:
        matched = any(balance["account_code"].startswith(prefix) for prefix in prefixes)
    if account_types:
        matched = matched or balance.get("account_type") in account_types
    return matched
