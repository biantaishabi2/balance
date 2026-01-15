# Specification: Ledger子账模块（往来/存货/固定资产）

## Overview
在主账基础上补齐往来核销、存货核算与固定资产模块，形成完整后端账务能力。

## Workflow Type
feature

## Task Scope

**In scope**：
- 往来核销：应收/应付明细、核销记录、账龄基础查询
- 存货核算：入库/出库、结存、成本结转（移动平均）
- 固定资产：资产卡片、折旧计提、资产处置
- 子账操作自动生成凭证并过账

**Out of scope**：
- 多币种与汇兑处理
- UI 与审批权限
- 高级成本法（标准成本/先进先出）

## Success Criteria
- 往来核销后主账余额与子账一致
- 存货结存与成本结转可核对
- 固定资产折旧自动生成凭证
- 子账与总账对平

## Requirements
- 子账操作必须生成平衡凭证
- 支持期间/维度过滤查询
- 不引入多币种

## Dev Environment

| 配置 | 值 |
|------|-----|
| Python | 3.8+ |
| 数据库 | SQLite (文件: ledger.db) |
| Worktree | .worktrees/004-ledger-subledgers |

测试命令：
```bash
cd .worktrees/004-ledger-subledgers
python3 -m pytest tests/ -v
bash scripts/ledger_smoke.sh
```

## Files to Modify
- `ledger/commands/ar.py` - 应收模块
- `ledger/commands/ap.py` - 应付模块
- `ledger/commands/inventory.py` - 存货模块
- `ledger/commands/fixed_asset.py` - 固定资产模块
- `ledger/services.py` - 子账与凭证生成
- `ledger/database/schema.py` - 子账表结构
- `tests/` - 子账测试
- `docs/LEDGER_DESIGN.md`
- `docs/LEDGER_TEST_PLAN.md`

## Files to Reference
- `docs/LEDGER_DESIGN.md`
- `docs/LEDGER_TEST_PLAN.md`
- `data/standard_accounts.json`

## QA Acceptance Criteria

通过测试用例 TC-LEDGER-SUB-01 ~ TC-LEDGER-SUB-06

- TC-LEDGER-SUB-01: 应收录入与核销生成凭证
- TC-LEDGER-SUB-02: 应付录入与核销生成凭证
- TC-LEDGER-SUB-03: 存货入库/出库与结存
- TC-LEDGER-SUB-04: 成本结转凭证正确
- TC-LEDGER-SUB-05: 固定资产折旧凭证生成
- TC-LEDGER-SUB-06: 子账与总账对平

## Test Setup

```bash
rm -f /tmp/test_ledger.db
python3 ledger.py init --db-path /tmp/test_ledger.db
```

## Notes
- 存货成本默认使用移动平均法
- 固定资产折旧按直线法

## Progress
- [ ] 设计文档补充
- [ ] 测试计划补充
- [ ] 往来核销实现
- [ ] 存货核算实现
- [ ] 固定资产实现
- [ ] 测试用例通过

## Next
- 创建 worktree 并开始实现
