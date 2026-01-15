# Specification: Balance记账系统实现

## Overview
为balance财务工具集添加完整的记账系统，实现凭证录入、账簿管理和三表生成功能，使balance从分析工具升级为具备基础记账能力的财务系统。

## Workflow Type
feature

## Task Scope

**In scope**：
- SQLite数据库设计（7张表：accounts、dimensions、vouchers、voucher_entries、balances、void_vouchers、periods）
- `ledger` CLI命令实现（init、record、confirm、delete、void、query、report、account、dimensions）
- 核心逻辑：余额计算、期间滚动、红字冲销
- 辅助核算支持（部门、项目、客户、供应商、人员）
- 与现有balance工具集成（调用balance calc生成三表）
- 基础测试脚本（smoke test）

**Out of scope**：
- 固定资产管理
- 工资管理
- 往来管理（应收应付对账）
- 发票管理
- Web界面
- 多用户权限管理

## Success Criteria
- `ledger init` 能成功初始化数据库和标准科目
- `ledger record` 能创建草稿凭证，`ledger confirm` 能确认凭证并更新余额
- `ledger void` 能生成红字冲销凭证
- `ledger report` 能生成三表（调用balance calc）
- `scripts/ledger_smoke.sh` 能通过所有测试
- 余额表正确计算，借贷必相等（允许0.01误差）
- 所有辅助核算维度正确关联到分录

## Requirements
- Python 3.8+
- SQLite3
- 保持与现有balance工具的兼容性
- 数据库文件默认为 `./ledger.db`，可配置 `--db-path`
- 凭证号格式：`VYYYYMMDDNNN`
- 三表映射从 `data/balance_mapping.json` 读取，可按科目前缀配置
- `ledger report` 支持利率/税率/折旧年限/残值参数，默认0

## Dev Environment

| 配置 | 值 |
|------|-----|
| Python | 3.8+ |
| 数据库 | SQLite (文件: ledger.db) |
| Worktree | .worktrees/001-ledger |

测试命令：
```bash
cd .worktrees/001-ledger
python3 -m pytest tests/ -v
bash scripts/ledger_smoke.sh
```

## Files to Modify

**新增文件：**
- `ledger.py` - CLI入口
- `ledger/__init__.py`
- `ledger/cli.py` - 主CLI逻辑
- `ledger/commands/__init__.py`
- `ledger/commands/init.py` - 初始化命令
- `ledger/commands/record.py` - 录入凭证
- `ledger/commands/confirm.py` - 确认草稿
- `ledger/commands/delete.py` - 删除凭证
- `ledger/commands/void.py` - 作废凭证
- `ledger/commands/query.py` - 查询凭证/余额
- `ledger/commands/report.py` - 生成报表
- `ledger/commands/account.py` - 科目管理
- `ledger/commands/dimension.py` - 辅助核算管理
- `ledger/models/__init__.py`
- `ledger/models/voucher.py` - 凭证模型
- `ledger/models/account.py` - 科目模型
- `ledger/models/balance.py` - 余额模型
- `ledger/models/dimension.py` - 维度模型
- `ledger/database/__init__.py`
- `ledger/database/connection.py` - 数据库连接
- `ledger/database/schema.py` - 建表SQL
- `ledger/database/migrations.py` - 数据迁移
- `data/standard_accounts.json` - 财政部标准科目
- `data/balance_mapping.json` - 三表映射配置
- `scripts/ledger_smoke.sh` - 烟雾测试
- `tests/__init__.py`
- `tests/test_connection.py` - 数据库连接测试
- `tests/test_voucher.py` - 凭证测试
- `tests/test_balance.py` - 余额计算测试

**参考文档：**
- `docs/LEDGER_DESIGN.md` - 设计文档
- `docs/LEDGER_TEST_PLAN.md` - 测试计划

## Files to Reference
- `balance.py` - 现有三表配平模型（run_calc）
- `fin_tools/tools/audit_tools.py` - 现有审计工具
- `balance.py` - 现有balance CLI
- `README.md` - 项目说明
- `scripts/smoke.sh` - 现有测试脚本格式

## QA Acceptance Criteria

通过测试用例 TC-LEDGER-01 ~ TC-LEDGER-10

- TC-LEDGER-01: 数据库初始化成功，标准科目加载
- TC-LEDGER-02: 草稿凭证创建正确，status='draft'
- TC-LEDGER-03: 凭证确认成功，余额表正确更新
- TC-LEDGER-04: 借贷不平等返回错误 `NOT_BALANCED`
- TC-LEDGER-05: 红字冲销凭证与原凭证金额相等、方向相反
- TC-LEDGER-06: 辅助核算正确关联到分录和余额
- TC-LEDGER-07: `ledger report` 生成三表，调用balance calc成功
- TC-LEDGER-08: smoke test全部通过
- TC-LEDGER-09: 删除草稿凭证为物理删除，已确认凭证禁止删除
- TC-LEDGER-10: 三表映射读取配置，报表参数可覆盖默认假设

## Test Setup

```bash
# 1. 初始化数据库
rm -f /tmp/test_ledger.db
python3 ledger.py init --db-path /tmp/test_ledger.db

# 2. 录入测试凭证
cat <<JSON | python3 ledger.py record --db-path /tmp/test_ledger.db
{
  "date": "2025-01-15",
  "description": "测试凭证",
  "entries": [
    {"account": "库存现金", "debit": 1000},
    {"account": "银行存款", "credit": 1000}
  ]
}
JSON

# 3. 确认凭证
python3 ledger.py confirm 1 --db-path /tmp/test_ledger.db

# 4. 查询余额
python3 ledger.py query balances --period 2025-01 --db-path /tmp/test_ledger.db

# 5. 生成三表
python3 ledger.py report --period 2025-01 --db-path /tmp/test_ledger.db
```

## Test Cases

### TC-LEDGER-01: 数据库初始化
- **前置**：无
- **操作**：运行 `ledger init`
- **预期**：
  - 数据库文件 `ledger.db` 创建成功
  - 7张表正确创建
  - 财政部标准科目（156个）加载成功
  - 默认期间创建成功
- **验证方式**：
  ```bash
  python3 ledger.py init
  sqlite3 ledger.db ".tables"
  sqlite3 ledger.db "SELECT COUNT(*) FROM accounts"
  ```

### TC-LEDGER-02: 草稿凭证创建
- **前置**：数据库已初始化
- **操作**：创建凭证（不带 `--auto`）
- **预期**：
  - vouchers表新增记录，status='draft'
  - voucher_entries表新增分录记录
  - 余额表不更新
  - 返回 `voucher_id` 和 `status: draft`
- **验证方式**：
  ```bash
  python3 ledger.py record <<JSON
  {
    "date": "2025-01-15",
    "description": "测试凭证",
    "entries": [
      {"account": "库存现金", "debit": 1000},
      {"account": "银行存款", "credit": 1000}
    ]
  }
  JSON
  sqlite3 ledger.db "SELECT status FROM vouchers WHERE id=1"
  ```

### TC-LEDGER-03: 凭证确认和余额更新
- **前置**：草稿凭证已创建
- **操作**：运行 `ledger confirm 1`
- **预期**：
  - vouchers表记录状态变为'confirmed'
  - balances表正确更新：
    - 库存现金：借方+1000，期末余额=1000
    - 银行存款：贷方+1000，期末余额=-1000
  - 三表自动生成（调用balance calc）
- **验证方式**：
  ```bash
  python3 ledger.py confirm 1
  sqlite3 ledger.db "SELECT * FROM balances WHERE account_code='1001'"
  python3 ledger.py report --period 2025-01 | jq '.is_balanced'
  ```

### TC-LEDGER-04: 借贷不平等校验
- **前置**：数据库已初始化
- **操作**：创建借贷不相等的凭证
- **预期**：
  - 返回错误码 `NOT_BALANCED`
  - 显示差额："借方10000，贷方9000，差额1000"
  - 凭证不写入数据库
- **验证方式**：
  ```bash
  python3 ledger.py record <<JSON
  {
    "date": "2025-01-15",
    "entries": [
      {"account": "库存现金", "debit": 10000},
      {"account": "银行存款", "credit": 9000}
    ]
  }
  JSON
  # 检查错误输出
  sqlite3 ledger.db "SELECT COUNT(*) FROM vouchers"
  ```

### TC-LEDGER-05: 红字冲销
- **前置**：已确认凭证ID=2
- **操作**：运行 `ledger void 2 --reason "测试"`
- **预期**：
  - 原凭证状态变为'voided'
  - 生成红字凭证（ID=3），金额取反
  - void_vouchers表记录冲销关系
  - 余额恢复到原凭证前状态
- **验证方式**：
  ```bash
  python3 ledger.py void 2 --reason "测试"
  sqlite3 ledger.db "SELECT id, status FROM vouchers WHERE id IN (2,3)"
  sqlite3 ledger.db "SELECT * FROM void_vouchers WHERE original_voucher_id=2"
  ```

### TC-LEDGER-06: 辅助核算关联
- **前置**：已添加部门D001、客户C001
- **操作**：创建带辅助核算的凭证
- **预期**：
  - 分录正确关联dept_id和customer_id
  - 余额表按维度正确汇总
  - 按维度查询返回正确结果
- **验证方式**：
  ```bash
  python3 ledger.py record --auto <<JSON
  {
    "date": "2025-01-15",
    "entries": [
      {"account": "应收账款", "debit": 50000, "customer": "C001"},
      {"account": "主营业务收入", "credit": 50000, "department": "D001"}
    ]
  }
  JSON
  sqlite3 ledger.db "SELECT dept_id, customer_id FROM voucher_entries WHERE voucher_id=1"
  python3 ledger.py query balances --dept-id 1
  python3 ledger.py query balances --dept-id 1 --customer-id 1
  ```

### TC-LEDGER-07: 三表生成
- **前置**：已确认多笔凭证
- **操作**：运行 `ledger report --period 2025-01`
- **预期**：
  - 调用balance calc成功
  - 返回资产负债表、利润表、现金流量表
  - `is_balanced` 为true
  - 三表数据与余额表一致
- **验证方式**：
  ```bash
  python3 ledger.py report --period 2025-01 | jq '.is_balanced'
  python3 ledger.py report --period 2025-01 | jq '.income_statement'
  ```

### TC-LEDGER-08: Smoke Test全部通过
- **前置**：代码已实现
- **操作**：运行 `scripts/ledger_smoke.sh`
- **预期**：
  - 所有命令执行成功
  - 无错误退出
  - 输出 `[smoke] OK`
- **验证方式**：
  ```bash
  bash scripts/ledger_smoke.sh
  echo $?
  ```

### TC-LEDGER-10: 三表映射与报表参数
- **前置**：数据库已初始化，存在余额数据
- **操作**：自定义 `data/balance_mapping.json` 并调用 `ledger report` 传入参数
- **预期**：
  - 映射文件生效，报表使用映射字段汇总
  - `--interest-rate`/`--tax-rate`/`--fixed-asset-life`/`--fixed-asset-salvage` 生效
- **验证方式**：
  ```bash
  python3 ledger.py report --period 2025-01 --interest-rate 0 --tax-rate 0 --fixed-asset-life 0 --fixed-asset-salvage 0
  ```

### TC-LEDGER-09: 删除草稿凭证
- **前置**：草稿凭证已创建
- **操作**：运行 `ledger delete <voucher_id>`
- **预期**：
  - vouchers 表记录被物理删除
  - voucher_entries 表记录被物理删除
  - 已确认凭证删除返回 `VOID_CONFIRMED`
- **验证方式**：
  ```bash
  python3 ledger.py delete 1
  sqlite3 ledger.db "SELECT COUNT(*) FROM vouchers WHERE id=1"
  sqlite3 ledger.db "SELECT COUNT(*) FROM voucher_entries WHERE voucher_id=1"
  ```

## Step-by-step Validation

0. **数据库初始化（已做）**
   - 做什么：实现 `database/connection.py` 和 `database/schema.py`
   - 测试：运行 `ledger init`，验证表创建
   - 验收：7张表正确创建，标准科目加载成功

1. **凭证模型实现（已做）**
   - 做什么：实现 `models/voucher.py`，定义Voucher和VoucherEntry
   - 测试：测试 `is_balanced()` 方法
   - 验收：借贷平衡判断正确（允许0.01误差）

2. **录入凭证命令（已做）**
   - 做什么：实现 `commands/record.py`，支持草稿和自动模式
   - 测试：创建草稿凭证，验证status='draft'
   - 验收：凭证正确写入数据库，分录正确关联

3. **确认凭证命令（已做）**
   - 做什么：实现 `commands/confirm.py`，更新状态和余额
   - 测试：确认凭证，验证余额表更新
   - 验收：余额计算正确，借贷必相等

4. **红字冲销命令（已做）**
   - 做什么：实现 `commands/void.py`，生成红字凭证
   - 测试：冲销已确认凭证
   - 验收：红字凭证正确生成，余额恢复

5. **查询命令（已做）**
   - 做什么：实现 `commands/query.py`，支持凭证和余额查询
   - 测试：查询凭证列表、余额列表、试算平衡
   - 验收：查询结果正确，按期间/科目/维度筛选正确

6. **三表生成命令（已做）**
   - 做什么：实现 `commands/report.py`，调用balance calc
   - 测试：生成三表
   - 验收：三表数据正确，配平成功

7. **科目管理命令（已做）**
   - 做什么：实现 `commands/account.py`，支持列表/添加/停用
   - 测试：添加自定义科目
   - 验收：科目正确添加，层级关系正确

8. **辅助核算管理（已做）**
   - 做什么：实现 `commands/dimension.py`，支持5个维度
   - 测试：添加部门、项目、客户、供应商、员工
   - 验收：维度正确添加，能关联到分录

9. **Smoke Test（已做）**
   - 做什么：创建 `scripts/ledger_smoke.sh`
   - 测试：运行smoke test
   - 验收：所有命令执行成功，输出OK

## Notes

**设计文档位置：** `docs/LEDGER_DESIGN.md`

**测试计划位置：** `docs/LEDGER_TEST_PLAN.md`

**财政部标准科目：** 已在 `data/standard_accounts.json` 中定义一级科目（156个，来源：财政部《企业会计准则——应用指南》附录）

**实现分6个阶段：**
- Phase 1: 核心框架（CLI、数据库连接、建表）
- Phase 2: 基础功能（init、account、dimensions、record、confirm）
- Phase 3: 余额计算（余额更新、查询、试算平衡）
- Phase 4: 报表生成（调用balance calc）
- Phase 5: 凭证管理（delete、void、查询）
- Phase 6: 高级功能（期间管理）

**参考实现：**
- 数据库连接参考 `database/connection.py` 的上下文管理器设计
- 命令行解析参考 `balance.py` 的argparse用法
- JSON输入输出参考其他CLI工具（ac.py、fa.py等）

## Progress

- [x] 完成设计文档（LEDGER_DESIGN.md）
- [x] 完成测试计划（LEDGER_TEST_PLAN.md）
- [x] 创建Spec文档（spec.md）
- [x] Phase 1: 核心框架
- [x] Phase 2: 基础功能
- [x] Phase 3: 余额计算
- [x] Phase 4: 报表生成
- [x] Phase 5: 凭证管理
- [x] Phase 6: 高级功能（期间管理）

## Next

无（已完成）
