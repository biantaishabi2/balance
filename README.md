# Balance 财务工具集

命令行财务工具合集，覆盖 **三表配平、财务建模、会计审计、预算/现金流、税务、风险、绩效** 等场景。核心依赖 `fin_tools` 库，所有工具可串联使用。

## 安装

```bash
git clone git@github.com:biantaishabi2/balance.git
cd balance
./install.sh
```

## 工具总览

| CLI | 主用途 | 典型子命令 |
|-----|--------|-----------|
| `balance` | 三表配平/诊断/场景 | `calc` `check` `diagnose` `scenario` `explain` |
| `excel_inspect` | 查看 Excel 结构 | - |
| `excel2json` | Excel/CSV → 标准 JSON | `--template tb/budget/ar/ap/voucher/cash` |
| `json2excel` | 将结果写回 Excel | - |
| `fm` | 综合财务模型 | `lbo` `ma` `dcf` `three` |
| `ac` | 会计/审计 | `tb` `adj` `sample` `consol` |
| `fa` | 财务分析/预算 | `variance` `flex` `forecast` `trend` |
| `cf` | 现金流/营运资金 | `forecast` `wcc` `drivers` |
| `ma` | 管理会计 | `dept` `product` `allocate` `cvp` `breakeven` |
| `ri` | 风险管理 | `credit` `aging` `provision` `fx` |
| `tx` | 税务筹划 | `vat` `cit` `iit` `bonus` `rd` `burden` |
| `kp` | KPI/绩效 | `kpi` `eva` `bsc` `okr` |

## 快速开始：三表配平

```bash
# 一行完成配平
excel2json 报表.xlsx | balance | json2excel - 报表.xlsx
```

## balance 子命令

```bash
balance calc      # 计算配平（默认）
balance check     # 校验输入数据
balance diagnose  # 诊断结果问题
balance scenario  # 场景分析
balance explain   # 追溯解释
```

### 示例

```bash
# 计算配平
echo '{"revenue":100000,"cost":60000}' | balance calc

# 校验输入
cat input.json | balance check

# 诊断问题
cat output.json | balance diagnose

# 场景分析：对比不同利率
cat input.json | balance scenario --vary "interest_rate:0.05,0.08,0.12"

# 解释净利润怎么算的
cat output.json | balance explain --field net_income
```

## 更多 CLI 示例

```bash
# 13周现金流预测
cf forecast < cash_plan.json

# LBO 快算（见 docs/AI_IO_GUIDE.md）
fm lbo calc < lbo_input.json

# 增值税快算
tx vat < vat_input.json

# 预算差异分析
fa variance < budget_vs_actual.json

# 试算平衡检查
ac tb < trial_balance.json
```

更多输入/输出样例与模板对齐：`docs/AI_IO_GUIDE.md`。自动化最小回归：`./scripts/smoke.sh`。

## 计算流程

```
融资(利息) → 折旧 → 损益(净利润) → 权益(留存收益) → 配平
```

**为什么是这个顺序？**
- 利息依赖借款额 → 先算融资
- 折旧依赖资产 → 再算投资
- 净利润依赖利息+折旧 → 再算损益
- 留存收益依赖净利润 → 再算权益
- 最后配平轧差

## 文件结构

```
balance/
├── README.md / skills.md       # 文档（人/AI）
├── requirements.txt / install.sh
├── balance.py                  # 三表配平 CLI
├── excel_inspect.py / excel2json.py / json2excel.py
├── fm.py / ac.py / fa.py / cf.py / ma.py / ri.py / tx.py / kp.py   # 其他 CLI
├── fin_tools/                  # 核心库：模型、工具、ERP 解析、测试
└── examples/                   # 示例输入输出、报告与 Excel 模板
    ├── input.json / output.json
    ├── sample.xlsx
    ├── mapping_template.json
    ├── report_template.md
    └── report_sample.md
```

## 输入字段

| 字段 | 含义 |
|------|------|
| `revenue` | 营业收入 |
| `cost` | 营业成本 |
| `other_expense` | 其他费用 |
| `opening_cash` | 期初现金 |
| `opening_debt` | 期初借款 |
| `opening_equity` | 期初股本 |
| `opening_retained` | 期初留存收益 |
| `fixed_asset_cost` | 固定资产原值 |
| `fixed_asset_life` | 折旧年限 |
| `interest_rate` | 利率 |
| `tax_rate` | 税率 |
| `dividend` | 分红 |

## 输出字段

| 字段 | 含义 |
|------|------|
| `interest` | 利息费用 |
| `depreciation` | 折旧费用 |
| `net_income` | 净利润 |
| `closing_cash` | 期末现金 |
| `closing_debt` | 期末负债 |
| `closing_total_equity` | 期末权益 |
| `is_balanced` | 是否配平成功 |

## AI 使用

AI 使用时参考 `skills.md`，完成配平后输出报告，参考 `examples/report_sample.md`。

## License

MIT
