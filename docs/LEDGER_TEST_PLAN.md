# 记账系统测试计划

## 单元测试（pytest）

### 数据库模块测试

#### database/connection.py
- [ ] 数据库连接正常建立
- [ ] 上下文管理器自动提交成功事务
- [ ] 异常时自动回滚事务
- [ ] 连接正常关闭

#### database/schema.py
- [ ] 所有7张表正确创建
- [ ] 外键约束正确建立
- [ ] 索引正确创建
- [ ] 默认值正确设置

### 模型测试

#### models/voucher.py
- [ ] `Voucher.is_balanced()` 正确判断借贷平衡
- [ ] 借贷相等时返回True（允许0.01误差）
- [ ] 借贷不相等时返回False
- [ ] 空分录时返回True

#### models/account.py
- [ ] 科目层级关系正确（parent_code关联）
- [ ] 科目类型校验（asset/liability/equity/revenue/expense）
- [ ] 借贷方向校验（debit/credit）

### 核心逻辑测试

#### 余额计算
- [ ] 借方科目：期末 = 期初 + 借方 - 贷方
- [ ] 贷方科目：期末 = 期初 - 借方 + 贷方
- [ ] 凭证确认后余额表正确更新
- [ ] 按维度组合（部门、项目等）正确汇总余额

#### 期间滚动
- [ ] 本期期末余额 = 下期期初余额
- [ ] 新期间借方、贷方发生额归零
- [ ] 期间状态正确变更（open → closed）

#### 三表生成
- [ ] 从余额表正确提取数据
- [ ] 正确调用 `balance calc`
- [ ] 返回的三表数据格式正确
- [ ] `is_balanced` 字段正确

### 辅助核算测试

- [ ] 部门维度正确关联到分录
- [ ] 项目维度正确关联到分录
- [ ] 客户维度正确关联到分录
- [ ] 供应商维度正确关联到分录
- [ ] 员工维度正确关联到分录
- [ ] 多维度组合正确汇总余额

---

## 集成测试

### 完整记账流程

```
1. 初始化账套
2. 添加自定义科目
3. 添加辅助核算维度
4. 录入凭证（草稿）
5. 确认凭证
6. 查询余额
7. 生成三表
8. 作废凭证（红字冲销）
```

**验证点：**
- [ ] `ledger init` 创建数据库和标准科目
- [ ] `ledger account add` 成功添加自定义科目
- [ ] `ledger dimensions add` 成功添加维度
- [ ] `ledger record` 创建草稿凭证，状态为'draft'
- [ ] `ledger confirm` 更新状态为'confirmed'，余额表更新
- [ ] `ledger query balances` 返回正确余额
- [ ] `ledger report` 生成正确的三表
- [ ] `ledger void` 生成红字凭证，原凭证状态为'voided'

### 借贷平衡校验

**测试用例：**
- [ ] 借贷相等：凭证正常确认
- [ ] 借贷不相等：返回 `NOT_BALANCED` 错误
- [ ] 允许0.01误差范围内视为平衡
- [ ] 超过0.01误差视为不平衡

### 红字冲销

**测试用例：**
- [ ] 红字凭证金额与原凭证相等、方向相反
- [ ] 冲销后余额恢复到原凭证前状态
- [ ] `void_vouchers` 表正确记录冲销关系
- [ ] 原凭证状态从'confirmed'变为'voided'
- [ ] 红字凭证状态为'confirmed'

### 与现有工具集成

#### 调用 balance calc
- [ ] 余额数据正确映射到 balance calc 输入格式
- [ ] balance calc 返回结果正确
- [ ] 生成的三表与 balance calc 结果一致

#### 调用 ac tb
- [ ] 余额数据正确映射到 ac tb 输入格式
- [ ] 试算平衡结果正确
- [ ] 借方总额 = 贷方总额

---

## 回归测试

### 基础回归

**运行命令：**
```bash
# 初始化
ledger init

# 录入凭证
cat <<'JSON' | ledger record
{
  "date": "2025-01-15",
  "description": "测试凭证",
  "entries": [
    {"account": "库存现金", "debit": 1000},
    {"account": "银行存款", "credit": 1000}
  ]
}
JSON

# 确认凭证
ledger confirm 1

# 查询余额
ledger query balances --period 2025-01

# 生成三表
ledger report --period 2025-01
ledger report --period 2025-01 --interest-rate 0 --tax-rate 0 --fixed-asset-life 0 --fixed-asset-salvage 0
```

**预期结果：**
- [ ] 所有命令执行成功
- [ ] 余额表正确更新
- [ ] 三表生成成功且配平
- [ ] 报表参数覆盖默认假设生效

### 多凭证回归

**运行命令：**
```bash
# 初始化
ledger init

# 添加辅助核算
ledger dimensions add <<'JSON'
{"type": "department", "code": "D001", "name": "销售部"}
JSON
ledger dimensions add <<'JSON'
{"type": "customer", "code": "C001", "name": "客户A"}
JSON

# 批量录入凭证
cat <<'JSON' | ledger record --auto
{
  "date": "2025-01-15",
  "description": "销售产品",
  "entries": [
    {"account": "应收账款", "debit": 50000, "customer": "C001", "department": "D001"},
    {"account": "主营业务收入", "credit": 50000, "department": "D001"}
  ]
}
JSON

cat <<'JSON' | ledger record --auto
{
  "date": "2025-01-16",
  "description": "购买原材料",
  "entries": [
    {"account": "原材料", "debit": 20000},
    {"account": "应付账款", "credit": 20000}
  ]
}
JSON

# 查询余额（按维度组合）
ledger query balances --dept-id 1
ledger query balances --customer-id 1
ledger query balances --dept-id 1 --customer-id 1

# 生成三表
ledger report --period 2025-01
ledger report --period 2025-01 --interest-rate 0 --tax-rate 0 --fixed-asset-life 0 --fixed-asset-salvage 0
```

**预期结果：**
- [ ] 辅助核算正确关联
- [ ] 按维度组合查询返回正确结果
- [ ] 三表正确生成
- [ ] 报表参数覆盖默认假设生效

### 三表映射配置

**运行命令：**
```bash
# 调整映射文件后生成报表
sed -n '1,120p' data/balance_mapping.json
ledger report --period 2025-01 --interest-rate 0 --tax-rate 0 --fixed-asset-life 0 --fixed-asset-salvage 0
```

**预期结果：**
- [ ] 映射文件生效（报表汇总字段随配置变化）

---

## 自动化测试

### 测试脚本

**文件：** `scripts/ledger_smoke.sh`

```bash
#!/usr/bin/env bash
# Minimal smoke test for ledger CLI.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB="/tmp/ledger_test.db"
rm -f "$DB"

echo "[smoke] ledger init"
python3 "$ROOT/ledger.py" init --db-path "$DB"

echo "[smoke] ledger account list"
python3 "$ROOT/ledger.py" account list --db-path "$DB" >/dev/null

echo "[smoke] ledger dimensions add"
python3 "$ROOT/ledger.py" dimensions add --db-path "$DB" <<'JSON' >/dev/null
{"type": "department", "code": "D001", "name": "销售部"}
JSON

echo "[smoke] ledger record (draft)"
python3 "$ROOT/ledger.py" record --db-path "$DB" <<'JSON' >/dev/null
{
  "date": "2025-01-15",
  "description": "测试凭证",
  "entries": [
    {"account": "库存现金", "debit": 1000},
    {"account": "银行存款", "credit": 1000}
  ]
}
JSON

echo "[smoke] ledger confirm"
python3 "$ROOT/ledger.py" confirm 1 --db-path "$DB" >/dev/null

echo "[smoke] ledger query balances"
python3 "$ROOT/ledger.py" query balances --period 2025-01 --db-path "$DB" >/dev/null

echo "[smoke] ledger report"
python3 "$ROOT/ledger.py" report --period 2025-01 --db-path "$DB" >/dev/null

echo "[smoke] ledger void"
python3 "$ROOT/ledger.py" void 1 --reason "测试" --db-path "$DB" >/dev/null

echo "[smoke] OK"
```

### CI集成

**文件：** `.github/workflows/ledger_smoke.yml`

```yaml
name: Ledger Smoke Test

on: [push, pull_request]

jobs:
  smoke:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Run smoke test
        run: bash scripts/ledger_smoke.sh
```

---

## 手工/行为验证

### 错误处理测试

#### 凭证借贷不平衡
```bash
ledger record <<'JSON'
{
  "date": "2025-01-15",
  "entries": [
    {"account": "库存现金", "debit": 1000},
    {"account": "银行存款", "credit": 900}
  ]
}
JSON
```

**预期结果：**
- [ ] 返回错误码 `NOT_BALANCED`
- [ ] 显示差额："借方1000，贷方900，差额100"
- [ ] 凭证不写入数据库

#### 科目不存在
```bash
ledger record <<'JSON'
{
  "date": "2025-01-15",
  "entries": [
    {"account": "不存在的科目", "debit": 1000},
    {"account": "银行存款", "credit": 1000}
  ]
}
JSON
```

**预期结果：**
- [ ] 返回错误码 `ACCOUNT_NOT_FOUND`
- [ ] 显示科目名称
- [ ] 凭证不写入数据库

#### 凭证不存在
```bash
ledger confirm 9999
```

**预期结果：**
- [ ] 返回错误码 `VOUCHER_NOT_FOUND`
- [ ] 显示凭证ID

#### 删除草稿凭证（物理删除）
```bash
# 创建草稿
ledger record <<'JSON'
{
  "date": "2025-01-15",
  "description": "草稿删除测试",
  "entries": [
    {"account": "库存现金", "debit": 1000},
    {"account": "银行存款", "credit": 1000}
  ]
}
JSON

# 删除草稿
ledger delete 1

# 验证数据库无记录
sqlite3 ledger.db "SELECT COUNT(*) FROM vouchers WHERE id=1"
sqlite3 ledger.db "SELECT COUNT(*) FROM voucher_entries WHERE voucher_id=1"
```

**预期结果：**
- [ ] 返回 `deleted: true`
- [ ] vouchers 表记录已删除
- [ ] voucher_entries 表记录已删除

#### 删除已确认凭证
```bash
ledger delete 1  # 假设凭证1已确认
```

**预期结果：**
- [ ] 返回错误码 `VOID_CONFIRMED`
- [ ] 提示已确认凭证不能删除，只能冲销
- [ ] 建议使用 `ledger void` 命令

### 极端参数测试

#### 零金额凭证
```bash
ledger record <<'JSON'
{
  "date": "2025-01-15",
  "entries": [
    {"account": "库存现金", "debit": 0},
    {"account": "银行存款", "credit": 0}
  ]
}
JSON
```

**预期结果：**
- [ ] 允许零金额凭证
- [ ] 视为借贷平衡

#### 大金额凭证
```bash
ledger record <<'JSON'
{
  "date": "2025-01-15",
  "entries": [
    {"account": "库存现金", "debit": 999999999999.99},
    {"account": "银行存款", "credit": 999999999999.99}
  ]
}
JSON
```

**预期结果：**
- [ ] 正常处理大金额
- [ ] 余额计算准确

#### 跨期间凭证
```bash
# 初始化期间为 2025-01
ledger init

# 录入 2026-01 的凭证
ledger record <<'JSON'
{
  "date": "2026-01-15",
  "entries": [
    {"account": "库存现金", "debit": 1000},
    {"account": "银行存款", "credit": 1000}
  ]
}
JSON
```

**预期结果：**
- [ ] 自动创建新期间（2026-01）
- [ ] 凭证正确记录到新期间

---

## 性能测试

### 批量凭证录入

**测试目标：**
- [ ] 录入1000张凭证 < 10秒
- [ ] 确认1000张凭证 < 30秒
- [ ] 生成三表 < 5秒

**测试脚本：**
```bash
#!/usr/bin/env bash
# Performance test: batch vouchers

DB="/tmp/ledger_perf.db"
rm -f "$DB"
ledger init --db-path "$DB"

# 生成1000张凭证
for i in {1..1000}; do
  cat <<JSON | ledger record --auto --db-path "$DB" >/dev/null
{
  "date": "2025-01-$(( (i - 1) % 28 + 1 ))",
  "description": "批量凭证$i",
  "entries": [
    {"account": "库存现金", "debit": 1000},
    {"account": "银行存款", "credit": 1000}
  ]
}
JSON
done

# 生成三表
time ledger report --period 2025-01 --db-path "$DB" >/dev/null

echo "[perf] 凭证数量: 1000"
```

### 大量辅助核算

**测试目标：**
- [ ] 10个维度组合查询 < 2秒
- [ ] 按维度汇总余额 < 3秒

---

## 数据完整性测试

### 事务回滚测试

**测试场景：**
- [ ] 确认凭证时余额更新失败，整个事务回滚
- [ ] 凭证状态保持为'draft'
- [ ] 余额表未受影响

**测试方法：**
```bash
# 模拟余额更新失败（手动断开数据库连接）
# 验证事务回滚
```

### 并发测试

**测试场景：**
- [ ] 多个进程同时确认不同凭证
- [ ] 余额表最终状态正确
- [ ] 无数据损坏

**测试脚本：**
```bash
#!/usr/bin/env bash
# Concurrent test

DB="/tmp/ledger_concurrent.db"
rm -f "$DB"
ledger init --db-path "$DB"

# 并发录入10张凭证
for i in {1..10}; do
  (
    cat <<JSON | ledger record --auto --db-path "$DB" >/dev/null
{
  "date": "2025-01-$(( (i - 1) % 28 + 1 ))",
  "description": "并发凭证$i",
  "entries": [
    {"account": "库存现金", "debit": 1000},
    {"account": "银行存款", "credit": 1000}
  ]
}
JSON
  ) &
done
wait

# 验证结果
ledger query vouchers --db-path "$DB" | jq '.vouchers | length'  # 应为10
```

---

## 兼容性测试

### Python版本兼容性

**测试目标：**
- [ ] Python 3.8: 所有功能正常
- [ ] Python 3.9: 所有功能正常
- [ ] Python 3.10: 所有功能正常
- [ ] Python 3.11: 所有功能正常

**测试方法：**
```bash
for py in python3.8 python3.9 python3.10 python3.11; do
  echo "Testing with $py"
  $py -m pytest tests/ -v
done
```

### SQLite版本兼容性

**测试目标：**
- [ ] SQLite 3.35+: 所有功能正常
- [ ] SQLite 3.38+: 所有功能正常
- [ ] SQLite 3.40+: 所有功能正常

### 操作系统兼容性

**测试目标：**
- [ ] Ubuntu 22.04: 所有功能正常
- [ ] macOS 13+: 所有功能正常
- [ ] Windows 10+: 所有功能正常

---

## 示例数据测试

### 使用 examples/ 数据

**测试用例：**
- [ ] 使用 `examples/ledger_sample_001.json` 录入凭证
- [ ] 验证结果与 `examples/ledger_output_001.json` 一致
- [ ] 三表结果与 `examples/ledger_reports_001.json` 一致

**测试脚本：**
```bash
#!/usr/bin/env bash
# Example data regression test

DB="/tmp/ledger_example.db"
rm -f "$DB"
ledger init --db-path "$DB"

# 导入示例凭证
cat examples/ledger_sample_001.json | ledger record --auto --db-path "$DB"

# 导出结果
ledger query balances --period 2025-01 --db-path "$DB" > /tmp/actual.json
ledger report --period 2025-01 --db-path "$DB" > /tmp/actual_reports.json

# 对比
diff /tmp/actual.json examples/ledger_output_001.json
diff /tmp/actual_reports.json examples/ledger_reports_001.json
```

---

## 测试覆盖率

**目标覆盖率：**
- [ ] 核心模块（database、models、commands）: > 80%
- [ ] 整体覆盖率: > 70%

**查看覆盖率：**
```bash
pytest --cov=ledger --cov-report=html tests/
```

---

## 问题追踪

**测试失败处理流程：**
1. 记录失败用例
2. 提交Issue到GitHub
3. 标记Issue标签：`test-failure`
4. 修复后重新运行测试
5. 验证通过后关闭Issue

---

## 持续改进

**定期审查：**
- [ ] 每月审查测试用例覆盖率
- [ ] 每季度添加新的边界测试
- [ ] 根据用户反馈补充测试用例
- [ ] 优化测试执行速度

**测试报告：**
- [ ] 每次CI运行生成测试报告
- [ ] 失败用例自动通知开发者
- [ ] 生成趋势报告（通过率、执行时间）
