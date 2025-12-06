#!/usr/bin/env bash
# Minimal smoke test for key CLIs (no external deps).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[smoke] balance calc"
python3 "$ROOT/balance.py" calc --compact < "$ROOT/examples/input.json" >/dev/null

echo "[smoke] balance calc (iterations)"
python3 "$ROOT/balance.py" calc --iterations 3 --compact < "$ROOT/examples/input.json" >/dev/null

echo "[smoke] fa variance"
python3 "$ROOT/fa.py" variance --json <<'JSON' >/dev/null
{"budget":{"收入":1000,"成本":600},"actual":{"收入":1100,"成本":650},"threshold":0.1}
JSON

echo "[smoke] cf forecast"
python3 "$ROOT/cf.py" forecast --json <<'JSON' >/dev/null
{"opening_cash":100,"receivables_schedule":[{"week":1,"amount":80}],"payables_schedule":[{"week":2,"amount":50}],"weeks":4}
JSON

echo "[smoke] tx vat"
python3 "$ROOT/tx.py" vat --json <<'JSON' >/dev/null
{"sales":[{"amount":113000,"rate":0.13}],"purchases":[{"amount":56500,"rate":0.13}],"taxpayer_type":"general"}
JSON

echo "[smoke] ac tb"
python3 "$ROOT/ac.py" tb --json <<'JSON' >/dev/null
{"accounts":[{"code":"1001","name":"现金","debit":500,"credit":0},{"code":"2001","name":"应付账款","debit":0,"credit":500}],"tolerance":0.01}
JSON

echo "[smoke] ma cvp"
python3 "$ROOT/ma.py" cvp --json <<'JSON' >/dev/null
{"selling_price":100,"variable_cost":60,"fixed_costs":200000,"current_volume":5000,"target_profit":50000}
JSON

echo "[smoke] ri credit"
python3 "$ROOT/ri.py" credit --json <<'JSON' >/dev/null
{"customer_name":"ABC","payment_history":{"on_time_rate":0.95,"avg_days_late":2},"credit_utilization":{"credit_limit":100000,"current_ar":40000},"relationship":{"years":3},"order_frequency":{"orders_per_year":12},"financial_health":{"current_ratio":1.8,"debt_ratio":0.5,"profitable":true}}
JSON

echo "[smoke] kp kpi"
python3 "$ROOT/kp.py" kpi --json <<'JSON' >/dev/null
[{"name":"收入","target":1000000,"actual":950000,"direction":"higher_better","weight":0.3},{"name":"成本率","target":0.6,"actual":0.55,"direction":"lower_better","weight":0.2}]
JSON

echo "[smoke] json2excel"
python3 "$ROOT/json2excel.py" "$ROOT/examples/output.json" /tmp/smoke_output.xlsx >/dev/null

echo "[smoke] excel2json (trial balance CSV)"
cat > /tmp/smoke_tb.csv <<'CSV'
科目代码,科目名称,期初借方,期初贷方,本期借方,本期贷方,期末借方,期末贷方
1001,现金,0,0,0,0,100,0
2001,应付账款,0,50,0,0,0,50
CSV
python3 "$ROOT/excel2json.py" /tmp/smoke_tb.csv --template tb --header 1 >/dev/null

echo "[smoke] excel2json -> balance -> json2excel"
python3 - <<PY
from pathlib import Path
from openpyxl import Workbook
import subprocess
import json

ROOT = Path("$ROOT")
tmp = Path("/tmp/smoke_balance_chain.xlsx")
wb = Workbook()
ws = wb.active
ws.title = "资产负债表"
ws["A1"] = "现金"; ws["B1"] = 5000
ws["A2"] = "固定资产原值"; ws["B2"] = 10000
ws["A3"] = "累计折旧"; ws["B3"] = 0
ws["A4"] = "短期借款"; ws["B4"] = 4000
ws["A5"] = "股本"; ws["B5"] = 6000
ws["A6"] = "留存收益"; ws["B6"] = 1000
ws2 = wb.create_sheet("损益表")
ws2["A1"] = "营业收入"; ws2["B1"] = 20000
ws2["A2"] = "营业成本"; ws2["B2"] = 12000
ws2["A3"] = "其他费用"; ws2["B3"] = 2000
ws3 = wb.create_sheet("参数")
ws3["A1"] = "利率"; ws3["B1"] = 0.05
ws3["A2"] = "税率"; ws3["B2"] = 0.25
ws3["A3"] = "折旧年限"; ws3["B3"] = 5
wb.save(tmp)

excel2json = subprocess.run(
    ["python3", str(ROOT / "excel2json.py"), str(tmp)],
    capture_output=True, text=True, check=True
).stdout
balance = subprocess.run(
    ["python3", str(ROOT / "balance.py"), "calc", "--compact"],
    input=excel2json, capture_output=True, text=True, check=True
).stdout
out_path = "/tmp/smoke_chain_out.xlsx"
subprocess.run(
    ["python3", str(ROOT / "json2excel.py"), "-", out_path],
    input=balance, check=True, text=True
)
PY

echo "[smoke] OK"
