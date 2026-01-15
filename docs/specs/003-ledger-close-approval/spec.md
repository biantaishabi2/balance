# Specification: Ledger期末结账与凭证审核流程

## Overview
新增期末结账与凭证审核流程，完善凭证流转与期间关闭，保证账务口径一致。

## Workflow Type
feature

## Task Scope

**In scope**：
- 凭证审核流程：制单(draft) → 审核(reviewed) → 记账(confirmed)
- 记账前置校验：未审核凭证不可记账
- 期末结账：关闭期间、结转本期损益到权益、生成下期余额
- 关闭期间后禁止新增/记账凭证
- `ledger close`/`ledger reopen` 命令

**Out of scope**：
- 权限与审批角色
- UI 流程与消息通知
- 多币种与外币折算

## Success Criteria
- `ledger review`/`ledger unreview` 可切换凭证审核状态
- `ledger confirm` 仅允许审核后凭证记账
- `ledger close --period` 关闭期间并生成下期余额
- 结账后期间不可新增/记账凭证
- 期末损益正确结转到权益（本年利润/利润分配）

## Requirements
- 保持现有 `ledger confirm` 行为不回退
- 支持指定期间结账
- 期末结转逻辑可配置科目（本年利润/利润分配）

## Dev Environment

| 配置 | 值 |
|------|-----|
| Python | 3.8+ |
| 数据库 | SQLite (文件: ledger.db) |
| Worktree | .worktrees/003-ledger-close-approval |

测试命令：
```bash
cd .worktrees/003-ledger-close-approval
python3 -m pytest tests/ -v
bash scripts/ledger_smoke.sh
```

## Files to Modify
- `ledger/commands/confirm.py` - 记账前置审核校验
- `ledger/commands/review.py` - 审核凭证
- `ledger/commands/unreview.py` - 反审核
- `ledger/commands/close.py` - 期末结账
- `ledger/commands/reopen.py` - 反结账
- `ledger/services.py` - 期间关闭、损益结转
- `ledger/database/schema.py` - 期间/凭证状态调整
- `tests/` - 新增审核与结账测试
- `docs/LEDGER_DESIGN.md`
- `docs/LEDGER_TEST_PLAN.md`

## Files to Reference
- `docs/LEDGER_DESIGN.md`
- `docs/LEDGER_TEST_PLAN.md`
- `data/standard_accounts.json`

## QA Acceptance Criteria

通过测试用例 TC-LEDGER-CLOSE-01 ~ TC-LEDGER-CLOSE-06

- TC-LEDGER-CLOSE-01: 审核/反审核状态切换
- TC-LEDGER-CLOSE-02: 未审核凭证禁止记账
- TC-LEDGER-CLOSE-03: 期末结账成功并生成下期余额
- TC-LEDGER-CLOSE-04: 结账期间禁止新增/记账
- TC-LEDGER-CLOSE-05: 损益结转到权益科目
- TC-LEDGER-CLOSE-06: 反结账恢复可记账状态

## Test Setup

```bash
rm -f /tmp/test_ledger.db
python3 ledger.py init --db-path /tmp/test_ledger.db
```

## Test Cases

### TC-LEDGER-CLOSE-01: 审核/反审核
- **操作**：`ledger review 1`、`ledger unreview 1`
- **预期**：凭证状态在 draft/reviewed 间切换

### TC-LEDGER-CLOSE-02: 未审核禁止记账
- **操作**：`ledger confirm 1`
- **预期**：返回错误 `VOUCHER_NOT_REVIEWED`

### TC-LEDGER-CLOSE-03: 期末结账
- **操作**：`ledger close --period 2025-01`
- **预期**：期间状态变为 closed，下期余额生成

### TC-LEDGER-CLOSE-04: 结账后禁止记账
- **操作**：`ledger record`/`ledger confirm`
- **预期**：返回错误 `PERIOD_CLOSED`

### TC-LEDGER-CLOSE-05: 损益结转
- **操作**：结账后查询权益科目
- **预期**：本期损益结转到权益

### TC-LEDGER-CLOSE-06: 反结账
- **操作**：`ledger reopen --period 2025-01`
- **预期**：期间状态恢复 open

## Notes
- 期末结转默认使用本年利润与利润分配科目，可通过配置覆盖

## Progress
- [ ] 设计文档补充
- [ ] 测试计划补充
- [ ] 审核流程实现
- [ ] 结账逻辑实现
- [ ] 测试用例通过

## Next
- 创建 worktree 并开始实现
