#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reporting helpers for ledger."""

from __future__ import annotations

from typing import Any, Dict, Optional

from balance import run_calc

from ledger.reporting_consolidation import generate_consolidated_statements
from ledger.reporting_engine import generate_ledger_statements
from ledger.services import (
    balances_for_period,
    budget_variance,
    build_balance_input,
    calculate_income_tax,
    summarize_tax_adjustments,
    vat_summary,
)


def generate_statements(
    conn,
    period: str,
    assumptions: Optional[Dict[str, Any]] = None,
    dims: Optional[Dict[str, int]] = None,
    engine: str = "balance",
    scope: str = "all",
    consolidation_args: Optional[Dict[str, Any]] = None,
    budget: Optional[Dict[str, Optional[str]]] = None,
) -> Dict[str, Any]:
    if engine == "consolidation":
        return generate_consolidated_statements(
            conn, period, **(consolidation_args or {})
        )
    if engine == "ledger":
        return generate_ledger_statements(conn, period, dims=dims, scope=scope)

    balances = balances_for_period(conn, period, dims=dims, scope=scope)
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
    if budget:
        output["budget_variance"] = budget_variance(
            conn,
            period,
            budget.get("dim_type") or "department",
            budget.get("dim_code"),
        )
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


def generate_tax_report(
    conn,
    period: str,
    *,
    accounting_profit: Optional[float] = None,
    tax_rate: float = 0.25,
    prior_year_loss: float = 0.0,
    taxpayer_type: str = "general",
) -> Dict[str, Any]:
    vat = vat_summary(conn, period, taxpayer_type=taxpayer_type)
    adjustments_bundle = summarize_tax_adjustments(conn, period)
    if accounting_profit is None:
        statements = generate_ledger_statements(conn, period)
        accounting_profit = statements["income_statement"]["net_income"]
    income_tax = calculate_income_tax(
        accounting_profit,
        adjustments=adjustments_bundle["adjustments"],
        tax_rate=tax_rate,
        prior_year_loss=prior_year_loss,
    )
    temp_net = adjustments_bundle["summary"]["temporary"]["net"]
    deferred_tax_asset = abs(temp_net * tax_rate) if temp_net < 0 else 0.0
    deferred_tax_liability = temp_net * tax_rate if temp_net > 0 else 0.0
    return {
        "period": period,
        "vat": vat,
        "income_tax": income_tax,
        "tax_adjustments": {
            "summary": adjustments_bundle["summary"],
            "items": adjustments_bundle["items"],
        },
        "deferred_tax": {
            "temporary_difference": temp_net,
            "tax_rate": round(tax_rate, 4),
            "deferred_tax_asset": round(deferred_tax_asset, 2),
            "deferred_tax_liability": round(deferred_tax_liability, 2),
        },
    }
