#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reporting helpers for ledger."""

from __future__ import annotations

from typing import Any, Dict, Optional

from balance import run_calc

from ledger.reporting_consolidation import generate_consolidated_statements
from ledger.reporting_engine import generate_ledger_statements
from ledger.services import balances_for_period, build_balance_input


def generate_statements(
    conn,
    period: str,
    assumptions: Optional[Dict[str, Any]] = None,
    dims: Optional[Dict[str, int]] = None,
    engine: str = "balance",
    consolidation_args: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if engine == "consolidation":
        return generate_consolidated_statements(
            conn, period, **(consolidation_args or {})
        )
    if engine == "ledger":
        return generate_ledger_statements(conn, period, dims=dims)

    balances = balances_for_period(conn, period, dims=dims)
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


def generate_group_statements(
    conn,
    period: str,
    *,
    ledger_codes: Optional[list[str]] = None,
    rule_name: Optional[str] = None,
    template_code: Optional[str] = None,
    group_currency: Optional[str] = None,
    rate_type_map: Optional[Dict[str, str]] = None,
    rate_date: Optional[str] = None,
) -> Dict[str, Any]:
    return generate_consolidated_statements(
        conn,
        period,
        ledger_codes=ledger_codes,
        rule_name=rule_name,
        template_code=template_code,
        group_currency=group_currency,
        rate_type_map=rate_type_map,
        rate_date=rate_date,
    )
