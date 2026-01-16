# 复杂期间处理与结转模板（详细设计/测试合一）

## Overview
在现有结账/反结账基础上补齐跨期调整、追溯重述与结转模板能力，确保期间口径可复现且流程可控。

## Workflow Type
feature

## Task Scope

**In scope**：
- 结转模板（按期间自动生成结转凭证）
- 跨期调整凭证与口径追溯
- 结账后调整的回溯策略（不改历史、用调整凭证）
- 期间锁定级别（open/closed/adjustment-only）

**Out of scope**：
- 多账簿与多准则
- 审批流与权限体系

## 目标
- 结转规则可配置、可复用
- 结账后仍可通过“调整凭证”修正口径
- 期间状态支持“仅调整”模式

## 当前问题（已解决）

## 核心设计

### 1. 期间状态扩展
- `periods.status` 扩展为：`open` / `closed` / `adjustment`
- `adjustment` 仅允许调整凭证写入

### 2. 调整凭证
- `vouchers` 增加 `entry_type` 字段：`normal` / `adjustment`
- 调整凭证可落在已结账期间，但需期间状态为 `adjustment`
- 记账与余额更新与正常凭证一致，报表需要区分披露

### 2.1 调整口径与滚动规则
- 调整凭证影响本期间余额与报表口径
- 若下一期间无凭证/发生额：自动重算下期期初余额
- 若下一期间已有发生额：生成“调整结转凭证”在下一期间反映差额

### 3. 结转模板
- 新增 `closing_templates`：
  - `code, name, rule_json, is_active`
- `rule_json` 定义：
  - 来源科目范围（按前缀/科目类型）
  - 目标科目（如本年利润）
  - 生成凭证摘要与分录规则
- `ledger close` 增加 `--template <code>` 参数

### 4. 追溯重述策略
- 不直接改历史凭证
- 通过“调整凭证”在历史期间修正
- 报表可在“正常口径/调整口径”之间切换

### 5. 报表披露口径
- 报表接口增加 `scope`：`normal` / `adjustment` / `all`
- `normal`：仅统计 `entry_type=normal`
- `adjustment`：仅统计 `entry_type=adjustment`
- `all`：合并口径，用于对外披露

## 方案差异（相对现状）
- 从“结账后不可录入”升级为“结账后可调整但受控”
- 从“固定结转逻辑”升级为“模板化结转”

## 落地步骤与测试（统一版）

0. **表结构与状态（已完成）**
   - 做什么：扩展 `periods.status` 与新增 `entry_type`
   - 测试：期间状态可切换到 `adjustment`
   - 结果/验收：调整凭证可写入

1. **结转模板（已完成）**
   - 做什么：新增模板表与 `ledger close --template`
   - 测试：不同模板生成不同结转凭证
   - 结果/验收：模板生效且凭证平衡

2. **追溯重述（已完成）**
   - 做什么：历史期间写入调整凭证
   - 测试：历史期间余额与报表口径更新
   - 结果/验收：调整记录可追溯

3. **报表披露口径（已完成）**
   - 做什么：报表支持 `scope` 口径切换
   - 测试：相同期间输出 normal/adjustment/all
   - 结果/验收：口径差异可复现

## 可执行测试用例

### 测试环境准备
```bash
rm -f /tmp/ledger_period.db
ledger init --db-path /tmp/ledger_period.db
```

### TC-PERIOD-01: 期间进入调整状态
- **操作**：切换期间状态为 `adjustment`
- **预期**：仅允许调整凭证记账

### TC-PERIOD-02: 结转模板生效
- **操作**：`ledger close --period 2025-01 --template profit_v1`
- **预期**：生成模板定义的结转凭证

### TC-PERIOD-03: 结账后调整
- **操作**：在 2025-01 录入调整凭证（金额 100）
- **预期**：2025-01 余额更新，若 2025-02 已有凭证则生成调整结转凭证

### TC-PERIOD-04: 正常凭证被拒绝
- **操作**：在 `adjustment` 期间录入 `normal` 凭证
- **预期**：返回错误 `PERIOD_ADJUSTMENT_ONLY`

### TC-PERIOD-05: 报表口径切换
- **操作**：同期间录入 normal 与 adjustment 凭证，分别输出 `scope=normal/adjustment/all`
- **预期**：normal 不含调整；adjustment 仅含调整；all 合并一致

## 备注
- 期间状态与凭证类型仅影响写入权限，不影响历史数据完整性
- 结转模板规则可复用为未来自动凭证体系的基础
