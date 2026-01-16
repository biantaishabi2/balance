import pytest

from ledger.api import LedgerAPI
from ledger.database import get_db, init_db
from ledger.services import load_standard_accounts
from ledger.utils import LedgerError


BASIC_ACCOUNTS = [
    {"code": "1001", "name": "Cash", "level": 1, "type": "asset", "direction": "debit"},
    {"code": "2001", "name": "Short Loan", "level": 1, "type": "liability", "direction": "credit"},
]


def _voucher_entries(amount: float):
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
            "account_name": "Short Loan",
            "debit_amount": 0,
            "credit_amount": amount,
        },
    ]


def test_api_multi_tenant_voucher_flow(tmp_path):
    db_path = tmp_path / "ledger.db"

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, BASIC_ACCOUNTS, tenant_id="t1", org_id="o1")
        load_standard_accounts(conn, BASIC_ACCOUNTS, tenant_id="t2", org_id="o2")

        api = LedgerAPI(conn)
        token_a = api.issue_token("t1", "o1", name="tenant-a")
        token_b = api.issue_token("t2", "o2", name="tenant-b")

        created = api.create_voucher(
            token_a,
            {"date": "2025-01-02", "description": "t1 voucher"},
            _voucher_entries(500),
            status="reviewed",
            auto_confirm=True,
        )
        assert created["status"] == "confirmed"

        fetched = api.get_voucher(token_a, created["voucher_id"])
        assert fetched["voucher_no"] == created["voucher_no"]
        assert fetched["entries"]

        with pytest.raises(LedgerError) as exc:
            api.get_voucher(token_b, created["voucher_id"])
        assert exc.value.code == "VOUCHER_NOT_FOUND"

        archive = api.archive_vouchers(token_a, "2025-01")
        assert archive["voucher_count"] == 1

        assert api.list_vouchers(token_a, include_archived=False) == []
        assert len(api.list_vouchers(token_a, include_archived=True)) == 1
