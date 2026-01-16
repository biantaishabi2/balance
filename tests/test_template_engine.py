import pytest

from ledger.database import get_db, init_db
from ledger.services import (
    add_voucher_template,
    generate_voucher_from_template,
    disable_voucher_template,
    load_standard_accounts,
)
from ledger.utils import LedgerError


def test_template_generate_and_disable(tmp_path):
    db_path = tmp_path / "ledger.db"
    accounts = [
        {"code": "1001", "name": "Cash", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "6001", "name": "Revenue", "level": 1, "type": "revenue", "direction": "credit"},
    ]
    rule = {
        "header": {"description": "cash in", "date_field": "date"},
        "lines": [
            {"account": "1001", "debit": "amount", "credit": "0"},
            {"account": "6001", "debit": "0", "credit": "amount"},
        ],
    }

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, accounts)
        add_voucher_template(conn, "cash_in", "Cash In", rule)
        result = generate_voucher_from_template(
            conn,
            "cash_in",
            {"amount": 100, "date": "2025-01-05"},
        )
        assert result["voucher_id"] is not None

        disable_voucher_template(conn, "cash_in")
        with pytest.raises(LedgerError) as exc:
            generate_voucher_from_template(
                conn,
                "cash_in",
                {"amount": 50, "date": "2025-01-06"},
            )
        assert exc.value.code == "TEMPLATE_DISABLED"
