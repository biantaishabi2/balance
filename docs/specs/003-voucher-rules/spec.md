# Specification: 凭证模板与业务规则引擎

## Overview
建立凭证模板库与业务规则引擎，支持事件驱动自动生成凭证。

## Workflow Type
feature

## Task Scope

**In scope**：
- 凭证模板 CRUD 与启停管理
- 业务事件与模板映射
- 模板表达式与校验规则
- 自动生成凭证并落库

**Out of scope**：
- 复杂工作流编排
- UI 模板设计器

## Success Criteria
- 模板可启用/禁用并被事件触发
- 自动生成凭证借贷平衡
- 校验失败时阻断并返回错误
- 模板变更即时生效

## Requirements
- 模板表达式支持常量/字段/条件判断
- 规则校验包含借贷平衡与必填项
- 自动生成需记录事件来源与幂等标识

## Files to Modify
- `ledger/database/schema.py`
- `ledger/services.py`
- `ledger/commands/record.py`
- `ledger/commands/template.py`
- `tests/`

## Files to Reference
- `docs/技术文档/ledger-core/03-voucher-rules.md`

## QA Acceptance Criteria
通过测试用例 TC-TPL-01 ~ TC-TPL-04

## Notes
详细设计见 `docs/技术文档/ledger-core/03-voucher-rules.md`
