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

## 当前问题（需要解决）
- 手工录凭证成本高
- 缺少规则与模板复用能力

## 核心设计

### 1. 凭证模板表
- `voucher_templates(code, name, rule_json, is_active, created_at)`
- `rule_json` 结构：
  - `header`: {`description`, `date_field`}
  - `lines`: [{`account`, `debit`, `credit`, `dims`, `description`}] 
  - `formula`: 支持基础表达式（金额、比例、取反）

### 2. 规则引擎
- 输入：`event_type` + `payload`
- 输出：凭证 JSON（与现有 `record` 结构一致）
- 规则执行：
  - 验证必填字段
  - 解析表达式
  - 生成分录

### 3. CLI/接口
- `ledger template add/list/disable`
- `ledger auto --template <code>`
- 记录模板来源字段（voucher.source）

### 4. 校验
- 生成凭证必须平衡
- 不允许未启用模板
- 模板引用科目必须存在

## 方案差异（相对现状）
- 从“手工录入”升级为“模板自动生成”
- 从“无规则”升级为“可配置规则”

## 落地步骤与测试（统一版）

0. **模板表与解析器（待做）**
   - 做什么：新增模板表与规则解析器
   - 测试：模板可保存/读取/禁用

1. **自动凭证生成（待做）**
   - 做什么：增加 `ledger auto` 入口
   - 测试：传入 payload 生成平衡凭证

2. **校验与报错（待做）**
   - 做什么：模板缺字段、科目不存在时报错
   - 测试：错误码与提示正确

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
- **操作**：`ledger auto --template cash_in` + payload
- **预期**：生成凭证并记账

### TC-TPL-03: 模板禁用
- **操作**：禁用后再次调用
- **预期**：返回 `TEMPLATE_DISABLED`

### TC-TPL-04: 模板校验失败
- **操作**：引用不存在科目
- **预期**：返回 `ACCOUNT_NOT_FOUND`

## 备注
- 规则引擎先支持简单表达式，复杂逻辑后续扩展
