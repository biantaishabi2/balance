# 固定资产深度能力（详细设计/测试合一）

## Overview
在现有固定资产新增/折旧/处置基础上补齐资产变动、减值、在建工程与成本中心分摊。

## Workflow Type
feature

## Task Scope

**In scope**：
- 资产变动（改扩建/转移/拆分）
- 资产减值与减值冲回
- 在建工程（CIP）转固
- 折旧费用分摊到成本中心

**Out of scope**：
- 租赁会计
- 复杂税务折旧

## 目标
- 固定资产全生命周期可追踪
- 折旧费用可分摊到维度
- 减值与转固有完整凭证

## 当前问题（已解决）
- 仅支持新增、折旧与处置
- 无减值/转固
- 折旧费用无法分摊

## 核心设计

### 1. 资产变动
- 新增 `fixed_asset_changes`：
  - `asset_id, change_type, amount, date, voucher_id`
- 变动类型：`upgrade`/`transfer`/`split`
- `upgrade`：增加资产原值，凭证借“固定资产”，贷“银行存款/应付账款”
- `transfer`：仅维度/使用部门变更，不改变金额（`fixed_assets.dept_id/project_id`）
- `split`：按比例拆分原值/累计折旧/净值，记录变动但不生成金额凭证

### 2. 资产减值
- `fixed_asset_impairments`：
  - `asset_id, period, amount, voucher_id`
- 减值凭证：借“资产减值损失”，贷“固定资产减值准备”
- 减值冲回：借“固定资产减值准备”，贷“资产减值损失”（或“营业外收入”，按会计政策配置）

### 3. 在建工程
- `cip_projects`：
  - `id, name, cost, status`
- `cip_transfers`：
  - `project_id, asset_id, amount, date`
- 在建期间计入“在建工程”科目
- 转固凭证：借“固定资产”，贷“在建工程”
- 支持部分转固，剩余金额保留在 CIP，状态保持 `ongoing`
- 全额转固后状态更新为 `converted`
- 转固后自下一期间开始折旧

### 4. 折旧分摊
- 折旧凭证按成本中心维度拆分分录
- 分摊规则：资产自定义比例优先，否则按期间分摊基础
- 分摊基础数据：
  - `allocation_basis_values(period, dim_type, dim_id, value)`
  - 常用口径：面积/人数/收入
  - 分摊维度优先级：department → project → customer → supplier → employee

### 5. 子账科目映射
- 固定资产业务科目映射通过 `data/subledger_mapping.json` 配置
- 关键键位：
  - `fixed_asset.asset_account` / `fixed_asset.accum_depreciation_account`
  - `fixed_asset.depreciation_expense_account` / `fixed_asset.cip_account`
  - `fixed_asset.impairment_loss_account` / `fixed_asset.impairment_reserve_account`

## 方案差异（相对现状）
- 从“折旧为主”升级为“全生命周期管理”

## 落地步骤与测试（统一版）

0. **资产变动与减值（已完成）**
   - 做什么：新增变动/减值表
   - 测试：变动与减值凭证

0.1 **减值冲回（已完成）**
   - 做什么：支持减值冲回凭证
   - 测试：冲回凭证金额与方向正确

1. **在建工程转固（已完成）**
   - 做什么：CIP 转固
   - 测试：转固凭证与资产状态

2. **折旧分摊（已完成）**
   - 做什么：折旧按成本中心分摊
   - 测试：分摊分录正确

## 可执行测试用例

### 测试环境准备
```bash
rm -f /tmp/ledger_fa.db
ledger init --db-path /tmp/ledger_fa.db
```

### TC-FA-01: 资产变动
- **操作**：
  1) 资产原值 100,000
  2) 改扩建支出 20,000
  3) 按 6:4 拆分资产
- **预期**：
  - 改扩建凭证：借“固定资产”20,000，贷“银行存款”20,000
  - 拆分后原值分别为 72,000 与 48,000

### TC-FA-02: 资产减值
- **操作**：
  1) 计提减值 10,000
  2) 冲回减值 4,000
- **预期**：
  - 减值凭证：借“资产减值损失”10,000，贷“固定资产减值准备”10,000
  - 冲回凭证：借“固定资产减值准备”4,000，贷“资产减值损失”4,000

### TC-FA-03: CIP 转固
- **操作**：
  1) CIP 累计 50,000
  2) 部分转固 20,000
  3) 余量转固 30,000
- **预期**：
  - 部分转固凭证：借“固定资产”20,000，贷“在建工程”20,000
  - 剩余金额保留在 CIP，状态为 `ongoing`
  - 余量转固后状态为 `converted`，下期计提折旧

### TC-FA-04: 折旧分摊
- **操作**：
  1) 当期折旧 10,000
  2) 成本中心 A:60，B:40
- **预期**：
  - 分摊凭证：借“制造费用(A)”6,000，借“制造费用(B)”4,000，贷“累计折旧”10,000

### TC-FA-05: 映射配置生效
- **操作**：调整固定资产映射科目后生成折旧/减值凭证
- **预期**：分录科目按新映射落账

## 备注
- 成本中心可使用现有维度（department/project）
