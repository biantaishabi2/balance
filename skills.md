# 财务三表配平技能

## 概述

自动配平财务三张报表（资产负债表、损益表、现金流量表），确保勾稽关系正确。

## 可用工具

| 工具 | 作用 | 帮助 |
|------|------|------|
| `excel_inspect` | 查看 Excel 结构（sheet名、科目名） | `excel_inspect --help` |
| `excel2json` | 从 Excel 提取数据，生成 JSON | `excel2json --help` |
| `balance` | 五步配平计算 | `balance --help` |
| `json2excel` | 将计算结果写回 Excel | `json2excel --help` |

## 工作流程

```
excel_inspect → excel2json → balance → json2excel
   查看结构      提取数据     配平计算    写回结果
```

## AI 使用流程

### 1. 用户给了 Excel

```bash
# 先看结构
excel_inspect 用户文件.xlsx

# 如果格式标准，直接一行
excel2json 用户文件.xlsx | balance | json2excel - 用户文件.xlsx

# 如果格式不标准，需要自定义 mapping.json（见下文）
excel2json 用户文件.xlsx --mapping /tmp/mapping.json | balance
```

### 2. 用户 Excel 格式不标准

先 `excel_inspect` 看结构，然后生成 `mapping.json`：

```json
{
  "用户的sheet名": {
    "用户的科目名": "标准JSON字段名"
  }
}
```

**标准 JSON 字段名：**

| 字段 | 含义 |
|------|------|
| `opening_cash` | 期初现金 |
| `opening_receivable` | 期初应收账款 |
| `opening_inventory` | 期初存货 |
| `opening_debt` | 期初借款 |
| `opening_payable` | 期初应付账款 |
| `opening_equity` | 期初股本 |
| `opening_retained` | 期初留存收益 |
| `fixed_asset_cost` | 固定资产原值 |
| `accum_depreciation` | 累计折旧 |
| `revenue` | 营业收入 |
| `cost` | 营业成本 |
| `other_expense` | 其他费用 |
| `interest_rate` | 利率 |
| `tax_rate` | 税率 |
| `fixed_asset_life` | 折旧年限 |
| `dividend` | 分红 |
| `capex` | 资本支出 |
| `min_cash` | 最低现金 |

### 3. 用户只给了部分数据

直接构造 JSON 调用 `balance`：

```bash
echo '{"revenue":100000,"cost":60000,...}' | balance
```

## 计算顺序

```
融资(利息) → 折旧 → 损益(净利润) → 权益(留存收益) → 配平
```

## 输出字段

配平后新增的字段：

| 字段 | 含义 |
|------|------|
| `interest` | 利息费用 |
| `depreciation` | 折旧费用 |
| `net_income` | 净利润 |
| `closing_cash` | 期末现金 |
| `closing_debt` | 期末负债 |
| `closing_total_equity` | 期末权益 |
| `is_balanced` | 是否配平成功 |
