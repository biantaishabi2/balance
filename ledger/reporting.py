#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reporting helpers for ledger."""

from __future__ import annotations

from typing import Any, Dict, Optional

from balance import run_calc

from ledger.services import balances_for_period, build_balance_input


def generate_statements(
    conn, period: str, assumptions: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    balances = balances_for_period(conn, period)
    input_data = build_balance_input(balances)
    if assumptions:
        input_data.update(assumptions)
    result = run_calc(input_data)

    output = {
        "period": period,
        "income_statement": {
            "revenue": result.get("revenue", 0),
            "cost": result.get("cost", 0),
            "gross_profit": result.get("gross_profit", 0),
            "net_income": result.get("net_income", 0),
        },
        "balance_sheet": {
            "total_assets": result.get("total_assets", 0),
            "total_liabilities": result.get("total_liabilities", 0),
            "total_equity": result.get("total_equity", 0),
        },
        "cash_flow_statement": {
            "operating_cf": result.get("operating_cashflow", 0),
            "investing_cf": result.get("investing_cashflow", 0),
            "financing_cf": result.get("financing_cashflow", 0),
            "net_change": result.get("financing_cashflow", 0)
            + result.get("investing_cashflow", 0)
            + result.get("operating_cashflow", 0),
        },
        "is_balanced": result.get("is_balanced", False),
    }
    if assumptions:
        output["assumptions"] = assumptions
    return output
