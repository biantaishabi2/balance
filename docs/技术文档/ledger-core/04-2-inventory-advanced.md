# 存货深度能力（详细设计/测试合一）

## Overview
在现有存货入库/出库基础上补齐仓库/库位、批次/序列号、盘点与高级成本法（FIFO/标准成本）。

## Workflow Type
feature

## Task Scope

**In scope**：
- 仓库/库位管理
- 批次/序列号
- 盘点与盘盈盘亏
- FIFO 与标准成本（可配置）

**Out of scope**：
- 生产领用与制造流程
- 复杂供应链与采购计划

## 目标
- 存货可追溯到仓库/批次
- 支持多种成本法
- 盘点差异可入账

## 当前问题（部分已解决）
- 序列号追溯尚未落地

## 核心设计

### 1. 仓库/库位
- `warehouses(id, code, name)`
- `locations(id, warehouse_id, code, name)`
- `inventory_moves` 增加 `warehouse_id` / `location_id`

### 2. 批次/序列号
- `inventory_batches(id, sku, batch_no, qty, cost, status)`
- 入库生成批次，出库消耗批次
- 序列号追溯：
  - `inventory_serials(serial_no, sku, status, move_in_id, move_out_id, warehouse_id, location_id)`
  - 入库登记序列号，出库时校验并占用

### 3. 盘点
- `inventory_counts(id, sku, warehouse_id, counted_qty, book_qty, diff_qty)`
- 盘盈/盘亏生成凭证

### 4. 成本法
- `inventory_cost_method` 配置：`avg`/`fifo`/`standard`
- FIFO：出库按批次先入先出
- 标准成本：
  - `standard_costs(sku, period, cost, variance_account_id)`
  - 入库按标准成本入账，实际采购价与标准成本差异计入差异科目
  - 出库按标准成本计价，差异不在出库时产生
  - 差异科目按存货类别映射（如：原材料/库存商品）

### 5. 负库存处理
- `inventory_negative_policy`：`reject`（默认）/`allow`
- `reject`：出库数量超过可用库存直接报错
- `allow`：按最近一次有效成本出库，记录负数部分 `pending_cost_adjustment` 待后续入库冲回
- 负库存被入库覆盖时，按实际入库成本与预估成本差额生成“负库存成本调整”凭证并清理 `pending_cost_adjustment`

### 6. 子账科目映射
- 存货科目映射通过 `data/subledger_mapping.json` 配置
- 关键键位：`inventory.inventory_account` / `inventory.cost_account` / `inventory.offset_account`

## 方案差异（相对现状）
- 从“汇总库存”升级为“仓库/批次/盘点”
- 从“移动平均”升级为“多成本法”

## 落地步骤与测试（统一版）

0. **仓库/批次（已完成）**
   - 做什么：新增仓库、批次表
   - 测试：入库生成批次

1. **盘点差异（已完成）**
   - 做什么：盘点生成差异凭证
   - 测试：盘盈盘亏入账

2. **FIFO 与标准成本（已完成）**
   - 做什么：切换成本法、配置标准成本与差异科目
   - 测试：出库成本与差异凭证符合预期

3. **负库存策略（已完成）**
   - 做什么：配置负库存策略，允许路径在入库时生成调整凭证并清理 pending
   - 测试：拒绝/允许路径符合预期

4. **序列号追溯（待做）**
   - 做什么：入库登记序列号并在出库时校验/占用
   - 测试：序列号出入库状态可追溯

## 可执行测试用例

### 测试环境准备
```bash
rm -f /tmp/ledger_inventory.db
ledger init --db-path /tmp/ledger_inventory.db
```

### TC-INV-01: 批次入库/出库
- **操作**：
  1) SKU-A 入库 10 件，单价 10（批次 B1）
  2) SKU-A 入库 5 件，单价 12（批次 B2）
  3) FIFO 出库 12 件
- **预期**：
  - 成本 = 10*10 + 2*12 = 124
  - 批次 B2 剩余 3 件，成本 36
  - 生成出库凭证：借“主营业务成本”124，贷“库存商品”124

### TC-INV-02: 盘点差异
- **操作**：
  1) 账面库存 10 件（单价 10）
  2) 盘点数量 8 件
- **预期**：
  - 差异数量 -2 件，差异金额 -20
  - 凭证：借“盘点损失/管理费用”20，贷“库存商品”20

### TC-INV-03: 标准成本
- **操作**：
  1) 标准成本=10，差异科目=“存货成本差异”
  2) 入库 10 件，采购单价 12
  3) 出库 5 件
- **预期**：
  - 入库凭证：借“库存商品”100，借“存货成本差异”20，贷“应付账款”120
  - 出库凭证：借“主营业务成本”50，贷“库存商品”50

### TC-INV-04: 负库存策略
- **操作**：
  1) 账面库存 2 件
  2) 出库 3 件
  3) 入库 1 件，单价高于出库估值
- **预期**：
  - `reject`：报错并拒绝出库
  - `allow`：按最近成本出库并记录 `pending_cost_adjustment`
  - 入库后生成“负库存成本调整”凭证，库存数量与金额归零

### TC-INV-05: 序列号追溯
- **操作**：入库登记序列号 SN001/SN002，出库指定 SN001
- **预期**：SN001 状态为已出库且关联出库记录，SN002 仍在库

## 备注
- 成本法切换需限定期间与库存状态
