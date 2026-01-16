#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Consolidated reporting helpers for ledger."""

from __future__ import annotations

import ast
import calendar
import json
from typing import Any, Dict, Iterable, List, Optional

from ledger.database import get_db
from ledger.reporting_engine import _load_report_mapping, _sum_rule
from ledger.services import balances_for_period
from ledger.utils import LedgerError


DEFAULT_RATE_POLICY = {
    "asset": "closing",
    "liability": "closing",
    "equity": "historical",
    "revenue": "average",
    "expense": "average",
}


def generate_consolidated_statements(
    conn,
    period: str,
    *,
    ledger_codes: Optional[List[str]] = None,
    rule_name: Optional[str] = None,
    template_code: Optional[str] = None,
    group_currency: Optional[str] = None,
    rate_type_map: Optional[Dict[str, str]] = None,
    rate_date: Optional[str] = None,
) -> Dict[str, Any]:
    rule = _load_consolidation_rule(conn, rule_name) if rule_name else {}
    elimination_rules = rule.get("elimination_accounts", [])
    ownership_map = rule.get("ownership", {})

    ledgers = _load_ledgers(conn, ledger_codes)
    if not ledgers:
        raise LedgerError("LEDGER_NOT_FOUND", "未找到可合并账套")

    if not group_currency:
        group_currency = rule.get("group_currency")

    group_currency = _resolve_group_currency(group_currency, ledgers)
    rate_date = rate_date or _period_end_date(period)

    rate_policy = DEFAULT_RATE_POLICY.copy()
    if rate_type_map:
        rate_policy.update(rate_type_map)

    converted_balances: List[Dict[str, Any]] = []
    ledger_summary: List[Dict[str, Any]] = []
    for ledger in ledgers:
        ownership = _ownership_for_ledger(ledger, ownership_map)
        ledger_summary.append(
            {
                "code": ledger["code"],
                "company_code": ledger["company_code"],
                "base_currency": ledger["base_currency"],
                "ownership": ownership,
            }
        )
        with get_db(ledger["db_path"]) as ledger_conn:
            balances = balances_for_period(ledger_conn, period)
        converted = _convert_balances(
            balances,
            ledger["base_currency"],
            group_currency,
            rate_date,
            rate_policy,
            conn,
        )
        if ownership != 1.0:
            converted = _apply_ownership(converted, ownership)
        converted_balances.extend(converted)

    aggregated = _aggregate_balances(converted_balances)
    eliminations = []
    if elimination_rules:
        eliminations, aggregated = _apply_eliminations(aggregated, elimination_rules)

    statements = _generate_statements_from_balances(aggregated)
    template_report = None
    if template_code:
        template = _load_report_template(conn, template_code)
        template_report = _apply_report_template(template, statements, aggregated)

    output = {
        "period": period,
        "group_currency": group_currency,
        "ledger_count": len(ledgers),
        "ledgers": ledger_summary,
        "income_statement": statements["income_statement"],
        "balance_sheet": statements["balance_sheet"],
        "cash_flow_statement": statements["cash_flow_statement"],
        "adjustments": statements["adjustments"],
        "eliminations": eliminations,
        "is_balanced": statements["is_balanced"],
    }
    if template_report:
        output["template_report"] = template_report
    return output


def _load_ledgers(conn, ledger_codes: Optional[List[str]]) -> List[Dict[str, Any]]:
    params: List[Any] = []
    clause = ""
    if ledger_codes:
        placeholders = ", ".join("?" for _ in ledger_codes)
        clause = f" AND l.code IN ({placeholders})"
        params.extend(ledger_codes)

    rows = conn.execute(
        f"""
        SELECT l.code, l.name, l.base_currency, l.db_path,
               c.code AS company_code, c.base_currency AS company_currency
        FROM ledgers l
        JOIN companies c ON l.company_id = c.id
        WHERE l.is_enabled = 1 {clause}
        """,
        params,
    ).fetchall()
    ledgers = []
    for row in rows:
        base_currency = row["base_currency"] or row["company_currency"]
        db_path = row["db_path"]
        if not db_path:
            raise LedgerError(
                "LEDGER_DB_PATH_REQUIRED",
                f"账套 {row['code']} 缺少 db_path",
            )
        if not base_currency:
            raise LedgerError(
                "LEDGER_CURRENCY_REQUIRED",
                f"账套 {row['code']} 缺少本位币",
            )
        ledgers.append(
            {
                "code": row["code"],
                "name": row["name"],
                "company_code": row["company_code"],
                "base_currency": base_currency,
                "db_path": db_path,
            }
        )
    return ledgers


def _load_consolidation_rule(conn, rule_name: Optional[str]) -> Dict[str, Any]:
    if not rule_name:
        return {}
    row = conn.execute(
        "SELECT * FROM consolidation_rules WHERE name = ?",
        (rule_name,),
    ).fetchone()
    if not row:
        raise LedgerError("CONSOLIDATION_RULE_NOT_FOUND", f"规则不存在: {rule_name}")
    elimination_accounts = _load_json_field(row["elimination_accounts"], "elimination")
    ownership = _load_json_field(row["ownership"], "ownership")
    return {
        "name": row["name"],
        "group_currency": row["group_currency"],
        "elimination_accounts": elimination_accounts,
        "ownership": ownership,
    }


def _load_report_template(conn, template_code: str) -> Dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM report_templates WHERE code = ?",
        (template_code,),
    ).fetchone()
    if not row:
        raise LedgerError("REPORT_TEMPLATE_NOT_FOUND", f"模板不存在: {template_code}")
    fields = _load_json_field(row["fields"], "fields")
    formula = _load_json_field(row["formula"], "formula")
    return {
        "code": row["code"],
        "name": row["name"],
        "fields": fields,
        "formula": formula,
    }


def _load_json_field(value: Optional[str], label: str) -> Any:
    if not value:
        return [] if label in {"fields", "elimination"} else {}
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise LedgerError(
            "INVALID_JSON",
            f"{label} JSON错误: {exc}",
        ) from exc


def _resolve_group_currency(
    group_currency: Optional[str], ledgers: Iterable[Dict[str, Any]]
) -> str:
    if group_currency:
        return group_currency
    currencies = {ledger["base_currency"] for ledger in ledgers}
    if len(currencies) == 1:
        return currencies.pop()
    raise LedgerError("GROUP_CURRENCY_REQUIRED", "请指定集团本位币")


def _ownership_for_ledger(
    ledger: Dict[str, Any], ownership_map: Dict[str, Any]
) -> float:
    ownership = ownership_map.get(ledger["code"])
    if ownership is None:
        ownership = ownership_map.get(ledger["company_code"], 1.0)
    try:
        return float(ownership)
    except (TypeError, ValueError):
        raise LedgerError(
            "INVALID_OWNERSHIP",
            f"无效权益比例: {ledger['code']}",
        )


def _period_end_date(period: str) -> str:
    year, month = period.split("-")
    year_i = int(year)
    month_i = int(month)
    last_day = calendar.monthrange(year_i, month_i)[1]
    return f"{year_i:04d}-{month_i:02d}-{last_day:02d}"


def _convert_balances(
    balances: List[Dict[str, Any]],
    base_currency: str,
    group_currency: str,
    rate_date: str,
    rate_policy: Dict[str, str],
    conn,
) -> List[Dict[str, Any]]:
    converted = []
    for balance in balances:
        account_type = balance.get("account_type") or "asset"
        rate_type = rate_policy.get(account_type, "closing")
        rate = _lookup_fx_rate(
            conn,
            rate_date,
            base_currency,
            group_currency,
            rate_type,
        )
        converted.append(_apply_rate(balance, rate))
    return converted


def _lookup_fx_rate(
    conn,
    rate_date: str,
    base_currency: str,
    group_currency: str,
    rate_type: str,
) -> float:
    if base_currency == group_currency:
        return 1.0
    row = conn.execute(
        """
        SELECT rate FROM fx_rates
        WHERE base_currency = ? AND quote_currency = ? AND rate_type = ? AND date <= ?
        ORDER BY date DESC
        LIMIT 1
        """,
        (base_currency, group_currency, rate_type, rate_date),
    ).fetchone()
    if row:
        return float(row["rate"])

    inverse = conn.execute(
        """
        SELECT rate FROM fx_rates
        WHERE base_currency = ? AND quote_currency = ? AND rate_type = ? AND date <= ?
        ORDER BY date DESC
        LIMIT 1
        """,
        (group_currency, base_currency, rate_type, rate_date),
    ).fetchone()
    if inverse:
        return 1 / float(inverse["rate"])

    raise LedgerError(
        "FX_RATE_NOT_FOUND",
        f"缺少汇率: {base_currency}->{group_currency} {rate_type} {rate_date}",
    )


def _apply_rate(balance: Dict[str, Any], rate: float) -> Dict[str, Any]:
    converted = dict(balance)
    for field in ("opening_balance", "debit_amount", "credit_amount", "closing_balance"):
        converted[field] = float(balance.get(field) or 0) * rate
    return converted


def _apply_ownership(
    balances: List[Dict[str, Any]], ownership: float
) -> List[Dict[str, Any]]:
    scaled = []
    for balance in balances:
        updated = dict(balance)
        for field in ("opening_balance", "debit_amount", "credit_amount", "closing_balance"):
            updated[field] = float(updated.get(field) or 0) * ownership
        scaled.append(updated)
    return scaled


def _aggregate_balances(balances: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    aggregated: Dict[str, Dict[str, Any]] = {}
    for balance in balances:
        code = balance["account_code"]
        if code not in aggregated:
            aggregated[code] = {
                "account_code": balance["account_code"],
                "account_name": balance.get("account_name"),
                "account_type": balance.get("account_type"),
                "account_direction": balance.get("account_direction"),
                "opening_balance": 0.0,
                "debit_amount": 0.0,
                "credit_amount": 0.0,
                "closing_balance": 0.0,
            }
        target = aggregated[code]
        target["opening_balance"] += float(balance.get("opening_balance") or 0)
        target["debit_amount"] += float(balance.get("debit_amount") or 0)
        target["credit_amount"] += float(balance.get("credit_amount") or 0)
        target["closing_balance"] += float(balance.get("closing_balance") or 0)
    return list(aggregated.values())


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _resolve_elimination_side(
    balance_map: Dict[str, Dict[str, Any]],
    pair: Dict[str, Any],
    side: str,
) -> List[Dict[str, Any]]:
    codes = pair.get(side)
    if codes is not None:
        return [
            balance_map[code]
            for code in _as_list(codes)
            if code in balance_map
        ]
    prefixes = pair.get(f"{side}_prefixes") or pair.get(f"{side}_prefix")
    account_types = pair.get(f"{side}_account_types") or pair.get(f"{side}_account_type")
    prefixes_list = _as_list(prefixes)
    types_list = _as_list(account_types)
    matches = []
    if prefixes_list or types_list:
        for balance in balance_map.values():
            code = str(balance.get("account_code") or "")
            if prefixes_list and any(code.startswith(prefix) for prefix in prefixes_list):
                matches.append(balance)
                continue
            if types_list and balance.get("account_type") in types_list:
                matches.append(balance)
    return matches


def _apply_elimination_to_balances(
    balances: List[Dict[str, Any]],
    source: str,
    amount: float,
) -> None:
    total = sum(abs(float(balance.get(source) or 0)) for balance in balances)
    if total <= 0:
        return
    remaining = amount
    for idx, balance in enumerate(balances):
        value = float(balance.get(source) or 0)
        if idx == len(balances) - 1:
            reduction = remaining
        else:
            reduction = amount * (abs(value) / total)
        balance[source] = _reduce_towards_zero(value, reduction)
        remaining -= reduction


def _apply_eliminations(
    balances: List[Dict[str, Any]], elimination_rules: Any
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if not isinstance(elimination_rules, list):
        raise LedgerError("INVALID_ELIMINATION_RULE", "elimination_accounts 必须为列表")
    balance_map = {balance["account_code"]: balance for balance in balances}
    eliminations: List[Dict[str, Any]] = []
    for rule in elimination_rules:
        if rule is None:
            continue
        if isinstance(rule, dict) and "pairs" in rule:
            pairs = rule.get("pairs") or []
        else:
            pairs = [rule]
        for pair in pairs:
            if not isinstance(pair, dict):
                raise LedgerError("INVALID_ELIMINATION_RULE", "抵销规则格式错误")
            source = pair.get("source", "closing_balance")
            left_config = any(
                pair.get(key) is not None
                for key in (
                    "left",
                    "left_prefixes",
                    "left_prefix",
                    "left_account_types",
                    "left_account_type",
                )
            )
            right_config = any(
                pair.get(key) is not None
                for key in (
                    "right",
                    "right_prefixes",
                    "right_prefix",
                    "right_account_types",
                    "right_account_type",
                )
            )
            left_balances = _resolve_elimination_side(balance_map, pair, "left")
            right_balances = _resolve_elimination_side(balance_map, pair, "right")
            if not left_config or not right_config:
                raise LedgerError(
                    "INVALID_ELIMINATION_RULE",
                    "抵销规则缺少 left/right 或前缀/类型配置",
                )
            if not left_balances or not right_balances:
                continue
            left_total = sum(abs(float(item.get(source) or 0)) for item in left_balances)
            right_total = sum(abs(float(item.get(source) or 0)) for item in right_balances)
            elimination = min(left_total, right_total)
            if elimination <= 0:
                continue
            _apply_elimination_to_balances(left_balances, source, elimination)
            _apply_elimination_to_balances(right_balances, source, elimination)
            record = {
                "source": source,
                "amount": round(elimination, 2),
                "left_codes": [item["account_code"] for item in left_balances],
                "right_codes": [item["account_code"] for item in right_balances],
            }
            if pair.get("left") is not None and pair.get("right") is not None:
                left_codes = _as_list(pair.get("left"))
                right_codes = _as_list(pair.get("right"))
                if len(left_codes) == 1 and len(right_codes) == 1:
                    record["left"] = left_codes[0]
                    record["right"] = right_codes[0]
            if pair.get("left_prefixes") or pair.get("left_prefix"):
                record["left_prefixes"] = _as_list(
                    pair.get("left_prefixes") or pair.get("left_prefix")
                )
            if pair.get("right_prefixes") or pair.get("right_prefix"):
                record["right_prefixes"] = _as_list(
                    pair.get("right_prefixes") or pair.get("right_prefix")
                )
            eliminations.append(record)
    return eliminations, list(balance_map.values())


def _reduce_towards_zero(value: float, amount: float) -> float:
    if value >= 0:
        return value - amount
    return value + amount


def _generate_statements_from_balances(
    balances: List[Dict[str, Any]]
) -> Dict[str, Any]:
    mapping = _load_report_mapping()
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

    adjustments: Dict[str, Any] = {}
    fx_adjustment = total_assets - total_liabilities - total_equity
    if abs(fx_adjustment) >= 0.01:
        total_equity += fx_adjustment
        adjustments["fx_translation"] = round(fx_adjustment, 2)

    is_balanced = (
        abs(total_assets - total_liabilities - total_equity) < 0.01
        and abs(net_change - cash_change) < 0.01
    )

    return {
        "income_statement": {
            "revenue": round(revenue, 2),
            "cost": round(cost, 2),
            "expense": round(expense, 2),
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
        "adjustments": adjustments,
        "is_balanced": is_balanced,
    }


def _apply_report_template(
    template: Dict[str, Any],
    statements: Dict[str, Any],
    balances: List[Dict[str, Any]],
) -> Dict[str, Any]:
    fields = _normalize_template_fields(template)
    context = _build_template_context(statements, balances)
    results = []
    for field in fields:
        key = field["key"]
        label = field["label"]
        value = None
        if field.get("formula"):
            value = _safe_eval(field["formula"], context)
        else:
            source_key = field.get("source") or key
            if source_key not in context:
                raise LedgerError("TEMPLATE_FIELD_NOT_FOUND", f"字段不存在: {source_key}")
            value = context[source_key]
        results.append(
            {
                "key": key,
                "label": label,
                "value": round(float(value), 2),
            }
        )
    return {"code": template["code"], "name": template["name"], "fields": results}


def _normalize_template_fields(template: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_fields = template.get("fields") or []
    formula_map = template.get("formula") or {}
    if not isinstance(raw_fields, list):
        raise LedgerError("INVALID_TEMPLATE", "fields 必须为列表")
    if formula_map and not isinstance(formula_map, dict):
        raise LedgerError("INVALID_TEMPLATE", "formula 必须为对象")
    fields = []
    for item in raw_fields:
        if isinstance(item, str):
            fields.append(
                {"key": item, "label": item, "formula": formula_map.get(item)}
            )
        elif isinstance(item, dict):
            key = item.get("key") or item.get("name")
            if not key:
                raise LedgerError("INVALID_TEMPLATE", "字段缺少 key")
            label = item.get("label") or key
            formula = item.get("formula") or formula_map.get(key)
            fields.append(
                {
                    "key": key,
                    "label": label,
                    "formula": formula,
                    "source": item.get("source"),
                }
            )
        else:
            raise LedgerError("INVALID_TEMPLATE", "字段格式错误")
    return fields


def _build_template_context(
    statements: Dict[str, Any], balances: List[Dict[str, Any]]
) -> Dict[str, Any]:
    income = statements["income_statement"]
    balance = statements["balance_sheet"]
    cash_flow = statements["cash_flow_statement"]

    context = {
        "revenue": income.get("revenue", 0),
        "cost": income.get("cost", 0),
        "expense": income.get("expense", 0),
        "gross_profit": income.get("gross_profit", 0),
        "net_income": income.get("net_income", 0),
        "total_assets": balance.get("total_assets", 0),
        "total_liabilities": balance.get("total_liabilities", 0),
        "total_equity": balance.get("total_equity", 0),
        "operating_cf": cash_flow.get("operating_cf", 0),
        "investing_cf": cash_flow.get("investing_cf", 0),
        "financing_cf": cash_flow.get("financing_cf", 0),
        "net_change": cash_flow.get("net_change", 0),
    }

    for balance_row in balances:
        code = str(balance_row.get("account_code"))
        key = f"acc_{code}"
        context[key] = float(balance_row.get("closing_balance") or 0)
    return context


_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow)
_ALLOWED_UNARYOPS = (ast.UAdd, ast.USub)


def _safe_eval(expr: str, context: Dict[str, Any]) -> float:
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise LedgerError("INVALID_FORMULA", f"公式语法错误: {expr}") from exc
    return _eval_node(tree.body, context)


def _eval_node(node: ast.AST, context: Dict[str, Any]) -> float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise LedgerError("INVALID_FORMULA", "公式包含非数字常量")
    if isinstance(node, ast.Name):
        if node.id not in context:
            raise LedgerError("INVALID_FORMULA", f"未知变量: {node.id}")
        return float(context[node.id])
    if isinstance(node, ast.BinOp) and isinstance(node.op, _ALLOWED_BINOPS):
        left = _eval_node(node.left, context)
        right = _eval_node(node.right, context)
        return _apply_binop(node.op, left, right)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, _ALLOWED_UNARYOPS):
        value = _eval_node(node.operand, context)
        return -value if isinstance(node.op, ast.USub) else value
    raise LedgerError("INVALID_FORMULA", "公式包含不支持的表达式")


def _apply_binop(op: ast.AST, left: float, right: float) -> float:
    if isinstance(op, ast.Add):
        return left + right
    if isinstance(op, ast.Sub):
        return left - right
    if isinstance(op, ast.Mult):
        return left * right
    if isinstance(op, ast.Div):
        return left / right
    if isinstance(op, ast.Mod):
        return left % right
    if isinstance(op, ast.Pow):
        return left**right
    raise LedgerError("INVALID_FORMULA", "公式包含不支持的运算符")
