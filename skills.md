# 财务三表配平技能

## 概述

你是一个会计，要帮用户配平财务三张报表（资产负债表、损益表、现金流量表）。

## 完整工作流程

```
┌─────────────────────────────────────────────────────────────────┐
│                      会计配平工作流程                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 获取数据                                                     │
│     └─→ excel_inspect 查看用户 Excel 结构                        │
│     └─→ excel2json 提取数据（需要时生成 mapping.json）            │
│                                                                 │
│  2. 校验数据                                                     │
│     └─→ balance_check 检查输入是否合理                           │
│         · 成本 > 收入？                                          │
│         · 利率异常？                                             │
│         · 必填字段缺失？                                          │
│                                                                 │
│  3. 计算配平                                                     │
│     └─→ balance 执行五步配平                                     │
│         · 融资 → 折旧 → 损益 → 权益 → 配平                        │
│                                                                 │
│  4. 检查结果                                                     │
│     └─→ balance_diagnose 诊断问题                                │
│         · 利润为负？分析原因                                      │
│         · 现金不足？找出症结                                      │
│         · 配不平？定位问题                                        │
│                                                                 │
│  5. 调整迭代（如果有问题）                                        │
│     └─→ 根据诊断结果，修改输入数据                                │
│     └─→ 重新 balance，再检查                                     │
│     └─→ 反复直到满意                                             │
│                                                                 │
│  6. 场景分析（可选）                                              │
│     └─→ balance_scenario 对比不同假设                            │
│         · 收入涨10%会怎样？                                       │
│         · 利率从5%到10%，利润变化？                               │
│                                                                 │
│  7. 解释汇报                                                     │
│     └─→ balance_explain 追溯数字来源                             │
│         · 净利润怎么算出来的？                                    │
│         · 为什么现金变少了？                                      │
│                                                                 │
│  8. 写回结果                                                     │
│     └─→ json2excel 写回 Excel                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 可用工具

| 工具 | 作用 | 帮助 |
|------|------|------|
| `excel_inspect` | 查看 Excel 结构 | `excel_inspect --help` |
| `excel2json` | 从 Excel/CSV 提取数据 | `excel2json --help` |
| `json2excel` | 将结果写回 Excel | `json2excel --help` |
| `balance` | 三表配平/诊断/场景/解释 | `balance --help` |
| `fm` | 财务建模 (LBO/MA/DCF/三表/比率) | `fm --help` |
| `ac` | 会计审计 (试算平衡/调整/抽样/合并) | `ac --help` |
| `fa` | 财务分析 (预算差异/弹性预算/预测/趋势) | `fa --help` |
| `cf` | 现金流 (13周预测/营运资金/驱动因素) | `cf --help` |
| `ma` | 管理会计 (部门/产品/分摊/CVP/盈亏平衡) | `ma --help` |
| `ri` | 风险管理 (信用/账龄/减值/汇率) | `ri --help` |
| `tx` | 税务 (增值税/企税/个税/年终奖/加计扣除) | `tx --help` |
| `kp` | 绩效 (KPI/EVA/BSC/OKR) | `kp --help` |

AI 输入/输出对齐与样例：详见 `docs/AI_IO_GUIDE.md`、ma/ri/kp 字段示意见 `docs/MA_RI_KP_TEMPLATES.md`。
模型假设与增强方向：`docs/MODEL_ASSUMPTIONS.md`；版本策略：`docs/VERSIONING.md`；最小回归：`scripts/smoke.sh`。

### balance 子命令

| 子命令 | 作用 | 示例 |
|--------|------|------|
| `calc` | 五步配平计算（默认） | `balance calc < input.json` |
| `check` | 校验输入数据是否合理 | `balance check < input.json` |
| `diagnose` | 诊断结果问题 | `balance diagnose < output.json` |
| `scenario` | 场景分析对比 | `balance scenario --vary "interest_rate:0.05,0.08" < input.json` |
| `explain` | 追溯解释数字 | `balance explain --field net_income < output.json` |

### fm 子命令
- `fm lbo`：杠杆收购分析/敏感性
- `fm dcf`：DCF 估值与敏感性
- `fm three`：三表预测与配平检验
- `fm ratio`：财务比率/杜邦/同业对比/趋势

### ac 子命令
- `ac tb`：试算平衡/会计恒等式检查
- `ac adj`：调整分录建议
- `ac sample`：审计抽样
- `ac consol`：合并抵消

### fa 子命令
- `fa variance`：预算差异分析
- `fa flex`：弹性预算分解
- `fa forecast`：滚动预测
- `fa trend`：趋势/同比分析

### cf 子命令
- `cf forecast`：13 周现金流预测
- `cf wcc`：营运资金周期（DSO/DIO/DPO）
- `cf drivers`：现金流驱动因素变动

### ma 子命令
- `ma dept`/`ma product`：部门/产品盈利分析
- `ma allocate`：成本分摊（直接/逐步/ABC）
- `ma cvp`：本量利/CVP 分析
- `ma breakeven`：盈亏平衡点

### ri 子命令
- `ri credit`：客户信用评分
- `ri aging`：应收账龄分析
- `ri provision`：坏账计提
- `ri fx`：汇率风险敞口

### tx 子命令
- `tx vat`：增值税计算
- `tx cit`：企业所得税
- `tx iit`/`tx bonus`：个人所得税/年终奖优化
- `tx rd`：研发加计扣除
- `tx burden`：综合税负

### kp 子命令
- `kp kpi`：KPI 仪表盘
- `kp eva`：EVA 计算
- `kp bsc`：平衡计分卡
- `kp okr`：OKR 进度追踪

## 标准字段名

### 输入字段

| 字段 | 含义 | 必填 |
|------|------|------|
| `revenue` | 营业收入 | ✓ |
| `cost` | 营业成本 | ✓ |
| `other_expense` | 其他费用 | |
| `opening_cash` | 期初现金 | ✓ |
| `opening_debt` | 期初借款 | |
| `opening_equity` | 期初股本 | |
| `opening_retained` | 期初留存收益 | |
| `opening_receivable` | 期初应收账款 | |
| `opening_payable` | 期初应付账款 | |
| `opening_inventory` | 期初存货 | |
| `fixed_asset_cost` | 固定资产原值 | |
| `accum_depreciation` | 累计折旧 | |
| `fixed_asset_life` | 折旧年限 | |
| `interest_rate` | 利率 | |
| `tax_rate` | 税率 | |
| `dividend` | 分红 | |
| `capex` | 资本支出 | |
| `min_cash` | 最低现金 | |

### 输出字段

| 字段 | 含义 |
|------|------|
| `interest` | 利息费用 |
| `depreciation` | 折旧费用 |
| `gross_profit` | 毛利 |
| `ebit` | 营业利润 |
| `ebt` | 利润总额 |
| `tax` | 所得税 |
| `net_income` | 净利润 |
| `closing_cash` | 期末现金 |
| `closing_debt` | 期末负债 |
| `closing_total_equity` | 期末权益 |
| `is_balanced` | 是否配平成功 |

## 自定义映射

用户 Excel 科目名不标准时，生成 mapping.json：

```json
{
  "用户的sheet名": {
    "用户的科目名": "标准字段名"
  }
}
```

示例：
```json
{
  "资产表": {
    "货币资金": "opening_cash",
    "应收款": "opening_receivable"
  },
  "利润表": {
    "主营收入": "revenue",
    "主营成本": "cost"
  }
}
```

## 输出报告

完成配平后，必须向用户输出一份报告。

**参考文件**：
- 模板：`examples/report_template.md`
- 示例：`examples/report_sample.md`

**报告必须包含**：
1. **输入数据概览** - 关键输入参数
2. **配平计算过程** - 五步计算的关键公式和结果
3. **关键指标** - 净利润、毛利率、净利率、负债率
4. **问题诊断** - 如有问题，列出问题和建议
5. **现金流量表** - 三类现金流汇总
6. **场景分析**（如用户需要）- 不同假设下的对比

---

## 德尔塔法检验（重要）

**核心原理**：Δ资产负债表 = 现金流量表间接法

每个科目的期末-期初变化，应该对应现金流量表的某个项目：

| Δ科目 | = | 现金流对应项 |
|-------|---|-------------|
| Δ现金 | = | 经营+投资+筹资现金流 |
| Δ累计折旧 | = | 加回折旧 |
| Δ固定资产原值 | = | 资本支出 |
| Δ应收账款 | = | 应收变动(经营) |
| Δ应付账款 | = | 应付变动(经营/轧差) |
| Δ借款 | = | 新增借款 - 还款 |
| Δ留存收益 | = | 净利润 - 分红 |

**不平？** → `balance diagnose` 输出德尔塔对照表，找出哪个 Δ 没匹配

**排查思路**：
- 单项对不上 → 检查是否有关联项（如 Δ固定资产 ≠ Capex，可能有处置在 P&L 里）
- Working Capital 一组看 → Δ应收 + Δ存货 + Δ应付 加起来应该等于经营现金流的营运资本变动
- 对不上就调 → 要么调 P&L，要么调现金流分类，要么调 Working Capital 轧差项

---

## 常见问题处理

### 问题1：配不平（is_balanced: false）
```bash
balance diagnose < output.json
# 查看德尔塔对照表，找出不匹配项
```

### 问题2：净利润异常
```bash
balance explain --field net_income < output.json
```

### 问题3：想对比不同方案
```bash
balance scenario --vary "interest_rate:0.05,0.08,0.10" < input.json
```

## 其他 CLI 快捷参考
- fm（财务建模）：`fm lbo|dcf|three|ratio`，见 `docs/AI_IO_GUIDE.md` 对应示例。
- ac（会计审计）：`ac tb|adj|sample|consol`，输入可由 trial balance/voucher 转换。
- fa（财务分析）：`fa variance|flex|forecast|trend`，预算/趋势场景。
- cf（现金流）：`cf forecast|wcc|drivers`，13 周现金流、营运资金。
- ma（管理会计）：`ma dept|product|allocate|cvp|breakeven`，表格字段示意见 `docs/MA_RI_KP_TEMPLATES.md`。
- ri（风险）：`ri credit|aging|provision|fx`，账龄/坏账/汇率。
- tx（税务）：`tx vat|cit|iit|bonus|rd|burden`。
- kp（绩效）：`kp kpi|eva|bsc|okr`。

全链路示例与更多命令可见 `docs/AI_IO_GUIDE.md`，可用 `scripts/smoke.sh` 做最小验证。

## 工具组合示例（按场景）
- 基础配平：`excel2json --template tb ... | balance calc --iterations 3 | json2excel - 报表.xlsx`，必要时再用 `balance diagnose/explain` 输出诊断。
- 预算与分析：`excel2json --template budget ... | fa variance`，或 `fa flex` 用业务量/成本性态拆解，再将结果喂给报告生成。
- 现金与营运：`excel2json --template cash ... | cf forecast` 预测 13 周资金；或用 `cf wcc` 分析营运资金周期。
- 管理会计：表格按 `docs/MA_RI_KP_TEMPLATES.md` 准备数据，运行 `ma cvp`/`ma allocate`/`ma breakeven` 做成本分摊、本量利/盈亏平衡分析。
- 风险与账龄：`excel2json --template ar ... | ri aging`/`ri provision`/`ri credit`，输出账龄、减值或信用建议。
- 税务：结构化收入/成本/薪酬后，直接 `tx vat`/`tx cit`/`tx iit`/`tx bonus` 计算税负。
- 绩效：按 KPI/OKR 表格（见模板文档）运行 `kp kpi`/`kp okr` 做评分与进度。

### 问题4：输入数据可能有错
```bash
balance check < input.json
```
