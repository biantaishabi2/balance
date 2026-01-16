# Specification: 管理会计与成本

## Overview
建立成本中心分摊与预算控制闭环，形成管理会计口径。

## Workflow Type
feature

## Task Scope

**In scope**：
- 成本中心/项目维度归集
- 分摊规则与分摊凭证
- 预算控制（占用/释放/冻结）
- 预算-实际差异分析

**Out of scope**：
- 经营预测与绩效模型
- 多版本预算管理

## Success Criteria
- 分摊凭证可生成且借贷平衡
- 超预算按策略提示或阻断
- 预算-实际差异可按维度查询

## Requirements
- 分摊口径支持收入/人数/面积/固定比例
- 分摊基础数据可维护并按期间生效
- 预算控制策略可配置（提示/阻断）

## Files to Modify
- `ledger/database/schema.py`
- `ledger/services.py`
- `ledger/commands/allocation.py`
- `ledger/commands/budget.py`
- `ledger/reporting.py`
- `tests/`

## Files to Reference
- `docs/技术文档/ledger-core/05-management-accounting.md`

## QA Acceptance Criteria
通过测试用例 TC-MA-01 ~ TC-MA-03

## Notes
详细设计见 `docs/技术文档/ledger-core/05-management-accounting.md`
