# 多币种与汇兑（详细设计/测试合一）

## Overview
在现有记账系统中引入多币种与汇兑能力，保持总账口径为本位币，同时记录外币原币与期末汇兑损益。

## Workflow Type
feature

## Task Scope

**In scope**：
- 本位币配置与币种档案
- 汇率维护与按日期取数
- 外币凭证录入与记账（原币+本位币）
- 期末汇兑重估与损益凭证
- 外币余额查询

**Out of scope**：
- 多账簿与多准则
- 税控/发票与资金系统对接
- 复杂票据/信用管理

## 目标
- 账簿仍以本位币为核算口径
- 外币凭证可录入原币并自动折算
- 汇兑损益可按期间重估并自动生成凭证

## 当前问题（已解决）
- 现有系统只有单币种金额字段
- 无汇率数据与汇兑损益处理
- 外币余额无法查询

## 核心设计

### 1. 基础配置与主数据
- 新增配置文件 `data/forex_config.json`
  - `base_currency`: 本位币代码（默认 CNY）
  - `fx_gain_account`: 汇兑收益科目（如 6051）
  - `fx_loss_account`: 汇兑损失科目（如 6603）
  - `revaluable_accounts`: 可重估科目列表（或通过科目属性标记）
- 新增币种表：`currencies(code, name, symbol, precision, is_active)`
- 新增汇率表：`exchange_rates(currency, date, rate, rate_type, source)`
  - `rate_type`: `spot`/`avg`/`closing`，同日可维护多种汇率口径

### 2. 凭证与分录扩展
- `voucher_entries` 增加字段：
  - `currency_code`：币种代码，默认本位币
  - `fx_rate`：折算率（本位币/外币）
  - `foreign_debit_amount` / `foreign_credit_amount`
- 记账校验口径：仍以本位币借贷平衡为准
- 外币分录录入规则：
  - 若传入 `fx_rate`，直接折算
  - 否则根据 `date` 从 `exchange_rates` 取数

### 2.1 汇率类型与舍入
- `rate_type` 建议支持：`spot`/`closing`/`average`
- 录入凭证默认用 `spot`，期末重估用 `closing`
- 舍入规则：
  - 汇率保留 6 位小数
  - 金额保留 2 位小数（四舍五入）

### 3. 余额与外币余额
- 现有 `balances` 继续保存本位币余额
- 新增 `balances_fx`：
  - `account_code, period, currency_code, dept_id, project_id, customer_id, supplier_id, employee_id`
  - `foreign_opening, foreign_debit, foreign_credit, foreign_closing`
- 记账时同步更新 `balances_fx`

### 4. 期末汇兑重估
- 针对可重估科目（如货币资金、应收、应付）计算期末汇率差：
  - `foreign_closing * period_end_rate - base_closing`
- 差额生成汇兑损益凭证：
  - 收益记入 `fx_gain_account`
  - 损失记入 `fx_loss_account`
- 重估不改变外币余额，只调整本位币余额

### 5. 查询与报表
- 新增命令：
  - `ledger fx rate add/list`
  - `ledger fx balance --period ...`
- 三表仍以本位币输出，汇兑损益计入利润表

## 方案差异（相对现状）
- 从“单币种金额”升级为“原币 + 本位币”并行记录
- 从“无汇率”升级为“按日期取汇率 + 期末重估”
- 从“仅本位币余额”升级为“本位币余额 + 外币余额表”

## 落地步骤与测试（统一版）

0. **表结构与配置（已完成）**
   - 做什么：新增币种/汇率/外币余额表与 forex 配置
   - 测试：初始化后可写入币种与汇率
   - 结果/验收：表创建成功

1. **凭证与记账（已完成）**
   - 做什么：分录支持外币字段与自动折算
   - 测试：外币凭证可记账并更新本位币/外币余额
   - 结果/验收：本位币余额正确、外币余额正确

2. **汇兑重估（已完成）**
   - 做什么：期末重估并生成损益凭证
   - 测试：重估凭证金额正确
   - 结果/验收：利润表体现汇兑损益

3. **汇率类型与可重估科目（已完成）**
   - 做什么：按 `rate_type` 取数；仅对 `revaluable_accounts` 进行重估
   - 测试：同日不同汇率类型可取；非重估科目不生成凭证
   - 结果/验收：仅命中的科目产生汇兑损益

## 可执行测试用例

### 测试环境准备
```bash
rm -f /tmp/ledger_fx.db
ledger init --db-path /tmp/ledger_fx.db
```

### TC-FX-01: 外币凭证录入
- **操作**：录入 USD 外币凭证（fx_rate=7.0）
  - 借：应收账款 100 USD（本位币 700）
  - 贷：主营业务收入 100 USD（本位币 700）
- **预期**：本位币余额更新 700；外币余额更新 100

### TC-FX-02: 汇率自动取数
- **操作**：先写入 2025-01-10 USD 汇率=7.1，再录入外币凭证不传 fx_rate
- **预期**：自动折算为 7.1，凭证平衡

### TC-FX-03: 外币余额查询
- **操作**：`ledger fx balance --period 2025-01`
- **预期**：外币余额与凭证一致

### TC-FX-04: 期末汇兑重估
- **操作**：期末汇率 7.2，外币余额 100 USD，本位币余额 700
- **预期**：重估差额 20，生成汇兑损益凭证

### TC-FX-05: 结账后口径
- **操作**：重估后结账
- **预期**：损益结转含汇兑损益

### TC-FX-06: 汇率类型取数
- **操作**：同一日期维护 `spot=7.1`、`closing=7.2`，录入凭证不传 `fx_rate`
- **预期**：凭证按 `spot` 取数；期末重估按 `closing` 取数

### TC-FX-07: 可重估科目过滤
- **操作**：配置 `revaluable_accounts=["1122"]`，同时存在可重估与非可重估外币余额
- **预期**：仅 `1122` 生成汇兑重估凭证

## 备注
- 本位币口径保持不变，外币余额用于对平与重估
- 具体可重估科目通过配置或科目属性标记
