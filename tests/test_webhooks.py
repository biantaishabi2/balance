from ledger.database import get_db, init_db
from ledger.services import (
    close_period,
    confirm_voucher,
    insert_voucher,
    inventory_move_in,
    load_standard_accounts,
)


def test_webhook_events_emitted(tmp_path):
    db_path = tmp_path / "ledger.db"
    accounts = [
        {"code": "1002", "name": "Bank", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "1403", "name": "Inventory", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "2001", "name": "Loan", "level": 1, "type": "liability", "direction": "credit"},
        {"code": "6401", "name": "COGS", "level": 1, "type": "expense", "direction": "debit"},
        {"code": "4103", "name": "Current Profit", "level": 1, "type": "equity", "direction": "credit"},
        {"code": "4104", "name": "Retained Profit", "level": 1, "type": "equity", "direction": "credit"},
    ]

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, accounts)
        voucher_id, _, period, _ = insert_voucher(
            conn,
            {"date": "2025-01-05", "description": "event"},
            [
                {
                    "line_no": 1,
                    "account_code": "1002",
                    "account_name": "Bank",
                    "debit_amount": 200,
                    "credit_amount": 0,
                },
                {
                    "line_no": 2,
                    "account_code": "2001",
                    "account_name": "Loan",
                    "debit_amount": 0,
                    "credit_amount": 200,
                },
            ],
            "reviewed",
        )
        confirm_voucher(conn, voucher_id)
        inventory_move_in(conn, "W1", 5, 10, "2025-01-10")
        close_period(conn, period)

        rows = conn.execute("SELECT event_type FROM webhook_events").fetchall()
        types = {row["event_type"] for row in rows}
        assert "voucher.created" in types
        assert "voucher.confirmed" in types
        assert "inventory.move_in" in types
        assert "period.closed" in types
