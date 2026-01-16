import pytest

from ledger.database import get_db, init_db
from ledger.services import (
    close_period,
    confirm_voucher,
    balances_for_period,
    insert_voucher,
    load_standard_accounts,
    set_period_status,
)
from ledger.utils import LedgerError


BASIC_ACCOUNTS = [
    {"code": "1001", "name": "Cash", "level": 1, "type": "asset", "direction": "debit"},
    {"code": "2001", "name": "Loan", "level": 1, "type": "liability", "direction": "credit"},
]


def _voucher_entries(amount: float = 100):
    return [
        {
            "line_no": 1,
            "account_code": "1001",
            "account_name": "Cash",
            "debit_amount": amount,
            "credit_amount": 0,
        },
        {
            "line_no": 2,
            "account_code": "2001",
            "account_name": "Loan",
            "debit_amount": 0,
            "credit_amount": amount,
        },
    ]


def test_adjustment_period_blocks_normal(tmp_path):
    db_path = tmp_path / "ledger.db"
    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, BASIC_ACCOUNTS)
        set_period_status(conn, "2025-01", "adjustment")

        with pytest.raises(LedgerError) as exc:
            insert_voucher(
                conn,
                {"date": "2025-01-05", "description": "normal"},
                _voucher_entries(),
                "draft",
            )
        assert exc.value.code == "PERIOD_ADJUSTMENT_ONLY"

        voucher_id, _, _, _ = insert_voucher(
            conn,
            {"date": "2025-01-05", "description": "adj", "entry_type": "adjustment"},
            _voucher_entries(),
            "reviewed",
        )
        confirm_voucher(conn, voucher_id)
        row = conn.execute(
            "SELECT status FROM vouchers WHERE id = ?",
            (voucher_id,),
        ).fetchone()
        assert row["status"] == "confirmed"


def test_adjustment_rollforward_creates_next_period_voucher(tmp_path):
    db_path = tmp_path / "ledger.db"
    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, BASIC_ACCOUNTS)

        # create activity in next period
        voucher_id, _, _, _ = insert_voucher(
            conn,
            {"date": "2025-02-03", "description": "next"},
            _voucher_entries(),
            "reviewed",
        )
        confirm_voucher(conn, voucher_id)

        set_period_status(conn, "2025-01", "adjustment")
        adj_id, _, _, _ = insert_voucher(
            conn,
            {"date": "2025-01-10", "description": "adj", "entry_type": "adjustment"},
            _voucher_entries(50),
            "reviewed",
        )
        confirm_voucher(conn, adj_id)

        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM vouchers WHERE period = ? AND description = ?",
            ("2025-02", "2025-01 调整结转"),
        ).fetchone()
        assert row["cnt"] == 1


def test_report_scope_balances(tmp_path):
    db_path = tmp_path / "ledger.db"
    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, BASIC_ACCOUNTS)

        normal_id, _, _, _ = insert_voucher(
            conn,
            {"date": "2025-01-05", "description": "normal"},
            _voucher_entries(),
            "reviewed",
        )
        confirm_voucher(conn, normal_id)
        adj_id, _, _, _ = insert_voucher(
            conn,
            {"date": "2025-01-10", "description": "adj", "entry_type": "adjustment"},
            _voucher_entries(50),
            "reviewed",
        )
        confirm_voucher(conn, adj_id)

        normal_balances = balances_for_period(conn, "2025-01", scope="normal")
        adj_balances = balances_for_period(conn, "2025-01", scope="adjustment")
        normal_cash = next(row for row in normal_balances if row["account_code"] == "1001")
        adj_cash = next(row for row in adj_balances if row["account_code"] == "1001")
        assert normal_cash["closing_balance"] == pytest.approx(100.0, rel=0.01)
        assert adj_cash["closing_balance"] == pytest.approx(50.0, rel=0.01)


def test_close_period_with_template(tmp_path):
    db_path = tmp_path / "ledger.db"
    accounts = [
        {"code": "1001", "name": "Cash", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "6001", "name": "Revenue", "level": 1, "type": "revenue", "direction": "credit"},
        {"code": "6401", "name": "Expense", "level": 1, "type": "expense", "direction": "debit"},
        {"code": "4103", "name": "Profit", "level": 1, "type": "equity", "direction": "credit"},
    ]

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, accounts)
        conn.execute(
            """
            INSERT INTO closing_templates (code, name, rule_json, is_active)
            VALUES (?, ?, ?, 1)
            """,
            (
                "T-01",
                "Template close",
                '{"source_types":["revenue","expense"],"target_account":"4103","description":"template close"}',
            ),
        )

        voucher_id, _, _, _ = insert_voucher(
            conn,
            {"date": "2025-01-05", "description": "sales"},
            [
                {"line_no": 1, "account_code": "1001", "account_name": "Cash", "debit_amount": 100, "credit_amount": 0},
                {"line_no": 2, "account_code": "6001", "account_name": "Revenue", "debit_amount": 0, "credit_amount": 100},
            ],
            "reviewed",
        )
        confirm_voucher(conn, voucher_id)
        voucher_id, _, _, _ = insert_voucher(
            conn,
            {"date": "2025-01-06", "description": "expense"},
            [
                {"line_no": 1, "account_code": "6401", "account_name": "Expense", "debit_amount": 40, "credit_amount": 0},
                {"line_no": 2, "account_code": "1001", "account_name": "Cash", "debit_amount": 0, "credit_amount": 40},
            ],
            "reviewed",
        )
        confirm_voucher(conn, voucher_id)

        result = close_period(conn, "2025-01", template_code="T-01")
        close_entries = conn.execute(
            "SELECT account_code FROM voucher_entries WHERE voucher_id = ?",
            (result["closing_voucher_id"],),
        ).fetchall()
        codes = {row["account_code"] for row in close_entries}
        assert "4103" in codes
