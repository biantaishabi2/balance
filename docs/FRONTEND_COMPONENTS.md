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

## 三、需新增组件清单（精简版）

### 3.1 核心业务组件（必须新增）- 6 个

| # | 组件 | 用途 | 优先级 | 说明 |
|---|------|------|--------|------|
| 1 | `EntryTable` | 可编辑分录表 | **P0** | 凭证修改核心，支持行内编辑、新增/删除行、借贷平衡校验 |
| 2 | `AccountSelector` | 科目选择器 | **P0** | 树形下拉 + 搜索，显示科目代码/名称/停用状态 |
| 3 | `DimensionSelector` | 维度选择器 | **P0** | 通用选择器，通过 `type` 参数支持：department/project/customer/supplier/employee/item |
| 4 | `HierarchyTable` | 层级分组表 | **P0** | 报表专用，建议用 AntV S2，支持展开/收起、小计/合计 |
| 5 | `DataTable` | 通用数据表格 | **P0** | 配置化表格，支持：列定义、筛选、排序、分页、行选择、行操作按钮 |
| 6 | `PeriodSelector` | 期间选择器 | **P1** | 年月选择，财务专用格式（YYYY-MM） |

### 3.2 通用 UI 组件（需新增）- 5 个

| # | 组件 | 用途 | 优先级 | 说明 |
|---|------|------|--------|------|
| 7 | `StatusBadge` | 状态徽章 | **P1** | 通用状态显示，通过 `type` 参数支持：voucher/period/ar/ap 等不同状态集 |
| 8 | `BalanceIndicator` | 借贷平衡指示器 | **P1** | 显示借方合计、贷方合计、是否平衡 |
| 9 | `FormDialog` | 通用表单对话框 | **P1** | 配置化表单弹窗，支持字段定义、校验、提交 |
| 10 | `ConfirmDialog` | 确认对话框 | **P1** | 二次确认弹窗，支持标题、说明文字、危险操作样式 |
| 11 | `ExportMenu` | 导出菜单 | **P2** | 下拉菜单，支持 Excel/PDF/CSV 格式导出 |

### 3.3 业务专用组件（需新增）- 5 个

| # | 组件 | 用途 | 优先级 | 说明 |
|---|------|------|--------|------|
| 12 | `AgingReport` | 账龄分析表 | **P1** | AR/AP 共用，按 0-30/31-60/61-90/90+ 天分组 |
| 13 | `BudgetCompareView` | 预算对比视图 | **P2** | 显示预算/实际/差异/执行率 |
| 14 | `AuditTimeline` | 审计轨迹 | **P2** | 基于 zcpg timeline 改造，显示操作历史 |
| 15 | `ReportParams` | 报表参数面板 | **P1** | 组合筛选：期间、口径、维度、预算对比开关 |
| 16 | `JSONEditor` | JSON 编辑器 | **P2** | 模板配置用，语法高亮、格式校验 |

---

## 四、可复用 zcpg 组件 - 10 个

| # | 组件 | 来源 | 用途 |
|---|------|------|------|
| 1 | `Table` | `data_card_components.ex` | 基础表格（只读场景） |
| 2 | `Timeline` | `ui_components.ex` | 时间线基础组件 |
| 3 | `StatCard` | `multiboard_card_components.ex` | 统计卡片 |
| 4 | `Modal` | 通用 UI | 弹窗容器 |
| 5 | `Button/ButtonGroup` | 通用 UI | 按钮 |
| 6 | `Select/Dropdown` | 通用 UI | 下拉选择 |
| 7 | `DatePicker` | 通用 UI | 日期选择 |
| 8 | `FileUpload` | 通用 UI | 文件上传 |
| 9 | `Tabs` | 通用 UI | Tab 切换 |
| 10 | `Charts` | ECharts | 图表 |

---

## 五、组件复用说明

### 5.1 DataTable 复用场景

`DataTable` 是通用表格组件，通过配置列定义复用于所有列表页面：

| 页面 | 列配置示例 |
|------|-----------|
| 凭证列表 | `[凭证号, 日期, 摘要, 借方, 贷方, 状态, 操作]` |
| 应收列表 | `[客户, 金额, 已收, 余额, 日期, 账龄, 操作]` |
| 应付列表 | `[供应商, 金额, 已付, 余额, 日期, 账龄, 操作]` |
| 固定资产列表 | `[资产编号, 名称, 原值, 累计折旧, 净值, 状态, 操作]` |
| 存货结存 | `[物料, 数量, 单位成本, 金额]` |
| 票据列表 | `[票据号, 金额, 到期日, 状态, 操作]` |
| 收/付款计划 | `[关联单据, 到期日, 金额, 状态, 操作]` |
| 科目列表 | `[代码, 名称, 类型, 方向, 状态, 操作]` |
| 维度列表 | `[代码, 名称, 状态, 操作]` |
| 预算列表 | `[期间, 维度, 金额, 操作]` |
| 模板列表 | `[名称, 描述, 状态, 操作]` |
| 币种/汇率 | `[币种, 汇率, 日期]` |

### 5.2 DimensionSelector 复用场景

`DimensionSelector` 通过 `type` 参数复用：

```typescript
// 部门选择
<DimensionSelector type="department" />

// 客户选择
<DimensionSelector type="customer" />

// 供应商选择
<DimensionSelector type="supplier" />

// 存货选择
<DimensionSelector type="item" />
```

### 5.3 FormDialog 复用场景

`FormDialog` 通过配置字段复用于所有新增/编辑场景：

| 场景 | 字段配置 |
|------|---------|
| 新增科目 | `[代码, 名称, 类型, 方向, 上级科目]` |
| 新增维度 | `[代码, 名称]` |
| 核销操作 | `[核销金额, 核销日期, 备注]` |
| 资产处置 | `[处置日期, 处置收入, 备注]` |
| 设置预算 | `[期间, 维度, 金额]` |
| 汇兑重估 | `[期间, 币种]` |

### 5.4 StatusBadge 复用场景

`StatusBadge` 通过 `type` 参数显示不同状态集：

```typescript
// 凭证状态
<StatusBadge type="voucher" status="draft" />     // 草稿
<StatusBadge type="voucher" status="reviewed" />  // 已审核
<StatusBadge type="voucher" status="confirmed" /> // 已确认
<StatusBadge type="voucher" status="voided" />    // 已作废

// 期间状态
<StatusBadge type="period" status="open" />       // 开放
<StatusBadge type="period" status="closed" />     // 已结账
<StatusBadge type="period" status="adjustment" /> // 调整期

// AR/AP 状态
<StatusBadge type="ar" status="open" />           // 未结清
<StatusBadge type="ar" status="settled" />        // 已结清
```

---

## 六、页面与组件对应关系

### 6.1 凭证工作台 `/vouchers`

| 组件 | 来源 |
|------|------|
| `PeriodSelector` | 新增 |
| `DataTable` | 新增（凭证列表配置） |
| `StatusBadge` | 新增（type=voucher） |
| `ConfirmDialog` | 新增（批量操作确认） |
| `StatCard` | 复用 zcpg |
| `Tabs` | 复用 zcpg |

### 6.2 凭证详情 `/vouchers/:id`

| 组件 | 来源 |
|------|------|
| `EntryTable` | **新增**（核心） |
| `AccountSelector` | **新增**（核心） |
| `DimensionSelector` | **新增**（核心） |
| `BalanceIndicator` | 新增 |
| `StatusBadge` | 新增 |
| `AuditTimeline` | 新增 |
| `ConfirmDialog` | 新增（操作确认） |
| `FileUpload` | 复用 zcpg |

### 6.3 报表中心 `/reports`

| 组件 | 来源 |
|------|------|
| `HierarchyTable` | **新增**（核心） |
| `ReportParams` | 新增 |
| `PeriodSelector` | 新增 |
| `DimensionSelector` | 新增 |
| `BudgetCompareView` | 新增 |
| `ExportMenu` | 新增 |
| `Tabs` | 复用 zcpg |

### 6.4 余额查询 `/balances`

| 组件 | 来源 |
|------|------|
| `DataTable` | 新增（余额表配置） |
| `PeriodSelector` | 新增 |
| `AccountSelector` | 新增 |
| `DimensionSelector` | 新增 |
| `Tabs` | 复用 zcpg |

### 6.5 期间管理 `/periods`

| 组件 | 来源 |
|------|------|
| `DataTable` | 新增（期间列表配置） |
| `StatusBadge` | 新增（type=period） |
| `ConfirmDialog` | 新增（结账确认） |

### 6.6 应收/应付管理 `/ar`, `/ap`

| 组件 | 来源 |
|------|------|
| `DataTable` | 新增（AR/AP/票据/计划列表配置） |
| `AgingReport` | 新增 |
| `DimensionSelector` | 新增（客户/供应商选择） |
| `FormDialog` | 新增（核销操作） |
| `StatusBadge` | 新增 |
| `Tabs` | 复用 zcpg |

### 6.7 存货管理 `/inventory`

| 组件 | 来源 |
|------|------|
| `DataTable` | 新增（结存/出入库列表配置） |
| `DimensionSelector` | 新增（type=item） |
| `FormDialog` | 新增（盘点录入） |

### 6.8 固定资产 `/fixed-assets`

| 组件 | 来源 |
|------|------|
| `DataTable` | 新增（资产/CIP列表配置） |
| `FormDialog` | 新增（处置/转移操作） |
| `DimensionSelector` | 新增（部门/项目选择） |

### 6.9 配置页面（科目/维度/预算/模板/外汇）

| 组件 | 来源 |
|------|------|
| `DataTable` | 新增（各列表配置） |
| `FormDialog` | 新增（新增/编辑操作） |
| `AccountSelector` | 新增（上级科目选择） |
| `JSONEditor` | 新增（模板编辑） |
| `Tabs` | 复用 zcpg |

---

## 七、核心组件详细规格

### 7.1 EntryTable 可编辑分录表

```typescript
interface EntryTableProps {
  entries: VoucherEntry[];
  editable: boolean;  // draft 状态可编辑
  onChange: (entries: VoucherEntry[]) => void;
  accounts: Account[];
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

**功能要求**：
- 行内编辑（点击单元格进入编辑模式）
- 科目列：使用 `AccountSelector`
- 维度列：使用 `DimensionSelector`
- 金额列：数字输入，自动千分位格式化
- 新增/删除行
- 实时计算借贷合计
- 平衡校验提示（使用 `BalanceIndicator`）

**技术建议**：基于 Ant Design ProComponents - EditableProTable

### 7.2 HierarchyTable 层级分组表

```typescript
interface HierarchyTableProps {
  data: ReportRow[];
  columns: ColumnDef[];
  expandable?: boolean;
  showSubTotals?: boolean;
  showGrandTotals?: boolean;
}

interface ReportRow {
  account_code: string;
  account_name: string;
  account_path: string[];  // 层级路径 ["资产", "流动资产", "货币资金"]
  level: number;
  amounts: Record<string, number>;  // { "期末余额": 100000, "年初余额": 90000 }
}
```

**功能要求**：
- 按层级展开/收起
- 自动计算小计/合计
- 支持多列（多期间对比）
- 金额格式化（千分位、负数红色）
- 点击行下钻

**技术建议**：使用 AntV S2，配置 `hierarchyType: 'tree'`

### 7.3 DataTable 通用数据表格

```typescript
interface DataTableProps<T> {
  columns: ColumnDef<T>[];
  data: T[];
  loading?: boolean;
  pagination?: { page: number; pageSize: number; total: number };
  filters?: FilterDef[];
  rowSelection?: { selectedKeys: string[]; onChange: (keys: string[]) => void };
  rowActions?: ActionDef[];
  onRowClick?: (row: T) => void;
  exportable?: boolean;
}

interface ColumnDef<T> {
  key: string;
  title: string;
  dataIndex: keyof T;
  sortable?: boolean;
  render?: (value: any, row: T) => ReactNode;
}

interface ActionDef {
  key: string;
  label: string;
  onClick: (row: any) => void;
  visible?: (row: any) => boolean;
  danger?: boolean;
}
```

**功能要求**：
- 列定义配置化
- 筛选、排序、分页
- 行选择（单选/多选）
- 行操作按钮（可配置可见性）
- 导出功能

---

## 八、技术建议

### 8.1 层级表方案

**推荐：AntV S2**

```typescript
const s2Options = {
  hierarchyType: 'tree',
  totals: {
    row: { showGrandTotals: true, showSubTotals: true },
    col: { showGrandTotals: true },
  },
};
```

### 8.2 可编辑表格方案

**推荐：Ant Design ProComponents - EditableProTable**

### 8.3 科目选择器方案

**推荐：Ant Design TreeSelect + 搜索**

---

## 九、总结

### 组件数量统计

| 类别 | 数量 |
|------|------|
| 核心业务组件（新增） | 6 |
| 通用 UI 组件（新增） | 5 |
| 业务专用组件（新增） | 5 |
| **需新增总计** | **16** |
| 可复用 zcpg | 10 |
| **总计** | **26** |

### 开发优先级

| 优先级 | 组件 | 说明 |
|--------|------|------|
| **P0** | `EntryTable`, `AccountSelector`, `DimensionSelector`, `HierarchyTable`, `DataTable` | 凭证和报表核心 |
| **P1** | `PeriodSelector`, `StatusBadge`, `BalanceIndicator`, `FormDialog`, `ConfirmDialog`, `AgingReport`, `ReportParams` | 基础交互 |
| **P2** | `ExportMenu`, `BudgetCompareView`, `AuditTimeline`, `JSONEditor` | 增强功能 |

### 页面开发顺序建议

1. **P0**：凭证工作台 + 凭证详情（依赖 EntryTable、AccountSelector、DimensionSelector、DataTable）
2. **P0**：报表中心（依赖 HierarchyTable、ReportParams）
3. **P1**：余额查询、期间管理
4. **P1**：子账管理（AR/AP/存货/固定资产）- 主要复用 DataTable + FormDialog
5. **P2**：配置页面
