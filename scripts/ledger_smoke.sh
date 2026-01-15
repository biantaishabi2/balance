#!/usr/bin/env bash
# Minimal smoke test for ledger CLI.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB="/tmp/ledger_test.db"
rm -f "$DB"

echo "[smoke] ledger init"
python3 "$ROOT/ledger.py" init --db-path "$DB"

echo "[smoke] ledger account list"
python3 "$ROOT/ledger.py" account list --db-path "$DB" >/dev/null

echo "[smoke] ledger dimensions add"
python3 "$ROOT/ledger.py" dimensions add --db-path "$DB" <<'JSON' >/dev/null
{"type": "department", "code": "D001", "name": "销售部"}
JSON

echo "[smoke] ledger record (draft)"
python3 "$ROOT/ledger.py" record --db-path "$DB" <<'JSON' >/dev/null
{
  "date": "2025-01-15",
  "description": "测试凭证",
  "entries": [
    {"account": "库存现金", "debit": 1000},
    {"account": "银行存款", "credit": 1000}
  ]
}
JSON

echo "[smoke] ledger confirm"
python3 "$ROOT/ledger.py" confirm 1 --db-path "$DB" >/dev/null

echo "[smoke] ledger query balances"
python3 "$ROOT/ledger.py" query balances --period 2025-01 --db-path "$DB" >/dev/null

echo "[smoke] ledger report"
python3 "$ROOT/ledger.py" report --period 2025-01 --db-path "$DB" >/dev/null

echo "[smoke] ledger void"
python3 "$ROOT/ledger.py" void 1 --reason "测试" --db-path "$DB" >/dev/null

echo "[smoke] OK"
