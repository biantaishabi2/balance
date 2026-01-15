from ledger.database import get_db, init_db
from ledger.reporting_engine import generate_ledger_statements
from ledger.services import insert_voucher, load_standard_accounts, update_balance_for_voucher


def test_generate_ledger_statements(tmp_path):
    db_path = tmp_path / "ledger.db"
    accounts = [
        {"code": "1001", "name": "库存现金", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "6001", "name": "主营业务收入", "level": 1, "type": "revenue", "direction": "credit"},
    ]

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, accounts)
        voucher_id, _, period, _ = insert_voucher(
            conn,
            {"date": "2025-01-15", "description": "测试"},
            [
                {
                    "line_no": 1,
                    "account_code": "1001",
                    "account_name": "库存现金",
                    "debit_amount": 1000,
                    "credit_amount": 0,
                },
                {
                    "line_no": 2,
                    "account_code": "6001",
                    "account_name": "主营业务收入",
                    "debit_amount": 0,
                    "credit_amount": 1000,
                },
            ],
            "confirmed",
        )
        update_balance_for_voucher(conn, voucher_id, period)
        report = generate_ledger_statements(conn, period)

    assert report["balance_sheet"]["total_assets"] == 1000
    assert report["balance_sheet"]["total_liabilities"] == 0
    assert report["balance_sheet"]["total_equity"] == 1000
    assert report["income_statement"]["revenue"] == 1000
    assert report["income_statement"]["cost"] == 0
    assert report["income_statement"]["net_income"] == 1000
    assert report["cash_flow_statement"]["net_change"] == 1000
    assert report["is_balanced"] is True
