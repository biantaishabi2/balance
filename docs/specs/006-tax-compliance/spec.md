# Specification: 合规与税务

## Overview
补齐发票/税控联动、税会差异与基础税务报表，形成合规闭环。

## Workflow Type
feature

## Task Scope

**In scope**：
- 发票档案与凭证关联
- 增值税与所得税口径
- 税会差异与递延税
- 税务报表基础输出

**Out of scope**：
- 复杂税务筹划
- 多准则多账簿

## Success Criteria
- 发票与凭证一致可追溯
- VAT/所得税口径汇总准确
- 税会差异可记录与披露

## Requirements
- 税额科目映射可配置
- 税率按票面/规则取数
- 税会差异支持永久性/暂时性

## Files to Modify
- `ledger/database/schema.py`
- `ledger/services.py`
- `ledger/commands/invoice.py`
- `ledger/reporting.py`
- `tests/`

## Files to Reference
- `docs/技术文档/ledger-core/06-tax-compliance.md`

## QA Acceptance Criteria
通过测试用例 TC-TAX-01 ~ TC-TAX-03

## Notes
详细设计见 `docs/技术文档/ledger-core/06-tax-compliance.md`
