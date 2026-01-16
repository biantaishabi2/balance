import pytest

from ledger.database import get_db, init_db
from ledger import services
from ledger.services import (
    close_period,
    confirm_voucher,
    ensure_period,
    insert_voucher,
    load_standard_accounts,
    reopen_period,
    review_voucher,
    unreview_voucher,
)
from ledger.utils import LedgerError


BASIC_ACCOUNTS = [
    {"code": "1001", "name": "Cash", "level": 1, "type": "asset", "direction": "debit"},
    {"code": "2001", "name": "Short Loan", "level": 1, "type": "liability", "direction": "credit"},
    {"code": "6001", "name": "Revenue", "level": 1, "type": "revenue", "direction": "credit"},
    {"code": "6401", "name": "Cost", "level": 1, "type": "expense", "direction": "debit"},
    {"code": "4103", "name": "Current Profit", "level": 1, "type": "equity", "direction": "credit"},
    {"code": "4104", "name": "Retained Profit", "level": 1, "type": "equity", "direction": "credit"},
]


def _get_balance(conn, account_code: str, period: str) -> dict:
    row = conn.execute(
        "SELECT opening_balance, closing_balance FROM balances WHERE account_code = ? AND period = ?",
        (account_code, period),
    ).fetchone()
    return dict(row) if row else {}


def test_review_confirm_flow(tmp_path):
    db_path = tmp_path / "ledger.db"

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, BASIC_ACCOUNTS)
        voucher_id, _, _, _ = insert_voucher(
            conn,
            {"date": "2025-01-05", "description": "test"},
            [
                {
                    "line_no": 1,
                    "account_code": "1001",
                    "account_name": "Cash",
                    "debit_amount": 1000,
                    "credit_amount": 0,
                },
                {
                    "line_no": 2,
                    "account_code": "2001",
                    "account_name": "Short Loan",
                    "debit_amount": 0,
                    "credit_amount": 1000,
                },
            ],
            "draft",
        )

        with pytest.raises(LedgerError) as exc:
            confirm_voucher(conn, voucher_id)
        assert exc.value.code == "VOUCHER_NOT_REVIEWED"

        reviewed = review_voucher(conn, voucher_id)
        assert reviewed["status"] == "reviewed"
        assert reviewed["reviewed_at"]

        confirmed = confirm_voucher(conn, voucher_id)
        assert confirmed["status"] == "confirmed"
        assert confirmed["balances_updated"] > 0


def test_unreview_resets_status(tmp_path):
    db_path = tmp_path / "ledger.db"

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, BASIC_ACCOUNTS)
        voucher_id, _, _, _ = insert_voucher(
            conn,
            {"date": "2025-01-08", "description": "test"},
            [
                {
                    "line_no": 1,
                    "account_code": "1001",
                    "account_name": "Cash",
                    "debit_amount": 500,
                    "credit_amount": 0,
                },
                {
                    "line_no": 2,
                    "account_code": "2001",
                    "account_name": "Short Loan",
                    "debit_amount": 0,
                    "credit_amount": 500,
                },
            ],
            "reviewed",
        )

        reverted = unreview_voucher(conn, voucher_id)
        assert reverted["status"] == "draft"
        assert reverted["reviewed_at"] is None


def test_close_period_and_reopen(tmp_path):
    db_path = tmp_path / "ledger.db"

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, BASIC_ACCOUNTS)

        voucher_id, _, _, _ = insert_voucher(
            conn,
            {"date": "2025-01-10", "description": "income"},
            [
                {
                    "line_no": 1,
                    "account_code": "1001",
                    "account_name": "Cash",
                    "debit_amount": 1000,
                    "credit_amount": 0,
                },
                {
                    "line_no": 2,
                    "account_code": "6001",
                    "account_name": "Revenue",
                    "debit_amount": 0,
                    "credit_amount": 1000,
                },
            ],
            "reviewed",
        )
        confirm_voucher(conn, voucher_id)

        voucher_id, _, _, _ = insert_voucher(
            conn,
            {"date": "2025-01-11", "description": "cost"},
            [
                {
                    "line_no": 1,
                    "account_code": "6401",
                    "account_name": "Cost",
                    "debit_amount": 400,
                    "credit_amount": 0,
                },
                {
                    "line_no": 2,
                    "account_code": "1001",
                    "account_name": "Cash",
                    "debit_amount": 0,
                    "credit_amount": 400,
                },
            ],
            "reviewed",
        )
        confirm_voucher(conn, voucher_id)

        result = close_period(conn, "2025-01")
        assert result["closing_voucher_id"] is not None
        assert result["transfer_voucher_id"] is not None
        assert result["next_period"] == "2025-02"
        assert result["net_income"] == 600

        profit_balance = _get_balance(conn, "4103", "2025-01")
        retain_balance = _get_balance(conn, "4104", "2025-01")
        assert profit_balance.get("closing_balance") == pytest.approx(0.0, rel=0.01)
        assert retain_balance.get("closing_balance") == pytest.approx(600.0, rel=0.01)

        cash_closing = _get_balance(conn, "1001", "2025-01")
        next_cash = _get_balance(conn, "1001", "2025-02")
        assert next_cash.get("opening_balance") == pytest.approx(
            cash_closing.get("closing_balance", 0.0), rel=0.01
        )

        period_status = conn.execute(
            "SELECT status FROM periods WHERE period = ?",
            ("2025-01",),
        ).fetchone()
        assert period_status["status"] == "closed"

        reopened = reopen_period(conn, "2025-01")
        assert reopened["status"] == "open"


def test_close_period_blocks_unposted(tmp_path):
    db_path = tmp_path / "ledger.db"

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, BASIC_ACCOUNTS)
        insert_voucher(
            conn,
            {"date": "2025-01-12", "description": "draft"},
            [
                {
                    "line_no": 1,
                    "account_code": "1001",
                    "account_name": "Cash",
                    "debit_amount": 200,
                    "credit_amount": 0,
                },
                {
                    "line_no": 2,
                    "account_code": "2001",
                    "account_name": "Short Loan",
                    "debit_amount": 0,
                    "credit_amount": 200,
                },
            ],
            "draft",
        )

        with pytest.raises(LedgerError) as exc:
            close_period(conn, "2025-01")
        assert exc.value.code == "PERIOD_HAS_UNPOSTED"


def test_close_period_blocks_reviewed(tmp_path):
    db_path = tmp_path / "ledger.db"

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, BASIC_ACCOUNTS)
        insert_voucher(
            conn,
            {"date": "2025-01-12", "description": "reviewed"},
            [
                {
                    "line_no": 1,
                    "account_code": "1001",
                    "account_name": "Cash",
                    "debit_amount": 100,
                    "credit_amount": 0,
                },
                {
                    "line_no": 2,
                    "account_code": "2001",
                    "account_name": "Short Loan",
                    "debit_amount": 0,
                    "credit_amount": 100,
                },
            ],
            "reviewed",
        )

        with pytest.raises(LedgerError) as exc:
            close_period(conn, "2025-01")
        assert exc.value.code == "PERIOD_HAS_UNPOSTED"


def test_close_period_blocks_new_voucher(tmp_path):
    db_path = tmp_path / "ledger.db"

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, BASIC_ACCOUNTS)

        voucher_id, _, _, _ = insert_voucher(
            conn,
            {"date": "2025-01-10", "description": "income"},
            [
                {
                    "line_no": 1,
                    "account_code": "1001",
                    "account_name": "Cash",
                    "debit_amount": 1000,
                    "credit_amount": 0,
                },
                {
                    "line_no": 2,
                    "account_code": "6001",
                    "account_name": "Revenue",
                    "debit_amount": 0,
                    "credit_amount": 1000,
                },
            ],
            "reviewed",
        )
        confirm_voucher(conn, voucher_id)

        close_period(conn, "2025-01")

        with pytest.raises(LedgerError) as exc:
            insert_voucher(
                conn,
                {"date": "2025-01-20", "description": "after close"},
                [
                    {
                        "line_no": 1,
                        "account_code": "1001",
                        "account_name": "Cash",
                        "debit_amount": 50,
                        "credit_amount": 0,
                    },
                    {
                        "line_no": 2,
                        "account_code": "2001",
                        "account_name": "Short Loan",
                        "debit_amount": 0,
                        "credit_amount": 50,
                    },
                ],
                "draft",
            )
        assert exc.value.code == "PERIOD_CLOSED"


def test_close_period_blocks_next_period_vouchers(tmp_path):
    db_path = tmp_path / "ledger.db"

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, BASIC_ACCOUNTS)

        voucher_id, _, _, _ = insert_voucher(
            conn,
            {"date": "2025-02-05", "description": "next"},
            [
                {
                    "line_no": 1,
                    "account_code": "1001",
                    "account_name": "Cash",
                    "debit_amount": 200,
                    "credit_amount": 0,
                },
                {
                    "line_no": 2,
                    "account_code": "2001",
                    "account_name": "Short Loan",
                    "debit_amount": 0,
                    "credit_amount": 200,
                },
            ],
            "reviewed",
        )
        confirm_voucher(conn, voucher_id)

        voucher_id, _, _, _ = insert_voucher(
            conn,
            {"date": "2025-01-10", "description": "income"},
            [
                {
                    "line_no": 1,
                    "account_code": "1001",
                    "account_name": "Cash",
                    "debit_amount": 100,
                    "credit_amount": 0,
                },
                {
                    "line_no": 2,
                    "account_code": "6001",
                    "account_name": "Revenue",
                    "debit_amount": 0,
                    "credit_amount": 100,
                },
            ],
            "reviewed",
        )
        confirm_voucher(conn, voucher_id)

        with pytest.raises(LedgerError) as exc:
            close_period(conn, "2025-01")
        assert exc.value.code == "NEXT_PERIOD_HAS_VOUCHERS"


def test_close_period_blocks_next_period_balances(tmp_path):
    db_path = tmp_path / "ledger.db"

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, BASIC_ACCOUNTS)
        ensure_period(conn, "2025-02")
        conn.execute(
            """
            INSERT INTO balances (
              account_code, period, dept_id, project_id, customer_id, supplier_id, employee_id,
              opening_balance, debit_amount, credit_amount, closing_balance
            )
            VALUES (?, ?, 0, 0, 0, 0, 0, 0, 100, 0, 100)
            """,
            ("1001", "2025-02"),
        )

        voucher_id, _, _, _ = insert_voucher(
            conn,
            {"date": "2025-01-10", "description": "income"},
            [
                {
                    "line_no": 1,
                    "account_code": "1001",
                    "account_name": "Cash",
                    "debit_amount": 100,
                    "credit_amount": 0,
                },
                {
                    "line_no": 2,
                    "account_code": "6001",
                    "account_name": "Revenue",
                    "debit_amount": 0,
                    "credit_amount": 100,
                },
            ],
            "reviewed",
        )
        confirm_voucher(conn, voucher_id)

        with pytest.raises(LedgerError) as exc:
            close_period(conn, "2025-01")
        assert exc.value.code == "NEXT_PERIOD_HAS_BALANCES"


def test_reopen_voids_closing_vouchers(tmp_path):
    db_path = tmp_path / "ledger.db"

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, BASIC_ACCOUNTS)

        voucher_id, _, _, _ = insert_voucher(
            conn,
            {"date": "2025-01-10", "description": "income"},
            [
                {
                    "line_no": 1,
                    "account_code": "1001",
                    "account_name": "Cash",
                    "debit_amount": 1000,
                    "credit_amount": 0,
                },
                {
                    "line_no": 2,
                    "account_code": "6001",
                    "account_name": "Revenue",
                    "debit_amount": 0,
                    "credit_amount": 1000,
                },
            ],
            "reviewed",
        )
        confirm_voucher(conn, voucher_id)

        close_result = close_period(conn, "2025-01")
        closing_id = close_result["closing_voucher_id"]
        transfer_id = close_result["transfer_voucher_id"]

        reopen_result = reopen_period(conn, "2025-01")
        assert reopen_result["status"] == "open"
        if closing_id:
            row = conn.execute(
                "SELECT status FROM vouchers WHERE id = ?",
                (closing_id,),
            ).fetchone()
            assert row["status"] == "voided"
        if transfer_id:
            row = conn.execute(
                "SELECT status FROM vouchers WHERE id = ?",
                (transfer_id,),
            ).fetchone()
            assert row["status"] == "voided"
        next_rows = conn.execute(
            "SELECT COUNT(*) AS cnt FROM balances WHERE period = ?",
            ("2025-02",),
        ).fetchone()
        assert next_rows["cnt"] == 0


def test_close_period_custom_config(tmp_path, monkeypatch):
    db_path = tmp_path / "ledger.db"
    accounts = BASIC_ACCOUNTS + [
        {"code": "4105", "name": "Alt Profit", "level": 1, "type": "equity", "direction": "credit"},
        {"code": "4106", "name": "Alt Retained", "level": 1, "type": "equity", "direction": "credit"},
    ]

    def _mock_config():
        return {"profit_account": "4105", "retain_account": "4106"}

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, accounts)
        monkeypatch.setattr(services, "_load_close_config", _mock_config)

        voucher_id, _, _, _ = insert_voucher(
            conn,
            {"date": "2025-01-10", "description": "income"},
            [
                {
                    "line_no": 1,
                    "account_code": "1001",
                    "account_name": "Cash",
                    "debit_amount": 500,
                    "credit_amount": 0,
                },
                {
                    "line_no": 2,
                    "account_code": "6001",
                    "account_name": "Revenue",
                    "debit_amount": 0,
                    "credit_amount": 500,
                },
            ],
            "reviewed",
        )
        confirm_voucher(conn, voucher_id)

        close_period(conn, "2025-01")
        alt_profit = _get_balance(conn, "4105", "2025-01")
        alt_retained = _get_balance(conn, "4106", "2025-01")
        assert alt_profit.get("closing_balance") == pytest.approx(0.0, rel=0.01)
        assert alt_retained.get("closing_balance") == pytest.approx(500.0, rel=0.01)
