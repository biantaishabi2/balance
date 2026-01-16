# Specification: 内控与审计

## Overview
补齐审计日志、审批流与稽核规则，形成可追溯的内控体系。

## Workflow Type
feature

## Task Scope

**In scope**：
- 操作日志与审计轨迹
- 审批流程（凭证/结账/反结账）
- 稽核规则库与执行

**Out of scope**：
- 复杂权限体系
- UI 审批界面

## Success Criteria
- 关键操作写入审计日志
- 审批状态流转可追踪
- 稽核规则可触发并记录

## Requirements
- 审计日志包含 actor/request/tenant 等关键字段
- 审批最小状态机可用
- 稽核规则可配置与复用

## Files to Modify
- `ledger/database/schema.py`
- `ledger/services.py`
- `ledger/commands/approve.py`
- `ledger/commands/review.py`
- `tests/`

## Files to Reference
- `docs/技术文档/ledger-core/08-audit-control.md`

## QA Acceptance Criteria
通过测试用例 TC-AUDIT-01 ~ TC-AUDIT-03

## Notes
详细设计见 `docs/技术文档/ledger-core/08-audit-control.md`
