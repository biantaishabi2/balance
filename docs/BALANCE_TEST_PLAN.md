# 配平模型测试计划（增强版）

## 单元测试（pytest）
- 利息迭代：设置 `min_cash` 缺口，验证新增借款带动利息上升且在 max_iter/tolerance 内收敛。
- 营运资本拆解：提供 `delta_receivable/delta_payable/delta_inventory`，确认经营现金流按输入走，轧差只输出 `auto_adjustment` 小额兜底。
- 现金恒等式：不同场景（无缺口/有缺口/负缺口）下 `cash_flow_check` ≈ `closing_cash`，`is_balanced`/`cash_balanced` 为 True。
- 校验路径：缺必填字段、异常利率/税率、非 dict/无效 JSON 等返回明确错误并退出码 1。
- 收敛失败：迭代超出 max_iter 时输出警告字段，调用方可感知。

## 集成/回归
- 示例回归：`balance calc --compact < examples/input.json`（默认单轮）应稳定。
- 迭代示例：新增 fixture（如 `tests/fixtures/balance_min_cash.json`），运行 `balance calc --iterations 5 --compact < ...`，检查 `is_balanced`/`cash_balanced` 为 True，`auto_adjustment` 合理。
- 多期（如实现）：多期数组输入，逐期验证期初=上一期期末，跨期恒等式成立。

## 自动化
- 将增强样例纳入 `scripts/smoke.sh`/CI（.github/workflows/smoke.yml），覆盖迭代开关。
- 对关键字段输出进行近似断言（误差 < tolerance），避免浮点抖动。

## 手工/行为验证
- 非 JSON/数组输入：应提示“输入必须是 JSON 对象”并退出。
- 极端参数：利率<0 或 >阈值、min_cash 远大于经营现金流时的提示与收敛行为。
