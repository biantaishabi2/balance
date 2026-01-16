# 报表与合并（详细设计/测试合一）

## Overview
在现有三表基础上补齐多账套合并、抵销与自定义报表能力，形成集团层报表输出。

## Workflow Type
feature

## Task Scope

**In scope**：
- 多账套/多公司合并
- 内部交易抵销
- 自定义报表模板
- 合并报表输出

**Out of scope**：
- 复杂税务合并
- 全量 BI 平台

## 目标
- 支持多账套合并口径
- 抵销逻辑可配置
- 报表模板可复用

## 当前问题（需要解决）
- 仅支持单账套报表
- 无合并与抵销

## 核心设计

### 1. 账套与公司
- `companies`：`id, code, name, base_currency`
- `ledgers` 关联公司

### 2. 合并规则
- `consolidation_rules`：
  - `id, name, elimination_accounts, ownership`
- 根据权益比例进行合并
- `elimination_accounts` 支持：
  - 精确科目：`{"left":"1122","right":"2202","source":"closing_balance"}`
  - 前缀/类型：`{"left_prefixes":["112"],"right_prefixes":["220"],"source":"closing_balance"}`

### 3. 合并币种与折算
- 集团本位币：`group_currency`
- 汇率表：`fx_rates(date, base_currency, quote_currency, rate, rate_type)`
- 折算口径：
  - 资产/负债：期末汇率
  - 收入/费用：期间平均汇率
  - 权益：历史汇率
  - 折算差额计入“外币报表折算差额”

### 4. 抵销处理
- 内部往来、内部交易生成抵销分录
- 抵销凭证不回写子账

### 5. 报表模板
- `report_templates`：
  - `code, name, fields, formula`
- 输出合并报表

## 方案差异（相对现状）
- 从“单账套三表”升级为“合并报表”

## 落地步骤与测试（统一版）

0. **多账套与公司（已做）**
   - 做什么：新增公司/账套基础数据、汇率表与合并规则表
   - 测试：`pytest -q tests/test_reporting_consolidation.py -k fx_translation`
   - 结果/验收：账套加载与折算汇率生效

1. **合并与抵销（已做）**
   - 做什么：抵销规则配置与合并输出
   - 测试：`pytest -q tests/test_reporting_consolidation.py -k elimination`
   - 结果/验收：内部往来科目抵销后余额为 0

2. **模板化报表（已做）**
   - 做什么：模板字段与公式计算
   - 测试：`pytest -q tests/test_reporting_consolidation.py -k template`
   - 结果/验收：模板字段与公式计算正确

## 可执行测试用例

### 测试环境准备
```bash
pytest -q tests/test_reporting_consolidation.py
```

### TC-CON-01: 多账套合并
- **操作**：
  1) 集团本位币 CNY
  2) 子公司 USD 账套：资产 100 USD，收入 100 USD
  3) 汇率：期末 7.1，平均 7.0
- **预期**：
  - 资产折算 710 CNY，收入折算 700 CNY
  - 折算差额 10 CNY 计入“外币报表折算差额”

### TC-CON-02: 抵销规则
- **操作**：
  1) 内部应收 200，内部应付 200
  2) 抵销规则：往来科目成对抵销
- **预期**：
  - 合并报表中内部往来余额为 0

### TC-CON-03: 模板报表
- **操作**：配置模板字段与公式（毛利=收入-成本）
- **预期**：毛利字段输出 40.00

### 补充验证：前缀抵销
- **操作**：配置 `left_prefixes=["112"]`、`right_prefixes=["220"]`
- **预期**：内部往来按前缀批量抵销，资产/负债同时下降

## 备注
- 合并口径初期仅支持全资或简单权益比例
- 多租户默认 `tenant_id/org_id=default`，可按环境变量覆盖
