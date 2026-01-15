# Specification: Ledger三表引擎（账务口径）

## Overview
新增账务口径三表引擎，直接基于凭证/余额生成报表，并与现有 balance 模型并存。

## Workflow Type
feature

## Task Scope

**In scope**：
- 新增账务口径三表引擎（资产负债表/利润表/现金流量表）
- 新增报表映射配置 `data/report_mapping.json`
- `ledger report` 支持 `--engine ledger|balance` 切换（默认保持 `balance`）
- 报表对平校验：资产=负债+权益；现金净增加=期末现金-期初现金
- 支持按期间/维度过滤生成报表（`--dept-id`/`--project-id`/`--customer-id`/`--supplier-id`/`--employee-id`）

**Out of scope**：
- 预测/预算/配平模型替代
- 报表模板/Excel样式输出
- 科目体系升级或历史数据迁移

## Success Criteria
- `ledger report --engine ledger` 输出三表且与余额表口径一致
- 资产负债表对平，现金净增加与现金期末变动一致
- 映射配置变更后报表汇总字段随之变化
- 现有 `balance` 模型不受影响

## Requirements
- 账务口径不依赖利率/税率/折旧假设
- 映射配置可按科目前缀/科目类型定义
- 现金流量表采用间接法口径
- 映射字段包含 `prefixes`、`source`（opening_balance/closing_balance/debit_amount/credit_amount）、`direction`（debit/credit）
- 保持现有 `ledger report` JSON 输出结构

## Dev Environment

| 配置 | 值 |
|------|-----|
| Python | 3.8+ |
| 数据库 | SQLite (文件: ledger.db) |
| Worktree | .worktrees/002-ledger-report-engine |

测试命令：
```bash
cd .worktrees/002-ledger-report-engine
python3 -m pytest tests/ -v
bash scripts/ledger_smoke.sh
```

## Files to Modify
- `ledger/commands/report.py` - 新增 `--engine` 参数
- `ledger/reporting.py` - 入口选择引擎
- `ledger/reporting_engine.py` - 账务口径三表引擎
- `ledger/services.py` - 余额/凭证读取辅助
- `data/report_mapping.json` - 报表映射配置
- `docs/LEDGER_DESIGN.md` - 设计文档补充
- `docs/LEDGER_TEST_PLAN.md` - 测试计划补充

## Files to Reference
- `docs/LEDGER_DESIGN.md`
- `docs/LEDGER_TEST_PLAN.md`
- `data/standard_accounts.json`
- `data/balance_mapping.json`
- `balance.py`

## QA Acceptance Criteria

通过测试用例 TC-LEDGER-RE-01 ~ TC-LEDGER-RE-06

- TC-LEDGER-RE-01: 账务三表可生成（`--engine ledger`）
- TC-LEDGER-RE-02: 资产负债表对平
- TC-LEDGER-RE-03: 现金净增加与期末现金变动一致
- TC-LEDGER-RE-04: 利润表金额与发生额一致
- TC-LEDGER-RE-05: 映射文件变更生效
- TC-LEDGER-RE-06: 维度过滤报表正确

## Test Setup

```bash
rm -f /tmp/test_ledger.db
python3 ledger.py init --db-path /tmp/test_ledger.db

cat <<JSON | python3 ledger.py record --db-path /tmp/test_ledger.db --auto
{
  "date": "2025-01-15",
  "description": "账务三表测试",
  "entries": [
    {"account": "库存现金", "debit": 1000},
    {"account": "主营业务收入", "credit": 1000}
  ]
}
JSON
```

## Test Cases

### TC-LEDGER-RE-01: 账务三表生成
- **操作**：运行 `ledger report --period 2025-01 --engine ledger`
- **预期**：返回三表结构，包含 `balance_sheet`/`income_statement`/`cash_flow_statement`

### TC-LEDGER-RE-02: 资产负债表对平
- **操作**：运行 `ledger report --period 2025-01 --engine ledger`
- **预期**：`total_assets = total_liabilities + total_equity`

### TC-LEDGER-RE-03: 现金净增加对平
- **操作**：运行 `ledger report --period 2025-01 --engine ledger`
- **预期**：`net_change = closing_cash - opening_cash`（间接法）

### TC-LEDGER-RE-04: 利润表发生额一致
- **操作**：运行 `ledger report --period 2025-01 --engine ledger`
- **预期**：收入/成本/费用与本期发生额汇总一致

### TC-LEDGER-RE-05: 映射配置生效
- **操作**：调整 `data/report_mapping.json` 前缀并重跑报表
- **预期**：报表汇总字段随映射变化

### TC-LEDGER-RE-06: 维度过滤
- **操作**：`ledger report --period 2025-01 --engine ledger --dept-id 1`
- **预期**：报表仅统计指定维度

## Step-by-step Validation

0. **账务三表引擎骨架（待做）**
   - 做什么：新增 `reporting_engine.py` 并实现入口
   - 测试：运行 `ledger report --engine ledger`
   - 验收：输出结构完整

1. **映射配置加载（待做）**
   - 做什么：新增 `data/report_mapping.json`
   - 测试：修改映射并观察报表变化
   - 验收：映射生效

2. **对平校验（待做）**
   - 做什么：资产负债表/现金对平逻辑
   - 测试：对平校验用例
   - 验收：对平通过

3. **维度过滤（待做）**
   - 做什么：按维度汇总余额与凭证
   - 测试：`--dept-id` 等过滤
   - 验收：维度报表正确

## Notes
- 账务口径不替代 `balance` 模型，保留并存
- 映射配置以科目前缀为主，必要时支持科目类型
- `data/report_mapping.json` 顶层包含 `balance_sheet`/`income_statement`/`cash_flow`

## Progress
- [ ] 设计文档补充
- [ ] 测试计划补充
- [ ] 账务口径三表引擎实现
- [ ] 报表映射配置
- [ ] 测试用例通过

## Next
- 同步设计/测试文档
- 实现报表引擎并补测
