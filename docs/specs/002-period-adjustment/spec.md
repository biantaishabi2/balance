# Specification: 复杂期间处理与结转模板

## Overview
补齐结转模板、跨期调整与期间锁定层级，确保结账后口径可追溯。

## Workflow Type
feature

## Task Scope

**In scope**：
- 结转模板配置与期间自动生成
- 调整凭证（结账后口径修正）
- 期间状态分级（open/closed/adjustment）
- 追溯重述与披露标识

**Out of scope**：
- 多账簿与多准则
- 审批流与权限体系

## Success Criteria
- 结转模板可配置并生成凭证
- 结账后仅允许调整凭证写入
- 调整凭证影响口径但不覆盖历史
- 报表可区分正常/调整口径

## Requirements
- `periods.status` 支持 `open`/`closed`/`adjustment`
- `vouchers.entry_type` 支持 `normal`/`adjustment`
- 结转模板可按期间复用
- 报表与余额查询支持调整披露

## Files to Modify
- `ledger/database/schema.py`
- `ledger/services.py`
- `ledger/commands/close.py`
- `ledger/commands/reopen.py`
- `ledger/commands/record.py`
- `tests/`

## Files to Reference
- `docs/技术文档/ledger-core/02-period-adjustment.md`

## QA Acceptance Criteria
通过测试用例 TC-PERIOD-01 ~ TC-PERIOD-04

## Notes
详细设计见 `docs/技术文档/ledger-core/02-period-adjustment.md`
