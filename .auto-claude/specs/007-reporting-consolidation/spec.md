# Specification: 报表与合并

## Overview
支持多账套合并、内部抵销与模板化报表输出，形成集团口径。

## Workflow Type
feature

## Task Scope

**In scope**：
- 多公司/多账套合并
- 内部往来与交易抵销
- 合并币种折算
- 报表模板与自定义指标

**Out of scope**：
- 全量 BI 平台
- 复杂税务合并

## Success Criteria
- 合并报表可输出并对平
- 抵销后内部往来清零
- 外币折算按口径生效

## Requirements
- 集团本位币与汇率表支持
- 折算规则区分资产/负债/利润
- 抵销凭证不回写子账

## Files to Modify
- `ledger/database/schema.py`
- `ledger/reporting.py`
- `ledger/reporting_consolidation.py`
- `ledger/commands/report.py`
- `tests/`

## Files to Reference
- `docs/技术文档/ledger-core/07-reporting-consolidation.md`

## QA Acceptance Criteria
通过测试用例 TC-CON-01 ~ TC-CON-03

## Notes
详细设计见 `docs/技术文档/ledger-core/07-reporting-consolidation.md`
