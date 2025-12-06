# AI 输入/输出对齐与回归样例

供机器人/LLM 调用时参考：用什么模板提取、喂给哪个 CLI、以及可直接运行的最小命令。

## 模板 → CLI 对齐
- trial_balance / tb → `balance calc`（三表配平）、`ac tb`（试算平衡）
- budget → `fa variance`（预算差异）、`fa flex`（弹性预算）
- ar_aging / ap_aging → `ri aging`（账龄分析）、`ri provision`（减值计提）
- voucher → `ac adj`（调整分录建议）
- cash → `cf forecast`（13 周现金流）
- 经营/产品数据（自定义表）→ `ma cvp`/`ma breakeven`/`ma allocate`（本量利、盈亏平衡、成本分摊）
- KPI/绩效（自定义表）→ `kp kpi`/`kp eva`/`kp bsc`/`kp okr`
- 投资模型（自定义表）→ `fm lbo`/`fm dcf`/`fm three`/`fm ratio`

> 推荐用 `excel2json --template ...` 先提取标准 JSON；若字段不直接匹配，调用层按下方示例字段重塑后再喂给目标 CLI。

## 可直接运行的最小样例

### 三表配平（balance）
```
balance calc --compact < examples/input.json
balance calc --iterations 3 --compact < examples/input.json   # 启用融资/利息迭代

# 非收敛示例（高利率+大 min_cash，会跑满迭代仍标记 iteration_converged=false）
python3 balance.py calc --iterations 3 --compact <<'JSON'
{"revenue":0,"cost":0,"opening_cash":0,"opening_debt":100,"interest_rate":1.0,"min_cash":1000}
JSON | tee /tmp/balance_iter_nonconv.json

# 用德尔塔法诊断该结果
python3 balance.py diagnose < /tmp/balance_iter_nonconv.json
```
`examples/input.json`/`examples/output.json` 是一组完整回归样例，可用于对比。

### 预算差异（fa variance）
```
cat <<'JSON' | fa variance --json
{"budget":{"收入":1000,"成本":600},"actual":{"收入":1100,"成本":650},"threshold":0.1}
JSON
```

### 13 周现金流（cf forecast）
```
cat <<'JSON' | cf forecast --json
{"opening_cash":100,"receivables_schedule":[{"week":1,"amount":80}],"payables_schedule":[{"week":2,"amount":50}],"weeks":4}
JSON
```

### 增值税计算（tx vat）
```
cat <<'JSON' | tx vat --json
{"sales":[{"amount":113000,"rate":0.13}],"purchases":[{"amount":56500,"rate":0.13}],"taxpayer_type":"general"}
JSON
```

### 试算平衡（ac tb）
```
cat <<'JSON' | ac tb --json
{"accounts":[{"code":"1001","name":"现金","debit":500,"credit":0},{"code":"2001","name":"应付账款","debit":0,"credit":500}],"tolerance":0.01}
JSON
```

### 客户信用评分（ri credit）
```
cat <<'JSON' | ri credit --json
{"customer_name":"ABC","payment_history":{"on_time_rate":0.95,"avg_days_late":2},"credit_utilization":{"credit_limit":100000,"current_ar":40000},"relationship":{"years":3},"order_frequency":{"orders_per_year":12},"financial_health":{"current_ratio":1.8,"debt_ratio":0.5,"profitable":true}}
JSON
```

### 本量利分析（ma cvp）
```
cat <<'JSON' | ma cvp --json
{"selling_price":100,"variable_cost":60,"fixed_costs":200000,"current_volume":5000,"target_profit":50000}
JSON
```

### KPI 仪表盘（kp kpi）
```
cat <<'JSON' | kp kpi --json
[{"name":"收入","target":1000000,"actual":950000,"direction":"higher_better","weight":0.3},{"name":"成本率","target":0.6,"actual":0.55,"direction":"lower_better","weight":0.2}]
JSON
```

### 账龄分析（ri aging）
```
cat <<'JSON' | ri aging --json
{"as_of_date":"2025-12-31","receivables":[{"customer_name":"A","amount":5000,"days_overdue":45},{"customer_name":"B","amount":8000,"days_overdue":10}]}
JSON
```

### 成本分摊（ma allocate）
```
cat <<'JSON' | ma allocate --json
{"total_cost":100000,"cost_objects":[{"name":"产线A","driver_units":100},{"name":"产线B","driver_units":50}],"method":"direct"}
JSON
```

更多表格字段示意：`docs/MA_RI_KP_TEMPLATES.md`。

### LBO 快算（fm lbo calc）
```
cat <<'JSON' | fm lbo calc --compact
{"entry_multiple":8,"exit_multiple":9,"ebitda":100,"revenue_growth":0.05,"ebitda_margin":0.25,"capex_percent":0.03,"tax_rate":0.25,"debt":300,"cash":20}
JSON
```

### DCF 估值（fm dcf calc）
```
cat <<'JSON' | fm dcf calc --compact
{"fcf_list":[50,55,60,65,70],"wacc":0.09,"terminal_growth":0.02,"net_debt":100,"shares_outstanding":10}
JSON
```

### 三表预测（fm three forecast）
```
cat <<'JSON' | fm three forecast --compact
{"assumptions":{"years":3,"revenue_growth":0.08},"income_statement":{"revenue":100,"gross_profit":40},"balance_sheet":{"total_assets":200,"total_equity":80}}
JSON
```

### 比率分析（fm ratio calc）
```
cat <<'JSON' | fm ratio calc --compact
{"income_statement":{"revenue":100,"gross_profit":40,"net_income":15},"balance_sheet":{"total_assets":120,"total_equity":60,"cash":20},"market_data":{"market_cap":200}}
JSON
```

## 调用约定
- 所有 CLI 默认从 stdin 读 JSON，`--json`/`--compact` 用于紧凑输出。
- 样例字段可作为调用层的规范格式；若来自 ERP 的字段名不一致，需在调用层做字段映射后再调用对应 CLI。
