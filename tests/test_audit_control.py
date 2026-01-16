import pytest

from ledger.database import get_db, init_db
from ledger.commands import delete as delete_cmd
from ledger.services import (
    add_audit_rule,
    approve_approval,
    close_period,
    confirm_voucher,
    fetch_approval,
    insert_voucher,
    load_standard_accounts,
    reopen_period,
    review_voucher,
)
from types import SimpleNamespace


BASIC_ACCOUNTS = [
    {"code": "1001", "name": "Cash", "level": 1, "type": "asset", "direction": "debit"},
    {"code": "2001", "name": "Loan", "level": 1, "type": "liability", "direction": "credit"},
    {"code": "4103", "name": "Current Profit", "level": 1, "type": "equity", "direction": "credit"},
    {"code": "4104", "name": "Retained Profit", "level": 1, "type": "equity", "direction": "credit"},
]


def _create_voucher(conn, amount=1000.0):
    return insert_voucher(
        conn,
        {"date": "2025-01-05", "description": "test"},
        [
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
        ],
        "draft",
    )


def test_audit_logs_written(tmp_path):
    db_path = tmp_path / "ledger.db"

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, BASIC_ACCOUNTS)
        voucher_id, _, _, _ = _create_voucher(conn, amount=500.0)
        review_voucher(conn, voucher_id)
        confirm_voucher(conn, voucher_id)
        close_period(conn, "2025-01")

        rows = conn.execute(
            "SELECT action, actor_type, actor_id, tenant_id, request_id FROM audit_logs"
        ).fetchall()
        actions = {row["action"] for row in rows}
        assert "voucher.create" in actions
        assert "voucher.post" in actions
        assert "period.close" in actions
        for row in rows:
            assert row["actor_type"]
            assert row["actor_id"]
            assert row["tenant_id"]
            assert row["request_id"]


def test_approval_flow(tmp_path):
    db_path = tmp_path / "ledger.db"

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, BASIC_ACCOUNTS)
        voucher_id, _, _, _ = _create_voucher(conn, amount=200.0)
        review_voucher(conn, voucher_id)
        approval = fetch_approval(conn, "voucher", voucher_id)
        assert approval is not None
        assert approval["status"] == "pending"

        approved = approve_approval(conn, "voucher", voucher_id)
        assert approved["status"] == "approved"


def test_audit_rules_trigger_warning(tmp_path):
    db_path = tmp_path / "ledger.db"

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, BASIC_ACCOUNTS)
        add_audit_rule(
            conn,
            "AMOUNT_HIGH",
            "Large amount",
            {"expr": "total_debit > 300", "message": "Large voucher"},
        )
        voucher_id, _, _, _ = _create_voucher(conn, amount=500.0)
        review_voucher(conn, voucher_id)
        result = confirm_voucher(conn, voucher_id)
        assert "Large voucher" in result.get("audit_warnings", [])


def test_delete_and_reopen_audit_logs(tmp_path):
    db_path = tmp_path / "ledger.db"

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, BASIC_ACCOUNTS)
        voucher_id, _, _, _ = _create_voucher(conn, amount=100.0)
        conn.commit()
        args = SimpleNamespace(db_path=str(db_path), voucher_id=voucher_id)
        delete_cmd.run(args)

        log_row = conn.execute(
            "SELECT action FROM audit_logs WHERE action = 'ledger.delete'"
        ).fetchone()
        assert log_row is not None

        voucher_id, _, _, _ = _create_voucher(conn, amount=300.0)
        review_voucher(conn, voucher_id)
        confirm_voucher(conn, voucher_id)
        close_period(conn, "2025-01")
        reopen_period(conn, "2025-01")

        approval_close = fetch_approval(conn, "period_close", "2025-01")
        approval_reopen = fetch_approval(conn, "period_reopen", "2025-01")
        assert approval_close["status"] == "approved"
        assert approval_reopen["status"] == "approved"

        reopen_log = conn.execute(
            "SELECT action FROM audit_logs WHERE action = 'period.reopen'"
        ).fetchone()
        assert reopen_log is not None
