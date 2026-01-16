# Specification: 多币种与汇兑处理

## Overview
补齐外币凭证、汇率管理、期末重估与汇兑损益，形成多币种记账闭环。

## Workflow Type
feature

## Task Scope

**In scope**：
- 汇率表与汇率类型（现汇/平均/期末）
- 外币凭证录入与本位币折算
- 期末重估与汇兑损益凭证
- 外币余额查询与披露口径

**Out of scope**：
- 复杂金融工具与套期保值
- 多账簿/多准则并存

## Success Criteria
- 外币凭证录入成功，本位币金额与汇率一致
- 期末重估生成凭证并计入汇兑损益
- 余额查询同时展示外币与本位币
- 汇率按日期/类型正确取数

## Requirements
- 账套设置本位币 `base_currency`
- 支持 `spot`/`avg`/`closing` 汇率类型
- 关键金额按 2 位小数四舍五入
- 支持配置 `revaluable_accounts`

## Files to Modify
- `ledger/database/schema.py`
- `ledger/services.py`
- `ledger/commands/record.py`
- `ledger/commands/query.py`
- `ledger/commands/close.py`
- `tests/`

## Files to Reference
- `docs/技术文档/ledger-core/01-multicurrency.md`

## QA Acceptance Criteria
通过测试用例 TC-FX-01 ~ TC-FX-05

## Notes
详细设计见 `docs/技术文档/ledger-core/01-multicurrency.md`
