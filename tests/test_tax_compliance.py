# -*- coding: utf-8 -*-

import pytest

from ledger.database import get_db, init_db, run_migrations
from ledger.reporting import generate_tax_report
from ledger.services import (
    add_invoice,
    accrue_income_tax,
    confirm_voucher,
    insert_voucher,
    link_invoice,
    post_vat_summary,
    record_tax_adjustment,
    summarize_tax_adjustments,
    vat_summary,
)


def test_vat_summary(tmp_path):
    db_path = tmp_path / "ledger.db"
    with get_db(str(db_path)) as conn:
        init_db(conn)
        run_migrations(conn)
        add_invoice(conn, "output", "A", "0001", "2025-01-10", 1000, 0.13)
        add_invoice(conn, "input", "B", "0002", "2025-01-12", 500, 0.13)

        summary = vat_summary(conn, "2025-01")
        assert summary["output_tax"] == pytest.approx(130.0, rel=0.01)
        assert summary["input_tax"] == pytest.approx(65.0, rel=0.01)
        assert summary["tax_payable"] == pytest.approx(65.0, rel=0.01)


def _seed_accounts(conn, accounts):
    for acc in accounts:
        conn.execute(
            """
            INSERT OR IGNORE INTO accounts (
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


def test_post_vat_summary_creates_voucher(tmp_path):
    db_path = tmp_path / "ledger.db"
    accounts = [
        {
            "code": "222101",
            "name": "VAT Output",
            "level": 1,
            "type": "liability",
            "direction": "credit",
        },
        {
            "code": "222102",
            "name": "VAT Input",
            "level": 1,
            "type": "asset",
            "direction": "debit",
        },
        {
            "code": "222103",
            "name": "VAT Unpaid",
            "level": 1,
            "type": "liability",
            "direction": "credit",
        },
    ]
    mapping = {
        "vat_output_account": "222101",
        "vat_input_account": "222102",
        "vat_unpaid_account": "222103",
    }

    with get_db(str(db_path)) as conn:
        init_db(conn)
        run_migrations(conn)
        _seed_accounts(conn, accounts)
        add_invoice(conn, "output", "A", "0101", "2025-01-05", 1000, 0.13)
        add_invoice(conn, "input", "B", "0201", "2025-01-08", 500, 0.13)

        result = post_vat_summary(conn, "2025-01", mapping=mapping)
        entries = conn.execute(
            "SELECT account_code, debit_amount, credit_amount FROM voucher_entries WHERE voucher_id = ?",
            (result["voucher_id"],),
        ).fetchall()
        entry_map = {row["account_code"]: row for row in entries}

        assert entry_map["222101"]["debit_amount"] == pytest.approx(130.0, rel=0.01)
        assert entry_map["222102"]["credit_amount"] == pytest.approx(65.0, rel=0.01)
        assert entry_map["222103"]["credit_amount"] == pytest.approx(65.0, rel=0.01)


def test_invoice_voucher_link(tmp_path):
    db_path = tmp_path / "ledger.db"
    accounts = [
        {"code": "1001", "name": "Cash", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "2001", "name": "Loan", "level": 1, "type": "liability", "direction": "credit"},
    ]

    with get_db(str(db_path)) as conn:
        init_db(conn)
        run_migrations(conn)
        _seed_accounts(conn, accounts)
        voucher_id, _, _, _ = insert_voucher(
            conn,
            {"date": "2025-01-05", "description": "invoice link"},
            [
                {
                    "line_no": 1,
                    "account_code": "1001",
                    "account_name": "Cash",
                    "debit_amount": 300,
                    "credit_amount": 0,
                },
                {
                    "line_no": 2,
                    "account_code": "2001",
                    "account_name": "Loan",
                    "debit_amount": 0,
                    "credit_amount": 300,
                },
            ],
            "reviewed",
        )
        confirm_voucher(conn, voucher_id)
        invoice = add_invoice(conn, "output", "A", "0102", "2025-01-06", 300, 0.13)
        linked = link_invoice(conn, invoice["invoice_id"], voucher_id)
        assert linked["voucher_id"] == voucher_id
        row = conn.execute(
            "SELECT voucher_id FROM invoices WHERE id = ?",
            (invoice["invoice_id"],),
        ).fetchone()
        assert row["voucher_id"] == voucher_id


def test_income_tax_adjustments_and_report(tmp_path):
    db_path = tmp_path / "ledger.db"
    accounts = [
        {
            "code": "6801",
            "name": "Income Tax Expense",
            "level": 1,
            "type": "expense",
            "direction": "debit",
        },
        {
            "code": "222104",
            "name": "Income Tax Payable",
            "level": 1,
            "type": "liability",
            "direction": "credit",
        },
    ]
    mapping = {
        "income_tax_expense_account": "6801",
        "income_tax_payable_account": "222104",
    }

    with get_db(str(db_path)) as conn:
        init_db(conn)
        run_migrations(conn)
        _seed_accounts(conn, accounts)
        record_tax_adjustment(
            conn,
            "2025-01",
            "permanent",
            100,
            "non-deductible",
        )
        record_tax_adjustment(
            conn,
            "2025-01",
            "temporary",
            -80,
            "timing",
        )

        adjustment_summary = summarize_tax_adjustments(conn, "2025-01")
        assert adjustment_summary["summary"]["permanent"]["add"] == pytest.approx(100.0)
        assert adjustment_summary["summary"]["temporary"]["subtract"] == pytest.approx(80.0)

        accrual = accrue_income_tax(
            conn,
            2000,
            0.25,
            period="2025-01",
            mapping=mapping,
        )
        assert accrual["tax_payable"] == pytest.approx(500.0, rel=0.01)
        entries = conn.execute(
            "SELECT account_code, debit_amount, credit_amount FROM voucher_entries WHERE voucher_id = ?",
            (accrual["voucher_id"],),
        ).fetchall()
        entry_map = {row["account_code"]: row for row in entries}
        assert entry_map["6801"]["debit_amount"] == pytest.approx(500.0, rel=0.01)
        assert entry_map["222104"]["credit_amount"] == pytest.approx(500.0, rel=0.01)

        report = generate_tax_report(
            conn,
            "2025-01",
            accounting_profit=2000,
            tax_rate=0.25,
        )
        assert report["income_tax"]["taxable_income"] == pytest.approx(2020.0, rel=0.01)
        assert report["deferred_tax"]["deferred_tax_asset"] == pytest.approx(20.0, rel=0.01)
