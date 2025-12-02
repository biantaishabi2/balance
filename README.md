# 财务三表配平工具

自动配平财务三张报表：**资产负债表**、**损益表**、**现金流量表**。

## 安装

```bash
git clone git@github.com:biantaishabi2/balance.git
cd balance
./install.sh
```

## 工具列表

| 工具 | 作用 |
|------|------|
| `excel_inspect` | 查看 Excel 结构 |
| `excel2json` | 从 Excel 提取数据 |
| `balance` | 配平计算（含多个子命令） |
| `json2excel` | 将结果写回 Excel |

## 快速开始

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
├── README.md               # 本文档（给人看）
├── skills.md               # AI 技能说明（给 AI 看）
├── requirements.txt        # Python 依赖
├── install.sh              # 安装脚本
├── balance.py              # 主工具（5个子命令）
├── excel_inspect.py        # 查看 Excel 结构
├── excel2json.py           # Excel → JSON
├── json2excel.py           # JSON → Excel
└── examples/
    ├── input.json          # 示例输入
    ├── output.json         # 示例输出
    ├── sample.xlsx         # 示例 Excel
    ├── mapping_template.json   # 字段映射模板
    ├── report_template.md  # 报告模板
    └── report_sample.md    # 报告示例
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
