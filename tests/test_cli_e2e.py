import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "ledger.py"


def run_cli(args, db_path, input_data=None, expect_ok=True):
    cmd = [sys.executable, str(LEDGER), *args, "--db-path", str(db_path)]
    payload = json.dumps(input_data) if input_data is not None else None
    result = subprocess.run(
        cmd,
        input=payload,
        text=True,
        capture_output=True,
    )
    if expect_ok:
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        assert result.returncode != 0, result.stdout + result.stderr
    output = result.stdout.strip()
    return json.loads(output) if output else {}


def test_cli_close_flow(tmp_path):
    db_path = tmp_path / "ledger.db"

    run_cli(["init"], db_path)

    record_payload = {
        "date": "2025-01-15",
        "description": "cli",
        "entries": [
            {"account": "1001", "debit": 100},
            {"account": "1002", "credit": 100},
        ],
    }
    draft = run_cli(["record"], db_path, input_data=record_payload)
    assert draft["status"] == "draft"

    run_cli(["review", "1"], db_path)
    run_cli(["confirm", "1"], db_path)
    run_cli(["close", "--period", "2025-01"], db_path)

    denied = run_cli(
        ["record"],
        db_path,
        input_data={
            "date": "2025-01-20",
            "description": "closed",
            "entries": [
                {"account": "1001", "debit": 50},
                {"account": "1002", "credit": 50},
            ],
        },
        expect_ok=False,
    )
    assert denied["code"] == "PERIOD_CLOSED"

    run_cli(["reopen", "--period", "2025-01"], db_path)
    reopened = run_cli(["record"], db_path, input_data=record_payload)
    assert reopened["status"] == "draft"


def test_cli_ar_ap_reconcile(tmp_path):
    db_path = tmp_path / "ledger.db"

    run_cli(["init"], db_path)

    run_cli(
        ["dimensions", "add"],
        db_path,
        input_data={"type": "customer", "code": "C001", "name": "Customer"},
    )
    run_cli(
        ["dimensions", "add"],
        db_path,
        input_data={"type": "supplier", "code": "S001", "name": "Supplier"},
    )

    run_cli(["ar", "add", "--customer", "C001", "--amount", "1000", "--date", "2025-01-10"], db_path)
    ar_recon = run_cli(["ar", "reconcile", "--period", "2025-01", "--customer", "C001"], db_path)
    assert ar_recon["difference"] == pytest.approx(0.0, rel=0.01)

    run_cli(["ap", "add", "--supplier", "S001", "--amount", "800", "--date", "2025-01-12"], db_path)
    ap_recon = run_cli(["ap", "reconcile", "--period", "2025-01", "--supplier", "S001"], db_path)
    assert ap_recon["difference"] == pytest.approx(0.0, rel=0.01)

def test_cli_inventory_fa_reconcile(tmp_path):
    db_path = tmp_path / "ledger.db"

    run_cli(["init"], db_path)

    run_cli(
        ["inventory", "in", "--sku", "A001", "--qty", "10", "--unit-cost", "50", "--date", "2025-01-15"],
        db_path,
    )
    run_cli(
        ["inventory", "out", "--sku", "A001", "--qty", "4", "--date", "2025-01-20"],
        db_path,
    )
    inv_recon = run_cli(["inventory", "reconcile", "--period", "2025-01"], db_path)
    assert inv_recon["difference"] == pytest.approx(0.0, rel=0.01)

    run_cli(
        [
            "fixed-asset",
            "add",
            "--name",
            "Machine",
            "--cost",
            "12000",
            "--life",
            "3",
            "--salvage",
            "2000",
            "--date",
            "2025-01-05",
        ],
        db_path,
    )
    run_cli(["fixed-asset", "depreciate", "--period", "2025-01"], db_path)
    fa_recon = run_cli(["fixed-asset", "reconcile", "--period", "2025-01"], db_path)
    assert fa_recon["asset_difference"] == pytest.approx(0.0, rel=0.01)
    assert fa_recon["accum_difference"] == pytest.approx(0.0, rel=0.01)

    assets = run_cli(["fixed-asset", "list", "--period", "2025-01"], db_path)
    assert assets["items"]
