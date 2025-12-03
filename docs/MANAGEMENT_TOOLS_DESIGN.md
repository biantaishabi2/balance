# 管理会计与财务分析工具设计

## 概述

现有工具体系主要覆盖**投行/PE视角**（LBO、M&A、DCF），本文档规划扩展**管理会计**和**企业财务分析**场景的原子工具。

## 现有工具回顾

| 分类 | 工具数 | 覆盖场景 |
|------|--------|----------|
| LBO | 9 | 杠杆收购分析 |
| MA | 8 | 并购交易分析 |
| DCF | 9 | 现金流估值 |
| THREE_STATEMENT | 11 | 三表联动预测 |
| RATIO | 7 | 财务比率分析 |
| PREPARE | 3 | 数据准备转换 |
| **合计** | **47** | |

## 扩展规划

### 一、管理报表工具 (MANAGEMENT)

面向 CFO 和管理层的内部分析报表。

#### 1.1 部门损益分析
```python
def calc_department_pnl(
    revenue_by_dept: Dict[str, float],      # 各部门收入
    direct_costs: Dict[str, float],          # 直接成本
    allocated_costs: Dict[str, float],       # 分摊成本
    allocation_method: str = "revenue"       # 分摊方法: revenue/headcount/square_feet
) -> Dict:
    """
    计算各部门损益

    Returns:
        {
            "departments": [
                {
                    "name": "华东区",
                    "revenue": 1000000,
                    "direct_cost": 600000,
                    "allocated_cost": 150000,
                    "contribution_margin": 400000,
                    "operating_profit": 250000,
                    "margin_percent": 0.25
                },
                ...
            ],
            "total": {...},
            "ranking": ["华东区", "华南区", ...]
        }
    """
```

#### 1.2 产品盈利分析
```python
def calc_product_profitability(
    products: List[Dict],                    # 产品列表 {name, revenue, cogs, volume}
    fixed_costs: float,                      # 固定成本
    allocation_base: str = "revenue"         # 分摊基础
) -> Dict:
    """
    计算各产品盈利能力

    Returns:
        {
            "products": [
                {
                    "name": "产品A",
                    "revenue": 500000,
                    "variable_cost": 300000,
                    "contribution_margin": 200000,
                    "cm_ratio": 0.40,
                    "allocated_fixed": 80000,
                    "net_profit": 120000,
                    "profit_margin": 0.24
                },
                ...
            ],
            "breakeven_analysis": {
                "total_fixed_cost": 200000,
                "weighted_cm_ratio": 0.38,
                "breakeven_revenue": 526316
            }
        }
    """
```

#### 1.3 客户盈利分析
```python
def calc_customer_profitability(
    customers: List[Dict],                   # 客户列表 {name, revenue, cost_to_serve}
    acquisition_cost: Dict[str, float],      # 获客成本
    retention_rate: Dict[str, float]         # 留存率
) -> Dict:
    """
    计算客户盈利能力和生命周期价值

    Returns:
        {
            "customers": [...],
            "segments": {
                "high_value": [...],
                "medium_value": [...],
                "low_value": [...]
            },
            "ltv_analysis": {
                "average_ltv": 50000,
                "cac_ltv_ratio": 0.15
            }
        }
    """
```

#### 1.4 成本分摊
```python
def calc_cost_allocation(
    cost_pools: Dict[str, float],            # 成本池 {行政: 100000, IT: 200000}
    cost_objects: List[str],                 # 成本对象（部门/产品）
    allocation_drivers: Dict[str, Dict],     # 分摊动因
    method: str = "step_down"                # direct/step_down/reciprocal
) -> Dict:
    """
    多步骤成本分摊

    Returns:
        {
            "allocation_matrix": [...],
            "cost_object_totals": {...},
            "method_used": "step_down"
        }
    """
```

---

### 二、预算管理工具 (BUDGET)

面向财务计划与控制。

#### 2.1 预算差异分析
```python
def calc_budget_variance(
    actual: Dict[str, float],                # 实际数
    budget: Dict[str, float],                # 预算数
    prior_year: Dict[str, float] = None,     # 去年同期
    variance_threshold: float = 0.05         # 重大差异阈值
) -> Dict:
    """
    预算差异分析（金额+百分比+同比）

    Returns:
        {
            "line_items": [
                {
                    "account": "销售收入",
                    "actual": 1000000,
                    "budget": 1100000,
                    "variance": -100000,
                    "variance_pct": -0.091,
                    "prior_year": 900000,
                    "yoy_growth": 0.111,
                    "is_material": True,
                    "status": "unfavorable"
                },
                ...
            ],
            "summary": {
                "total_favorable": 50000,
                "total_unfavorable": -150000,
                "net_variance": -100000
            }
        }
    """
```

#### 2.2 弹性预算
```python
def calc_flex_budget(
    static_budget: Dict[str, float],         # 静态预算
    actual_volume: float,                    # 实际业务量
    budget_volume: float,                    # 预算业务量
    cost_behavior: Dict[str, str]            # 成本性态 {account: "fixed"/"variable"/"mixed"}
) -> Dict:
    """
    按实际业务量调整预算

    Returns:
        {
            "static_budget": {...},
            "flex_budget": {...},
            "actual": {...},
            "volume_variance": {...},
            "efficiency_variance": {...}
        }
    """
```

#### 2.3 滚动预测
```python
def calc_rolling_forecast(
    historical: List[Dict],                  # 历史数据（按月）
    forecast_months: int = 12,               # 预测月数
    method: str = "trend",                   # trend/seasonal/ml
    drivers: Dict[str, float] = None         # 驱动因素假设
) -> Dict:
    """
    滚动预测（自动识别趋势和季节性）

    Returns:
        {
            "forecast": [
                {"month": "2025-01", "revenue": 1200000, "confidence": 0.85},
                ...
            ],
            "trend": "increasing",
            "seasonality": [1.1, 0.9, 1.0, ...],
            "accuracy_metrics": {
                "mape": 0.05,
                "rmse": 50000
            }
        }
    """
```

---

### 三、现金流管理工具 (CASH)

面向资金管理和流动性分析。

#### 3.1 13周现金流预测
```python
def calc_cash_forecast_13week(
    opening_cash: float,                     # 期初现金
    ar_aging: Dict[str, float],              # 应收账龄
    ap_aging: Dict[str, float],              # 应付账龄
    recurring_inflows: List[Dict],           # 固定流入
    recurring_outflows: List[Dict],          # 固定流出
    collection_pattern: List[float] = None   # 回款模式
) -> Dict:
    """
    13周滚动现金流预测

    Returns:
        {
            "weekly_forecast": [
                {
                    "week": 1,
                    "opening": 1000000,
                    "inflows": {...},
                    "outflows": {...},
                    "net_flow": 50000,
                    "closing": 1050000
                },
                ...
            ],
            "minimum_cash": 800000,
            "minimum_week": 5,
            "funding_gap": 0,
            "alerts": []
        }
    """
```

#### 3.2 营运资金周期
```python
def calc_working_capital_cycle(
    revenue: float,
    cogs: float,
    avg_inventory: float,
    avg_receivable: float,
    avg_payable: float
) -> Dict:
    """
    计算现金转换周期

    Returns:
        {
            "dso": 45,                       # 应收天数
            "dio": 30,                       # 存货天数
            "dpo": 40,                       # 应付天数
            "ccc": 35,                       # 现金转换周期
            "working_capital_need": 500000,
            "benchmark": {
                "industry_avg_ccc": 40,
                "status": "better_than_average"
            }
        }
    """
```

#### 3.3 现金流驱动因素分析
```python
def calc_cash_flow_drivers(
    current_period: Dict,                    # 本期数据
    prior_period: Dict,                      # 上期数据
    breakdown: bool = True
) -> Dict:
    """
    分析现金流变动的驱动因素

    Returns:
        {
            "net_change": 200000,
            "drivers": [
                {"factor": "净利润增加", "impact": 150000},
                {"factor": "应收减少", "impact": 80000},
                {"factor": "存货增加", "impact": -50000},
                {"factor": "资本支出", "impact": -100000},
                ...
            ],
            "waterfall_data": [...]          # 瀑布图数据
        }
    """
```

---

### 四、审计与合规工具 (AUDIT)

面向审计和财务合规。

#### 4.1 试算平衡表
```python
def calc_trial_balance(
    journal_entries: List[Dict],             # 分录列表
    account_structure: Dict                  # 科目结构
) -> Dict:
    """
    生成试算平衡表

    Returns:
        {
            "accounts": [
                {"code": "1001", "name": "现金", "debit": 100000, "credit": 0},
                ...
            ],
            "total_debit": 5000000,
            "total_credit": 5000000,
            "is_balanced": True,
            "difference": 0
        }
    """
```

#### 4.2 调整分录生成
```python
def generate_adjusting_entry(
    adjustment_type: str,                    # accrual/deferral/estimate/reclassify
    accounts: List[Dict],                    # 涉及科目
    amount: float,
    description: str,
    period: str
) -> Dict:
    """
    生成调整分录

    Returns:
        {
            "entry_id": "AJE-2025-001",
            "date": "2025-12-31",
            "type": "accrual",
            "lines": [
                {"account": "应付工资", "debit": 0, "credit": 50000},
                {"account": "工资费用", "debit": 50000, "credit": 0}
            ],
            "description": "计提12月工资",
            "approval_status": "pending"
        }
    """
```

#### 4.3 重要性水平
```python
def calc_materiality(
    financial_data: Dict,                    # 财务数据
    benchmark: str = "revenue",              # 基准: revenue/assets/equity/profit
    risk_level: str = "medium"               # low/medium/high
) -> Dict:
    """
    计算审计重要性水平

    Returns:
        {
            "overall_materiality": 500000,
            "performance_materiality": 375000,
            "trivial_threshold": 25000,
            "calculation": {
                "benchmark": "revenue",
                "benchmark_value": 10000000,
                "percentage": 0.05,
                "risk_adjustment": 1.0
            }
        }
    """
```

#### 4.4 审计抽样
```python
def calc_audit_sample(
    population: List[Dict],                  # 总体
    materiality: float,                      # 重要性
    confidence_level: float = 0.95,          # 置信度
    expected_error_rate: float = 0.01,       # 预期错报率
    method: str = "mus"                      # mus/random/stratified
) -> Dict:
    """
    计算审计样本

    Returns:
        {
            "sample_size": 60,
            "sampling_interval": 50000,
            "selected_items": [...],
            "method": "monetary_unit_sampling",
            "parameters": {...}
        }
    """
```

---

### 五、合并报表工具 (CONSOLIDATION)

面向集团财务合并。

#### 5.1 合并抵消
```python
def calc_consolidation_elimination(
    parent: Dict,                            # 母公司报表
    subsidiaries: List[Dict],                # 子公司报表
    intercompany_transactions: List[Dict],   # 内部交易
    ownership: Dict[str, float]              # 持股比例
) -> Dict:
    """
    生成合并抵消分录

    Returns:
        {
            "elimination_entries": [
                {
                    "type": "investment_elimination",
                    "debit": [...],
                    "credit": [...],
                    "amount": 1000000
                },
                {
                    "type": "intercompany_sales",
                    ...
                }
            ],
            "consolidated_trial_balance": {...}
        }
    """
```

#### 5.2 少数股东权益
```python
def calc_minority_interest(
    subsidiary_equity: float,
    subsidiary_net_income: float,
    ownership_percent: float
) -> Dict:
    """
    计算少数股东权益和损益

    Returns:
        {
            "minority_equity": 300000,
            "minority_income": 50000,
            "parent_share_equity": 700000,
            "parent_share_income": 116667
        }
    """
```

---

## 实施优先级

| 优先级 | 工具类别 | 工具数 | 理由 |
|--------|----------|--------|------|
| P0 | 预算差异分析 | 3 | CFO 最常用，月度必做 |
| P0 | 现金流预测 | 3 | 资金管理核心需求 |
| P1 | 部门/产品盈利 | 4 | 管理决策支持 |
| P1 | 营运资金分析 | 2 | 运营效率分析 |
| P2 | 审计工具 | 4 | 审计场景专用 |
| P2 | 合并报表 | 2 | 集团企业专用 |

## 工具命名规范

```
calc_*          计算类工具
generate_*      生成类工具（分录、报表）
analyze_*       分析类工具
forecast_*      预测类工具
```

---

## CLI 命令架构

按角色拆分为 8 个独立命令：

| 命令 | 全称 | 角色 | 功能 |
|------|------|------|------|
| `fm` | Financial Model | 投行/投资 | LBO、M&A、DCF、项目投资决策 |
| `fa` | Financial Analysis | 财务分析 | 预算差异、滚动预测、比率分析 |
| `ma` | Management Accounting | 管理会计 | 部门损益、产品盈利、成本分摊、CVP |
| `ac` | Accounting | 会计/审计 | 试算平衡、调整分录、审计抽样、合并报表 |
| `cf` | Cash Flow | 资金管理 | 现金流预测、融资方案、营运资金 |
| `tx` | Tax | 税务筹划 | 增值税、所得税、年终奖优化 |
| `ri` | Risk | 风控 | 信用评估、汇率风险、坏账准备 |
| `kp` | KPI | 绩效考核 | KPI仪表盘、EVA、平衡计分卡 |

### 命令详细设计

#### 1. fm - 投行/投资建模（已实现+待扩展）
```bash
# LBO 分析（已实现）
fm lbo calc < input.json              # LBO 分析
fm lbo sensitivity < input.json       # LBO 敏感性

# M&A 分析（已实现）
fm merger calc < deal.json            # 并购分析
fm merger accretion < deal.json       # 增厚稀释

# DCF 估值（已实现）
fm dcf calc < projections.json        # DCF 估值
fm dcf sensitivity < projections.json # DCF 敏感性

# 三表模型（已实现）
fm three forecast < financials.json   # 三表预测
fm ratio calc < financials.json       # 比率分析

# 项目投资决策（待实现）
fm project npv < cashflows.json       # 净现值分析
fm project irr < cashflows.json       # 内部收益率
fm project payback < cashflows.json   # 回收期分析
fm project compare < projects.json    # 多项目对比
fm project lease-vs-buy < options.json # 租赁vs购买决策

# 导出
fm export lbo,sensitivity -o out.xlsx # 导出 Excel
```

#### 2. fa - 财务分析（待实现）
```bash
fa variance < actual_vs_budget.json           # 预算差异分析
fa variance --yoy < multi_period.json         # 含同比分析
fa flex < volume_data.json                    # 弹性预算
fa forecast --months 12 < historical.json     # 滚动预测
fa forecast --method seasonal < historical.json
fa trend < multi_period.json                  # 趋势分析
fa export variance -o report.xlsx             # 导出报告
```

#### 3. ma - 管理会计（待实现）
```bash
ma dept-pnl < dept_data.json                  # 部门损益
ma dept-pnl --allocation revenue < data.json  # 指定分摊方法
ma product-profit < product_data.json         # 产品盈利分析
ma customer-profit < customer_data.json       # 客户盈利分析
ma cost-allocation < cost_pool.json           # 成本分摊
ma cost-allocation --method step_down < data.json
ma cvp < cost_volume.json                     # 本量利分析
ma breakeven < product_data.json              # 盈亏平衡分析
ma std-cost-variance < standard_cost.json     # 标准成本差异分析
ma export dept-pnl -o management.xlsx         # 导出管理报表
```

#### 4. ac - 会计/审计（待实现）
```bash
ac trial-balance < journal.json               # 试算平衡表
ac adjust --type accrual < adjustment.json    # 生成调整分录
ac adjust --type reclassify < adjustment.json
ac materiality --benchmark revenue < fin.json # 重要性水平
ac materiality --risk high < fin.json
ac sample --method mus < population.json      # 审计抽样
ac sample --method stratified < population.json
ac reconcile < account_data.json              # 账户调节
ac consolidate < group_data.json              # 合并报表
ac eliminate < intercompany.json              # 内部交易抵消
ac export trial-balance -o audit.xlsx         # 导出审计底稿
```

#### 5. cf - 资金管理（待实现）
```bash
cf forecast-13week < cash_data.json           # 13周现金流预测
cf forecast-13week --alert 500000 < data.json # 设置预警线
cf cycle < working_capital.json               # 营运资金周期
cf drivers < period_comparison.json           # 现金流驱动因素
cf dso-dpo-dio < working_capital.json         # 周转天数分析
cf financing-compare < loan_options.json      # 融资方案对比
cf loan-schedule < loan_terms.json            # 贷款还款计划
cf export forecast -o cash_report.xlsx        # 导出资金报告
```

#### 6. tx - 税务筹划（待实现）
```bash
tx vat < sales_data.json                      # 增值税计算
tx cit < income_data.json                     # 企业所得税
tx cit --preference small_micro < data.json   # 小微企业优惠
tx iit < salary_data.json                     # 个人所得税
tx optimize-bonus --total 500000              # 年终奖优化
tx rd-deduction --expense 1000000             # 研发加计扣除
tx burden < tax_data.json                     # 综合税负分析
tx transfer-pricing < related_party.json     # 转让定价
```

#### 7. ri - 风控（待实现）
```bash
ri credit-score < customer_data.json          # 客户信用评分
ri ar-aging < receivables.json                # 应收账龄分析
ri bad-debt < ar_aging.json                   # 坏账准备计提
ri fx-exposure < currency_data.json           # 汇率风险敞口
ri interest-sensitivity < debt_data.json      # 利率敏感性分析
ri concentration < customer_revenue.json      # 客户集中度风险
ri export ar-aging -o risk_report.xlsx        # 导出风险报告
```

#### 8. kp - 绩效考核（待实现）
```bash
kp dashboard < kpi_data.json                  # KPI 仪表盘
kp eva < financial_data.json                  # 经济增加值 EVA
kp roic < financial_data.json                 # 投入资本回报率
kp bsc < balanced_scorecard.json              # 平衡计分卡
kp dept-roi < dept_data.json                  # 部门 ROI
kp trend --metrics revenue,margin < hist.json # 指标趋势分析
kp export dashboard -o kpi_report.xlsx        # 导出绩效报告
```

---

## 文件结构规划

```
balance/
├── fm.py                    # 投行/投资建模 CLI（已实现）
├── fa.py                    # 财务分析 CLI（待实现）
├── ma.py                    # 管理会计 CLI（待实现）
├── ac.py                    # 会计审计 CLI（待实现）
├── cf.py                    # 资金管理 CLI（待实现）
├── tx.py                    # 税务筹划 CLI（待实现）
├── ri.py                    # 风控 CLI（待实现）
├── kp.py                    # 绩效考核 CLI（待实现）
│
├── fin_tools/
│   ├── tools/
│   │   ├── lbo_tools.py           # LBO 原子工具
│   │   ├── merger_tools.py        # M&A 并购工具（原 ma_tools.py）
│   │   ├── dcf_tools.py           # DCF 原子工具
│   │   ├── project_tools.py       # 项目投资决策工具（待实现）
│   │   ├── three_statement_tools.py  # 三表原子工具
│   │   ├── ratio_tools.py         # 比率分析工具
│   │   ├── prepare_tools.py       # 数据准备工具
│   │   │
│   │   ├── budget_tools.py        # 预算分析工具（待实现）
│   │   ├── management_tools.py    # 管理会计工具（待实现）
│   │   ├── audit_tools.py         # 审计工具（待实现）
│   │   ├── cash_tools.py          # 资金管理工具（待实现）
│   │   ├── tax_tools.py           # 税务工具（待实现）
│   │   ├── risk_tools.py          # 风控工具（待实现）
│   │   ├── kpi_tools.py           # 绩效考核工具（待实现）
│   │   └── consolidation_tools.py # 合并报表工具（待实现）
│   │
│   ├── io/
│   │   └── excel_writer.py        # Excel 导出（扩展新报表格式）
```

---

## 实施优先级

| 优先级 | CLI | 工具文件 | 工具数 | 理由 |
|--------|-----|----------|--------|------|
| P0 | `fm` (扩展) | project_tools.py | 5 | 项目投资决策常用 |
| P0 | `fa` | budget_tools.py | 3 | CFO 最常用，月度必做 |
| P0 | `cf` | cash_tools.py | 5 | 资金管理核心需求 |
| P1 | `ma` | management_tools.py | 5 | 管理决策支持 |
| P1 | `tx` | tax_tools.py | 8 | 税务筹划高频需求 |
| P1 | `ri` | risk_tools.py | 6 | 风控合规必备 |
| P2 | `ac` | audit_tools.py | 6 | 审计场景专用 |
| P2 | `kp` | kpi_tools.py | 6 | 绩效考核 |
| P2 | - | consolidation_tools.py | 2 | 集团企业专用 |

---

## 数据来源与接口设计

### 现实中的工作流程

| 角色 | 常用工具 | 数据来源 |
|------|----------|----------|
| 会计 | 金蝶、用友、SAP | ERP 系统记账 |
| 财务分析 | Excel | 从 ERP 导出，手工分析 |
| 管理会计 | Excel | 从 ERP 导出 + 手工整理 |
| 投行 | Excel | 公开财报 + 尽调数据 |
| 审计 | Excel + 审计软件 | 从客户 ERP 导出 |

### 数据流设计

```
ERP系统 (金蝶/用友/SAP)
    ↓ 导出 Excel/CSV
通用解析器 (excel2json)
    ↓ 转换为标准 JSON
原子工具 (fa/ma/ac/cf)
    ↓ 计算分析
Excel 报表输出
```

### 中国会计准则标准格式

所有 ERP 系统导出的底层格式是统一的，因为都要符合国家会计准则（财会字[2019]6号）。

#### 科目余额表（标准格式）
```
科目编码 | 科目名称 | 期初借方 | 期初贷方 | 本期借方 | 本期贷方 | 期末借方 | 期末贷方
1001    | 库存现金  | 10000   | 0       | 50000   | 45000   | 15000   | 0
1002    | 银行存款  | 500000  | 0       | 800000  | 750000  | 550000  | 0
1122    | 应收账款  | 200000  | 0       | 300000  | 280000  | 220000  | 0
2202    | 应付账款  | 0       | 150000  | 120000  | 180000  | 0       | 210000
...
```

#### 标准科目编码体系
```
1xxx - 资产类
2xxx - 负债类
3xxx - 权益类
4xxx - 成本类
5xxx - 损益类
```

#### 三大报表
- **资产负债表** - 财会字[2019]6号 规定格式
- **利润表** - 财会字[2019]6号 规定格式
- **现金流量表** - 财会字[2019]6号 规定格式

### 不同 ERP 的差异

| 相同点 | 不同点 |
|--------|--------|
| 科目编码体系 | Excel 导出的列名略有差异 |
| 报表项目结构 | 文件格式（xls/xlsx/csv） |
| 借贷方向规则 | 多余的辅助列 |

### 通用解析器设计

通过列名映射处理不同 ERP 的导出格式：

```python
# 列名映射配置
COLUMN_MAPPING = {
    # 科目编码
    "科目代码": "account_code",      # 金蝶
    "会计科目": "account_code",      # 用友
    "科目编码": "account_code",      # 通用
    "GL Account": "account_code",    # SAP

    # 科目名称
    "科目名称": "account_name",      # 金蝶/用友
    "科目": "account_name",          # 简写
    "Description": "account_name",   # SAP

    # 期初余额
    "期初借方": "opening_debit",
    "期初贷方": "opening_credit",
    "Beginning Debit": "opening_debit",
    "Beginning Credit": "opening_credit",

    # 本期发生
    "本期借方": "period_debit",
    "本期贷方": "period_credit",
    "Debit": "period_debit",
    "Credit": "period_credit",

    # 期末余额
    "期末借方": "closing_debit",
    "期末贷方": "closing_credit",
    "Ending Debit": "closing_debit",
    "Ending Credit": "closing_credit",
}
```

### 标准输入模板

#### 1. 科目余额表输入 (trial_balance_input.json)
```json
{
  "period": "2025-11",
  "company": "示例公司",
  "accounts": [
    {
      "code": "1001",
      "name": "库存现金",
      "opening_debit": 10000,
      "opening_credit": 0,
      "period_debit": 50000,
      "period_credit": 45000,
      "closing_debit": 15000,
      "closing_credit": 0
    },
    ...
  ]
}
```

#### 2. 预算对比输入 (budget_variance_input.json)
```json
{
  "period": "2025-11",
  "company": "示例公司",
  "line_items": [
    {
      "account": "营业收入",
      "actual": 1000000,
      "budget": 1100000,
      "prior_year": 900000
    },
    {
      "account": "营业成本",
      "actual": 650000,
      "budget": 700000,
      "prior_year": 600000
    },
    ...
  ]
}
```

#### 3. 现金流预测输入 (cash_forecast_input.json)
```json
{
  "as_of_date": "2025-12-01",
  "opening_cash": 1000000,
  "ar_aging": {
    "0-30": 500000,
    "31-60": 200000,
    "61-90": 100000,
    "90+": 50000
  },
  "ap_aging": {
    "0-30": 300000,
    "31-60": 150000,
    "61-90": 50000
  },
  "recurring_inflows": [
    {"description": "月度销售回款", "amount": 800000, "frequency": "weekly"}
  ],
  "recurring_outflows": [
    {"description": "工资", "amount": 200000, "frequency": "monthly", "day": 15},
    {"description": "房租", "amount": 50000, "frequency": "monthly", "day": 1}
  ]
}
```

### CLI 数据导入命令

```bash
# 从金蝶/用友导出的 Excel 转换为标准 JSON
python excel2json.py --template trial_balance < 金蝶科目余额表.xlsx > trial_balance.json
python excel2json.py --template budget < 预算表.xlsx > budget.json
python excel2json.py --template cash < 现金流数据.xlsx > cash.json

# 然后进行分析
ac trial-balance < trial_balance.json
fa variance < budget.json
cf forecast-13week < cash.json
```

---

## 六、税务工具 (TAX)

面向税务筹划与合规，在税法边缘合法优化。

### 6.1 增值税计算
```python
def calc_vat(
    sales_amount: float,                     # 销售额
    input_tax: float,                        # 进项税额
    tax_rate: float = 0.13,                  # 税率 13%/9%/6%
    exempt_sales: float = 0                  # 免税销售额
) -> Dict:
    """
    计算增值税及税负率

    Returns:
        {
            "output_tax": 130000,            # 销项税额
            "input_tax": 80000,              # 进项税额
            "vat_payable": 50000,            # 应纳增值税
            "tax_burden_rate": 0.05,         # 税负率
            "effective_rate": 0.038          # 实际税负
        }
    """
```

### 6.2 企业所得税计算
```python
def calc_corporate_tax(
    revenue: float,                          # 营业收入
    costs: float,                            # 成本费用
    adjustments: Dict[str, float],           # 纳税调整项
    preferences: List[str] = None            # 优惠政策
) -> Dict:
    """
    计算企业所得税（含纳税调整）

    Args:
        adjustments: {
            "entertainment_excess": 50000,   # 业务招待费超支
            "ad_excess": 0,                  # 广告费超支
            "donation_excess": 0,            # 捐赠超支
            "fine_penalty": 10000,           # 罚款不可扣
            "rd_extra_deduction": -100000    # 研发加计扣除（负数）
        }
        preferences: ["small_micro", "high_tech", "west_region"]

    Returns:
        {
            "accounting_profit": 1000000,
            "taxable_income": 960000,
            "tax_rate": 0.25,
            "tax_payable": 240000,
            "effective_rate": 0.24,
            "adjustments_detail": {...}
        }
    """
```

### 6.3 个人所得税计算
```python
def calc_individual_tax(
    monthly_salary: float,                   # 月薪
    annual_bonus: float = 0,                 # 年终奖
    social_insurance: float = 0,             # 社保
    housing_fund: float = 0,                 # 公积金
    special_deductions: Dict = None          # 专项附加扣除
) -> Dict:
    """
    计算个人所得税（综合所得+年终奖）

    Returns:
        {
            "monthly_tax": 2000,
            "annual_salary_tax": 24000,
            "bonus_tax": 15000,
            "total_tax": 39000,
            "effective_rate": 0.08
        }
    """
```

### 6.4 年终奖优化
```python
def optimize_bonus(
    total_income: float,                     # 年度总收入
    current_salary: float,                   # 当前月薪
    deductions: float = 60000                # 扣除项合计
) -> Dict:
    """
    年终奖与工资拆分优化（避开临界点）

    Returns:
        {
            "optimal_split": {
                "annual_salary": 300000,
                "bonus": 200000
            },
            "tax_saved": 15000,
            "warning_zones": [36000, 144000, 300000, ...],
            "comparison": [
                {"salary": 250000, "bonus": 250000, "total_tax": 55000},
                {"salary": 300000, "bonus": 200000, "total_tax": 40000},
                ...
            ]
        }
    """
```

### 6.5 研发费用加计扣除
```python
def calc_rd_deduction(
    rd_expense: float,                       # 研发费用
    deduction_rate: float = 1.0,             # 加计扣除比例 75%/100%
    capitalized_ratio: float = 0             # 资本化比例
) -> Dict:
    """
    计算研发费用加计扣除

    Returns:
        {
            "expensed_rd": 800000,
            "capitalized_rd": 200000,
            "extra_deduction": 800000,       # 加计扣除金额
            "tax_saving": 200000,            # 节税金额
            "amortization_deduction": 50000  # 资本化摊销加计
        }
    """
```

### 6.6 小微企业优惠
```python
def calc_sme_benefit(
    taxable_income: float,                   # 应纳税所得额
    employee_count: int,                     # 员工人数
    total_assets: float                      # 资产总额
) -> Dict:
    """
    计算小微企业所得税优惠

    符合条件：年应纳税所得额≤300万，从业人数≤300，资产≤5000万

    Returns:
        {
            "is_qualified": True,
            "taxable_income": 2800000,
            "normal_tax": 700000,            # 正常税额 25%
            "preferential_tax": 70000,       # 优惠税额
            "tax_saving": 630000,
            "effective_rate": 0.025,
            "breakdown": {
                "first_1m": {"income": 1000000, "rate": 0.025, "tax": 25000},
                "1m_to_3m": {"income": 1800000, "rate": 0.05, "tax": 45000}
            }
        }
    """
```

### 6.7 综合税负分析
```python
def calc_tax_burden(
    vat: float,
    corporate_tax: float,
    stamp_duty: float,
    other_taxes: Dict[str, float],
    revenue: float
) -> Dict:
    """
    综合税负分析

    Returns:
        {
            "total_tax": 500000,
            "tax_burden_rate": 0.05,
            "breakdown": {
                "vat": {"amount": 300000, "percent": 0.60},
                "corporate_tax": {"amount": 150000, "percent": 0.30},
                "stamp_duty": {"amount": 10000, "percent": 0.02},
                ...
            },
            "industry_benchmark": 0.045,
            "status": "slightly_above_average"
        }
    """
```

### 6.8 转让定价
```python
def calc_transfer_pricing(
    transaction_type: str,                   # goods/service/royalty/interest
    transaction_amount: float,
    comparable_data: List[Dict],             # 可比数据
    method: str = "tnmm"                     # cup/rpm/cpm/tnmm/psm
) -> Dict:
    """
    关联交易转让定价分析

    Returns:
        {
            "arm_length_range": {
                "min": 4500000,
                "median": 5000000,
                "max": 5500000
            },
            "current_price": 5200000,
            "is_compliant": True,
            "adjustment_needed": 0,
            "documentation_required": True
        }
    """
```

---

## 下一步

1. 确认优先级和需求范围
2. 实现通用 Excel 解析器（支持金蝶/用友/SAP 列名映射）
3. 实现 P0：`fa.py` + `budget_tools.py`（预算差异、弹性预算、滚动预测）
4. 实现 P0：`cf.py` + `cash_tools.py`（13周预测、营运资金周期、现金流驱动因素）
5. 实现 P1：`ma.py` + `management_tools.py`（部门损益、成本分摊）
6. 实现 P1：`tx.py` + `tax_tools.py`（增值税、所得税、年终奖优化）
7. 实现 P1：`ri.py` + `risk_tools.py`（信用评估、VAR、汇率风险）
8. 实现 P2：`kp.py` + `kpi_tools.py`（OKR进度、绩效考核）
9. 实现 P2：`ac.py` + `audit_tools.py`（审计场景专用）
10. 编写测试用例，扩展 `ExcelWriter` 支持新报表格式
