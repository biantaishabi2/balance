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

## CLI 命令规划

```bash
# 管理报表
fm management pnl < dept_data.json
fm management product-profit < product_data.json

# 预算
fm budget variance < actual_vs_budget.json
fm budget flex < volume_data.json
fm budget forecast --months 12 < historical.json

# 现金流
fm cash forecast-13week < cash_data.json
fm cash cycle < working_capital.json

# 审计
fm audit trial-balance < journal.json
fm audit materiality --benchmark revenue < financials.json
fm audit sample --method mus < population.json

# 合并
fm consolidation eliminate < group_data.json
```

## 下一步

1. 确认优先级和需求范围
2. 设计详细的输入输出格式
3. 实现 P0 工具（预算差异 + 现金流预测）
4. 编写测试用例
5. 集成到 fm CLI
