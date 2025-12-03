# -*- coding: utf-8 -*-
"""
performance_tools 测试用例
"""

import pytest
from fin_tools.tools.performance_tools import (
    kpi_dashboard,
    eva_calc,
    balanced_scorecard,
    okr_progress
)


class TestKpiDashboard:
    """KPI仪表盘测试"""

    def test_basic_kpis(self):
        """基本KPI计算"""
        result = kpi_dashboard([
            {"name": "收入", "target": 1000000, "actual": 1100000, "direction": "higher_better"},
            {"name": "成本率", "target": 0.6, "actual": 0.55, "direction": "lower_better"}
        ])

        assert result["summary"]["total_kpis"] == 2
        assert result["summary"]["overall_score"] > 100  # 都超额完成

    def test_exceeded_status(self):
        """超额完成状态"""
        result = kpi_dashboard([
            {"name": "销售", "target": 100, "actual": 120}
        ])

        assert result["kpis"][0]["status"] == "exceeded"
        assert result["summary"]["exceeded"] == 1
        assert len(result["highlights"]) > 0

    def test_on_target_status(self):
        """达标状态"""
        result = kpi_dashboard([
            {"name": "销售", "target": 100, "actual": 105}
        ])

        assert result["kpis"][0]["status"] == "on_target"

    def test_at_risk_status(self):
        """风险状态"""
        result = kpi_dashboard([
            {"name": "销售", "target": 100, "actual": 92}
        ])

        assert result["kpis"][0]["status"] == "at_risk"
        assert len(result["concerns"]) > 0

    def test_behind_status(self):
        """落后状态"""
        result = kpi_dashboard([
            {"name": "销售", "target": 100, "actual": 70}
        ])

        assert result["kpis"][0]["status"] == "behind"

    def test_lower_better_direction(self):
        """越低越好指标"""
        result = kpi_dashboard([
            {"name": "成本率", "target": 0.5, "actual": 0.4, "direction": "lower_better"}
        ])

        # 实际0.4 < 目标0.5，完成率 = 0.5/0.4 = 125%
        assert result["kpis"][0]["completion_rate"] > 1.0
        assert result["kpis"][0]["status"] == "exceeded"

    def test_weighted_score(self):
        """加权得分"""
        result = kpi_dashboard([
            {"name": "A", "target": 100, "actual": 100, "weight": 0.8},
            {"name": "B", "target": 100, "actual": 50, "weight": 0.2}
        ])

        # A得分100 * 0.8 + B得分50 * 0.2 = 80 + 10 = 90
        assert result["summary"]["weighted_score"] == pytest.approx(90, rel=0.01)

    def test_by_category(self):
        """按类别汇总"""
        result = kpi_dashboard([
            {"name": "收入", "target": 100, "actual": 100, "category": "财务"},
            {"name": "利润", "target": 50, "actual": 50, "category": "财务"},
            {"name": "满意度", "target": 90, "actual": 85, "category": "客户"}
        ])

        assert "财务" in result["by_category"]
        assert "客户" in result["by_category"]
        assert result["by_category"]["财务"]["count"] == 2

    def test_empty_kpis(self):
        """空KPI列表"""
        result = kpi_dashboard([])

        assert result["summary"]["total_kpis"] == 0
        assert result["summary"]["overall_score"] == 0

    def test_zero_target(self):
        """零目标"""
        result = kpi_dashboard([
            {"name": "测试", "target": 0, "actual": 100}
        ])

        assert "score" in result["kpis"][0]

    def test_period_parameter(self):
        """考核期间参数"""
        result = kpi_dashboard([], period="2024Q4")

        assert result["period"] == "2024Q4"


class TestEvaCalc:
    """EVA计算测试"""

    def test_basic_eva(self):
        """基本EVA计算"""
        result = eva_calc(
            nopat=5000000,
            invested_capital=30000000,
            wacc=0.10
        )

        # EVA = 5000000 - 30000000 * 0.10 = 5000000 - 3000000 = 2000000
        assert result["eva"] == 2000000
        assert result["capital_charge"] == 3000000
        assert result["value_created"] is True

    def test_negative_eva(self):
        """负EVA"""
        result = eva_calc(
            nopat=1000000,
            invested_capital=30000000,
            wacc=0.10
        )

        # EVA = 1000000 - 3000000 = -2000000
        assert result["eva"] == -2000000
        assert result["value_created"] is False

    def test_roic_calculation(self):
        """ROIC计算"""
        result = eva_calc(
            nopat=3000000,
            invested_capital=20000000,
            wacc=0.10
        )

        # ROIC = 3000000 / 20000000 = 15%
        assert result["roic"] == 0.15

    def test_eva_spread(self):
        """EVA利差"""
        result = eva_calc(
            nopat=3000000,
            invested_capital=20000000,
            wacc=0.10
        )

        # EVA利差 = ROIC - WACC = 15% - 10% = 5%
        assert result["eva_spread"] == 0.05

    def test_rd_adjustment(self):
        """研发费用调整"""
        result = eva_calc(
            nopat=5000000,
            invested_capital=30000000,
            wacc=0.10,
            adjustments={"rd_capitalized": 1000000}
        )

        # NOPAT调增1000000
        assert result["adjusted_nopat"] == 6000000
        # 投入资本调增 1000000 * 2.5 = 2500000
        assert result["adjusted_capital"] == 32500000

    def test_multiple_adjustments(self):
        """多项调整"""
        result = eva_calc(
            nopat=5000000,
            invested_capital=30000000,
            wacc=0.10,
            adjustments={
                "rd_capitalized": 500000,
                "goodwill_amortization": 200000,
                "operating_lease": 1000000
            }
        )

        assert result["adjusted_nopat"] > result["nopat"]
        assert result["adjusted_capital"] > result["invested_capital"]

    def test_zero_capital(self):
        """零投入资本"""
        result = eva_calc(
            nopat=1000000,
            invested_capital=0,
            wacc=0.10
        )

        # ROIC除零保护
        assert result["roic"] == 0

    def test_analysis_messages(self):
        """分析信息"""
        # 高价值创造
        result1 = eva_calc(nopat=2000000, invested_capital=10000000, wacc=0.10)
        assert "显著创造" in result1["analysis"]

        # 价值侵蚀
        result2 = eva_calc(nopat=500000, invested_capital=10000000, wacc=0.10)
        assert "侵蚀" in result2["analysis"]


class TestBalancedScorecard:
    """平衡计分卡测试"""

    def test_basic_bsc(self):
        """基本BSC"""
        result = balanced_scorecard({
            "财务": [{"name": "ROE", "target": 0.15, "actual": 0.18}],
            "客户": [{"name": "满意度", "target": 90, "actual": 85}]
        })

        assert "overall_score" in result
        assert "财务" in result["perspectives"]
        assert "客户" in result["perspectives"]

    def test_four_perspectives(self):
        """四个维度"""
        result = balanced_scorecard({
            "财务": [{"name": "利润", "target": 100, "actual": 100}],
            "客户": [{"name": "满意度", "target": 100, "actual": 100}],
            "内部流程": [{"name": "效率", "target": 100, "actual": 100}],
            "学习与成长": [{"name": "培训", "target": 100, "actual": 100}]
        })

        assert len(result["perspectives"]) == 4
        assert result["overall_score"] == 100

    def test_custom_weights(self):
        """自定义权重"""
        result = balanced_scorecard(
            perspectives={
                "财务": [{"name": "ROE", "target": 100, "actual": 100}],
                "客户": [{"name": "满意度", "target": 100, "actual": 50}]
            },
            weights={"财务": 0.8, "客户": 0.2}
        )

        # 财务100*0.8 + 客户50*0.2 = 80 + 10 = 90
        # 但还有内部流程和学习与成长两个维度是空的
        assert result["perspectives"]["财务"]["weighted_score"] == pytest.approx(80, rel=0.1)

    def test_strengths_weaknesses(self):
        """优势和劣势识别"""
        result = balanced_scorecard({
            "财务": [{"name": "ROE", "target": 100, "actual": 110}],  # 优秀
            "客户": [{"name": "满意度", "target": 100, "actual": 60}]   # 落后
        })

        assert "财务" in result["strengths"]
        assert "客户" in result["weaknesses"]

    def test_empty_perspectives(self):
        """空维度"""
        result = balanced_scorecard({})

        assert result["overall_score"] == 0

    def test_metric_weights(self):
        """指标权重"""
        result = balanced_scorecard({
            "财务": [
                {"name": "收入", "target": 100, "actual": 100, "weight": 0.7},
                {"name": "利润", "target": 100, "actual": 50, "weight": 0.3}
            ]
        })

        # 加权：100*0.7 + 50*0.3 = 70 + 15 = 85
        assert result["perspectives"]["财务"]["score"] == pytest.approx(85, rel=0.01)

    def test_recommendations(self):
        """建议生成"""
        result = balanced_scorecard({
            "财务": [{"name": "ROE", "target": 100, "actual": 60}]
        })

        assert len(result["recommendations"]) > 0

    def test_lower_better_metric(self):
        """越低越好指标"""
        result = balanced_scorecard({
            "财务": [
                {"name": "成本率", "target": 0.5, "actual": 0.4, "direction": "lower_better"}
            ]
        })

        assert result["perspectives"]["财务"]["metrics"][0]["completion"] > 1.0


class TestOkrProgress:
    """OKR进度追踪测试"""

    def test_basic_okr(self):
        """基本OKR"""
        result = okr_progress([
            {
                "objective": "提升收入",
                "key_results": [
                    {"kr": "新客户", "target": 100, "actual": 80},
                    {"kr": "客单价", "target": 500, "actual": 550}
                ]
            }
        ])

        assert result["summary"]["total_objectives"] == 1
        assert result["summary"]["total_krs"] == 2

    def test_on_track_status(self):
        """正常推进状态"""
        result = okr_progress([
            {
                "objective": "目标",
                "key_results": [
                    {"kr": "KR1", "target": 100, "actual": 95}
                ]
            }
        ])

        assert result["objectives"][0]["status"] == "on_track"

    def test_at_risk_status(self):
        """风险状态"""
        result = okr_progress([
            {
                "objective": "目标",
                "key_results": [
                    {"kr": "KR1", "target": 100, "actual": 75}
                ]
            }
        ])

        assert result["objectives"][0]["status"] == "at_risk"

    def test_behind_status(self):
        """落后状态"""
        result = okr_progress([
            {
                "objective": "目标",
                "key_results": [
                    {"kr": "KR1", "target": 100, "actual": 50}
                ]
            }
        ])

        assert result["objectives"][0]["status"] == "behind"

    def test_google_scoring(self):
        """Google风格评分"""
        result = okr_progress(
            objectives=[
                {
                    "objective": "目标",
                    "key_results": [
                        {"kr": "KR1", "target": 100, "actual": 70}
                    ]
                }
            ],
            scoring_method="google"
        )

        # 进度70%，Google评分 = 0.7 / 0.7 = 1.0 (满分)
        assert result["objectives"][0]["score"] == 1.0

    def test_by_owner(self):
        """按负责人汇总"""
        result = okr_progress([
            {"objective": "O1", "owner": "张三", "key_results": [{"kr": "KR", "target": 100, "actual": 100}]},
            {"objective": "O2", "owner": "张三", "key_results": [{"kr": "KR", "target": 100, "actual": 100}]},
            {"objective": "O3", "owner": "李四", "key_results": [{"kr": "KR", "target": 100, "actual": 100}]}
        ])

        assert "张三" in result["by_owner"]
        assert "李四" in result["by_owner"]
        assert result["by_owner"]["张三"]["count"] == 2

    def test_empty_objectives(self):
        """空目标列表"""
        result = okr_progress([])

        assert result["summary"]["total_objectives"] == 0
        assert result["summary"]["avg_progress"] == 0

    def test_progress_capping(self):
        """进度封顶"""
        result = okr_progress([
            {
                "objective": "目标",
                "key_results": [
                    {"kr": "KR1", "target": 100, "actual": 200}  # 超额
                ]
            }
        ])

        # 进度封顶100%
        assert result["objectives"][0]["key_results"][0]["progress"] == 1.0

    def test_recommendations(self):
        """建议生成"""
        result = okr_progress([
            {"objective": "O1", "key_results": [{"kr": "KR", "target": 100, "actual": 30}]}
        ])

        assert len(result["recommendations"]) > 0

    def test_lower_better_kr(self):
        """越低越好的KR"""
        result = okr_progress([
            {
                "objective": "降本增效",
                "key_results": [
                    {"kr": "成本下降", "target": 20, "actual": 15, "direction": "lower_better"}
                ]
            }
        ])

        # target/actual = 20/15 > 1
        assert result["objectives"][0]["key_results"][0]["progress"] > 1.0 or \
               result["objectives"][0]["key_results"][0]["progress"] == 1.0  # 封顶


# ============================================================
# 边界情况测试
# ============================================================

class TestKpiDashboardEdgeCases:
    """KPI仪表盘边界测试"""

    def test_zero_actual(self):
        """零实际值"""
        result = kpi_dashboard([
            {"name": "测试", "target": 100, "actual": 0}
        ])

        assert result["kpis"][0]["status"] == "behind"

    def test_both_zero(self):
        """目标和实际都为零"""
        result = kpi_dashboard([
            {"name": "测试", "target": 0, "actual": 0}
        ])

        assert result["kpis"][0]["completion_rate"] == 1.0

    def test_negative_values(self):
        """负值"""
        result = kpi_dashboard([
            {"name": "测试", "target": -100, "actual": -50, "direction": "higher_better"}
        ])

        # -50 > -100，应该是好的
        assert "score" in result["kpis"][0]

    def test_lower_better_zero_actual(self):
        """越低越好指标实际值为零"""
        result = kpi_dashboard([
            {"name": "缺陷率", "target": 5, "actual": 0, "direction": "lower_better"}
        ])

        # 实际为0是最好的，但要避免除零
        assert result["kpis"][0]["completion_rate"] == 2.0


class TestEvaCalcEdgeCases:
    """EVA计算边界测试"""

    def test_zero_wacc(self):
        """零WACC"""
        result = eva_calc(
            nopat=1000000,
            invested_capital=10000000,
            wacc=0
        )

        assert result["capital_charge"] == 0
        assert result["eva"] == 1000000

    def test_negative_nopat(self):
        """负NOPAT"""
        result = eva_calc(
            nopat=-1000000,
            invested_capital=10000000,
            wacc=0.10
        )

        assert result["eva"] < 0
        assert result["value_created"] is False

    def test_deferred_tax_adjustment(self):
        """递延税项调整"""
        result = eva_calc(
            nopat=5000000,
            invested_capital=30000000,
            wacc=0.10,
            adjustments={"deferred_tax": 200000}
        )

        assert result["adjusted_nopat"] == 5200000
        assert "deferred_tax" in result["adjustments"]

    def test_slight_value_creation(self):
        """轻微价值创造"""
        # ROIC略高于WACC，利差在0-5%之间
        result = eva_calc(
            nopat=1100000,  # ROIC = 11%
            invested_capital=10000000,
            wacc=0.10       # WACC = 10%
        )

        assert result["eva_spread"] > 0
        assert result["eva_spread"] < 0.05
        assert "创造" in result["analysis"] and "利差较小" in result["analysis"]

    def test_slight_value_erosion(self):
        """轻微价值侵蚀"""
        # ROIC略低于WACC，利差在-3%到0之间
        result = eva_calc(
            nopat=900000,   # ROIC = 9%
            invested_capital=10000000,
            wacc=0.10       # WACC = 10%
        )

        assert result["eva_spread"] < 0
        assert result["eva_spread"] > -0.03
        assert "轻微侵蚀" in result["analysis"]


class TestBalancedScorecardEdgeCases:
    """平衡计分卡边界测试"""

    def test_all_empty_metrics(self):
        """所有维度都无指标"""
        result = balanced_scorecard({
            "财务": [],
            "客户": []
        })

        assert result["overall_score"] == 0

    def test_zero_target(self):
        """零目标"""
        result = balanced_scorecard({
            "财务": [{"name": "测试", "target": 0, "actual": 100}]
        })

        assert "score" in result["perspectives"]["财务"]


class TestOkrProgressEdgeCases:
    """OKR进度边界测试"""

    def test_empty_key_results(self):
        """空KR列表"""
        result = okr_progress([
            {"objective": "目标", "key_results": []}
        ])

        assert result["objectives"][0]["progress"] == 0

    def test_zero_target_kr(self):
        """零目标KR"""
        result = okr_progress([
            {
                "objective": "目标",
                "key_results": [
                    {"kr": "KR", "target": 0, "actual": 100}
                ]
            }
        ])

        assert "progress" in result["objectives"][0]["key_results"][0]

    def test_all_behind(self):
        """全部落后"""
        result = okr_progress([
            {"objective": "O1", "key_results": [{"kr": "KR", "target": 100, "actual": 20}]},
            {"objective": "O2", "key_results": [{"kr": "KR", "target": 100, "actual": 30}]}
        ])

        assert result["summary"]["behind"] == 2
        assert "落后" in result["recommendations"][0]
