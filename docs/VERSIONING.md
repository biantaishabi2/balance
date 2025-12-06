# 版本策略

- 采用语义化版本（SemVer）：`MAJOR.MINOR.PATCH`
  - 破坏性变更或兼容性风险：MAJOR++
  - 向后兼容功能：MINOR++
  - 向后兼容修复：PATCH++
- 变更记录：`CHANGELOG.md` 维护每个版本的新增/变更/修复。
- 模型假设/适用范围：重大假设调整需在 `docs/MODEL_ASSUMPTIONS.md` 同步标注。
- 发布前确保 smoke/关键测试通过（`scripts/smoke.sh` 或 CI workflow）。
