import pytest

import ledger.services as services
from ledger.database import get_db, init_db
from ledger.services import (
    add_ar_item,
    add_bill,
    add_cip_cost,
    add_fixed_asset,
    create_cip_project,
    create_payment_plan,
    depreciate_assets,
    impair_fixed_asset,
    inventory_move_in,
    inventory_move_out,
    load_standard_accounts,
    provision_bad_debt,
    reverse_bad_debt,
    set_credit_profile,
    set_standard_cost,
    settle_payment_plan,
    split_fixed_asset,
    transfer_cip_to_asset,
    transfer_fixed_asset,
    update_bill_status,
    upgrade_fixed_asset,
)


def _seed_dimension(conn, dim_type: str, code: str, name: str) -> None:
    conn.execute(
        "INSERT INTO dimensions (type, code, name, is_enabled) VALUES (?, ?, ?, 1)",
        (dim_type, code, name),
    )


def test_credit_and_payment_plan(tmp_path):
    db_path = tmp_path / "ledger.db"
    accounts = [
        {"code": "1002", "name": "Bank", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "1122", "name": "AR", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "6001", "name": "Revenue", "level": 1, "type": "revenue", "direction": "credit"},
    ]

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, accounts)
        _seed_dimension(conn, "customer", "C100", "Cust")
        set_credit_profile(conn, "customer", "C100", 500, 30)

        item = add_ar_item(conn, "C100", 400, "2025-01-10", "sale")
        row = conn.execute("SELECT credit_used FROM dimensions WHERE code = 'C100'").fetchone()
        assert row["credit_used"] == pytest.approx(400.0, rel=0.01)

        add_ar_item(conn, "C100", 200, "2025-01-12", "sale")
        row = conn.execute("SELECT credit_used FROM dimensions WHERE code = 'C100'").fetchone()
        assert row["credit_used"] == pytest.approx(600.0, rel=0.01)

        plan = create_payment_plan(conn, "ar", item["item_id"], "2025-01-20", 400)
        settle_payment_plan(conn, plan["plan_id"], "2025-01-20")
        plan_row = conn.execute("SELECT status FROM payment_plans WHERE id = ?", (plan["plan_id"],)).fetchone()
        assert plan_row["status"] == "settled"


def test_bill_and_bad_debt(tmp_path):
    db_path = tmp_path / "ledger.db"
    accounts = [
        {"code": "1002", "name": "Bank", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "1122", "name": "AR", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "1123", "name": "Bill AR", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "6702", "name": "Bad Debt", "level": 1, "type": "expense", "direction": "debit"},
        {"code": "1231", "name": "Bad Debt Reserve", "level": 1, "type": "asset", "direction": "credit"},
        {"code": "6001", "name": "Revenue", "level": 1, "type": "revenue", "direction": "credit"},
    ]

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, accounts)
        _seed_dimension(conn, "customer", "C200", "Cust")

        add_bill(conn, "B001", "ar", 300, "2025-01-10")
        row = conn.execute("SELECT status FROM bills WHERE bill_no = 'B001'").fetchone()
        assert row["status"] == "holding"

        update_bill_status(conn, "B001", "endorsed", "2025-01-15")
        row = conn.execute("SELECT status, voucher_id FROM bills WHERE bill_no = 'B001'").fetchone()
        assert row["status"] == "endorsed"
        assert row["voucher_id"] is not None

        provision_bad_debt(conn, "2025-01", "C200", 50)
        reverse_bad_debt(conn, "2025-02", "C200", 20)
        row = conn.execute("SELECT COUNT(*) AS cnt FROM bad_debt_provisions").fetchone()
        assert row["cnt"] == 2


def test_inventory_fifo_and_standard(tmp_path):
    db_path = tmp_path / "ledger.db"
    accounts = [
        {"code": "1002", "name": "Bank", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "1403", "name": "Inventory", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "6401", "name": "COGS", "level": 1, "type": "expense", "direction": "debit"},
        {"code": "6403", "name": "Variance", "level": 1, "type": "expense", "direction": "debit"},
        {"code": "6051", "name": "Gain", "level": 1, "type": "revenue", "direction": "credit"},
        {"code": "6605", "name": "Loss", "level": 1, "type": "expense", "direction": "debit"},
    ]

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, accounts)

        inventory_move_in(conn, "A1", 10, 10, "2025-01-01", cost_method="fifo")
        inventory_move_in(conn, "A1", 5, 12, "2025-01-05", cost_method="fifo")
        out = inventory_move_out(conn, "A1", 12, "2025-01-10", cost_method="fifo")
        entries = conn.execute(
            "SELECT account_code, debit_amount, credit_amount FROM voucher_entries WHERE voucher_id = ?",
            (out["voucher_id"],),
        ).fetchall()
        entries_map = {row["account_code"]: row for row in entries}
        assert entries_map["6401"]["debit_amount"] == pytest.approx(124.0, rel=0.01)

        set_standard_cost(conn, "B1", "2025-01", 10, "6403")
        result = inventory_move_in(conn, "B1", 10, 12, "2025-01-02", cost_method="standard")
        entries = conn.execute(
            "SELECT account_code, debit_amount, credit_amount FROM voucher_entries WHERE voucher_id = ?",
            (result["voucher_id"],),
        ).fetchall()
        entries_map = {row["account_code"]: row for row in entries}
        assert entries_map["1403"]["debit_amount"] == pytest.approx(100.0, rel=0.01)
        assert entries_map["6403"]["debit_amount"] == pytest.approx(20.0, rel=0.01)
        assert entries_map["1002"]["credit_amount"] == pytest.approx(120.0, rel=0.01)


def test_fixed_asset_upgrade_impair_cip(tmp_path):
    db_path = tmp_path / "ledger.db"
    accounts = [
        {"code": "1002", "name": "Bank", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "1601", "name": "FA", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "1602", "name": "Accum", "level": 1, "type": "asset", "direction": "credit"},
        {"code": "1603", "name": "Impairment", "level": 1, "type": "asset", "direction": "credit"},
        {"code": "1604", "name": "CIP", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "6602", "name": "Expense", "level": 1, "type": "expense", "direction": "debit"},
        {"code": "6701", "name": "Impair Loss", "level": 1, "type": "expense", "direction": "debit"},
    ]

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, accounts)

        asset = add_fixed_asset(conn, "Machine", 1000, 5, 0, "2025-01-01")
        upgrade_fixed_asset(conn, asset["asset_id"], 200, "2025-01-02")
        row = conn.execute("SELECT cost FROM fixed_assets WHERE id = ?", (asset["asset_id"],)).fetchone()
        assert row["cost"] == pytest.approx(1200.0, rel=0.01)

        impair_fixed_asset(conn, asset["asset_id"], "2025-01", 100)
        imp_row = conn.execute("SELECT COUNT(*) AS cnt FROM fixed_asset_impairments").fetchone()
        assert imp_row["cnt"] == 1

        transfer_fixed_asset(conn, asset["asset_id"], None, None, "2025-01-03")
        change_row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM fixed_asset_changes WHERE asset_id = ? AND change_type = 'transfer'",
            (asset["asset_id"],),
        ).fetchone()
        assert change_row["cnt"] == 1

        split_result = split_fixed_asset(conn, asset["asset_id"], [6, 4])
        assert len(split_result["new_asset_ids"]) == 1
        split_row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM fixed_asset_changes WHERE asset_id = ? AND change_type = 'split'",
            (asset["asset_id"],),
        ).fetchone()
        assert split_row["cnt"] == 1

        project_id = create_cip_project(conn, "Plant")
        add_cip_cost(conn, project_id, 500, "2025-01-05")
        partial = transfer_cip_to_asset(conn, project_id, "Plant Asset A", 10, 0, "2025-01-10", amount=200)
        assert partial["asset_id"] is not None
        project = conn.execute(
            "SELECT status, cost FROM cip_projects WHERE id = ?",
            (project_id,),
        ).fetchone()
        assert project["status"] == "ongoing"
        assert project["cost"] == pytest.approx(300.0, rel=0.01)

        transfer = transfer_cip_to_asset(conn, project_id, "Plant Asset B", 10, 0, "2025-01-15", amount=300)
        assert transfer["asset_id"] is not None
        project = conn.execute("SELECT status, cost FROM cip_projects WHERE id = ?", (project_id,)).fetchone()
        assert project["status"] == "converted"
        assert project["cost"] == pytest.approx(0.0, rel=0.01)


def test_depreciation_allocation_basis(tmp_path):
    db_path = tmp_path / "ledger.db"
    accounts = [
        {"code": "1002", "name": "Bank", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "1601", "name": "FA", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "1602", "name": "Accum", "level": 1, "type": "asset", "direction": "credit"},
        {"code": "6602", "name": "Expense", "level": 1, "type": "expense", "direction": "debit"},
    ]

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, accounts)
        _seed_dimension(conn, "department", "D100", "Dept A")
        _seed_dimension(conn, "department", "D200", "Dept B")
        dept_rows = conn.execute(
            "SELECT id, code FROM dimensions WHERE type = 'department' ORDER BY code"
        ).fetchall()
        dept_id_a = dept_rows[0]["id"]
        dept_id_b = dept_rows[1]["id"]

        add_fixed_asset(conn, "Line", 1200, 1, 0, "2025-01-01")
        conn.execute(
            """
            INSERT INTO allocation_basis_values (period, dim_type, dim_id, value)
            VALUES (?, 'department', ?, ?)
            """,
            ("2025-01", dept_id_a, 60),
        )
        conn.execute(
            """
            INSERT INTO allocation_basis_values (period, dim_type, dim_id, value)
            VALUES (?, 'department', ?, ?)
            """,
            ("2025-01", dept_id_b, 40),
        )

        result = depreciate_assets(conn, "2025-01")
        entries = conn.execute(
            """
            SELECT account_code, debit_amount, dept_id
            FROM voucher_entries
            WHERE voucher_id = ?
            """,
            (result["voucher_id"],),
        ).fetchall()
        dept_map = {row["dept_id"]: row for row in entries if row["account_code"] == "6602"}
        assert dept_map[dept_id_a]["debit_amount"] == pytest.approx(60.0, rel=0.01)
        assert dept_map[dept_id_b]["debit_amount"] == pytest.approx(40.0, rel=0.01)


def test_inventory_negative_allow_adjustment(tmp_path, monkeypatch):
    db_path = tmp_path / "ledger.db"
    accounts = [
        {"code": "1002", "name": "Bank", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "1403", "name": "Inventory", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "6401", "name": "COGS", "level": 1, "type": "expense", "direction": "debit"},
    ]

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, accounts)
        monkeypatch.setattr(
            services, "_load_inventory_config", lambda: {"cost_method": "avg", "negative_policy": "allow"}
        )

        inventory_move_in(conn, "C1", 2, 10, "2025-01-01")
        inventory_move_out(conn, "C1", 3, "2025-01-05")
        inventory_move_in(conn, "C1", 1, 12, "2025-01-10")

        balance = conn.execute(
            "SELECT qty, amount FROM inventory_balances WHERE sku = ? AND period = ?",
            ("C1", "2025-01"),
        ).fetchone()
        assert balance["qty"] == pytest.approx(0.0, rel=0.01)
        assert balance["amount"] == pytest.approx(0.0, rel=0.01)
        voucher_row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM vouchers WHERE description = '负库存成本调整'"
        ).fetchone()
        assert voucher_row["cnt"] == 1
