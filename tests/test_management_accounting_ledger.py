import pytest

import ledger.services as services
from ledger.database import get_db, init_db
from ledger.services import (
    budget_variance,
    build_entries,
    confirm_voucher,
    create_allocation_rule,
    insert_voucher,
    load_standard_accounts,
    run_allocation,
    set_budget,
)
from ledger.utils import LedgerError


def _seed_dimension(conn, dim_type: str, code: str, name: str) -> None:
    conn.execute(
        "INSERT INTO dimensions (type, code, name, is_enabled) VALUES (?, ?, ?, 1)",
        (dim_type, code, name),
    )


def _record_voucher(conn, date: str, description: str, entries_data):
    entries, _, _ = build_entries(conn, entries_data, date)
    voucher_id, _, _, _ = insert_voucher(
        conn,
        {"date": date, "description": description},
        entries,
        "reviewed",
    )
    confirm_voucher(conn, voucher_id)
    return voucher_id


def test_allocation_revenue_basis(tmp_path):
    db_path = tmp_path / "ledger.db"
    accounts = [
        {"code": "1001", "name": "Cash", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "6001", "name": "Revenue", "level": 1, "type": "revenue", "direction": "credit"},
        {"code": "6601", "name": "Admin", "level": 1, "type": "expense", "direction": "debit"},
    ]

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, accounts)
        _seed_dimension(conn, "department", "D-A", "Dept A")
        _seed_dimension(conn, "department", "D-B", "Dept B")
        dept_rows = conn.execute(
            "SELECT id, code FROM dimensions WHERE type = 'department' ORDER BY code"
        ).fetchall()
        dept_a = dept_rows[0]["id"]
        dept_b = dept_rows[1]["id"]
        dept_a_code = dept_rows[0]["code"]
        dept_b_code = dept_rows[1]["code"]

        _record_voucher(
            conn,
            "2025-01-05",
            "rev A",
            [
                {"account": "1001", "debit": 3000, "credit": 0, "department": dept_a_code},
                {"account": "6001", "debit": 0, "credit": 3000, "department": dept_a_code},
            ],
        )
        _record_voucher(
            conn,
            "2025-01-06",
            "rev B",
            [
                {"account": "1001", "debit": 1000, "credit": 0, "department": dept_b_code},
                {"account": "6001", "debit": 0, "credit": 1000, "department": dept_b_code},
            ],
        )
        _record_voucher(
            conn,
            "2025-01-10",
            "pool",
            [
                {"account": "6601", "debit": 1000, "credit": 0},
                {"account": "1001", "debit": 0, "credit": 1000},
            ],
        )

        rule = create_allocation_rule(
            conn,
            "Admin Allocation",
            ["6601"],
            "department",
            "revenue",
            "2025-01",
        )
        result = run_allocation(conn, rule["rule_id"], "2025-01")
        rows = conn.execute(
            "SELECT account_code, debit_amount, credit_amount, dept_id FROM voucher_entries WHERE voucher_id = ?",
            (result["voucher_id"],),
        ).fetchall()
        debit_by_dept = {row["dept_id"]: row["debit_amount"] for row in rows if row["debit_amount"] > 0}
        credit_total = sum(row["credit_amount"] for row in rows)
        assert credit_total == pytest.approx(1000.0, rel=0.01)
        assert debit_by_dept[dept_a] == pytest.approx(750.0, rel=0.01)
        assert debit_by_dept[dept_b] == pytest.approx(250.0, rel=0.01)


def test_budget_block_and_warn(tmp_path, monkeypatch):
    db_path = tmp_path / "ledger.db"
    accounts = [
        {"code": "1001", "name": "Cash", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "6601", "name": "Admin", "level": 1, "type": "expense", "direction": "debit"},
    ]

    warn_path = tmp_path / "ledger_warn.db"
    with get_db(str(warn_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, accounts)
        _seed_dimension(conn, "department", "D-A", "Dept A")
        set_budget(conn, "2025-01", "department", "D-A", 500)
        entries, _, _ = build_entries(
            conn,
            [
                {"account": "6601", "debit": 600, "credit": 0, "department": "D-A"},
                {"account": "1001", "debit": 0, "credit": 600},
            ],
            "2025-01-15",
        )
        voucher_id, _, _, _ = insert_voucher(
            conn,
            {"date": "2025-01-15", "description": "expense"},
            entries,
            "reviewed",
        )
        monkeypatch.setattr(services, "_load_budget_config", lambda: {"mode": "block"})
        with pytest.raises(LedgerError) as exc:
            confirm_voucher(conn, voucher_id)
        assert exc.value.code == "BUDGET_EXCEEDED"

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, accounts)
        _seed_dimension(conn, "department", "D-A", "Dept A")
        set_budget(conn, "2025-01", "department", "D-A", 500)
        entries, _, _ = build_entries(
            conn,
            [
                {"account": "6601", "debit": 600, "credit": 0, "department": "D-A"},
                {"account": "1001", "debit": 0, "credit": 600},
            ],
            "2025-01-15",
        )
        voucher_id, _, _, _ = insert_voucher(
            conn,
            {"date": "2025-01-15", "description": "expense"},
            entries,
            "reviewed",
        )
        monkeypatch.setattr(services, "_load_budget_config", lambda: {"mode": "warn"})
        voucher = confirm_voucher(conn, voucher_id)
        assert voucher.get("budget_warnings")


def test_budget_variance(tmp_path):
    db_path = tmp_path / "ledger.db"
    accounts = [
        {"code": "1001", "name": "Cash", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "6601", "name": "Admin", "level": 1, "type": "expense", "direction": "debit"},
    ]

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, accounts)
        _seed_dimension(conn, "department", "D-A", "Dept A")
        set_budget(conn, "2025-01", "department", "D-A", 1000)
        _record_voucher(
            conn,
            "2025-01-20",
            "expense",
            [
                {"account": "6601", "debit": 800, "credit": 0, "department": "D-A"},
                {"account": "1001", "debit": 0, "credit": 800},
            ],
        )
        variance = budget_variance(conn, "2025-01", "department", "D-A")
        assert variance["variance"] == pytest.approx(200.0, rel=0.01)
