import pytest

from ledger.database import get_db, init_db
from ledger.services import (
    add_currency,
    add_fx_rate,
    build_entries,
    confirm_voucher,
    fx_balance,
    insert_voucher,
    load_standard_accounts,
    revalue_forex,
)


def test_fx_voucher_and_balance(tmp_path):
    db_path = tmp_path / "ledger.db"
    accounts = [
        {"code": "1122", "name": "AR", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "6001", "name": "Revenue", "level": 1, "type": "revenue", "direction": "credit"},
        {"code": "6051", "name": "FX Gain", "level": 1, "type": "revenue", "direction": "credit"},
        {"code": "6603", "name": "FX Loss", "level": 1, "type": "expense", "direction": "debit"},
    ]

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, accounts)
        add_currency(conn, "USD", "US Dollar", "$", 2)
        add_fx_rate(conn, "USD", "2025-01-10", 7.0, "spot")
        add_fx_rate(conn, "USD", "2025-01-31", 7.2, "closing")

        entries, total_debit, total_credit = build_entries(
            conn,
            [
                {"account": "1122", "foreign_debit_amount": 100, "currency_code": "USD", "fx_rate": 7.0},
                {"account": "6001", "foreign_credit_amount": 100, "currency_code": "USD", "fx_rate": 7.0},
            ],
            "2025-01-10",
        )
        assert total_debit == pytest.approx(700.0, rel=0.01)
        voucher_id, _, period, _ = insert_voucher(
            conn,
            {"date": "2025-01-10", "description": "fx sale"},
            entries,
            "reviewed",
        )
        confirm_voucher(conn, voucher_id)

        fx_rows = fx_balance(conn, period, "USD")
        assert fx_rows[0]["foreign_closing"] == pytest.approx(100.0, rel=0.01)

        revalue = revalue_forex(conn, period)
        assert revalue["voucher_id"] is not None
        gain_row = conn.execute(
            "SELECT closing_balance FROM balances WHERE period = ? AND account_code = ?",
            (period, "6051"),
        ).fetchone()
        assert gain_row["closing_balance"] == pytest.approx(20.0, rel=0.01)


def test_fx_rate_auto_lookup(tmp_path):
    db_path = tmp_path / "ledger.db"
    accounts = [
        {"code": "1122", "name": "AR", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "6001", "name": "Revenue", "level": 1, "type": "revenue", "direction": "credit"},
    ]

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, accounts)
        add_currency(conn, "USD", "US Dollar", "$", 2)
        add_fx_rate(conn, "USD", "2025-01-10", 7.1, "spot")

        entries, total_debit, total_credit = build_entries(
            conn,
            [
                {"account": "1122", "foreign_debit_amount": 100, "currency_code": "USD"},
                {"account": "6001", "foreign_credit_amount": 100, "currency_code": "USD"},
            ],
            "2025-01-10",
        )
        assert total_debit == pytest.approx(710.0, rel=0.01)
        assert total_credit == pytest.approx(710.0, rel=0.01)
