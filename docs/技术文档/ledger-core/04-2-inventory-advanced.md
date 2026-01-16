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

## 当前问题（需要解决）
- 只有汇总库存，无仓库与批次
- 成本法固定为移动平均

## 核心设计

### 1. 仓库/库位
- `warehouses(id, code, name)`
- `locations(id, warehouse_id, code, name)`
- `inventory_moves` 增加 `warehouse_id` / `location_id`

### 2. 批次/序列号
- `inventory_batches(id, sku, batch_no, qty, cost, status)`
- 入库生成批次，出库消耗批次

### 3. 盘点
- `inventory_counts(id, sku, warehouse_id, counted_qty, book_qty, diff_qty)`
- 盘盈/盘亏生成凭证

### 4. 成本法
- `inventory_cost_method` 配置：`avg`/`fifo`/`standard`
- FIFO：出库按批次先入先出
- 标准成本：出库按标准成本，差异入差异科目

## 方案差异（相对现状）
- 从“汇总库存”升级为“仓库/批次/盘点”
- 从“移动平均”升级为“多成本法”

## 落地步骤与测试（统一版）

0. **仓库与批次（待做）**
   - 做什么：新增仓库、批次表
   - 测试：入库生成批次

1. **盘点差异（待做）**
   - 做什么：盘点生成差异凭证
   - 测试：盘盈盘亏入账

2. **FIFO 与标准成本（待做）**
   - 做什么：切换成本法
   - 测试：出库成本符合预期

## 可执行测试用例

### 测试环境准备
```bash
rm -f /tmp/ledger_inventory.db
ledger init --db-path /tmp/ledger_inventory.db
```

### TC-INV-01: 批次入库/出库
- **操作**：批次入库 → FIFO 出库
- **预期**：出库成本与批次一致

### TC-INV-02: 盘点差异
- **操作**：盘盈/盘亏
- **预期**：差异凭证生成

### TC-INV-03: 标准成本
- **操作**：切换标准成本并出库
- **预期**：差异计入差异科目

## 备注
- 成本法切换需限定期间与库存状态
