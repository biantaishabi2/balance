# 凭证模板与规则引擎（详细设计/测试合一）

## Overview
在现有记账流程上增加凭证模板与规则引擎，实现业务事件到凭证的自动映射与校验。

## Workflow Type
feature

## Task Scope

**In scope**：
- 凭证模板管理（字段、分录规则、维度映射）
- 规则引擎（事件参数 → 凭证分录）
- 模板校验（借贷平衡、科目合法性）
- API/CLI 触发自动凭证生成

**Out of scope**：
- 审批流与权限
- UI 设计器
- 多账簿

## 目标
- 标准业务（收款/付款/费用/折旧）可通过模板自动生成凭证
- 可复用、可配置、可回溯

## 当前问题（部分已解决）
- 条件表达式与事件幂等未支持

## 核心设计

### 1. 凭证模板表
- `voucher_templates(code, name, rule_json, is_active, created_at)`
- `rule_json` 结构：
  - `header`: {`description`, `date_field`}
  - `lines`: [{`account`, `debit`, `credit`, `dims`, `description`}] 
  - `formula`: 支持基础表达式（金额、比例、取反）

### 1.1 表达式语法与边界
- 变量：`amount`/`qty`/`rate`/`tax`
- 运算：`+ - * / ( )`
- 函数：`round(x, n)`、`abs(x)`
- 条件：`if(cond, a, b)`，`cond` 支持 `> < >= <= == !=` 与 `and/or`
- 禁止任意代码执行与外部函数

### 2. 规则引擎
- 输入：`event_type` + `payload`
- 输出：凭证 JSON（与现有 `record` 结构一致）
- 规则执行：
  - 验证必填字段
  - 解析表达式
  - 生成分录

### 2.1 幂等与事件来源
- `vouchers` 增加字段：`source_template`、`source_event_id`
- 新增 `voucher_events(event_id, template_code, voucher_id)`，`event_id` 唯一
- 同一 `event_id` 重复触发时返回已有凭证

### 3. CLI/接口
- `ledger template add/list/disable`
- `ledger auto --template <code>`
- 记录模板来源字段（voucher.source_template）

### 4. 校验
- 生成凭证必须平衡
- 不允许未启用模板
- 模板引用科目必须存在

## 方案差异（相对现状）
- 从“手工录入”升级为“模板自动生成”
- 从“无规则”升级为“可配置规则”

## 落地步骤与测试（统一版）

0. **模板表与解析器（已完成）**
   - 做什么：新增模板表与规则解析器
   - 测试：模板可保存/读取/禁用

1. **自动凭证生成（已完成）**
   - 做什么：增加 `ledger auto` 入口
   - 测试：传入 payload 生成平衡凭证

2. **校验与报错（已完成）**
   - 做什么：模板缺字段、科目不存在时报错
   - 测试：错误码与提示正确

3. **条件表达式与幂等（待做）**
   - 做什么：支持 `if` 条件与事件幂等
   - 测试：条件分录与重复事件返回已生成凭证

## 可执行测试用例

### 测试环境准备
```bash
rm -f /tmp/ledger_template.db
ledger init --db-path /tmp/ledger_template.db
```

### TC-TPL-01: 模板新增与启用
- **操作**：`ledger template add` + `ledger template list`
- **预期**：模板可读写

### TC-TPL-02: 自动凭证生成
- **操作**：`ledger auto --template cash_in` + `{"amount":100}`
- **预期**：生成凭证，借贷均为 100

### TC-TPL-03: 模板禁用
- **操作**：禁用后再次调用
- **预期**：返回 `TEMPLATE_DISABLED`

### TC-TPL-04: 模板校验失败
- **操作**：引用不存在科目
- **预期**：返回 `ACCOUNT_NOT_FOUND`

### TC-TPL-05: 条件表达式
- **操作**：模板分录用 `if(amount>1000, amount, 0)` 生成
- **预期**：amount<=1000 时不生成金额

### TC-TPL-06: 幂等事件
- **操作**：相同 `event_id` 调用两次
- **预期**：第二次返回同一 `voucher_id`，不重复生成

## 备注
- 规则引擎先支持简单表达式，复杂逻辑后续扩展
