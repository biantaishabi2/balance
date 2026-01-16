from ledger.database import get_db, init_db
from ledger.reporting_consolidation import generate_consolidated_statements


def _init_ledger_db(db_path, accounts, vouchers):
    with get_db(str(db_path)) as conn:
        init_db(conn)
        account_map = {}
        for acc in accounts:
            account_map[acc["code"]] = acc
            conn.execute(
                """
                INSERT INTO accounts (
                  code, name, level, parent_code, type, direction, cash_flow, is_enabled, is_system
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    acc["code"],
                    acc["name"],
                    acc.get("level", 1),
                    acc.get("parent_code"),
                    acc.get("type", "asset"),
                    acc.get("direction", "debit"),
                    acc.get("cash_flow"),
                    acc.get("is_enabled", 1),
                    acc.get("is_system", 1),
                ),
            )

        totals = {}
        for voucher_entries in vouchers:
            for entry in voucher_entries:
                code = entry["account_code"]
                totals.setdefault(code, {"debit": 0.0, "credit": 0.0})
                totals[code]["debit"] += float(entry.get("debit_amount") or 0)
                totals[code]["credit"] += float(entry.get("credit_amount") or 0)

        period = "2025-01"
        for code, sums in totals.items():
            direction = account_map[code].get("direction", "debit")
            opening = 0.0
            debit = sums["debit"]
            credit = sums["credit"]
            if direction == "debit":
                closing = opening + debit - credit
            else:
                closing = opening - debit + credit
            conn.execute(
                """
                INSERT INTO balances (
                  account_code, period, dept_id, project_id, customer_id, supplier_id, employee_id,
                  opening_balance, debit_amount, credit_amount, closing_balance
                )
                VALUES (?, ?, 0, 0, 0, 0, 0, ?, ?, ?, ?)
                """,
                (code, period, opening, debit, credit, closing),
            )
    return period


def _init_group_db(db_path, ledgers, fx_rates=None, rule=None, template=None):
    with get_db(str(db_path)) as conn:
        init_db(conn)
        for ledger in ledgers:
            company_id = conn.execute(
                "INSERT INTO companies (code, name, base_currency) VALUES (?, ?, ?)",
                (
                    ledger["company_code"],
                    ledger["company_name"],
                    ledger["base_currency"],
                ),
            ).lastrowid
            conn.execute(
                """
                INSERT INTO ledgers (company_id, code, name, base_currency, db_path)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    company_id,
                    ledger["code"],
                    ledger["name"],
                    ledger["base_currency"],
                    ledger["db_path"],
                ),
            )
        if fx_rates:
            for rate in fx_rates:
                conn.execute(
                    """
                    INSERT INTO fx_rates (date, base_currency, quote_currency, rate, rate_type)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        rate["date"],
                        rate["base_currency"],
                        rate["quote_currency"],
                        rate["rate"],
                        rate["rate_type"],
                    ),
                )
        if rule:
            conn.execute(
                """
                INSERT INTO consolidation_rules (name, group_currency, elimination_accounts, ownership)
                VALUES (?, ?, ?, ?)
                """,
                (
                    rule["name"],
                    rule.get("group_currency"),
                    rule.get("elimination_accounts"),
                    rule.get("ownership"),
                ),
            )
        if template:
            conn.execute(
                """
                INSERT INTO report_templates (code, name, fields, formula)
                VALUES (?, ?, ?, ?)
                """,
                (
                    template["code"],
                    template["name"],
                    template["fields"],
                    template.get("formula"),
                ),
            )


def test_consolidation_fx_translation(tmp_path):
    sub_db = tmp_path / "sub.db"
    period = _init_ledger_db(
        sub_db,
        [
            {"code": "1001", "name": "现金", "level": 1, "type": "asset", "direction": "debit"},
            {"code": "6001", "name": "收入", "level": 1, "type": "revenue", "direction": "credit"},
        ],
        [
            [
                {
                    "line_no": 1,
                    "account_code": "1001",
                    "account_name": "现金",
                    "debit_amount": 100,
                    "credit_amount": 0,
                },
                {
                    "line_no": 2,
                    "account_code": "6001",
                    "account_name": "收入",
                    "debit_amount": 0,
                    "credit_amount": 100,
                },
            ]
        ],
    )

    group_db = tmp_path / "group.db"
    _init_group_db(
        group_db,
        [
            {
                "company_code": "SUB",
                "company_name": "Subsidiary",
                "code": "SUB",
                "name": "Subsidiary Ledger",
                "base_currency": "USD",
                "db_path": str(sub_db),
            }
        ],
        fx_rates=[
            {
                "date": "2025-01-31",
                "base_currency": "USD",
                "quote_currency": "CNY",
                "rate": 7.1,
                "rate_type": "closing",
            },
            {
                "date": "2025-01-31",
                "base_currency": "USD",
                "quote_currency": "CNY",
                "rate": 7.0,
                "rate_type": "average",
            },
            {
                "date": "2025-01-31",
                "base_currency": "USD",
                "quote_currency": "CNY",
                "rate": 6.9,
                "rate_type": "historical",
            },
        ],
        rule={
            "name": "GROUP",
            "group_currency": "CNY",
            "elimination_accounts": "[]",
            "ownership": "{}",
        },
    )

    with get_db(str(group_db)) as conn:
        report = generate_consolidated_statements(conn, period, rule_name="GROUP")

    assert report["balance_sheet"]["total_assets"] == 710.0
    assert report["income_statement"]["revenue"] == 700.0
    assert report["balance_sheet"]["total_equity"] == 710.0
    assert report["adjustments"]["fx_translation"] == 10.0


def test_consolidation_elimination(tmp_path):
    ledger_a = tmp_path / "ledger_a.db"
    ledger_b = tmp_path / "ledger_b.db"
    accounts = [
        {"code": "1122", "name": "应收账款", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "2202", "name": "应付账款", "level": 1, "type": "liability", "direction": "credit"},
        {"code": "3001", "name": "实收资本", "level": 1, "type": "equity", "direction": "credit"},
    ]
    period = _init_ledger_db(
        ledger_a,
        accounts,
        [
            [
                {
                    "line_no": 1,
                    "account_code": "1122",
                    "account_name": "应收账款",
                    "debit_amount": 200,
                    "credit_amount": 0,
                },
                {
                    "line_no": 2,
                    "account_code": "3001",
                    "account_name": "实收资本",
                    "debit_amount": 0,
                    "credit_amount": 200,
                },
            ]
        ],
    )
    _init_ledger_db(
        ledger_b,
        accounts,
        [
            [
                {
                    "line_no": 1,
                    "account_code": "3001",
                    "account_name": "实收资本",
                    "debit_amount": 200,
                    "credit_amount": 0,
                },
                {
                    "line_no": 2,
                    "account_code": "2202",
                    "account_name": "应付账款",
                    "debit_amount": 0,
                    "credit_amount": 200,
                },
            ]
        ],
    )

    group_db = tmp_path / "group_elim.db"
    _init_group_db(
        group_db,
        [
            {
                "company_code": "A",
                "company_name": "Company A",
                "code": "A",
                "name": "Ledger A",
                "base_currency": "CNY",
                "db_path": str(ledger_a),
            },
            {
                "company_code": "B",
                "company_name": "Company B",
                "code": "B",
                "name": "Ledger B",
                "base_currency": "CNY",
                "db_path": str(ledger_b),
            },
        ],
        rule={
            "name": "ELIM",
            "group_currency": "CNY",
            "elimination_accounts": '[{"left":"1122","right":"2202","source":"closing_balance"}]',
            "ownership": "{}",
        },
    )

    with get_db(str(group_db)) as conn:
        report = generate_consolidated_statements(conn, period, rule_name="ELIM")

    assert report["balance_sheet"]["total_assets"] == 0.0
    assert report["balance_sheet"]["total_liabilities"] == 0.0
    assert report["eliminations"][0]["amount"] == 200.0


def test_consolidation_template_report(tmp_path):
    ledger_db = tmp_path / "ledger_tpl.db"
    period = _init_ledger_db(
        ledger_db,
        [
            {"code": "1001", "name": "现金", "level": 1, "type": "asset", "direction": "debit"},
            {"code": "6001", "name": "收入", "level": 1, "type": "revenue", "direction": "credit"},
            {"code": "6401", "name": "成本", "level": 1, "type": "expense", "direction": "debit"},
        ],
        [
            [
                {
                    "line_no": 1,
                    "account_code": "1001",
                    "account_name": "现金",
                    "debit_amount": 100,
                    "credit_amount": 0,
                },
                {
                    "line_no": 2,
                    "account_code": "6001",
                    "account_name": "收入",
                    "debit_amount": 0,
                    "credit_amount": 100,
                },
            ],
            [
                {
                    "line_no": 1,
                    "account_code": "6401",
                    "account_name": "成本",
                    "debit_amount": 60,
                    "credit_amount": 0,
                },
                {
                    "line_no": 2,
                    "account_code": "1001",
                    "account_name": "现金",
                    "debit_amount": 0,
                    "credit_amount": 60,
                },
            ],
        ],
    )

    group_db = tmp_path / "group_tpl.db"
    _init_group_db(
        group_db,
        [
            {
                "company_code": "TPL",
                "company_name": "Template Co",
                "code": "TPL",
                "name": "Template Ledger",
                "base_currency": "CNY",
                "db_path": str(ledger_db),
            }
        ],
        rule={
            "name": "TPL",
            "group_currency": "CNY",
            "elimination_accounts": "[]",
            "ownership": "{}",
        },
        template={
            "code": "GROSS",
            "name": "Gross Report",
            "fields": '[{"key":"gross_margin","label":"Gross Margin","formula":"revenue - cost"}]',
            "formula": "{}",
        },
    )

    with get_db(str(group_db)) as conn:
        report = generate_consolidated_statements(
            conn, period, rule_name="TPL", template_code="GROSS"
        )

    fields = report["template_report"]["fields"]
    assert fields[0]["key"] == "gross_margin"
    assert fields[0]["value"] == 40.0
