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

## 当前问题（需要解决）
- 仅支持新增、折旧与处置
- 无减值/转固
- 折旧费用无法分摊

## 核心设计

### 1. 资产变动
- 新增 `fixed_asset_changes`：
  - `asset_id, change_type, amount, date, voucher_id`
- 变动类型：`upgrade`/`transfer`/`split`

### 2. 资产减值
- `fixed_asset_impairments`：
  - `asset_id, period, amount, voucher_id`
- 减值与冲回生成凭证

### 3. 在建工程
- `cip_projects`：
  - `id, name, cost, status`
- `cip_transfers`：
  - `project_id, asset_id, amount, date`
- 转固生成凭证

### 4. 折旧分摊
- 折旧凭证按成本中心维度拆分分录
- 分摊规则：按比例或固定金额

## 方案差异（相对现状）
- 从“折旧为主”升级为“全生命周期管理”

## 落地步骤与测试（统一版）

0. **资产变动与减值（待做）**
   - 做什么：新增变动/减值表
   - 测试：变动与减值凭证

1. **在建工程转固（待做）**
   - 做什么：CIP 转固
   - 测试：转固凭证与资产状态

2. **折旧分摊（待做）**
   - 做什么：折旧按成本中心分摊
   - 测试：分摊分录正确

## 可执行测试用例

### 测试环境准备
```bash
rm -f /tmp/ledger_fa.db
ledger init --db-path /tmp/ledger_fa.db
```

### TC-FA-01: 资产变动
- **操作**：资产改扩建与拆分
- **预期**：变动凭证正确

### TC-FA-02: 资产减值
- **操作**：计提减值与冲回
- **预期**：损益科目正确

### TC-FA-03: CIP 转固
- **操作**：在建工程转固
- **预期**：固定资产增加、CIP 减少

### TC-FA-04: 折旧分摊
- **操作**：按成本中心分摊折旧
- **预期**：分摊分录正确

## 备注
- 成本中心可使用现有维度（department/project）
