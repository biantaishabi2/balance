import pytest

from ledger.database import get_db, init_db
from ledger.services import (
    add_ap_item,
    add_ar_item,
    add_fixed_asset,
    ap_aging,
    depreciate_assets,
    dispose_fixed_asset,
    inventory_balance,
    inventory_move_in,
    inventory_move_out,
    list_ap_items,
    list_ar_items,
    load_standard_accounts,
    reconcile_ap,
    reconcile_ar,
    reconcile_fixed_assets,
    reconcile_inventory,
    settle_ap_item,
    settle_ar_item,
)


def _seed_dimension(conn, dim_type: str, code: str, name: str) -> None:
    conn.execute(
        "INSERT INTO dimensions (type, code, name, is_enabled) VALUES (?, ?, ?, 1)",
        (dim_type, code, name),
    )


def _get_balance(conn, account_code: str, period: str) -> float:
    row = conn.execute(
        "SELECT closing_balance FROM balances WHERE account_code = ? AND period = ?",
        (account_code, period),
    ).fetchone()
    return float(row["closing_balance"]) if row else 0.0


def test_ar_add_settle(tmp_path):
    db_path = tmp_path / "ledger.db"
    accounts = [
        {"code": "1002", "name": "Bank", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "1122", "name": "AR", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "6001", "name": "Revenue", "level": 1, "type": "revenue", "direction": "credit"},
    ]

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, accounts)
        _seed_dimension(conn, "customer", "C001", "Customer A")

        result = add_ar_item(conn, "C001", 1000, "2025-01-10", "sale")
        items = list_ar_items(conn, "open", "2025-01", "C001")
        assert len(items) == 1
        settle_ar_item(conn, result["item_id"], 1000, "2025-01-20", "collect")

        settlements = conn.execute(
            "SELECT COUNT(*) AS cnt FROM settlements WHERE item_type = 'ar'"
        ).fetchone()
        assert settlements["cnt"] == 1

        balance = _get_balance(conn, "1122", "2025-01")
        assert balance == pytest.approx(0.0, rel=0.01)


def test_ap_add_settle(tmp_path):
    db_path = tmp_path / "ledger.db"
    accounts = [
        {"code": "1002", "name": "Bank", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "1403", "name": "Inventory", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "2202", "name": "AP", "level": 1, "type": "liability", "direction": "credit"},
    ]

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, accounts)
        _seed_dimension(conn, "supplier", "S001", "Supplier A")

        result = add_ap_item(conn, "S001", 800, "2025-01-05", "purchase")
        items = list_ap_items(conn, "open", "2025-01", "S001")
        assert len(items) == 1
        settle_ap_item(conn, result["item_id"], 800, "2025-01-25", "pay")

        settlements = conn.execute(
            "SELECT COUNT(*) AS cnt FROM settlements WHERE item_type = 'ap'"
        ).fetchone()
        assert settlements["cnt"] == 1

        balance = _get_balance(conn, "2202", "2025-01")
        assert balance == pytest.approx(0.0, rel=0.01)


def test_inventory_moves(tmp_path):
    db_path = tmp_path / "ledger.db"
    accounts = [
        {"code": "1002", "name": "Bank", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "1403", "name": "Inventory", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "6401", "name": "COGS", "level": 1, "type": "expense", "direction": "debit"},
    ]

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, accounts)

        inventory_move_in(conn, "A001", 10, 50, "2025-01-12", "inbound", "Item A", "pcs")
        out_result = inventory_move_out(conn, "A001", 4, "2025-01-20", "outbound")

        balances = inventory_balance(conn, "2025-01", "A001")
        assert balances[0]["qty"] == pytest.approx(6.0, rel=0.01)
        assert balances[0]["amount"] == pytest.approx(300.0, rel=0.01)

        ledger_balance = _get_balance(conn, "1403", "2025-01")
        assert ledger_balance == pytest.approx(300.0, rel=0.01)

        entries = conn.execute(
            "SELECT account_code, debit_amount, credit_amount FROM voucher_entries WHERE voucher_id = ?",
            (out_result["voucher_id"],),
        ).fetchall()
        entries_map = {row["account_code"]: row for row in entries}
        assert entries_map["6401"]["debit_amount"] == pytest.approx(200.0, rel=0.01)
        assert entries_map["1403"]["credit_amount"] == pytest.approx(200.0, rel=0.01)


def test_fixed_asset_depreciation_and_dispose(tmp_path):
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

        result = add_fixed_asset(conn, "Machine", 12000, 3, 2000, "2025-01-05")
        depr = depreciate_assets(conn, "2025-01")
        expected = round((12000 - 2000) / 36, 2)
        assert depr["total_amount"] == pytest.approx(expected, rel=0.01)

        accum_balance = _get_balance(conn, "1602", "2025-01")
        expense_balance = _get_balance(conn, "6602", "2025-01")
        assert accum_balance == pytest.approx(expected, rel=0.01)
        assert expense_balance == pytest.approx(expected, rel=0.01)

        dispose_fixed_asset(conn, result["asset_id"], "2025-02-01")
        asset_balance = _get_balance(conn, "1601", "2025-02")
        assert asset_balance == pytest.approx(0.0, rel=0.01)


def test_ap_aging(tmp_path):
    db_path = tmp_path / "ledger.db"
    accounts = [
        {"code": "1002", "name": "Bank", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "1403", "name": "Inventory", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "2202", "name": "AP", "level": 1, "type": "liability", "direction": "credit"},
    ]

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, accounts)
        _seed_dimension(conn, "supplier", "S002", "Supplier B")

        add_ap_item(conn, "S002", 500, "2025-01-03", "purchase")
        aging = ap_aging(conn, "2025-01-20")
        assert aging["0_30"] == pytest.approx(500.0, rel=0.01)


def test_reconcile_ar_ap(tmp_path):
    db_path = tmp_path / "ledger.db"
    accounts = [
        {"code": "1002", "name": "Bank", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "1122", "name": "AR", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "2202", "name": "AP", "level": 1, "type": "liability", "direction": "credit"},
        {"code": "6001", "name": "Revenue", "level": 1, "type": "revenue", "direction": "credit"},
        {"code": "1403", "name": "Inventory", "level": 1, "type": "asset", "direction": "debit"},
    ]

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, accounts)
        _seed_dimension(conn, "customer", "C010", "Customer X")
        _seed_dimension(conn, "supplier", "S010", "Supplier X")

        add_ar_item(conn, "C010", 300, "2025-01-10", "sale")
        add_ap_item(conn, "S010", 200, "2025-01-12", "purchase")

        ar_recon = reconcile_ar(conn, "2025-01", "C010")
        assert ar_recon["difference"] == pytest.approx(0.0, rel=0.01)

        ap_recon = reconcile_ap(conn, "2025-01", "S010")
        assert ap_recon["difference"] == pytest.approx(0.0, rel=0.01)

def test_reconcile_inventory(tmp_path):
    db_path = tmp_path / "ledger.db"
    accounts = [
        {"code": "1002", "name": "Bank", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "1403", "name": "Inventory", "level": 1, "type": "asset", "direction": "debit"},
        {"code": "6401", "name": "COGS", "level": 1, "type": "expense", "direction": "debit"},
    ]

    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, accounts)
        inventory_move_in(conn, "A100", 5, 20, "2025-01-15", "in")
        inventory_move_out(conn, "A100", 2, "2025-01-20", "out")

        inv_recon = reconcile_inventory(conn, "2025-01")
        assert inv_recon["difference"] == pytest.approx(0.0, rel=0.01)


def test_reconcile_fixed_assets(tmp_path):
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
        add_fixed_asset(conn, "Tool", 600, 3, 0, "2025-01-05")
        depreciate_assets(conn, "2025-01")

        fa_recon = reconcile_fixed_assets(conn, "2025-01")
        assert fa_recon["asset_difference"] == pytest.approx(0.0, rel=0.01)
        assert fa_recon["accum_difference"] == pytest.approx(0.0, rel=0.01)
