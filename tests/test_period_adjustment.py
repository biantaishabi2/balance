import pytest

from ledger.database import get_db, init_db
from ledger.services import (
    confirm_voucher,
    insert_voucher,
    load_standard_accounts,
    set_period_status,
)
from ledger.utils import LedgerError


BASIC_ACCOUNTS = [
    {"code": "1001", "name": "Cash", "level": 1, "type": "asset", "direction": "debit"},
    {"code": "2001", "name": "Loan", "level": 1, "type": "liability", "direction": "credit"},
]


def _voucher_entries():
    return [
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
            "account_name": "Loan",
            "debit_amount": 0,
            "credit_amount": 100,
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
            _voucher_entries(),
            "reviewed",
        )
        confirm_voucher(conn, adj_id)

        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM vouchers WHERE period = ? AND description = ?",
            ("2025-02", "2025-01 调整结转"),
        ).fetchone()
        assert row["cnt"] == 1
