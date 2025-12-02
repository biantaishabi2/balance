# 财务三表配平工具 (Balance Sheet Tool)

## 项目目标

自动配平财务三张报表：**资产负债表**、**损益表**、**现金流量表**。

核心逻辑：按正确顺序计算各项数值，确保三表勾稽关系正确。

## 计算顺序（五步流程）

```
┌─────────────────┐
│ 1. 融资现金流   │ → 输出: 利息费用、新增借款、期末负债、期末现金
└────────┬────────┘
         ▼
┌─────────────────┐
│ 2. 投资现金流   │ → 输出: 折旧费用、资本支出、期末固定资产
└────────┬────────┘
         ▼
┌─────────────────┐
│ 3. 损益表计算   │ → 输入: 利息+折旧 → 输出: 净利润
└────────┬────────┘
         ▼
┌─────────────────┐
│ 4. 权益变动     │ → 输入: 净利润 → 输出: 留存收益、期末权益
└────────┬────────┘
         ▼
┌─────────────────┐
│ 5. 配平轧差     │ → 检查: 资产 = 负债 + 权益，调整应收应付
└─────────────────┘
```

**为什么是这个顺序？**

- 融资现金流先算 → 因为要确定**利息**（利息依赖借款额）
- 投资现金流再算 → 因为要确定**折旧**（折旧依赖资产）
- 损益表用利息+折旧 → 才能算出**净利润**
- 净利润定了 → 才能算**留存收益**（权益的一部分）
- 最后配平 → 微调应收应付让**资产=负债+权益**

---

## CLI 使用说明

### 安装

```bash
chmod +x balance.py
```

### 基本用法

```bash
# 运行全部五步
echo '{"revenue": 1000, ...}' | ./balance.py

# 只运行某一步
./balance.py --step finance < input.json
./balance.py --step depreciation < input.json
./balance.py --step profit < input.json
./balance.py --step equity < input.json
./balance.py --step reconcile < input.json

# 顺序执行多步（管道）
cat input.json | ./balance.py --step finance | ./balance.py --step depreciation | ...
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `--step <name>` | 只执行某一步：`finance`, `depreciation`, `profit`, `equity`, `reconcile` |
| `--all` | 执行全部五步（默认） |
| `--pretty` | 输出格式化 JSON（默认开启） |
| `--compact` | 输出紧凑 JSON |

---

## 输入 JSON 结构

```json
{
  "// === 基础数据 ===": "",
  "revenue": 10000,           // 营业收入
  "cost": 6000,               // 营业成本（不含折旧）
  "other_expense": 500,       // 其他费用

  "// === 期初余额 ===": "",
  "opening_cash": 2000,       // 期初现金
  "opening_debt": 5000,       // 期初负债（借款）
  "opening_equity": 3000,     // 期初股本
  "opening_retained": 1000,   // 期初留存收益
  "opening_receivable": 800,  // 期初应收账款
  "opening_payable": 600,     // 期初应付账款
  "opening_inventory": 1200,  // 期初存货

  "// === 固定资产 ===": "",
  "fixed_asset_cost": 10000,  // 固定资产原值
  "fixed_asset_life": 10,     // 使用年限
  "fixed_asset_salvage": 0,   // 残值
  "accum_depreciation": 2000, // 累计折旧（期初）
  "capex": 0,                 // 本期资本支出

  "// === 融资参数 ===": "",
  "interest_rate": 0.08,      // 年利率
  "min_cash": 500,            // 最低现金余额
  "repayment": 0,             // 本期还款
  "new_equity": 0,            // 新增股本

  "// === 其他 ===": "",
  "tax_rate": 0.25,           // 所得税率
  "dividend": 0               // 分红
}
```

---

## 各步骤算法详解

### 第一步：融资现金流 (finance)

**目的**：确定利息费用、新增借款、期末现金和期末负债。

**难点**：存在循环依赖 —— 借多少钱取决于现金缺口，现金缺口取决于利息，利息取决于借了多少钱。

**算法**：

```python
# 简化模型：利息按期初负债计算（避免循环）
interest = opening_debt * interest_rate

# 计算现金流入流出（不含新借款）
cash_inflow = revenue - delta_receivable        # 实际收到的现金
cash_outflow = cost + other_expense + interest + tax + repayment + capex - delta_payable

# 现金缺口
cash_before_financing = opening_cash + cash_inflow - cash_outflow
gap = min_cash - cash_before_financing

# 需要借款吗？
new_borrowing = max(gap, 0)

# 期末值
closing_cash = cash_before_financing + new_borrowing
closing_debt = opening_debt + new_borrowing - repayment
```

**进阶模型**（处理循环依赖）：

```python
# 如果利息按平均负债计算，需要迭代求解
for _ in range(10):  # 迭代收敛
    avg_debt = (opening_debt + closing_debt) / 2
    interest = avg_debt * interest_rate
    # 重新计算 closing_debt...
```

---

### 第二步：投资现金流 / 折旧 (depreciation)

**目的**：计算本期折旧费用、期末固定资产净值。

**算法**：

```python
# 直线法折旧
annual_depreciation = (fixed_asset_cost - fixed_asset_salvage) / fixed_asset_life

# 期末累计折旧
closing_accum_depreciation = accum_depreciation + annual_depreciation

# 期末固定资产净值
closing_fixed_asset_net = fixed_asset_cost + capex - closing_accum_depreciation

# 投资现金流出
investing_cashflow = -capex
```

**可选：其他折旧方法**

```python
# 双倍余额递减法
rate = 2 / fixed_asset_life
net_value = fixed_asset_cost - accum_depreciation
annual_depreciation = net_value * rate

# 年数总和法
remaining_life = fixed_asset_life - years_used
sum_of_years = fixed_asset_life * (fixed_asset_life + 1) / 2
annual_depreciation = (fixed_asset_cost - fixed_asset_salvage) * remaining_life / sum_of_years
```

---

### 第三步：损益表 (profit)

**目的**：用收入、成本、利息、折旧计算净利润。

**算法**：

```python
# 毛利
gross_profit = revenue - cost

# 营业利润（EBIT）
ebit = gross_profit - other_expense - depreciation

# 利润总额（EBT）
ebt = ebit - interest

# 所得税（亏损不交税）
tax = max(ebt, 0) * tax_rate

# 净利润
net_income = ebt - tax
```

**损益表结构**：

```
营业收入                    revenue
- 营业成本                  cost
─────────────────────────────────────
= 毛利                      gross_profit
- 折旧                      depreciation
- 其他费用                  other_expense
─────────────────────────────────────
= 营业利润 (EBIT)           ebit
- 利息费用                  interest
─────────────────────────────────────
= 利润总额 (EBT)            ebt
- 所得税                    tax
─────────────────────────────────────
= 净利润                    net_income
```

---

### 第四步：权益变动 (equity)

**目的**：用净利润计算留存收益变动、期末权益。

**算法**：

```python
# 留存收益变动 = 净利润 - 分红
retained_earnings_change = net_income - dividend

# 期末留存收益
closing_retained = opening_retained + retained_earnings_change

# 期末股本（如有增资）
closing_equity_capital = opening_equity + new_equity

# 期末所有者权益合计
closing_total_equity = closing_equity_capital + closing_retained
```

---

### 第五步：配平轧差 (reconcile)

**目的**：验证资产=负债+权益，必要时调整应收应付。

**算法**：

```python
# 计算各项期末值
total_assets = (
    closing_cash +
    closing_receivable +
    closing_inventory +
    closing_fixed_asset_net
)

total_liabilities = closing_debt + closing_payable

total_equity = closing_total_equity

# 检查是否平衡
balance_diff = total_assets - total_liabilities - total_equity

# 如果不平，调整应收或应付（取决于差额正负）
if balance_diff > 0:
    # 资产多了，增加应付（或减少应收）
    closing_payable += balance_diff
elif balance_diff < 0:
    # 负债+权益多了，增加应收（或减少应付）
    closing_receivable += abs(balance_diff)

# 验证
assert total_assets == total_liabilities + total_equity
```

**配平检查清单**：

```python
checks = {
    "资产负债平衡": total_assets == total_liabilities + total_equity,
    "现金流勾稽": opening_cash + net_cashflow == closing_cash,
    "留存收益勾稽": opening_retained + net_income - dividend == closing_retained,
}
```

---

## AI 调用方式

### 方式一：单次完整计算

```bash
# AI 准备输入 JSON，调用工具，获取完整结果
echo '{"revenue":10000,"cost":6000,...}' | ./balance.py
```

### 方式二：分步调用（调试用）

```bash
# 第一步
echo '{"opening_debt":5000,"interest_rate":0.08,...}' | ./balance.py --step finance

# 拿到利息后，第二步
echo '{"fixed_asset_cost":10000,...}' | ./balance.py --step depreciation

# 依次类推...
```

### 方式三：管道串联

```bash
cat input.json \
  | ./balance.py --step finance \
  | ./balance.py --step depreciation \
  | ./balance.py --step profit \
  | ./balance.py --step equity \
  | ./balance.py --step reconcile \
  > output.json
```

### AI 使用建议

1. **准备输入**：从 Excel/CSV 读取数据，构造 JSON
2. **调用工具**：`cat input.json | ./balance.py > output.json`
3. **解析输出**：从 output.json 提取需要的数值
4. **写回报表**：将结果写入 Excel 对应单元格

---

## 输出 JSON 结构

```json
{
  "// === 输入数据（原样保留）===": "",
  "revenue": 10000,
  "cost": 6000,
  "...": "...",

  "// === 计算结果 ===": "",

  "// 第一步：融资": "",
  "interest": 400,
  "new_borrowing": 0,
  "closing_debt": 5000,
  "closing_cash": 2100,

  "// 第二步：折旧": "",
  "depreciation": 1000,
  "closing_fixed_asset_net": 7000,

  "// 第三步：损益": "",
  "gross_profit": 4000,
  "ebit": 2500,
  "ebt": 2100,
  "tax": 525,
  "net_income": 1575,

  "// 第四步：权益": "",
  "retained_earnings_change": 1575,
  "closing_retained": 2575,
  "closing_total_equity": 5575,

  "// 第五步：配平": "",
  "total_assets": 10575,
  "total_liabilities": 5000,
  "total_equity": 5575,
  "balance_diff": 0,
  "is_balanced": true
}
```

---

## 文件结构

```
balance/
├── README.md           # 本文档
├── balance.py          # CLI 工具主程序
├── examples/
│   ├── input.json      # 示例输入
│   └── output.json     # 示例输出
└── tests/
    └── test_balance.py # 单元测试
```
