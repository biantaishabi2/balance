# ma/ri/kp 输入模板示意（Excel/CSV）

方便从表格快速映射到 CLI 所需的 JSON，可用 csv/Excel 直接保存后 `cat file.csv | <cli>` 或用自定义脚本转换。

## ma（管理会计）
- 本量利/盈亏平衡（ma cvp/ma breakeven）
  - 列：产品/项目、售价、变动成本、固定成本（breakeven 可按产品逐项提供销量/收入占比）。
  - 例：`产品,售价,变动成本,固定成本`。
- 成本分摊（ma allocate）
  - 列：对象名称、分摊动因值（driver_units）。
  - 例：`成本对象,动因值` → 转成 `{"cost_objects":[{"name":"A","driver_units":100},...]}`。
- 部门/产品损益（ma dept/product）
  - 列：部门/产品、收入、直接成本、分摊成本（可选）。

## ri（风险管理）
- 账龄分析（ri aging）
  - 列：客户名称、金额、逾期天数（days_overdue）。
  - 例：`客户,金额,逾期天数`。
- 坏账计提（ri provision）
  - 列：客户/科目、余额、账龄区间；可按区间百分比计提。
- 信用评分（ri credit）
  - 列：客户、准时率、平均逾期、合作年限、订单数、信用额度、当前应收等核心字段。

## kp（绩效/KPI）
- KPI 仪表盘（kp kpi）
  - 列：名称、目标、实际、方向(higher_better/lower_better)、权重、类别。
- BSC/EVA/OKR
  - BSC：目标、指标、权重、达成值/目标值。
  - OKR：目标、KR 描述、目标值、当前值、权重。

> 这些表格可直接存为 CSV，再用简单脚本或 jq 组装成 CLI JSON 输入；没有现成 excel2json 模板时，示例结构可参考 `docs/AI_IO_GUIDE.md`。
