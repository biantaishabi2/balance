# Financial Model CLI 设计文档

## 概述

统一的财务建模命令行工具 `fm`，整合 LBO、M&A、DCF、三表模型等功能。

```
fm - Financial Model CLI

用法: fm <command> [subcommand] [options] < input.json

命令:
  lbo      杠杆收购分析
  ma       并购分析
  dcf      DCF估值
  three    三表模型
  tool     原子工具（直接调用）
```

---

## 1. 命令结构

### 1.1 总体架构

```
fm
├── lbo                    # LBO分析
│   ├── calc               # 完整计算
│   ├── sensitivity        # 敏感性分析
│   └── export             # 导出Excel
│
├── ma                     # M&A分析
│   ├── calc               # 完整计算
│   ├── accretion          # 增厚/稀释分析
│   ├── breakeven          # 盈亏平衡
│   └── export             # 导出Excel
│
├── dcf                    # DCF估值
│   ├── calc               # 完整计算
│   ├── sensitivity        # 敏感性分析
│   └── export             # 导出Excel
│
├── three                  # 三表模型
│   ├── forecast           # 预测
│   ├── check              # 配平检验
│   └── export             # 导出Excel
│
└── tool                   # 原子工具（高级用法）
    ├── list               # 列出所有工具
    └── run <tool_name>    # 运行指定工具
```

### 1.2 通用选项

```bash
fm [command] --help              # 显示帮助
fm [command] --output FILE       # 输出到文件（默认stdout）
fm [command] --format json|table # 输出格式（默认json）
fm [command] --compact           # 紧凑JSON输出
fm [command] --quiet             # 安静模式，只输出结果
```

---

## 2. LBO 命令

### 2.1 fm lbo calc

完整LBO分析

```bash
fm lbo calc < input.json
fm lbo calc --holding-period 5 --exit-multiple 8.0 < input.json
```

**输入 (stdin):**
```json
{
  "entry_ebitda": 100000000,
  "entry_multiple": 8.0,
  "exit_multiple": 8.0,
  "holding_period": 5,
  "revenue_growth": [0.05, 0.06, 0.07, 0.06, 0.05],
  "ebitda_margin": 0.20,
  "debt_structure": {
    "senior": {"amount_percent": 0.40, "interest_rate": 0.06, "amortization_rate": 0.05},
    "sub": {"amount_percent": 0.20, "interest_rate": 0.10, "pik_rate": 0.02}
  }
}
```

**输出:**
```json
{
  "irr": 0.172,
  "moic": 2.21,
  "equity_invested": 344000000,
  "equity_proceeds": 760000000,
  "exit_debt": 180000000
}
```

**选项:**
```
--entry-multiple FLOAT    覆盖入场倍数
--exit-multiple FLOAT     覆盖退出倍数
--holding-period INT      覆盖持有期
--sweep-percent FLOAT     现金扫荡比例（默认0.75）
--detail                  输出完整详情（含债务计划表等）
```

### 2.2 fm lbo sensitivity

敏感性分析

```bash
fm lbo sensitivity --entry 7,7.5,8,8.5,9 --exit 7,8,9 < input.json
fm lbo sensitivity --leverage 0.4,0.5,0.6 --growth 0.03,0.05,0.07 < input.json
```

**输出:**
```
IRR Sensitivity (Entry vs Exit Multiple)
┌─────────┬────────┬────────┬────────┐
│ Entry   │ 7.0x   │ 8.0x   │ 9.0x   │
├─────────┼────────┼────────┼────────┤
│ 7.0x    │ 24.1%  │ 28.5%  │ 32.3%  │
│ 8.0x    │ 17.2%  │ 21.3%  │ 25.1%  │
│ 9.0x    │ 11.8%  │ 15.6%  │ 19.2%  │
└─────────┴────────┴────────┴────────┘
```

**选项:**
```
--entry FLOATS      入场倍数范围（逗号分隔）
--exit FLOATS       退出倍数范围
--leverage FLOATS   杠杆比例范围
--growth FLOATS     增长率范围
--metric irr|moic   输出指标（默认irr）
```

### 2.3 fm lbo export

导出Excel

```bash
fm lbo calc < input.json | fm lbo export -o lbo_model.xlsx
fm lbo export --input result.json -o lbo_model.xlsx
```

---

## 3. M&A 命令

### 3.1 fm ma calc

完整M&A分析

```bash
fm ma calc < deal.json
```

**输入:**
```json
{
  "acquirer": {
    "share_price": 100,
    "shares_outstanding": 1000000000,
    "net_income": 50000000000
  },
  "target": {
    "share_price": 50,
    "shares_outstanding": 200000000,
    "net_income": 2000000000
  },
  "deal_terms": {
    "premium_percent": 0.30,
    "cash_percent": 0.60,
    "stock_percent": 0.40
  },
  "synergies": {
    "cost_synergies": 500000000
  }
}
```

**输出:**
```json
{
  "purchase_price": 13000000000,
  "premium": "30.0%",
  "accretion_dilution": {
    "without_synergies": "-1.7%",
    "with_synergies": "+0.5%",
    "status": "Dilutive → Accretive"
  },
  "goodwill": 5000000000,
  "breakeven_synergies": 893000000
}
```

**选项:**
```
--premium FLOAT           覆盖溢价比例
--cash-percent FLOAT      现金支付比例
--stock-percent FLOAT     股票支付比例
--synergies FLOAT         协同效应金额
--detail                  输出完整详情
```

### 3.2 fm ma accretion

快速增厚/稀释分析

```bash
fm ma accretion --premium 0.20,0.30,0.40 --stock 0.2,0.4,0.6 < deal.json
```

**输出:**
```
EPS Accretion/Dilution Analysis
┌─────────────┬──────────┬──────────┬──────────┐
│ Premium     │ 20% Stk  │ 40% Stk  │ 60% Stk  │
├─────────────┼──────────┼──────────┼──────────┤
│ 20%         │ +2.1%    │ +0.8%    │ -0.5%    │
│ 30%         │ +0.5%    │ -1.2%    │ -2.8%    │
│ 40%         │ -1.0%    │ -3.1%    │ -5.0%    │
└─────────────┴──────────┴──────────┴──────────┘
```

### 3.3 fm ma breakeven

盈亏平衡分析

```bash
fm ma breakeven < deal.json
```

**输出:**
```json
{
  "synergies_needed": 893000000,
  "synergies_needed_formatted": "8.93亿",
  "current_status": "Dilutive (-1.7%)",
  "interpretation": "需要年化税前协同效应 8.93亿 才能使EPS不稀释"
}
```

---

## 4. DCF 命令

### 4.1 fm dcf calc

DCF估值

```bash
fm dcf calc < projections.json
fm dcf calc --wacc 0.09 --growth 0.02 < projections.json
```

**输入:**
```json
{
  "fcf_projections": [50000000, 55000000, 60000000, 65000000, 70000000],
  "wacc": 0.09,
  "terminal_growth": 0.02,
  "net_debt": 200000000,
  "shares_outstanding": 100000000
}
```

**输出:**
```json
{
  "enterprise_value": 893000000,
  "equity_value": 693000000,
  "per_share_value": 6.93,
  "terminal_value": 1020000000,
  "pv_of_fcf": 243000000,
  "pv_of_terminal": 650000000
}
```

**选项:**
```
--wacc FLOAT              加权平均资本成本
--growth FLOAT            永续增长率
--exit-multiple FLOAT     使用退出倍数法（替代永续增长）
--method perpetual|multiple  终值计算方法
```

### 4.2 fm dcf sensitivity

敏感性分析

```bash
fm dcf sensitivity --wacc 0.08,0.09,0.10,0.11 --growth 0.01,0.02,0.03 < projections.json
```

**输出:**
```
Per Share Value Sensitivity (WACC vs Terminal Growth)
┌────────┬────────┬────────┬────────┐
│ WACC   │ 1.0%   │ 2.0%   │ 3.0%   │
├────────┼────────┼────────┼────────┤
│ 8.0%   │ $8.52  │ $9.31  │ $10.45 │
│ 9.0%   │ $6.21  │ $6.93  │ $7.85  │
│ 10.0%  │ $4.58  │ $5.21  │ $6.02  │
│ 11.0%  │ $3.35  │ $3.91  │ $4.62  │
└────────┴────────┴────────┴────────┘
```

### 4.3 fm dcf wacc

WACC计算器

```bash
fm dcf wacc --rf 0.03 --beta 1.2 --mrp 0.06 --rd 0.05 --tax 0.25 --de 0.3
```

**输出:**
```json
{
  "cost_of_equity": 0.102,
  "cost_of_debt_after_tax": 0.0375,
  "wacc": 0.0826,
  "formula": "WACC = E/(D+E) × Re + D/(D+E) × Rd × (1-t)"
}
```

---

## 5. 三表模型命令

### 5.1 fm three forecast

财务预测

```bash
fm three forecast --years 5 < base_financials.json
```

**输入:**
```json
{
  "base_year": {
    "revenue": 500000000,
    "cost": 375000000,
    "opex": 60000000
  },
  "assumptions": {
    "revenue_growth": 0.08,
    "gross_margin": 0.25,
    "opex_ratio": 0.12,
    "tax_rate": 0.25,
    "ar_days": 60,
    "ap_days": 45,
    "capex_ratio": 0.05
  }
}
```

**选项:**
```
--years INT               预测年数
--growth FLOAT            收入增长率
--margin FLOAT            毛利率
```

### 5.2 fm three check

配平检验

```bash
fm three check < forecast_result.json
```

**输出:**
```json
{
  "is_balanced": true,
  "balance_diff": 0,
  "checks": {
    "assets_equals_liabilities_plus_equity": true,
    "cash_flow_reconciles": true,
    "retained_earnings_reconciles": true
  }
}
```

---

## 6. 原子工具命令

### 6.1 fm tool list

列出所有可用工具

```bash
fm tool list
fm tool list --module lbo
fm tool list --search "irr"
```

**输出:**
```
Available Tools (37 total)

LBO Tools (9):
  calc_purchase_price      计算收购价格
  calc_sources_uses        资金来源与用途
  project_operations       预测运营数据
  calc_debt_schedule       债务计划表
  calc_exit_value          退出价值
  calc_equity_proceeds     股权所得
  calc_irr                 内部收益率
  calc_moic                投资倍数
  lbo_quick_build          快捷构建

M&A Tools (8):
  calc_offer_price         收购报价
  calc_funding_mix         融资结构
  calc_goodwill            商誉计算
  calc_pro_forma           合并报表
  calc_accretion_dilution  增厚/稀释
  calc_synergies           协同效应
  calc_breakeven           盈亏平衡
  ma_quick_build           快捷构建

DCF Tools (9):
  calc_capm                CAPM股权成本
  calc_wacc                加权平均资本成本
  calc_fcff                企业自由现金流
  calc_terminal_value      终值计算
  calc_enterprise_value    企业价值
  calc_equity_value        股权价值
  calc_per_share_value     每股价值
  dcf_sensitivity          敏感性分析
  dcf_quick_valuate        快捷估值

Three Statement Tools (11):
  forecast_revenue         收入预测
  forecast_cost            成本预测
  forecast_opex            费用预测
  calc_income_statement    利润表计算
  calc_working_capital     营运资本
  calc_depreciation        折旧计算
  calc_capex               资本支出
  calc_operating_cash_flow 经营现金流
  calc_cash_flow_statement 现金流量表
  check_balance            配平检验
  three_statement_quick_build 快捷构建
```

### 6.2 fm tool run

直接运行原子工具

```bash
# 计算IRR
echo '{"cash_flows": [-344000000, 0, 0, 0, 0, 880000000]}' | fm tool run calc_irr

# 计算WACC
echo '{"cost_of_equity":0.102,"cost_of_debt":0.05,"tax_rate":0.25,"debt_ratio":0.3}' | fm tool run calc_wacc

# 计算商誉
echo '{"purchase_price":13000000000,"target_book_value":10000000000}' | fm tool run calc_goodwill
```

**选项:**
```
--help-tool              显示工具的参数说明
--validate               验证输入参数
```

### 6.3 fm tool help

显示工具详细帮助

```bash
fm tool help calc_irr
```

**输出:**
```
calc_irr - 计算内部收益率 (IRR)

用法:
  echo '{"cash_flows": [...]}' | fm tool run calc_irr

参数:
  cash_flows (必需)    现金流序列 [-投入, cf1, cf2, ..., 退出所得]

返回:
  {
    "value": 0.207,           # IRR值
    "formula": "IRR(...)",    # 公式说明
    "inputs": {...}           # 输入参数
  }

示例:
  echo '{"cash_flows": [-100, 0, 0, 0, 0, 200]}' | fm tool run calc_irr
  # 输出: {"value": 0.1487, ...}
```

---

## 7. 管道组合示例

### 7.1 LBO + 导出

```bash
# 计算并导出
fm lbo calc < input.json | fm lbo export -o result.xlsx

# 敏感性分析并导出
fm lbo sensitivity --entry 7,8,9 --exit 7,8,9 < input.json > sensitivity.json
```

### 7.2 M&A 完整流程

```bash
# 计算增厚/稀释
fm ma calc < deal.json | jq '.accretion_dilution'

# 计算所需协同
fm ma breakeven < deal.json | jq '.synergies_needed'

# 协同效应敏感性
fm ma accretion --synergies 0,500000000,1000000000 < deal.json
```

### 7.3 原子工具组合

```bash
# 自定义LBO流程：用DCF计算退出价值
purchase=$(echo '{"ebitda":100000000,"multiple":8}' | fm tool run calc_purchase_price | jq '.value')
exit_ev=$(fm dcf calc < projections.json | jq '.enterprise_value')
echo "Purchase: $purchase, Exit EV: $exit_ev"
```

### 7.4 批量处理

```bash
# 对多个交易进行分析
for f in deals/*.json; do
  echo "=== $f ==="
  fm ma calc < "$f" | jq '{file: "'$f'", eps_impact: .accretion_dilution.without_synergies}'
done
```

---

## 8. 输出格式

### 8.1 JSON (默认)

```bash
fm lbo calc < input.json
```

### 8.2 表格

```bash
fm lbo calc --format table < input.json
```

```
LBO Analysis Results
────────────────────────────────────
Metric              Value
────────────────────────────────────
IRR                 17.2%
MOIC                2.21x
Equity Invested     $344,000,000
Equity Proceeds     $760,000,000
Holding Period      5 years
────────────────────────────────────
```

### 8.3 CSV

```bash
fm lbo sensitivity --format csv > sensitivity.csv
```

### 8.4 Markdown

```bash
fm ma calc --format markdown < deal.json
```

---

## 9. 配置文件

### 9.1 默认配置 `~/.fmrc`

```json
{
  "defaults": {
    "format": "json",
    "compact": false,
    "tax_rate": 0.25,
    "discount_rate": 0.10
  },
  "aliases": {
    "quick-lbo": "lbo calc --detail",
    "quick-ma": "ma calc --detail"
  }
}
```

### 9.2 项目配置 `.fmrc`

```json
{
  "company": "Target Corp",
  "defaults": {
    "tax_rate": 0.21,
    "cost_of_debt": 0.05
  }
}
```

---

## 10. 实现计划

### Phase 1: 核心框架
- [ ] CLI入口和参数解析 (`fm.py`)
- [ ] 子命令路由
- [ ] JSON输入输出
- [ ] 帮助系统

### Phase 2: 模型命令
- [ ] `fm lbo calc/sensitivity/export`
- [ ] `fm ma calc/accretion/breakeven/export`
- [ ] `fm dcf calc/sensitivity/wacc`
- [ ] `fm three forecast/check`

### Phase 3: 原子工具
- [ ] `fm tool list`
- [ ] `fm tool run`
- [ ] `fm tool help`

### Phase 4: 增强功能
- [ ] 表格输出格式
- [ ] 配置文件支持
- [ ] 批量处理
- [ ] Shell补全

---

## 11. 文件结构

```
balance/
├── fm.py                    # CLI入口
├── fm/
│   ├── __init__.py
│   ├── cli.py               # 主CLI逻辑
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── lbo.py           # lbo子命令
│   │   ├── ma.py            # ma子命令
│   │   ├── dcf.py           # dcf子命令
│   │   ├── three.py         # three子命令
│   │   └── tool.py          # tool子命令
│   ├── formatters/
│   │   ├── __init__.py
│   │   ├── json_fmt.py
│   │   ├── table_fmt.py
│   │   └── csv_fmt.py
│   └── utils.py
└── fin_tools/         # 现有模型库（不变）
    ├── models/
    └── tools/
```

---

## 12. 使用示例汇总

```bash
# 帮助
fm --help
fm lbo --help
fm lbo calc --help

# LBO
fm lbo calc < input.json
fm lbo sensitivity --entry 7,8,9 --exit 7,8,9 < input.json
fm lbo export -o model.xlsx < result.json

# M&A
fm ma calc < deal.json
fm ma accretion --premium 0.2,0.3,0.4 < deal.json
fm ma breakeven < deal.json

# DCF
fm dcf calc --wacc 0.09 < projections.json
fm dcf sensitivity --wacc 0.08,0.09,0.10 --growth 0.01,0.02,0.03 < projections.json
fm dcf wacc --rf 0.03 --beta 1.2 --mrp 0.06 --rd 0.05 --de 0.3

# 三表
fm three forecast --years 5 < base.json
fm three check < forecast.json

# 原子工具
fm tool list
fm tool run calc_irr < cashflows.json
fm tool help calc_wacc
```
