# Specification: 子账深度能力（应收应付/存货/固定资产）

## Overview
补齐子账深度能力，覆盖应收应付高级功能、存货高级成本法与固定资产全生命周期。

## Workflow Type
feature

## Task Scope

**In scope**：
- 应收/应付：信用管理、票据、收付款计划、坏账计提
- 存货：仓库/库位、批次/序列号、盘点、FIFO/标准成本
- 固定资产：资产变动、减值、在建工程转固、折旧分摊
- 子账操作自动生成总账凭证

**Out of scope**：
- 生产领用与制造流程
- 租赁会计
- UI 与权限

## Success Criteria
- 子账与总账对平
- 高级成本法与差异凭证正确
- 固定资产变动/减值/转固有完整凭证
- 应收应付信用与票据流程可追踪

## Requirements
- 子账与总账科目映射可配置
- 子账凭证必须借贷平衡
- 批次/序列号需可追溯
- 折旧分摊支持按维度分配

## Files to Modify
- `ledger/database/schema.py`
- `ledger/services.py`
- `ledger/commands/ar.py`
- `ledger/commands/ap.py`
- `ledger/commands/inventory.py`
- `ledger/commands/fixed_asset.py`
- `tests/`

## Files to Reference
- `docs/技术文档/ledger-core/04-1-ar-ap-advanced.md`
- `docs/技术文档/ledger-core/04-2-inventory-advanced.md`
- `docs/技术文档/ledger-core/04-3-fixed-asset-advanced.md`

## QA Acceptance Criteria
通过测试用例 TC-ARAP-01 ~ TC-ARAP-04、TC-INV-01 ~ TC-INV-04、TC-FA-01 ~ TC-FA-04

## Notes
详细设计见 `docs/技术文档/ledger-core/04-1-ar-ap-advanced.md`、`docs/技术文档/ledger-core/04-2-inventory-advanced.md`、`docs/技术文档/ledger-core/04-3-fixed-asset-advanced.md`
