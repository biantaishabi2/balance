# 前端组件需求清单（Balance/Ledger）

## 设计原则

**核心模式：AI 录入，人确认/修改**

- AI 通过 `ledger record` 命令录入凭证（JSON 输入）
- 人通过前端页面 **查看、审核、确认、修改**
- 前端重点是 **查看 + 操作**，不是从零录入

---

## 一、Ledger 完整功能清单

### 1.1 凭证流程（核心）

| 命令 | 功能 | 操作者 | JSON 输入 | 前端需要 |
|------|------|--------|----------|---------|
| `record` | 录入凭证（草稿） | AI | `{date, description, entries}` | ❌ |
| `record --auto` | 录入并自动确认 | AI | 同上 | ❌ |
| `review` | 审核凭证 | 人 | voucher_id | ✅ 审核按钮 |
| `unreview` | 反审核（回退草稿） | 人 | voucher_id | ✅ 反审核按钮 |
| `confirm` | 确认入账 | 人 | voucher_id | ✅ 确认按钮 |
| `void` | 作废（红字冲销） | 人 | voucher_id, reason | ✅ 作废按钮 |
| `delete` | 删除草稿 | 人 | voucher_id | ✅ 删除按钮 |
| `approve` | 审批操作 | 人 | target_type, target_id, action | ✅ 审批按钮组 |

**凭证状态流转：**
```
draft → reviewed → confirmed
  ↓        ↑           ↓
delete  unreview     void
```

### 1.2 查询

| 命令 | 功能 | 主要参数 |
|------|------|---------|
| `query vouchers` | 凭证列表 | `--period`, `--status`, `--account`, `--voucher-no` |
| `query balances` | 余额查询 | `--period`, `--account`, `--dept-id`, `--project-id` |
| `query trial-balance` | 试算平衡 | `--period` |

### 1.3 报表

| 命令参数 | 功能 |
|---------|------|
| `report --period` | 三表（资产负债表/利润表/现金流量表） |
| `--consolidate` | 合并报表 |
| `--tax` | 税务报表 |
| `--scope normal/adjustment/all` | 口径切换 |
| `--dept-id/project-id/...` | 维度过滤 |
| `--budget-dim-type/code` | 预算对比 |

### 1.4 期间管理

| 命令 | 功能 |
|------|------|
| `period set-status` | 设置期间状态（open/closed/adjustment） |
| `close` | 期末结账（结转损益、生成报表） |
| `reopen` | 重新开启已关闭期间 |

### 1.5 科目管理

| 命令 | 功能 |
|------|------|
| `account list` | 科目列表（支持 `--type`, `--level` 过滤） |
| `account add` | 新增科目（JSON: code, name, type, direction, parent_code） |
| `account disable` | 停用科目 |

### 1.6 维度管理

| 命令 | 功能 |
|------|------|
| `dimension list` | 维度列表（支持 `--type` 过滤） |
| `dimension add` | 新增维度（JSON: type, code, name） |

维度类型：`department`, `project`, `customer`, `supplier`, `employee`

### 1.7 发票管理

| 命令 | 功能 |
|------|------|
| `invoice add` | 新增发票（JSON: invoice_no, type, amount, tax, date） |
| `invoice list` | 发票列表（`--period`, `--type`, `--linked`） |
| `invoice link` | 关联凭证（invoice_id, voucher_id） |
| `invoice vat` | 增值税汇总（`--period`） |
| `invoice vat --post` | 生成 VAT 结转凭证 |

### 1.8 应收管理 (AR)

| 命令 | 功能 |
|------|------|
| `ar add` | 新增应收（`--customer`, `--amount`, `--date`） |
| `ar settle` | 核销（`--item-id`, `--amount`） |
| `ar list` | 应收列表（`--status`, `--period`, `--customer`） |
| `ar aging` | 账龄分析（`--as-of`） |
| `ar reconcile` | 对平检查（`--period`） |
| `ar credit` | 信用额度（`--customer`, `--limit`, `--days`） |
| `ar plan` | 收款计划（`--item-id`, `--due-date`, `--amount`） |
| `ar plan-settle` | 计划回款 |
| `ar bill` | 票据登记 |
| `ar bill-status` | 票据状态更新 |
| `ar bad-debt` | 坏账计提 |
| `ar bad-debt-auto` | 自动计提（按账龄） |
| `ar bad-debt-reverse` | 坏账冲回 |

### 1.9 应付管理 (AP)

| 命令 | 功能 |
|------|------|
| `ap add` | 新增应付（`--supplier`, `--amount`, `--date`） |
| `ap settle` | 核销 |
| `ap list` | 应付列表 |
| `ap aging` | 账龄分析 |
| `ap reconcile` | 对平检查 |
| `ap credit` | 信用额度 |
| `ap plan` | 付款计划 |
| `ap plan-settle` | 计划付款 |
| `ap bill` | 票据登记 |
| `ap bill-status` | 票据状态更新 |

### 1.10 存货管理

| 命令 | 功能 |
|------|------|
| `inventory in` | 入库（`--item`, `--qty`, `--cost`） |
| `inventory out` | 出库（`--item`, `--qty`, `--method`） |
| `inventory balance` | 结存查询 |
| `inventory reconcile` | 对平检查 |
| `inventory count` | 盘点（`--item`, `--qty`, `--date`） |
| `inventory standard-cost` | 标准成本设置 |

### 1.11 固定资产

| 命令 | 功能 |
|------|------|
| `fixed-asset add` | 新增资产 |
| `fixed-asset depreciate` | 计提折旧（`--period`） |
| `fixed-asset dispose` | 处置 |
| `fixed-asset list` | 资产列表 |
| `fixed-asset reconcile` | 对平检查 |
| `fixed-asset upgrade` | 改扩建 |
| `fixed-asset split` | 拆分 |
| `fixed-asset transfer` | 转移（部门/项目） |
| `fixed-asset impair` | 减值计提 |
| `fixed-asset impair-reverse` | 减值冲回 |
| `fixed-asset cip-add` | 新建在建工程 |
| `fixed-asset cip-cost` | 在建投入 |
| `fixed-asset cip-transfer` | 转固 |
| `fixed-asset allocate` | 折旧分摊配置 |

### 1.12 外汇管理

| 命令 | 功能 |
|------|------|
| `fx currency add` | 新增币种 |
| `fx currency list` | 币种列表 |
| `fx rate add` | 新增汇率 |
| `fx rate list` | 汇率列表 |
| `fx balance` | 外币余额 |
| `fx revalue` | 汇兑重估 |

### 1.13 预算管理

| 命令 | 功能 |
|------|------|
| `budget set` | 设置预算（`--period`, `--dim-type`, `--dim-code`, `--amount`） |
| `budget list` | 预算列表 |
| `budget variance` | 差异分析 |

### 1.14 成本分摊

| 命令 | 功能 |
|------|------|
| `allocation add` | 新增分摊规则 |
| `allocation list` | 规则列表 |
| `allocation run` | 执行分摊 |
| `allocation basis set` | 设置分摊基础数据 |
| `allocation basis list` | 基础数据列表 |

### 1.15 凭证模板

| 命令 | 功能 |
|------|------|
| `template add` | 新增模板（JSON 配置） |
| `template list` | 模板列表 |
| `template disable` | 禁用模板 |
| `auto --template` | 根据模板生成凭证 |

---

## 二、页面规划

### 2.1 核心页面

| 页面 | 路由 | 对应命令 | 优先级 |
|------|------|---------|--------|
| 凭证工作台 | `/vouchers` | record, review, confirm, void, delete, approve | P0 |
| 凭证详情 | `/vouchers/:id` | query vouchers, 修改操作 | P0 |
| 余额查询 | `/balances` | query balances, query trial-balance | P0 |
| 报表中心 | `/reports` | report | P0 |
| 期间管理 | `/periods` | period, close, reopen | P0 |

### 2.2 子账管理页面

| 页面 | 路由 | 对应命令 | 优先级 |
|------|------|---------|--------|
| 应收管理 | `/ar` | ar * | P1 |
| 应付管理 | `/ap` | ap * | P1 |
| 存货管理 | `/inventory` | inventory * | P1 |
| 固定资产 | `/fixed-assets` | fixed-asset * | P1 |
| 发票管理 | `/invoices` | invoice * | P1 |

### 2.3 配置页面

| 页面 | 路由 | 对应命令 | 优先级 |
|------|------|---------|--------|
| 科目表 | `/accounts` | account * | P1 |
| 维度管理 | `/dimensions` | dimension * | P1 |
| 预算管理 | `/budgets` | budget * | P2 |
| 分摊规则 | `/allocations` | allocation * | P2 |
| 凭证模板 | `/templates` | template *, auto | P2 |
| 外汇设置 | `/fx` | fx * | P2 |

---

## 三、页面详细设计 + 组件需求

### 3.1 凭证工作台 `/vouchers`

**功能**：查看待处理凭证、执行审核/确认操作

**页面布局**：
```
┌─────────────────────────────────────────────────────────┐
│ [筛选工具条]                                            │
│ 期间选择 | 状态筛选 | 科目筛选 | 凭证号搜索 | 导出按钮  │
├─────────────────────────────────────────────────────────┤
│ [统计卡片]                                              │
│ 待审核: 12  | 已审核待确认: 5  | 本期已确认: 48         │
├─────────────────────────────────────────────────────────┤
│ [凭证列表表格]                                          │
│ ☐ | 凭证号 | 日期 | 摘要 | 借方合计 | 贷方合计 | 状态 | 操作 │
│ ☐ | 2025-01-001 | 01-15 | 销售收入 | 10,000 | 10,000 | draft | [审核][删除] │
│ ☐ | 2025-01-002 | 01-16 | 采购付款 | 5,000 | 5,000 | reviewed | [确认][反审核] │
├─────────────────────────────────────────────────────────┤
│ [批量操作栏]                                            │
│ 已选 3 条 | [批量审核] [批量确认]                        │
└─────────────────────────────────────────────────────────┘
```

**需要的组件**：

| 组件 | 描述 | 复用/新增 |
|------|------|---------|
| `PeriodSelector` | 期间选择器（年月） | 新增 |
| `StatusFilter` | 状态筛选（draft/reviewed/confirmed/voided） | 可复用 zcpg |
| `AccountSelector` | 科目选择器（树形/搜索） | 新增 |
| `VoucherTable` | 凭证列表表格（可选择、可排序） | 新增 |
| `StatCards` | 统计卡片组 | 可复用 zcpg |
| `BatchActionBar` | 批量操作栏 | 新增 |
| `ExportButton` | 导出按钮（CSV/Excel） | 可复用 zcpg |

---

### 3.2 凭证详情 `/vouchers/:id`

**功能**：查看凭证详情、修改分录、执行操作

**页面布局**：
```
┌─────────────────────────────────────────────────────────┐
│ [凭证头信息]                                            │
│ 凭证号: 2025-01-001    日期: 2025-01-15    状态: draft  │
│ 摘要: 销售收入                                          │
│ [编辑] [审核] [确认] [作废] [删除]                      │
├─────────────────────────────────────────────────────────┤
│ [分录表格] (可编辑)                                     │
│ 行号 | 科目 | 科目名称 | 摘要 | 借方 | 贷方 | 部门 | 项目 │
│ 1 | [1001▼] | 银行存款 | | 10,000.00 | | [销售部▼] | |
│ 2 | [6001▼] | 主营收入 | | | 10,000.00 | | |
│ [+ 新增行]                                              │
├─────────────────────────────────────────────────────────┤
│ [合计行]                                                │
│ 借方合计: 10,000.00  贷方合计: 10,000.00  ✓ 平衡        │
├─────────────────────────────────────────────────────────┤
│ [附件区域]                                              │
│ 📎 发票_001.pdf  📎 合同_A.pdf  [上传附件]              │
├─────────────────────────────────────────────────────────┤
│ [审计轨迹]                                              │
│ 2025-01-15 10:30 AI 创建草稿                            │
│ 2025-01-15 14:20 张三 审核通过                          │
└─────────────────────────────────────────────────────────┘
```

**需要的组件**：

| 组件 | 描述 | 复用/新增 |
|------|------|---------|
| `VoucherHeader` | 凭证头信息展示 | 新增 |
| `VoucherStatusBadge` | 状态徽章 | 新增 |
| `EntryTable` | **可编辑分录表**（核心组件） | **新增** |
| `AccountSelector` | 科目选择器（下拉树/搜索） | **新增** |
| `DimensionSelector` | 维度选择器（部门/项目/客户/供应商/员工） | **新增** |
| `BalanceIndicator` | 借贷平衡指示器 | 新增 |
| `AttachmentList` | 附件列表 | 可复用 zcpg |
| `FileUpload` | 文件上传 | 可复用 zcpg |
| `AuditTimeline` | 审计时间线 | 新增（基于 zcpg timeline） |
| `ActionButtons` | 操作按钮组（审核/确认/作废/删除） | 新增 |
| `ConfirmDialog` | 确认对话框（二次确认） | 可复用 zcpg |

**EntryTable 可编辑分录表 - 详细规格**：

```typescript
interface EntryTableProps {
  entries: VoucherEntry[];
  editable: boolean;  // draft 状态可编辑
  onChange: (entries: VoucherEntry[]) => void;
  accounts: Account[];  // 科目列表
  dimensions: {
    departments: Dimension[];
    projects: Dimension[];
    customers: Dimension[];
    suppliers: Dimension[];
    employees: Dimension[];
  };
}

interface VoucherEntry {
  line_no: number;
  account_code: string;
  account_name: string;
  description?: string;
  debit_amount: number;
  credit_amount: number;
  dept_id?: number;
  project_id?: number;
  customer_id?: number;
  supplier_id?: number;
  employee_id?: number;
}
```

功能要求：
- 行内编辑（点击单元格进入编辑模式）
- 科目列：下拉树 + 搜索
- 金额列：数字输入，自动格式化
- 维度列：下拉选择
- 新增/删除行
- 实时计算借贷合计
- 平衡校验提示

---

### 3.3 余额查询 `/balances`

**页面布局**：
```
┌─────────────────────────────────────────────────────────┐
│ [Tab 切换]                                              │
│ [余额表] [试算平衡表]                                   │
├─────────────────────────────────────────────────────────┤
│ [筛选工具条]                                            │
│ 期间: [2025-01▼] | 科目: [全部▼] | 部门: [全部▼] | 项目: [全部▼] │
├─────────────────────────────────────────────────────────┤
│ [余额表格]                                              │
│ 科目代码 | 科目名称 | 期初余额 | 本期借方 | 本期贷方 | 期末余额 │
│ 1001 | 银行存款 | 100,000 | 50,000 | 30,000 | 120,000 │
│ 1002 | 应收账款 | 80,000 | 20,000 | 15,000 | 85,000 │
│ ...                                                     │
├─────────────────────────────────────────────────────────┤
│ [导出] [打印]                                           │
└─────────────────────────────────────────────────────────┘
```

**需要的组件**：

| 组件 | 描述 | 复用/新增 |
|------|------|---------|
| `TabNav` | Tab 导航 | 可复用 zcpg |
| `PeriodSelector` | 期间选择 | 复用 |
| `AccountSelector` | 科目筛选 | 复用 |
| `DimensionFilter` | 维度筛选组 | 新增 |
| `BalanceTable` | 余额表格 | 新增 |
| `TrialBalanceTable` | 试算平衡表 | 新增 |

---

### 3.4 报表中心 `/reports`

**页面布局**：
```
┌─────────────────────────────────────────────────────────┐
│ [报表类型选择]                                          │
│ [资产负债表] [利润表] [现金流量表] [合并报表] [税务报表] │
├─────────────────────────────────────────────────────────┤
│ [参数设置]                                              │
│ 期间: [2025-01▼]  口径: [全部▼]  部门: [全部▼]          │
│ ☐ 预算对比  预算维度: [部门▼]                           │
├─────────────────────────────────────────────────────────┤
│ [报表展示 - 层级表]                                     │
│ 项目                    | 期末余额   | 年初余额   |     │
│ ▼ 资产                  | 500,000   | 450,000   |     │
│   ▼ 流动资产            | 300,000   | 280,000   |     │
│     货币资金            | 120,000   | 100,000   |     │
│     应收账款            | 85,000    | 80,000    |     │
│     存货                | 95,000    | 100,000   |     │
│   ▼ 非流动资产          | 200,000   | 170,000   |     │
│     固定资产            | 180,000   | 150,000   |     │
│     无形资产            | 20,000    | 20,000    |     │
│ ▼ 负债                  | 200,000   | 180,000   |     │
│ ...                                                     │
├─────────────────────────────────────────────────────────┤
│ [对平校验]                                              │
│ ✓ 资产 = 负债 + 所有者权益 (500,000 = 200,000 + 300,000) │
├─────────────────────────────────────────────────────────┤
│ [导出 Excel] [导出 PDF] [打印]                          │
└─────────────────────────────────────────────────────────┘
```

**需要的组件**：

| 组件 | 描述 | 复用/新增 |
|------|------|---------|
| `ReportTypeNav` | 报表类型导航 | 新增 |
| `ReportParams` | 报表参数面板 | 新增 |
| `ScopeSelector` | 口径选择器（normal/adjustment/all） | 新增 |
| `HierarchyTable` | **层级分组表**（核心组件，建议用 AntV S2） | **新增** |
| `BalanceCheckCard` | 对平校验卡片 | 新增 |
| `BudgetCompareView` | 预算对比视图（预算/实际/差异列） | 新增 |
| `ExportMenu` | 导出菜单（Excel/PDF） | 新增 |

**HierarchyTable 层级表 - 详细规格**：

建议使用 **AntV S2** 实现：

```typescript
// S2 配置示例
const s2Options = {
  hierarchyType: 'tree',  // 树形层级
  totals: {
    row: { showGrandTotals: true, showSubTotals: true },
    col: { showGrandTotals: true },
  },
  style: {
    cellCfg: { height: 32 },
  },
};

const s2DataConfig = {
  fields: {
    rows: ['account_path'],  // 层级路径
    columns: ['period'],
    values: ['amount'],
  },
  data: reportData,
};
```

功能要求：
- 按科目层级展开/收起
- 自动计算小计/合计
- 支持多期间对比（列）
- 金额格式化（千分位、负数红色）
- 点击下钻

---

### 3.5 期间管理 `/periods`

**页面布局**：
```
┌─────────────────────────────────────────────────────────┐
│ [期间列表]                                              │
│ 期间     | 状态       | 凭证数 | 操作                   │
│ 2025-01 | ● 开放     | 48    | [结账]                 │
│ 2024-12 | ● 已结账   | 52    | [重开]                 │
│ 2024-11 | ● 已结账   | 45    | [重开]                 │
├─────────────────────────────────────────────────────────┤
│ [结账确认对话框]                                        │
│ 确认结账 2025-01？                                      │
│ - 将结转损益到本年利润                                  │
│ - 生成期末报表                                          │
│ - 期间状态改为 closed                                   │
│ [取消] [确认结账]                                       │
└─────────────────────────────────────────────────────────┘
```

**需要的组件**：

| 组件 | 描述 | 复用/新增 |
|------|------|---------|
| `PeriodTable` | 期间列表 | 新增 |
| `PeriodStatusBadge` | 期间状态徽章（open/closed/adjustment） | 新增 |
| `CloseConfirmDialog` | 结账确认对话框 | 新增 |

---

### 3.6 应收管理 `/ar`

**页面布局**：
```
┌─────────────────────────────────────────────────────────┐
│ [Tab 切换]                                              │
│ [应收列表] [账龄分析] [收款计划] [票据] [坏账]          │
├─────────────────────────────────────────────────────────┤
│ [筛选]                                                  │
│ 状态: [未结清▼] | 期间: [2025-01▼] | 客户: [全部▼]      │
├─────────────────────────────────────────────────────────┤
│ [应收列表]                                              │
│ ID | 客户 | 金额 | 已收 | 余额 | 日期 | 账龄 | 操作     │
│ 1 | 客户A | 10,000 | 5,000 | 5,000 | 01-10 | 7天 | [核销] │
├─────────────────────────────────────────────────────────┤
│ [核销对话框]                                            │
│ 应收ID: 1  客户: 客户A  未收金额: 5,000                  │
│ 核销金额: [________]                                    │
│ 核销日期: [2025-01-17]                                  │
│ [取消] [确认核销]                                       │
└─────────────────────────────────────────────────────────┘
```

**需要的组件**：

| 组件 | 描述 | 复用/新增 |
|------|------|---------|
| `ARList` | 应收列表 | 新增 |
| `AgingReport` | 账龄分析表（0-30/31-60/61-90/90+天） | 新增 |
| `PaymentPlanList` | 收款计划列表 | 新增 |
| `BillList` | 票据列表 | 新增 |
| `BadDebtList` | 坏账列表 | 新增 |
| `SettleDialog` | 核销对话框 | 新增 |
| `CustomerSelector` | 客户选择器 | 新增 |

---

### 3.7 应付管理 `/ap`

与应收类似，组件可复用，换成供应商维度。

**需要的组件**：

| 组件 | 描述 |
|------|------|
| `APList` | 应付列表 |
| `AgingReport` | 复用应收的账龄组件 |
| `PaymentPlanList` | 付款计划列表 |
| `BillList` | 复用票据组件 |
| `SettleDialog` | 复用核销对话框 |
| `SupplierSelector` | 供应商选择器 |

---

### 3.8 存货管理 `/inventory`

**需要的组件**：

| 组件 | 描述 |
|------|------|
| `InventoryBalanceTable` | 存货结存表 |
| `InventoryMovementList` | 出入库记录 |
| `CountForm` | 盘点录入表单 |
| `CountResultTable` | 盘点结果（账实差异） |
| `ItemSelector` | 存货项目选择器 |

---

### 3.9 固定资产 `/fixed-assets`

**需要的组件**：

| 组件 | 描述 |
|------|------|
| `AssetList` | 资产卡片列表 |
| `AssetDetail` | 资产详情（含折旧计划） |
| `DepreciationTable` | 折旧明细表 |
| `AssetForm` | 资产登记表单 |
| `DisposeDialog` | 处置对话框 |
| `CIPList` | 在建工程列表 |
| `TransferDialog` | 转固/转移对话框 |

---

### 3.10 科目表 `/accounts`

**需要的组件**：

| 组件 | 描述 |
|------|------|
| `AccountTree` | 科目树形表（展开/收起） |
| `AccountForm` | 科目新增/编辑表单 |
| `AccountTypeFilter` | 科目类型筛选（资产/负债/权益/收入/费用） |

---

### 3.11 维度管理 `/dimensions`

**需要的组件**：

| 组件 | 描述 |
|------|------|
| `DimensionTabs` | 维度类型 Tab（部门/项目/客户/供应商/员工） |
| `DimensionList` | 维度列表 |
| `DimensionForm` | 维度新增表单 |

---

### 3.12 预算管理 `/budgets`

**需要的组件**：

| 组件 | 描述 |
|------|------|
| `BudgetTable` | 预算表（可编辑） |
| `BudgetVarianceReport` | 预算执行分析（预算/实际/差异/执行率） |
| `BudgetForm` | 预算设置表单 |

---

### 3.13 凭证模板 `/templates`

**需要的组件**：

| 组件 | 描述 |
|------|------|
| `TemplateList` | 模板列表 |
| `TemplateEditor` | 模板编辑器（JSON + 预览） |
| `JSONEditor` | JSON 编辑器（语法高亮、校验） |

---

### 3.14 外汇设置 `/fx`

**需要的组件**：

| 组件 | 描述 |
|------|------|
| `CurrencyList` | 币种列表 |
| `RateTable` | 汇率表（按日期） |
| `FXBalanceTable` | 外币余额表 |
| `RevalueDialog` | 重估对话框 |

---

## 四、通用组件清单

### 4.1 可直接复用 zcpg 的组件

| 组件 | 来源 |
|------|------|
| `Table` | `data_card_components.ex` |
| `Timeline` | `ui_components.ex` |
| `StatCard` | `multiboard_card_components.ex` |
| `Modal/Dialog` | 通用 UI |
| `Button/ButtonGroup` | 通用 UI |
| `Dropdown/Select` | 通用 UI |
| `DatePicker` | 通用 UI |
| `FileUpload` | 通用 UI |
| `Tabs` | 通用 UI |
| `Charts (ECharts)` | 图表组件 |

### 4.2 需要新增的核心组件

| 组件 | 优先级 | 描述 |
|------|--------|------|
| `EntryTable` | **P0** | 可编辑分录表（凭证修改核心） |
| `AccountSelector` | **P0** | 科目选择器（树形 + 搜索） |
| `DimensionSelector` | **P0** | 维度选择器（部门/项目/客户/供应商/员工） |
| `HierarchyTable` | **P0** | 层级分组表（报表用，建议 AntV S2） |
| `PeriodSelector` | P1 | 期间选择器 |
| `BalanceIndicator` | P1 | 借贷平衡指示器 |
| `VoucherStatusBadge` | P1 | 凭证状态徽章 |
| `AgingReport` | P1 | 账龄分析表 |
| `AuditTimeline` | P2 | 审计轨迹时间线 |
| `JSONEditor` | P2 | JSON 编辑器 |

---

## 五、技术建议

### 5.1 层级表方案

**推荐：AntV S2**

- 原生支持树形层级（`hierarchyType: 'tree'`）
- 自动小计/合计
- 展开/收起交互
- 适合资产负债表、利润表等

备选：如果数据量小，可在后端计算好层级小计，前端用普通表格渲染。

### 5.2 可编辑表格方案

**推荐：Ant Design ProComponents - EditableProTable**

或自研基于 Ant Design Table + Form 的方案。

核心功能：
- 行内编辑
- 新增/删除行
- 自定义单元格渲染（科目选择器、维度选择器）
- 实时校验

### 5.3 科目选择器方案

**推荐：TreeSelect + 搜索**

- 展示科目层级
- 支持搜索（按代码/名称）
- 显示停用状态
- 可配置是否允许选择父级科目

---

## 六、JSON 输出结构示例

### 凭证详情页
```json
{
  "component": "voucher_detail",
  "voucher": {
    "id": 1,
    "voucher_no": "2025-01-001",
    "date": "2025-01-15",
    "description": "销售收入",
    "status": "draft"
  },
  "entries": [
    {"line_no": 1, "account_code": "1001", "account_name": "银行存款", "debit": 10000, "credit": 0, "dept_id": 1},
    {"line_no": 2, "account_code": "6001", "account_name": "主营收入", "debit": 0, "credit": 10000}
  ],
  "actions": ["review", "delete"],
  "editable": true
}
```

### 报表页
```json
{
  "component": "pivot_table",
  "engine": "antv-s2",
  "title": "资产负债表",
  "period": "2025-01",
  "rows": ["account_path"],
  "columns": ["metric"],
  "values": ["amount"],
  "totals": {"row": true, "col": false},
  "balance_check": {
    "formula": "资产 = 负债 + 所有者权益",
    "is_balanced": true
  }
}
```

---

## 七、总结

| 类别 | 数量 | 说明 |
|------|------|------|
| Ledger 命令 | 60+ | 覆盖完整财务流程 |
| 前端页面 | 14 | 核心5个 + 子账5个 + 配置4个 |
| 需新增组件 | 10 | P0 级别 4 个（EntryTable、AccountSelector、DimensionSelector、HierarchyTable） |
| 可复用组件 | 10+ | 来自 zcpg |

**开发优先级建议**：
1. P0：凭证工作台 + 凭证详情（含可编辑分录表）
2. P0：报表中心（含层级表）
3. P1：余额查询、期间管理
4. P1：子账管理（AR/AP/存货/固定资产）
5. P2：配置页面
