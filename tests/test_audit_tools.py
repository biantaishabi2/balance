# -*- coding: utf-8 -*-
"""
audit_tools 测试用例
"""

import pytest
from fin_tools.tools.audit_tools import (
    trial_balance,
    adjusting_entries,
    audit_sampling,
    consolidation
)


class TestTrialBalance:
    """试算平衡检查测试"""

    def test_balanced_accounts(self):
        """平衡的科目"""
        result = trial_balance([
            {"code": "1001", "name": "现金", "type": "asset", "debit": 100000, "credit": 0},
            {"code": "2001", "name": "应付账款", "type": "liability", "debit": 0, "credit": 60000},
            {"code": "3001", "name": "实收资本", "type": "equity", "debit": 0, "credit": 40000}
        ])

        assert result["balanced"] is True
        assert result["total_debit"] == 100000
        assert result["total_credit"] == 100000
        assert result["difference"] == 0

    def test_unbalanced_accounts(self):
        """不平衡的科目"""
        result = trial_balance([
            {"code": "1001", "name": "现金", "type": "asset", "debit": 100000, "credit": 0},
            {"code": "2001", "name": "应付账款", "type": "liability", "debit": 0, "credit": 50000}
        ])

        assert result["balanced"] is False
        assert result["difference"] == 50000
        assert any(issue["type"] == "unbalanced" for issue in result["issues"])

    def test_tolerance_check(self):
        """误差容忍度检查"""
        result = trial_balance([
            {"code": "1001", "name": "现金", "type": "asset", "debit": 100000.005, "credit": 0},
            {"code": "2001", "name": "负债", "type": "liability", "debit": 0, "credit": 100000}
        ], tolerance=0.01)

        assert result["balanced"] is True  # 误差在容忍范围内

    def test_by_type_summary(self):
        """按类型汇总"""
        result = trial_balance([
            {"code": "1001", "name": "现金", "type": "asset", "debit": 50000, "credit": 0},
            {"code": "1002", "name": "应收", "type": "asset", "debit": 30000, "credit": 0},
            {"code": "2001", "name": "应付", "type": "liability", "debit": 0, "credit": 80000}
        ])

        assert result["by_type"]["asset"]["count"] == 2
        assert result["by_type"]["asset"]["debit"] == 80000
        assert result["by_type"]["liability"]["count"] == 1

    def test_abnormal_balance_asset(self):
        """资产类科目异常余额（贷方）"""
        result = trial_balance([
            {"code": "1001", "name": "现金", "type": "asset", "debit": 0, "credit": 10000}
        ])

        assert result["accounts"][0]["is_normal"] is False
        assert any(issue["type"] == "abnormal_balance" for issue in result["issues"])

    def test_abnormal_balance_liability(self):
        """负债类科目异常余额（借方）"""
        result = trial_balance([
            {"code": "2001", "name": "应付", "type": "liability", "debit": 10000, "credit": 0}
        ])

        assert result["accounts"][0]["is_normal"] is False

    def test_both_sides_warning(self):
        """借贷双方同时有余额警告"""
        result = trial_balance([
            {"code": "1001", "name": "现金", "type": "asset", "debit": 50000, "credit": 10000}
        ])

        assert any(issue["type"] == "both_sides" for issue in result["issues"])

    def test_accounting_equation(self):
        """会计恒等式检查"""
        result = trial_balance([
            {"code": "1001", "name": "资产", "type": "asset", "debit": 100000, "credit": 0},
            {"code": "2001", "name": "负债", "type": "liability", "debit": 0, "credit": 60000},
            {"code": "3001", "name": "权益", "type": "equity", "debit": 0, "credit": 40000}
        ])

        eq = result["equation"]
        assert eq["assets"] == 100000
        assert eq["liabilities"] == 60000
        assert eq["equity"] == 40000
        assert eq["balanced"] is True

    def test_empty_accounts(self):
        """空科目列表"""
        result = trial_balance([])

        assert result["balanced"] is True
        assert result["total_debit"] == 0
        assert result["total_credit"] == 0

    def test_revenue_expense_accounts(self):
        """收入费用类科目"""
        # 借方：资产100000 + 费用80000 = 180000
        # 贷方：收入100000 + 权益80000 = 180000
        result = trial_balance([
            {"code": "6001", "name": "收入", "type": "revenue", "debit": 0, "credit": 100000},
            {"code": "6401", "name": "费用", "type": "expense", "debit": 80000, "credit": 0},
            {"code": "3001", "name": "权益", "type": "equity", "debit": 0, "credit": 80000},
            {"code": "1001", "name": "资产", "type": "asset", "debit": 100000, "credit": 0}
        ])

        assert result["balanced"] is True


class TestAdjustingEntries:
    """调整分录建议测试"""

    def test_accrual_entry(self):
        """应计费用分录"""
        result = adjusting_entries([
            {
                "type": "accrual",
                "description": "计提12月工资",
                "amount": 500000,
                "details": {
                    "expense_account": "管理费用-工资",
                    "liability_account": "应付职工薪酬"
                }
            }
        ])

        assert len(result["entries"]) == 1
        entry = result["entries"][0]
        assert entry["lines"][0]["account"] == "管理费用-工资"
        assert entry["lines"][0]["debit"] == 500000
        assert entry["lines"][1]["account"] == "应付职工薪酬"
        assert entry["lines"][1]["credit"] == 500000

    def test_deferral_entry(self):
        """递延费用摊销分录"""
        result = adjusting_entries([
            {
                "type": "deferral",
                "description": "房租摊销",
                "amount": 10000,
                "details": {
                    "asset_account": "预付账款-房租",
                    "expense_account": "管理费用-租金",
                    "total_periods": 12,
                    "current_period": 3
                }
            }
        ])

        entry = result["entries"][0]
        assert entry["lines"][0]["debit"] == 10000
        assert "第3/12期" in entry.get("note", "")

    def test_depreciation_straight_line(self):
        """直线法折旧"""
        result = adjusting_entries([
            {
                "type": "depreciation",
                "description": "设备折旧",
                "details": {
                    "asset_name": "生产设备",
                    "original_cost": 1200000,
                    "salvage_value": 0,
                    "useful_life": 10,
                    "method": "straight_line"
                }
            }
        ])

        entry = result["entries"][0]
        # 年折旧 = 1200000 / 10 = 120000, 月折旧 = 10000
        assert entry["amount"] == 10000
        assert "折旧费用-生产设备" in entry["lines"][0]["account"]
        assert "累计折旧-生产设备" in entry["lines"][1]["account"]

    def test_bad_debt_provision(self):
        """坏账准备计提"""
        result = adjusting_entries([
            {
                "type": "bad_debt",
                "description": "计提坏账准备",
                "details": {
                    "ar_balance": 1000000,
                    "provision_rate": 0.05,
                    "existing_provision": 30000
                }
            }
        ])

        entry = result["entries"][0]
        # 应提 = 1000000 * 5% = 50000, 补提 = 50000 - 30000 = 20000
        assert entry["amount"] == 20000
        assert entry["calculation"]["required_provision"] == 50000
        assert entry["calculation"]["adjustment"] == 20000

    def test_bad_debt_reversal(self):
        """坏账准备转回"""
        result = adjusting_entries([
            {
                "type": "bad_debt",
                "description": "转回坏账准备",
                "details": {
                    "ar_balance": 500000,
                    "provision_rate": 0.05,
                    "existing_provision": 50000
                }
            }
        ])

        entry = result["entries"][0]
        # 应提 = 500000 * 5% = 25000, 转回 = 25000 - 50000 = -25000
        assert "转回" in entry.get("note", "")

    def test_inventory_writedown(self):
        """存货跌价"""
        result = adjusting_entries([
            {
                "type": "inventory",
                "description": "存货跌价准备",
                "details": {
                    "book_value": 200000,
                    "market_value": 150000,
                    "existing_provision": 20000
                }
            }
        ])

        entry = result["entries"][0]
        # 应提 = 200000 - 150000 = 50000, 补提 = 50000 - 20000 = 30000
        assert entry["amount"] == 30000

    def test_reclassification(self):
        """重分类"""
        result = adjusting_entries([
            {
                "type": "reclassification",
                "description": "长期借款重分类",
                "amount": 1000000,
                "details": {
                    "from_account": "长期借款",
                    "to_account": "一年内到期的非流动负债",
                    "reason": "一年内到期"
                }
            }
        ])

        entry = result["entries"][0]
        assert entry["lines"][0]["account"] == "一年内到期的非流动负债"
        assert entry["lines"][1]["account"] == "长期借款"

    def test_summary_by_type(self):
        """按类型汇总"""
        result = adjusting_entries([
            {"type": "accrual", "description": "工资", "amount": 100000, "details": {}},
            {"type": "accrual", "description": "水电", "amount": 20000, "details": {}},
            {"type": "depreciation", "description": "折旧", "details": {"asset_name": "设备", "original_cost": 120000, "salvage_value": 0, "useful_life": 10}}
        ])

        assert result["summary"]["by_type"]["accrual"]["count"] == 2
        assert result["summary"]["by_type"]["accrual"]["amount"] == 120000
        assert result["summary"]["by_type"]["depreciation"]["count"] == 1

    def test_empty_items(self):
        """空调整列表"""
        result = adjusting_entries([])

        assert result["summary"]["total_entries"] == 0


class TestAuditSampling:
    """审计抽样测试"""

    def test_random_sampling(self):
        """简单随机抽样"""
        population = [{"id": f"INV{i:03d}", "amount": i * 1000} for i in range(1, 101)]

        result = audit_sampling(
            population=population,
            method="random",
            sample_size=10,
            seed=42
        )

        assert result["method"] == "random"
        assert result["population_size"] == 100
        assert result["sample_size"] == 10
        assert len(result["samples"]) == 10

    def test_systematic_sampling(self):
        """系统抽样"""
        population = [{"id": f"INV{i:03d}", "amount": i * 1000} for i in range(1, 101)]

        result = audit_sampling(
            population=population,
            method="systematic",
            sample_size=10,
            seed=42
        )

        assert result["method"] == "systematic"
        assert result["sample_size"] == 10

    def test_mus_sampling(self):
        """货币单位抽样"""
        population = [{"id": f"INV{i:03d}", "amount": i * 1000} for i in range(1, 101)]

        result = audit_sampling(
            population=population,
            method="mus",
            sample_size=20,
            seed=42
        )

        assert result["method"] == "mus"
        assert len(result["samples"]) <= 20
        # MUS应该偏向大金额
        assert result["coverage"] > 0.1

    def test_stratified_sampling(self):
        """分层抽样"""
        population = [{"id": f"INV{i:03d}", "amount": i * 1000} for i in range(1, 101)]

        result = audit_sampling(
            population=population,
            method="stratified",
            sample_size=15,
            seed=42
        )

        assert result["method"] == "stratified"
        assert len(result["samples"]) > 0

    def test_stratified_by_field(self):
        """按字段分层抽样"""
        population = [
            {"id": "1", "amount": 1000, "region": "东区"},
            {"id": "2", "amount": 2000, "region": "东区"},
            {"id": "3", "amount": 3000, "region": "西区"},
            {"id": "4", "amount": 4000, "region": "西区"},
            {"id": "5", "amount": 5000, "region": "南区"}
        ]

        result = audit_sampling(
            population=population,
            method="stratified",
            sample_size=3,
            strata_field="region",
            seed=42
        )

        assert len(result["samples"]) >= 1

    def test_high_value_items(self):
        """大额项目识别"""
        population = [
            {"id": "1", "amount": 1000},
            {"id": "2", "amount": 2000},
            {"id": "3", "amount": 100000},  # 大额
            {"id": "4", "amount": 150000}   # 大额
        ]

        result = audit_sampling(
            population=population,
            method="random",
            sample_size=2,
            tolerable_error=50000,
            seed=42
        )

        assert len(result["high_value_items"]) == 2
        # 大额项目全部抽取
        high_value_ids = [item["id"] for item in result["high_value_items"]]
        assert "3" in high_value_ids
        assert "4" in high_value_ids

    def test_coverage_calculation(self):
        """覆盖率计算"""
        population = [{"id": str(i), "amount": 1000} for i in range(100)]

        result = audit_sampling(
            population=population,
            method="random",
            sample_size=10,
            seed=42
        )

        # 10% 样本 = 10% 覆盖率（金额相同时）
        assert result["coverage"] == pytest.approx(0.1, rel=0.01)

    def test_custom_value_field(self):
        """自定义金额字段"""
        population = [{"id": str(i), "value": i * 100} for i in range(1, 11)]

        result = audit_sampling(
            population=population,
            method="random",
            sample_size=5,
            value_field="value",
            seed=42
        )

        assert result["population_value"] == 5500  # sum(100 to 1000)

    def test_empty_population(self):
        """空总体"""
        result = audit_sampling(population=[], method="random")

        assert result["population_size"] == 0
        assert result["sample_size"] == 0
        assert result["samples"] == []

    def test_sample_size_calculation(self):
        """样本量自动计算"""
        population = [{"id": str(i), "amount": 1000} for i in range(1000)]

        result = audit_sampling(
            population=population,
            method="random",
            tolerable_error=50000,
            confidence_level=0.95
        )

        # 样本量应该被计算出来
        assert result["sample_size"] > 0


class TestConsolidation:
    """合并报表抵消测试"""

    def test_basic_consolidation(self):
        """基本合并"""
        result = consolidation(
            parent={
                "name": "母公司",
                "assets": 10000000,
                "liabilities": 4000000,
                "equity": 6000000,
                "revenue": 5000000,
                "expenses": 4000000,
                "net_income": 1000000
            },
            subsidiaries=[
                {
                    "name": "子公司A",
                    "ownership": 0.8,
                    "assets": 5000000,
                    "liabilities": 2000000,
                    "equity": 3000000,
                    "paid_in_capital": 1500000,
                    "capital_reserve": 600000,
                    "retained_earnings": 900000,
                    "revenue": 3000000,
                    "expenses": 2500000,
                    "net_income": 500000
                }
            ]
        )

        assert result["summary"]["subsidiaries_count"] == 1
        assert len(result["eliminations"]) >= 1
        assert "consolidated" in result

    def test_minority_interest(self):
        """少数股东权益"""
        result = consolidation(
            parent={"name": "母公司", "assets": 10000000, "liabilities": 4000000, "equity": 6000000},
            subsidiaries=[
                {
                    "name": "子公司",
                    "ownership": 0.6,  # 60%持股
                    "assets": 5000000,
                    "liabilities": 2000000,
                    "equity": 3000000,
                    "net_income": 1000000
                }
            ]
        )

        # 少数股东权益 = 3000000 * 40% = 1200000
        assert result["minority_interest"]["equity"] == 1200000
        # 少数股东损益 = 1000000 * 40% = 400000
        assert result["minority_interest"]["income"] == 400000

    def test_intercompany_sale(self):
        """内部销售抵消"""
        result = consolidation(
            parent={"name": "母公司", "assets": 10000000, "liabilities": 4000000, "equity": 6000000, "revenue": 5000000},
            subsidiaries=[
                {"name": "子公司", "ownership": 1.0, "assets": 5000000, "liabilities": 2000000, "equity": 3000000, "revenue": 3000000}
            ],
            intercompany=[
                {
                    "type": "sale",
                    "from": "母公司",
                    "to": "子公司",
                    "amount": 1000000,
                    "unrealized_profit": 200000
                }
            ]
        )

        # 应该有内部销售抵消分录
        sale_entries = [e for e in result["eliminations"] if e["type"] == "intercompany_sale"]
        assert len(sale_entries) == 1
        assert result["summary"]["intercompany_eliminated"] == 1000000
        assert result["summary"]["unrealized_profit_eliminated"] == 200000

    def test_intercompany_loan(self):
        """内部借款抵消"""
        result = consolidation(
            parent={"name": "母公司", "assets": 10000000, "liabilities": 4000000, "equity": 6000000},
            subsidiaries=[
                {"name": "子公司", "ownership": 1.0, "assets": 5000000, "liabilities": 2000000, "equity": 3000000}
            ],
            intercompany=[
                {
                    "type": "loan",
                    "from": "母公司",
                    "to": "子公司",
                    "amount": 500000,
                    "interest": 25000
                }
            ]
        )

        loan_entries = [e for e in result["eliminations"] if e["type"] == "intercompany_loan"]
        assert len(loan_entries) == 1

    def test_intercompany_dividend(self):
        """内部股利抵消"""
        result = consolidation(
            parent={"name": "母公司", "assets": 10000000, "liabilities": 4000000, "equity": 6000000},
            subsidiaries=[
                {"name": "子公司", "ownership": 0.8, "assets": 5000000, "liabilities": 2000000, "equity": 3000000}
            ],
            intercompany=[
                {
                    "type": "dividend",
                    "from": "母公司",
                    "to": "子公司",
                    "amount": 400000
                }
            ]
        )

        div_entries = [e for e in result["eliminations"] if e["type"] == "intercompany_dividend"]
        assert len(div_entries) == 1

    def test_goodwill_calculation(self):
        """商誉计算"""
        result = consolidation(
            parent={"name": "母公司", "assets": 10000000, "liabilities": 4000000, "equity": 6000000},
            subsidiaries=[
                {"name": "子公司", "ownership": 1.0, "assets": 5000000, "liabilities": 2000000, "equity": 3000000}
            ],
            investments=[
                {
                    "subsidiary": "子公司",
                    "investment_cost": 3500000,  # 投资成本高于权益份额
                    "goodwill": 500000
                }
            ]
        )

        assert result["goodwill"] == 500000
        assert result["consolidated"]["goodwill"] == 500000

    def test_multiple_subsidiaries(self):
        """多个子公司"""
        result = consolidation(
            parent={"name": "母公司", "assets": 20000000, "liabilities": 8000000, "equity": 12000000},
            subsidiaries=[
                {"name": "子公司A", "ownership": 0.8, "assets": 5000000, "liabilities": 2000000, "equity": 3000000, "net_income": 500000},
                {"name": "子公司B", "ownership": 0.6, "assets": 4000000, "liabilities": 1500000, "equity": 2500000, "net_income": 300000}
            ]
        )

        assert result["summary"]["subsidiaries_count"] == 2
        # 少数股东权益 = 3000000*20% + 2500000*40% = 600000 + 1000000 = 1600000
        assert result["minority_interest"]["equity"] == 1600000

    def test_ar_ap_elimination(self):
        """应收应付抵消"""
        result = consolidation(
            parent={"name": "母公司", "assets": 10000000, "liabilities": 4000000, "equity": 6000000},
            subsidiaries=[
                {"name": "子公司", "ownership": 1.0, "assets": 5000000, "liabilities": 2000000, "equity": 3000000}
            ],
            intercompany=[
                {
                    "type": "receivable_payable",
                    "from": "母公司",
                    "to": "子公司",
                    "amount": 300000
                }
            ]
        )

        ar_ap_entries = [e for e in result["eliminations"] if e["type"] == "intercompany_ar_ap"]
        assert len(ar_ap_entries) == 1


# ============================================================
# 边界情况测试
# ============================================================

class TestTrialBalanceEdgeCases:
    """试算平衡边界测试"""

    def test_zero_amounts(self):
        """零金额科目"""
        result = trial_balance([
            {"code": "1001", "name": "现金", "type": "asset", "debit": 0, "credit": 0}
        ])

        assert result["balanced"] is True
        assert result["total_debit"] == 0

    def test_large_amounts(self):
        """大金额"""
        result = trial_balance([
            {"code": "1001", "name": "资产", "type": "asset", "debit": 1e12, "credit": 0},
            {"code": "2001", "name": "负债", "type": "liability", "debit": 0, "credit": 1e12}
        ])

        assert result["balanced"] is True

    def test_none_values(self):
        """None值处理"""
        result = trial_balance([
            {"code": "1001", "name": "现金", "type": "asset", "debit": None, "credit": None}
        ])

        assert result["total_debit"] == 0
        assert result["total_credit"] == 0


class TestAdjustingEntriesEdgeCases:
    """调整分录边界测试"""

    def test_zero_amount(self):
        """零金额调整"""
        result = adjusting_entries([
            {"type": "accrual", "description": "测试", "amount": 0, "details": {}}
        ])

        assert result["entries"][0]["amount"] == 0

    def test_deferral_with_total_amount(self):
        """递延费用使用total_amount计算"""
        result = adjusting_entries([
            {
                "type": "deferral",
                "description": "预付房租摊销",
                "amount": 0,  # 不直接提供amount
                "details": {
                    "total_amount": 120000,
                    "total_periods": 12,
                    "current_period": 1
                }
            }
        ])

        # 应按 120000 / 12 = 10000 计算
        assert result["entries"][0]["amount"] == 10000

    def test_inventory_reversal(self):
        """存货跌价准备转回"""
        result = adjusting_entries([
            {
                "type": "inventory",
                "description": "存货跌价转回",
                "details": {
                    "book_value": 100000,
                    "market_value": 120000,  # 市价高于账面
                    "existing_provision": 30000
                }
            }
        ])

        entry = result["entries"][0]
        # 应提 = max(0, 100000 - 120000) = 0, 转回 = 0 - 30000 = -30000
        assert "转回" in entry.get("note", "")

    def test_custom_entry_type(self):
        """自定义分录类型"""
        result = adjusting_entries([
            {
                "type": "custom_adjustment",
                "description": "特殊调整",
                "amount": 50000,
                "details": {
                    "debit_account": "其他应收款",
                    "credit_account": "其他应付款"
                }
            }
        ])

        entry = result["entries"][0]
        assert entry["lines"][0]["account"] == "其他应收款"
        assert entry["lines"][1]["account"] == "其他应付款"

    def test_amortization_entry(self):
        """摊销分录"""
        result = adjusting_entries([
            {
                "type": "amortization",
                "description": "专利摊销",
                "details": {
                    "asset_name": "专利权",
                    "original_cost": 1200000,
                    "useful_life": 10
                }
            }
        ])

        entry = result["entries"][0]
        # 年摊销 = 1200000 / 10 = 120000, 月摊销 = 10000
        assert entry["amount"] == 10000

    def test_depreciation_declining(self):
        """双倍余额递减法折旧"""
        result = adjusting_entries([
            {
                "type": "depreciation",
                "description": "设备折旧",
                "details": {
                    "asset_name": "设备",
                    "original_cost": 100000,
                    "salvage_value": 0,
                    "useful_life": 5,
                    "method": "declining",
                    "net_book_value": 80000
                }
            }
        ])

        entry = result["entries"][0]
        # 年折旧率 = 2/5 = 40%, 年折旧 = 80000 * 40% = 32000, 月折旧 ≈ 2666.67
        assert entry["amount"] > 0


class TestAuditSamplingEdgeCases:
    """审计抽样边界测试"""

    def test_sample_size_exceeds_population(self):
        """样本量超过总体"""
        population = [{"id": str(i), "amount": 1000} for i in range(5)]

        result = audit_sampling(
            population=population,
            method="random",
            sample_size=10
        )

        assert result["sample_size"] <= 5

    def test_default_sample_size_calculation(self):
        """默认样本量计算（无tolerable_error）"""
        population = [{"id": str(i), "amount": 1000} for i in range(500)]

        result = audit_sampling(
            population=population,
            method="random",
            # 不指定sample_size和tolerable_error
            seed=42
        )

        # 默认10%，最少25个，最多100个
        # 500 * 10% = 50
        assert result["sample_size"] == 50

    def test_zero_amount_items(self):
        """零金额项目"""
        population = [
            {"id": "1", "amount": 0},
            {"id": "2", "amount": 0},
            {"id": "3", "amount": 1000}
        ]

        result = audit_sampling(
            population=population,
            method="mus",
            sample_size=2,
            seed=42
        )

        # MUS应该能处理零金额
        assert result["sample_size"] >= 1

    def test_single_item_population(self):
        """单项目总体"""
        result = audit_sampling(
            population=[{"id": "1", "amount": 1000}],
            method="random",
            sample_size=1
        )

        assert result["sample_size"] == 1
        assert result["coverage"] == 1.0


class TestConsolidationEdgeCases:
    """合并报表边界测试"""

    def test_wholly_owned_subsidiary(self):
        """全资子公司"""
        result = consolidation(
            parent={"name": "母公司", "assets": 10000000, "liabilities": 4000000, "equity": 6000000},
            subsidiaries=[
                {"name": "子公司", "ownership": 1.0, "assets": 5000000, "liabilities": 2000000, "equity": 3000000}
            ]
        )

        # 全资子公司无少数股东权益
        assert result["minority_interest"]["equity"] == 0

    def test_no_subsidiaries(self):
        """无子公司"""
        result = consolidation(
            parent={"name": "母公司", "assets": 10000000, "liabilities": 4000000, "equity": 6000000},
            subsidiaries=[]
        )

        assert result["summary"]["subsidiaries_count"] == 0
        assert result["consolidated"]["assets"] == 10000000

    def test_no_intercompany(self):
        """无内部交易"""
        result = consolidation(
            parent={"name": "母公司", "assets": 10000000, "liabilities": 4000000, "equity": 6000000},
            subsidiaries=[
                {"name": "子公司", "ownership": 0.8, "assets": 5000000, "liabilities": 2000000, "equity": 3000000}
            ],
            intercompany=[]
        )

        assert result["summary"]["intercompany_eliminated"] == 0

    def test_service_transaction(self):
        """内部服务交易"""
        result = consolidation(
            parent={"name": "母公司", "assets": 10000000, "liabilities": 4000000, "equity": 6000000, "revenue": 5000000},
            subsidiaries=[
                {"name": "子公司", "ownership": 1.0, "assets": 5000000, "liabilities": 2000000, "equity": 3000000}
            ],
            intercompany=[
                {"type": "service", "from": "母公司", "to": "子公司", "amount": 100000}
            ]
        )

        service_entries = [e for e in result["eliminations"] if e["type"] == "intercompany_service"]
        assert len(service_entries) == 1
