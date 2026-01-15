# 记账系统设计文档

## 概述

为 balance 添加 `ledger` 命令，实现完整的凭证录入、账簿管理和三表生成功能，使 balance 从分析工具升级为具备基础记账能力的财务系统。

```
ledger - 记账系统

用法: ledger <command> [options] [input.json]

命令:
  record     录入凭证
  confirm    确认草稿凭证
  delete     删除凭证
  void       作废凭证（红字冲销）
  query      查询凭证/余额
  report     生成三表
  account    科目管理
  dimensions 辅助核算管理
  init       初始化账套
```

---

## 1. 设计理念

### 1.1 与传统ERP的差异

| 特性 | 传统ERP（金蝶） | balance ledger |
|------|----------------|---------------|
| **目标用户** | 多人协作 | AI工具（单调用） |
| **审核流程** | 制单人→审核人→记账人 | 用户确认 |
| **权限管理** | 复杂角色权限 | 不需要 |
| **审计轨迹** | 详细操作日志 | AI自己记录 |
| **期间管理** | 结账后不可修改 | 可重算所有期间 |
| **辅助核算** | 预先定义所有维度 | 按需使用 |
| **业务联动** | 采购→库存→应付→凭证 | 只记账，不做业务 |

### 1.2 核心原则

1. **简单优先**：只实现核心记账功能，不做人用ERP的复杂特性
2. **状态管理**：草稿→确认→作废，支持红字冲销
3. **自动生成**：确认凭证自动更新余额，自动生成三表
4. **辅助核算**：支持部门、项目、客户、供应商、人员五个维度
5. **SQLite存储**：单文件数据库，易于部署和备份

---

## 2. 数据库设计

### 2.1 数据库文件

- 默认路径：`./ledger.db`
- 可配置：`--db-path` 参数指定
- 引擎：SQLite3

### 2.2 表结构

#### accounts - 科目表

```sql
CREATE TABLE accounts (
  code TEXT PRIMARY KEY,              -- 科目代码（如 1001, 1001001）
  name TEXT NOT NULL,                 -- 科目名称
  level INTEGER NOT NULL,             -- 级别（1-4）
  parent_code TEXT,                   -- 上级科目代码
  type TEXT NOT NULL,                 -- 科目类型: asset|liability|equity|revenue|expense
  direction TEXT NOT NULL,            -- 借贷方向: debit|credit
  cash_flow TEXT,                    -- 现金流量项目: 经营活动|投资活动|筹资活动
  is_enabled INTEGER DEFAULT 1,       -- 是否启用
  is_system INTEGER DEFAULT 0,        -- 是否系统预设
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (parent_code) REFERENCES accounts(code)
);

CREATE INDEX idx_accounts_type ON accounts(type);
CREATE INDEX idx_accounts_level ON accounts(level);
```

**示例数据：**
```json
{
  "code": "1001",
  "name": "库存现金",
  "level": 1,
  "parent_code": null,
  "type": "asset",
  "direction": "debit",
  "cash_flow": "经营活动",
  "is_enabled": 1,
  "is_system": 1
}
```

#### dimensions - 辅助核算表

```sql
CREATE TABLE dimensions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT NOT NULL,                -- 维度类型: department|project|customer|supplier|employee
  code TEXT NOT NULL,                -- 编码
  name TEXT NOT NULL,                 -- 名称
  parent_id INTEGER,                 -- 上级（支持层级）
  extra TEXT,                        -- 额外信息（JSON格式）
  is_enabled INTEGER DEFAULT 1,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(type, code)
);

CREATE INDEX idx_dimensions_type ON dimensions(type);
```

**示例数据：**
```json
[
  {"type": "department", "code": "D001", "name": "销售部"},
  {"type": "project", "code": "P001", "name": "项目A"},
  {"type": "customer", "code": "C001", "name": "客户A"},
  {"type": "supplier", "code": "S001", "name": "供应商A"},
  {"type": "employee", "code": "E001", "name": "张三"}
]
```

#### vouchers - 凭证表

```sql
CREATE TABLE vouchers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  voucher_no TEXT UNIQUE NOT NULL,   -- 凭证号（格式：VYYYYMMDDNNN）
  date TEXT NOT NULL,                -- 凭证日期（YYYY-MM-DD）
  period TEXT NOT NULL,              -- 会计期间（YYYY-MM）
  description TEXT,                  -- 摘要
  status TEXT NOT NULL DEFAULT 'draft',  -- 状态: draft|confirmed|voided
  void_reason TEXT,                  -- 作废原因
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  confirmed_at TEXT,
  voided_at TEXT
);

CREATE INDEX idx_vouchers_period ON vouchers(period);
CREATE INDEX idx_vouchers_date ON vouchers(date);
CREATE INDEX idx_vouchers_status ON vouchers(status);
```

**状态流转：**
```
draft（草稿） → confirmed（已确认） → voided（已作废）
                                      ↓
                                  可生成报表
```

#### voucher_entries - 凭证分录表

```sql
CREATE TABLE voucher_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  voucher_id INTEGER NOT NULL,
  line_no INTEGER NOT NULL,          -- 分录序号
  account_code TEXT NOT NULL,        -- 科目代码
  account_name TEXT,                 -- 科目名称（冗余，便于查询）
  description TEXT,                  -- 摘要
  debit_amount REAL DEFAULT 0,       -- 借方金额
  credit_amount REAL DEFAULT 0,      -- 贷方金额
  dept_id INTEGER,                   -- 部门ID
  project_id INTEGER,                -- 项目ID
  customer_id INTEGER,               -- 客户ID
  supplier_id INTEGER,               -- 供应商ID
  employee_id INTEGER,              -- 员工ID
  FOREIGN KEY (voucher_id) REFERENCES vouchers(id),
  FOREIGN KEY (dept_id) REFERENCES dimensions(id),
  FOREIGN KEY (project_id) REFERENCES dimensions(id),
  FOREIGN KEY (customer_id) REFERENCES dimensions(id),
  FOREIGN KEY (supplier_id) REFERENCES dimensions(id),
  FOREIGN KEY (employee_id) REFERENCES dimensions(id),
  FOREIGN KEY (account_code) REFERENCES accounts(code)
);

CREATE INDEX idx_entries_voucher ON voucher_entries(voucher_id);
CREATE INDEX idx_entries_account ON voucher_entries(account_code);
```

#### balances - 余额表

```sql
CREATE TABLE balances (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_code TEXT NOT NULL,
  period TEXT NOT NULL,
  dept_id INTEGER NOT NULL DEFAULT 0,       -- 部门ID（0=未指定）
  project_id INTEGER NOT NULL DEFAULT 0,    -- 项目ID（0=未指定）
  customer_id INTEGER NOT NULL DEFAULT 0,   -- 客户ID（0=未指定）
  supplier_id INTEGER NOT NULL DEFAULT 0,   -- 供应商ID（0=未指定）
  employee_id INTEGER NOT NULL DEFAULT 0,   -- 员工ID（0=未指定）
  opening_balance REAL DEFAULT 0,           -- 期初余额
  debit_amount REAL DEFAULT 0,              -- 借方发生额
  credit_amount REAL DEFAULT 0,             -- 贷方发生额
  closing_balance REAL DEFAULT 0,           -- 期末余额
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(
    account_code,
    period,
    dept_id,
    project_id,
    customer_id,
    supplier_id,
    employee_id
  )
);

CREATE INDEX idx_balances_account ON balances(account_code);
CREATE INDEX idx_balances_period ON balances(period);
CREATE INDEX idx_balances_dept ON balances(dept_id);
CREATE INDEX idx_balances_project ON balances(project_id);
CREATE INDEX idx_balances_customer ON balances(customer_id);
CREATE INDEX idx_balances_supplier ON balances(supplier_id);
CREATE INDEX idx_balances_employee ON balances(employee_id);
```

#### void_vouchers - 红字冲销记录

```sql
CREATE TABLE void_vouchers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  original_voucher_id INTEGER NOT NULL,      -- 原凭证ID
  void_voucher_id INTEGER NOT NULL,          -- 冲销凭证ID
  void_reason TEXT,                          -- 冲销原因
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (original_voucher_id) REFERENCES vouchers(id),
  FOREIGN KEY (void_voucher_id) REFERENCES vouchers(id)
);
```

#### periods - 期间表

```sql
CREATE TABLE periods (
  period TEXT PRIMARY KEY,                  -- 期间（YYYY-MM）
  status TEXT NOT NULL DEFAULT 'open',      -- 状态: open|closed
  opened_at TEXT,
  closed_at TEXT
);

CREATE INDEX idx_periods_status ON periods(status);
```

### 2.3 ER图

```
accounts (科目)
  ├─ 1:N → voucher_entries (分录)

dimensions (辅助核算)
  ├─ 1:N → voucher_entries (分录)

vouchers (凭证)
  ├─ 1:N → voucher_entries (分录)

balances (余额)
  └─ 按科目、期间、维度组合汇总

void_vouchers (冲销记录)
  ├─ N:1 → vouchers (原凭证)
  ├─ N:1 → vouchers (冲销凭证)

periods (期间)
  └─ vouchers、balances 的期间控制
```

---

## 3. API设计

### 3.1 ledger init - 初始化账套

初始化数据库，创建标准科目体系。

```bash
ledger init
ledger init --db-path /path/to/ledger.db
```

**功能：**
1. 创建数据库表
2. 导入财政部标准科目（一级科目）
3. 创建默认期间（当前年月）

**输出：**
```json
{
  "status": "success",
  "message": "账套初始化完成",
  "accounts_loaded": 156,
  "current_period": "2025-01"
}
```

---

### 3.2 ledger account - 科目管理

#### 3.2.1 ledger account list - 列出科目

```bash
ledger account list
ledger account list --type asset
ledger account list --level 1
```

**输出：**
```json
{
  "accounts": [
    {
      "code": "1001",
      "name": "库存现金",
      "level": 1,
      "type": "asset",
      "direction": "debit",
      "is_enabled": true,
      "children": [
        {
          "code": "1001001",
          "name": "人民币",
          "level": 2
        }
      ]
    }
  ]
}
```

#### 3.2.2 ledger account add - 添加科目

```bash
ledger account add <<EOF
{
  "code": "1002001",
  "name": "美元存款",
  "parent_code": "1002",
  "type": "asset",
  "direction": "debit"
}
EOF
```

**输出：**
```json
{
  "status": "success",
  "message": "科目已添加",
  "code": "1002001"
}
```

#### 3.2.3 ledger account disable - 停用科目

```bash
ledger account disable 1002001
```

---

### 3.3 ledger dimensions - 辅助核算管理

#### 3.3.1 列出维度

```bash
ledger dimensions list --type department
ledger dimensions list --type customer
```

**输出：**
```json
{
  "dimensions": [
    {"id": 1, "code": "D001", "name": "销售部", "parent_id": null},
    {"id": 2, "code": "D002", "name": "市场部", "parent_id": null}
  ]
}
```

#### 3.3.2 添加维度

```bash
ledger dimensions add <<EOF
{
  "type": "department",
  "code": "D003",
  "name": "技术部"
}
EOF
```

---

### 3.4 ledger record - 录入凭证

#### 3.4.1 基本用法（草稿模式）

```bash
ledger record <<EOF
{
  "date": "2025-01-15",
  "description": "购买原材料",
  "entries": [
    {
      "account": "原材料",
      "debit": 10000,
      "description": "采购钢材"
    },
    {
      "account": "应付账款",
      "credit": 10000,
      "supplier": "S001"
    }
  ]
}
EOF
```

**输出（草稿）：**
```json
{
  "voucher_id": 1,
  "voucher_no": "V20250115001",
  "status": "draft",
  "message": "草稿已保存，使用 ledger confirm 确认",
  "voucher": {
    "date": "2025-01-15",
    "description": "购买原材料",
    "entries": [
      {
        "account": "1403",
        "account_name": "原材料",
        "debit": 10000,
        "credit": 0
      },
      {
        "account": "2202",
        "account_name": "应付账款",
        "debit": 0,
        "credit": 10000,
        "supplier": "供应商A"
      }
    ],
    "debit_total": 10000,
    "credit_total": 10000,
    "is_balanced": true
  }
}
```

#### 3.4.2 带辅助核算

```bash
ledger record <<EOF
{
  "date": "2025-01-15",
  "description": "销售产品",
  "entries": [
    {
      "account": "应收账款",
      "debit": 50000,
      "customer": "C001",
      "project": "P001"
    },
    {
      "account": "主营业务收入",
      "credit": 50000,
      "department": "D001"
    }
  ]
}
EOF
```

#### 3.4.3 自动模式（直接确认）

```bash
ledger record --auto <<EOF
{
  "date": "2025-01-15",
  "description": "支付租金",
  "entries": [
    {
      "account": "管理费用",
      "debit": 8000
    },
    {
      "account": "银行存款",
      "credit": 8000
    }
  ]
}
EOF
```

**输出（已确认）：**
```json
{
  "voucher_id": 2,
  "voucher_no": "V20250115002",
  "status": "confirmed",
  "message": "凭证已确认，余额已更新，三表已生成",
  "confirmed_at": "2025-01-15 10:30:00",
  "balances_updated": 2,
  "reports_generated": true
}
```

---

### 3.5 ledger confirm - 确认草稿

```bash
ledger confirm 1
```

**处理逻辑：**
1. 更新凭证状态：`draft` → `confirmed`
2. 校验借贷平衡
3. 更新余额表
4. 自动生成三表

**输出：**
```json
{
  "voucher_id": 1,
  "status": "confirmed",
  "message": "凭证已确认，余额已更新，三表已生成",
  "confirmed_at": "2025-01-15 10:30:00",
  "balances_updated": 2,
  "reports_generated": true
}
```

---

### 3.6 ledger delete - 删除草稿

```bash
ledger delete 1
```

**条件：** 只能删除 `draft` 状态的凭证（物理删除）

**输出：**
```json
{
  "voucher_id": 1,
  "deleted": true,
  "message": "草稿已删除"
}
```

---

### 3.7 ledger void - 作废凭证（红字冲销）

```bash
ledger void 2 --reason "原凭证有误"
```

**处理逻辑：**
1. 创建红字凭证（借/贷金额取反）
2. 原凭证状态：`confirmed` → `voided`
3. 红字凭证状态：`confirmed`
4. 记录到 `void_vouchers` 表
5. 更新余额表

**输出：**
```json
{
  "original_voucher_id": 2,
  "void_voucher_id": 3,
  "status": "voided",
  "message": "凭证已作废，红字冲销凭证已生成",
  "void_voucher_no": "V20250115003"
}
```

---

### 3.8 ledger query - 查询

#### 3.8.1 查询凭证

```bash
ledger query vouchers
ledger query vouchers --period 2025-01
ledger query vouchers --status draft
ledger query vouchers --account 1001
```

**输出：**
```json
{
  "vouchers": [
    {
      "id": 1,
      "voucher_no": "V20250115001",
      "date": "2025-01-15",
      "description": "购买原材料",
      "status": "confirmed",
      "entries": [
        {"account": "原材料", "debit": 10000},
        {"account": "应付账款", "credit": 10000}
      ]
    }
  ]
}
```

#### 3.8.2 查询余额

```bash
ledger query balances
ledger query balances --period 2025-01
ledger query balances --account 1001
ledger query balances --dept-id 1
ledger query balances --dept-id 1 --customer-id 2
```

**输出：**
```json
{
  "period": "2025-01",
  "balances": [
    {
      "account_code": "1001",
      "account_name": "库存现金",
      "opening_balance": 50000,
      "debit_amount": 8000,
      "credit_amount": 3000,
      "closing_balance": 55000
    }
  ]
}
```

#### 3.8.3 查询科目余额表（试算平衡）

```bash
ledger query trial-balance --period 2025-01
```

**输出：**
```json
{
  "period": "2025-01",
  "trial_balance": [
    {
      "account_code": "1001",
      "account_name": "库存现金",
      "type": "asset",
      "opening_balance": 50000,
      "debit_amount": 8000,
      "credit_amount": 3000,
      "closing_balance": 55000,
      "direction": "debit"
    }
  ],
  "total_debit": 150000,
  "total_credit": 150000,
  "is_balanced": true
}
```

---

### 3.9 ledger report - 生成三表

```bash
ledger report --period 2025-01
ledger report --period 2025-01 --output reports/2025-01.xlsx
```

**功能：**
1. 从余额表提取数据
2. 调用 `balance calc` 计算配平
3. 生成资产负债表、利润表、现金流量表
4. 输出JSON或Excel

**输出（JSON）：**
```json
{
  "period": "2025-01",
  "income_statement": {
    "revenue": 500000,
    "cost": 300000,
    "gross_profit": 200000,
    "net_income": 50000
  },
  "balance_sheet": {
    "total_assets": 1000000,
    "total_liabilities": 400000,
    "total_equity": 600000
  },
  "cash_flow_statement": {
    "operating_cf": 30000,
    "investing_cf": -20000,
    "financing_cf": -10000,
    "net_change": 0
  },
  "is_balanced": true
}
```

---

## 4. 核心算法

### 4.1 余额计算

```python
def update_balance(voucher_id, period):
    """
    确认凭证时更新余额表

    逻辑：
    1. 读取凭证的所有分录
    2. 按科目+期间+维度组合分组汇总
    3. 计算期末余额 = 期初 + 借方 - 贷方（或反之）
    """

    entries = get_voucher_entries(voucher_id)

    for entry in entries:
        # 查找或创建余额记录
        balance = get_or_create_balance(
            account_code=entry.account_code,
            period=period,
            dept_id=entry.dept_id or 0,
            project_id=entry.project_id or 0,
            customer_id=entry.customer_id or 0,
            supplier_id=entry.supplier_id or 0,
            employee_id=entry.employee_id or 0
        )

        # 更新发生额
        balance.debit_amount += entry.debit_amount
        balance.credit_amount += entry.credit_amount

        # 计算期末余额
        account = get_account(entry.account_code)

        if account.direction == 'debit':
            balance.closing_balance = (
                balance.opening_balance +
                balance.debit_amount -
                balance.credit_amount
            )
        else:  # credit
            balance.closing_balance = (
                balance.opening_balance -
                balance.debit_amount +
                balance.credit_amount
            )

        save_balance(balance)
```

### 4.2 期间滚动

```python
def roll_period(current_period, next_period):
    """
    期间结账：本期期末 = 下期期初
    """

    balances = get_balances_by_period(current_period)

    for balance in balances:
        # 创建下期余额
        new_balance = Balance(
            account_code=balance.account_code,
            period=next_period,
            opening_balance=balance.closing_balance,
            debit_amount=0,
            credit_amount=0,
            closing_balance=balance.closing_balance
        )
        save_balance(new_balance)

    # 标记本期为已结账
    close_period(current_period)
```

### 4.3 三表生成

```python
def generate_statements(period):
    """
    从余额表生成三表
    """

    # 1. 读取余额表
    balances = get_balances_by_period(period)

    # 2. 映射到 balance calc 的输入格式
    input_data = {
        "revenue": sum(get_balance(balances, "主营业务收入").closing_balance),
        "cost": sum(get_balance(balances, "主营业务成本").closing_balance),
        "opening_cash": get_balance(balances, "1001").closing_balance,
        "opening_debt": sum_debt_balances(balances),
        # ... 更多字段
    }

    # 3. 调用 balance calc
    result = call_balance_calc(input_data)

    # 4. 返回结果
    return result
```

---

## 5. 实现架构

### 5.1 目录结构

```
balance/
├── ledger.py                    # CLI入口
├── ledger/
│   ├── __init__.py
│   ├── cli.py                   # 主CLI逻辑
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── init.py              # 初始化
│   │   ├── record.py            # 录入凭证
│   │   ├── confirm.py           # 确认草稿
│   │   ├── delete.py            # 删除草稿
│   │   ├── query.py             # 查询
│   │   ├── report.py            # 生成报表
│   │   ├── account.py           # 科目管理
│   │   └── dimension.py        # 辅助核算管理
│   ├── models/
│   │   ├── __init__.py
│   │   ├── voucher.py           # 凭证模型
│   │   ├── account.py           # 科目模型
│   │   ├── balance.py           # 余额模型
│   │   └── dimension.py        # 维度模型
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py        # 数据库连接
│   │   ├── schema.py           # 建表SQL
│   │   └── migrations.py       # 数据迁移
│   └── utils.py
├── data/
│   └── standard_accounts.json   # 财政部标准科目
└── fin_tools/                   # 现有工具
```

### 5.2 依赖库

```
sqlite3              # Python内置
click                # CLI参数解析
tabulate             # 表格输出
```

### 5.3 模块设计

#### database/connection.py

```python
import sqlite3
from contextlib import contextmanager

@contextmanager
def get_db(db_path='./ledger.db'):
    """数据库连接上下文管理器"""

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

#### models/voucher.py

```python
from dataclasses import dataclass
from typing import List

@dataclass
class VoucherEntry:
    account_code: str
    debit_amount: float = 0
    credit_amount: float = 0
    description: str = None
    dept_id: int = None
    project_id: int = None
    customer_id: int = None
    supplier_id: int = None
    employee_id: int = None

@dataclass
class Voucher:
    id: int = None
    voucher_no: str = None
    date: str = None
    period: str = None
    description: str = None
    status: str = 'draft'
    entries: List[VoucherEntry] = None

    def is_balanced(self):
        """校验借贷平衡"""
        total_debit = sum(e.debit_amount for e in self.entries)
        total_credit = sum(e.credit_amount for e in self.entries)
        return abs(total_debit - total_credit) < 0.01
```

---

## 6. 与现有工具集成

### 6.1 调用 balance calc

```python
def generate_statements(period):
    """生成三表，调用现有的 balance calc"""

    # 1. 从余额表提取数据
    balances = get_balances_by_period(period)
    input_data = balances_to_balance_input(balances)

    # 2. 调用 balance calc
    from balance import run_calc
    result = run_calc(input_data)

    # 3. 返回结果
    return result
```

### 6.2 调用 ac tb

```python
def trial_balance(period):
    """试算平衡，调用 ac tb"""

    balances = get_balances_by_period(period)
    accounts = balances_to_ac_accounts(balances)

    from fin_tools.tools.audit_tools import trial_balance
    result = trial_balance(accounts=accounts, tolerance=0.01)

    return result
```

---

## 7. 使用示例

### 7.1 完整流程

```bash
# 1. 初始化
ledger init

# 2. 录入凭证（草稿）
ledger record <<EOF
{
  "date": "2025-01-15",
  "description": "购买原材料",
  "entries": [
    {"account": "原材料", "debit": 10000},
    {"account": "应付账款", "credit": 10000, "supplier": "S001"}
  ]
}
EOF

# 3. 确认凭证
ledger confirm 1

# 4. 查询余额
ledger query balances --period 2025-01

# 5. 生成三表
ledger report --period 2025-01
```

### 7.2 红字冲销

```bash
# 1. 查询凭证
ledger query vouchers --voucher-no V20250115001

# 2. 作废凭证（生成红字）
ledger void 1 --reason "原凭证科目错误"

# 3. 重新录入正确凭证
ledger record --auto <<EOF
{
  "date": "2025-01-15",
  "description": "购买库存商品（更正）",
  "entries": [
    {"account": "库存商品", "debit": 10000},
    {"account": "应付账款", "credit": 10000, "supplier": "S001"}
  ]
}
EOF
```

### 7.3 批量导入凭证

```bash
# 从JSON导入
cat vouchers.json | jq '.[]' | while read voucher; do
  echo "$voucher" | ledger record --auto
done

# 查询导入结果
ledger query vouchers --period 2025-01
```

---

## 8. 实现计划

### Phase 1: 核心框架
- [ ] `ledger.py` CLI入口
- [ ] 数据库连接管理（`database/connection.py`）
- [ ] 建表SQL（`database/schema.py`）
- [ ] 标准科目数据（`data/standard_accounts.json`）

### Phase 2: 基础功能
- [ ] `ledger init` 初始化账套
- [ ] `ledger account add/list` 科目管理
- [ ] `ledger dimensions add/list` 辅助核算管理
- [ ] `ledger record` 录入凭证（草稿）
- [ ] `ledger confirm` 确认草稿

### Phase 3: 余额计算
- [ ] 余额更新逻辑
- [ ] `ledger query balances` 查询余额
- [ ] `ledger query trial-balance` 试算平衡

### Phase 4: 报表生成
- [ ] 调用 `balance calc` 生成三表
- [ ] `ledger report` 生成报表
- [ ] Excel导出

### Phase 5: 凭证管理
- [ ] `ledger delete` 删除草稿
- [ ] `ledger void` 红字冲销
- [ ] `ledger query vouchers` 查询凭证

### Phase 6: 高级功能
- [ ] 期间管理（结账、开账）
- [ ] 批量导入凭证
- [ ] 数据导出（JSON、Excel）

---

## 9. 数据完整性校验

### 9.1 凭证校验

- [ ] 借贷必相等（允许0.01误差）
- [ ] 日期必须在期间内
- [ ] 科目必须存在且启用
- [ ] 辅助核算值必须存在

### 9.2 余额校验

- [ ] 所有科目期末余额 = 期初 + 借方 - 贷方（或反之）
- [ ] 资产 = 负债 + 权益
- [ ] 净利润 = 收入 - 费用

### 9.3 冲销校验

- [ ] 冲销凭证与原凭证金额相等、方向相反
- [ ] 冲销后余额恢复到原凭证前状态

---

## 10. 性能优化

### 10.1 索引策略

已在表结构中定义关键索引：
- `idx_vouchers_period` - 按期间查询凭证
- `idx_entries_account` - 按科目查询分录
- `idx_balances_account` - 按科目查询余额

### 10.2 批量操作

```python
def batch_confirm(voucher_ids):
    """批量确认凭证，减少事务次数"""

    with get_db() as conn:
        for voucher_id in voucher_ids:
            update_balance(conn, voucher_id)
        conn.commit()
```

### 10.3 缓存策略

```python
# 三表结果缓存（5分钟）
CACHE_TTL = 300
_statement_cache = {}

def generate_statements(period):
    cache_key = f"statements_{period}"

    if cache_key in _statement_cache:
        cached = _statement_cache[cache_key]
        if time.time() - cached['timestamp'] < CACHE_TTL:
            return cached['result']

    # 计算并缓存
    result = calculate_statements(period)
    _statement_cache[cache_key] = {
        'result': result,
        'timestamp': time.time()
    }

    return result
```

---

## 11. 错误处理

### 11.1 错误码

| 错误码 | 说明 |
|--------|------|
| `DB_NOT_FOUND` | 数据库文件不存在 |
| `VOUCHER_NOT_FOUND` | 凭证不存在 |
| `ACCOUNT_NOT_FOUND` | 科目不存在 |
| `ACCOUNT_DISABLED` | 科目已停用 |
| `NOT_BALANCED` | 借贷不相等 |
| `PERIOD_CLOSED` | 期间已结账 |
| `VOID_CONFIRMED` | 已确认凭证不能删除，只能冲销 |
| `DIMENSION_NOT_FOUND` | 辅助核算值不存在 |

### 11.2 错误输出格式

```json
{
  "error": true,
  "code": "NOT_BALANCED",
  "message": "借贷不相等：借方10000，贷方9000",
  "details": {
    "debit_total": 10000,
    "credit_total": 9000,
    "difference": 1000
  }
}
```

---

## 12. 扩展方向

### 12.1 短期扩展

- [ ] 凭证模板（常用凭证快速录入）
- [ ] 自动编号规则自定义
- [ ] 多账套支持
- [ ] 数据导入导出（从金蝶/用友导入）

### 12.2 长期扩展

- [ ] 固定资产管理（资产卡片、折旧）
- [ ] 工资管理（工资单、个税计算）
- [ ] 往来管理（应收应付对账）
- [ ] 发票管理（发票录入、税控接口）
- [ ] 结算管理（银行对账、往来核销）

---

## 13. 附录

### 13.1 财政部标准科目表（部分）

```json
{
  "1001": "库存现金",
  "1002": "银行存款",
  "1122": "应收账款",
  "1403": "原材料",
  "1601": "固定资产",
  "2001": "短期借款",
  "2202": "应付账款",
  "4001": "实收资本",
  "4103": "本年利润",
  "5001": "生产成本",
  "6001": "主营业务收入",
  "6401": "主营业务成本"
}
```

### 13.2 术语表

| 术语 | 英文 | 说明 |
|------|------|------|
| 凭证 | Voucher | 记录经济业务的原始凭证 |
| 分录 | Entry | 凭证中的借贷明细 |
| 科目 | Account | 会计科目代码和名称 |
| 借方 | Debit | 资产/费用增加，负债/权益/收入减少 |
| 贷方 | Credit | 负债/权益/收入增加，资产/费用减少 |
| 余额 | Balance | 科目的当前金额 |
| 期间 | Period | 会计期间（月度） |
| 草稿 | Draft | 未确认的凭证 |
| 确认 | Confirm | 确认凭证并更新余额 |
| 作废 | Void | 作废凭证并生成红字冲销 |
| 辅助核算 | Auxiliary Accounting | 部门、项目、客户等多维度核算 |

---

## 14. 参考资料

- 财政部《企业会计准则——基本准则》
- 财政部《企业会计制度——会计科目和会计报表》
- balance 项目现有文档（`README.md`, `skills.md`, `CLI_DESIGN.md`）
