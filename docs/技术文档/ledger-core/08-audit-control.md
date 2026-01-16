# 内控与审计（详细设计/测试合一）

## Overview
在现有记账基础上补齐审批、审计轨迹与稽核规则，形成可追溯的内控体系。

## Workflow Type
feature

## Task Scope

**In scope**：
- 操作日志与审计轨迹
- 审批流程（凭证、结账、反结账）
- 稽核规则库与自动校验

**Out of scope**：
- 复杂权限体系
- UI 审批界面

## 目标
- 关键操作可追溯
- 凭证与结账过程可审计

## 当前问题（需要解决）
- 无审计日志
- 无审批与稽核规则

## 核心设计

### 1. 操作日志
- `audit_logs`：
  - `id, actor, action, target_type, target_id, detail, created_at`
- 关键操作均写日志

### 2. 审批流
- `approvals`：
  - `id, target_type, target_id, status, created_at`
- 凭证/结账/反结账触发审批

### 3. 稽核规则
- `audit_rules`：
  - `id, code, name, rule_json`
- 规则执行后给出风险提示

## 方案差异（相对现状）
- 从“无内控”升级为“可审计+可审批”

## 落地步骤与测试（统一版）

0. **审计日志（待做）**
   - 做什么：新增日志表与记录
   - 测试：关键操作写入日志

1. **审批流程（待做）**
   - 做什么：新增审批表与状态
   - 测试：审批前后状态变化

2. **稽核规则（待做）**
   - 做什么：规则库与执行
   - 测试：触发规则提示

## 可执行测试用例

### 测试环境准备
```bash
rm -f /tmp/ledger_audit.db
ledger init --db-path /tmp/ledger_audit.db
```

### TC-AUDIT-01: 操作日志
- **操作**：录入凭证、结账
- **预期**：audit_logs 有记录

### TC-AUDIT-02: 审批流
- **操作**：提交审批并通过
- **预期**：状态从 pending → approved

### TC-AUDIT-03: 稽核规则
- **操作**：触发稽核规则
- **预期**：输出风险提示

## 备注
- 审批流先做最简状态机，权限后置
