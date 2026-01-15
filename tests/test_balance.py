from ledger.database import get_db, init_db
from ledger.services import insert_voucher, load_standard_accounts, update_balance_for_voucher


def test_update_balance_for_voucher(tmp_path):
    db_path = tmp_path / "ledger.db"
    accounts = [
        {"code": "1001", "name": "库存现金", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "2001", "name": "短期借款", "level": 1, "type": "liability", "direction": "credit"},
    ]

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, accounts)
        voucher_id, _, period, _ = insert_voucher(
            conn,
            {"date": "2025-01-15", "description": "测试"},
            [
                {"line_no": 1, "account_code": "1001", "account_name": "库存现金", "debit_amount": 1000, "credit_amount": 0},
                {"line_no": 2, "account_code": "2001", "account_name": "短期借款", "debit_amount": 0, "credit_amount": 1000},
            ],
            "confirmed",
        )
        update_balance_for_voucher(conn, voucher_id, period)

    with get_db(str(db_path)) as conn:
        rows = conn.execute(
            "SELECT account_code, closing_balance FROM balances ORDER BY account_code"
        ).fetchall()
        balances = {row["account_code"]: row["closing_balance"] for row in rows}
        assert balances["1001"] == 1000
        assert balances["2001"] == 1000
