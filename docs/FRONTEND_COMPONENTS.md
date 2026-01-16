# 前端组件需求清单（Balance/Ledger）

目标：基于 ../zcpg 的 JSON 驱动渲染模式，整理本项目所需组件，区分不同业务场景，并明确哪些可复用、哪些需要新增。

参考：
- JSON 驱动看板配置：`../zcpg/lib/multi_board/dashboard_engine.ex`
- 渲染分发与组件映射：`../zcpg/lib/zcpg_web/live/board_live/dashboard_configurable_live.ex`
- 表格组件：`../zcpg/lib/zcpg_web/components/data_card_components.ex`

## 场景分组与组件清单

### 1) 录入/编辑（小量数据 + 人工确认）
适用命令/流程：`ledger record`、`ledger confirm`、`ledger void`、`ledger invoice add` 等  
特点：输入量小、强校验、需要确认/审批

组件需求：
- **表单容器**：分步或单屏表单（凭证头 + 分录明细）
- **可编辑分录表**：行内编辑、借贷平衡校验、自动合计
- **科目选择器**：树形科目、搜索、可用/禁用提示
- **维度选择器**：部门/项目/客户/供应商/人员
- **币种与汇率输入**：外币金额与本位币折算
- **附件上传**：发票/凭证附件
- **确认按钮组**：保存草稿、提交复核、确认入账（带二次确认）

复用可能：
- 表单基础布局与按钮组可复用 zcpg 通用组件  
需新增：
- 可编辑分录表、科目树、借贷平衡提示条

### 2) 查询/列表（表格为主）
适用命令/流程：`ledger query vouchers/balances`、发票/子账/审计日志查询  
特点：数据量中等，强调筛选/排序/分页/导出

组件需求：
- **筛选工具条**：期间、科目、维度、状态、金额区间
- **可排序表格**：分页 + 列显示控制
- **详情抽屉/侧边栏**：点击行查看明细
- **导出按钮**：导出 CSV/Excel/JSON

复用可能：
- zcpg `table` 组件（只读）
需新增：
- 列配置面板、筛选器组合、详情抽屉模板

### 3) 统计/报表（图表 + 层级表）
适用命令/流程：`ledger report`、合并报表、税务报表、预算分析  
特点：聚合、分组、层级、对平校验

组件需求：
- **图表卡片**：折线/柱状/饼图/仪表盘
- **KPI 卡**：收入、利润、现金流等
- **层级分组表 + 小计**（见 S2 方案）
- **对平状态提示**：资产=负债+权益、现金净增加对平

复用可能：
- zcpg 图表类型（ECharts）
需新增：
- 报表级的层级表（AntV S2）
- 报表口径切换（normal/adjustment/all）

### 4) 审核/审批/审计
适用命令/流程：`ledger review`、`ledger approve`、审计日志  
特点：流程化、时间线、状态可追溯

组件需求：
- **审批状态机卡片**：pending/approved/rejected
- **审计时间线**：操作轨迹、操作者、请求信息
- **风险提示卡片**：稽核规则警告、预算超限

复用可能：
- 现有时间线/工作流组件（来自 zcpg）：
  - 配置驱动时间线：`../zcpg/lib/zcpg_web/components/ui_components.ex` 的 `timeline_display`
  - 时间线卡片（报销/待办/事件等）：`../zcpg/lib/zcpg_web/components/multiboard_card_components.ex`
  - 工作流/时间线图：`../zcpg/lib/zcpg_web/components/simple_graph.ex`
  - 工作流配置 UI：`../zcpg/lib/zcpg_web/components/workflow/`
需新增：
- 审计日志渲染模板

### 5) 配置/模板管理
适用命令/流程：凭证模板、报表映射、税务映射、预算配置  
特点：JSON/规则编辑、版本管理

组件需求：
- **JSON 编辑器**：语法高亮、校验、模板示例
- **规则/公式编辑器**：提示变量、字段列表
- **版本对比**：diff 视图

复用可能：
- zcpg 配置编辑基础 UI
需新增：
- JSON schema 校验与错误定位

### 6) 集成/系统/归档
适用命令/流程：API token、webhook、归档  
特点：操作列表 + 明细查看

组件需求：
- **Token 列表**：创建/撤销
- **Webhook 事件表**：状态 + payload 查看
- **归档任务**：批次列表 + 统计

复用可能：
- zcpg 表格 + 详情抽屉

## 层级分组表与小计：AntV S2 方案

目标：资产负债表/利润表/现金流等按科目层级分组，并展示小计/合计。

### 数据准备建议
输入字段示例（后端聚合后输出给前端）：
- `account_code`
- `account_name`
- `account_level`（1/2/3）
- `parent_code`（层级父节点）
- `period`
- `amount`
- `dim_type/dim_code`（可选）

前端可构建层级路径：
- `account_path = ["资产", "流动资产", "货币资金"]`
- 或构造 `id/parentId` 用于树形结构

### S2 配置思路（伪配置）
```js
const dataConfig = {
  fields: {
    rows: ["account_path"],
    columns: ["period"],
    values: ["amount"],
  },
  data: rows,
};

const options = {
  hierarchyType: "tree",
  totals: {
    row: { showGrandTotals: true, showSubTotals: true },
    col: { showGrandTotals: true },
  },
  style: { cellCfg: { height: 32 } },
};
```

关键点：
- `hierarchyType: "tree"` 让行维度按层级展开/收起
- `showSubTotals` 打开小计行
- 金额格式化：统一保留 2 位小数
- 支持点击行节点下钻（展开子科目）

### 适用范围
- 资产负债表、利润表（按科目层级）
- 预算/实际对比（行是科目，列是期间或预算/实际）

### 备选方案
如果数据量小，可在后端先计算层级小计，前端使用普通表格渲染（成本低但交互弱）。

## 建议的组件输出 JSON 结构（示例）

### 录入（分录编辑器）
```json
{
  "component": "voucher_editor",
  "header": { "date": "2025-01-05", "description": "" },
  "lines": [
    { "account": "", "debit": 0, "credit": 0, "dims": {} }
  ],
  "actions": ["save_draft", "review", "confirm"]
}
```

### 查询（表格）
```json
{
  "component": "table",
  "columns": ["date", "voucher_no", "status", "amount"],
  "filters": ["period", "status", "account"],
  "page_size": 50
}
```

### 统计（报表 + S2）
```json
{
  "component": "pivot_table",
  "engine": "antv-s2",
  "rows": ["account_path"],
  "columns": ["period"],
  "values": ["amount"],
  "totals": { "row": true, "col": true }
}
```

## 结论
- 查询/统计类可直接复用 zcpg 的图表与表格组件。
- 录入类必须新增“可编辑分录表 + 科目/维度选择器”。
- 报表层级表建议用 AntV S2；小规模场景可用后端小计 + 普通表格。
