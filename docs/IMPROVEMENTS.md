# 现状改进与质量评估

## 已识别的改进
- 安装覆盖不足：`install.sh` 只安装 balance/excel2json/json2excel/excel_inspect，README 列出的 fm/ac/fa/cf/ma/ri/tx/kp 都不会进 PATH；需要统一安装方案（复制或打包 entrypoint）。
- 分发与依赖：缺少 pip 包、版本号、依赖锁和 changelog；建议提供 `pyproject.toml`/`requirements.lock`，并用 CLI entrypoint 安装。
- 示例与校验：多数 CLI 只接受 JSON；需为各 CLI 提供一键示例（JSON+Excel 模板）和校验命令，让会计能照抄运行。
- 端到端可用性：没有 CLI 级 smoke/集成测试；建议添加最小输入→输出的回归脚本，保证工具链可用。
- 日常操作性：缺少日志级别/错误码约定、运行失败的提示与建议，影响落地。

## 质量与可用性评估
- 优点：核心函数拆成原子工具（`fin_tools/tools/*`），预算/现金/税务/LBO 等模块有单测；CLI 支持 JSON/表格输出，结构清晰。
- 不足：三表配平模型假设粗略（利息不随新增借款迭代、营运资本轧差简单），输入校验提示少；没有端到端例子确保不同 CLI 间数据契合；未提供打包/版本管理。
- 适用范围：教学、粗略估算或作为 LLM 组件较合适；直接月结/审计需补充分录、校验和安装可用性后再上线。

## 已完成
- 安装覆盖：`install.sh` 安装全部 CLI。
- 桥接与样例：`docs/AI_IO_GUIDE.md` 列出模板→CLI 对齐和可运行样例，`skills.md` 引用。
- 质量标注：`docs/MODEL_ASSUMPTIONS.md` 说明模型假设；新增 `CHANGELOG.md`。
- Smoke：`scripts/smoke.sh` 最小回归脚本。

## 接下来要做
- 示例与桥接：补充 fm 子命令的最小样例（LBO/DCF/三表/比率），以及 ma/ri/kp 的 Excel 模板示意，降低输入门槛。
- 校验与提示：在 balance/fm/cf 等 CLI 增强输入校验、错误码和日志级别，给出可操作的修复建议。
- 可用性验证：将 smoke/集成脚本纳入 CI，覆盖导入→计算→诊断→导出链路。
- 质量管理：明确版本策略，结合 changelog 标注模型适用范围与假设更新。
