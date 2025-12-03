# -*- coding: utf-8 -*-
"""
budget_tools 测试用例
"""

import pytest
from fin_tools.tools.budget_tools import (
    variance_analysis,
    flex_budget,
    rolling_forecast,
    trend_analysis
)


class TestVarianceAnalysis:
    """预算差异分析测试"""

    def test_basic_variance(self):
        """基本差异计算"""
        result = variance_analysis(
            budget={"收入": 1000, "成本": 600},
            actual={"收入": 1100, "成本": 650}
        )

        assert "variances" in result
        assert len(result["variances"]) == 2

        # 收入：实际>预算，有利
        revenue = next(v for v in result["variances"] if v["account"] == "收入")
        assert revenue["variance"] == 100
        assert revenue["is_favorable"] is True

        # 成本：实际>预算，不利
        cost = next(v for v in result["variances"] if v["account"] == "成本")
        assert cost["variance"] == 50
        assert cost["is_favorable"] is False

    def test_significant_threshold(self):
        """重大差异阈值测试"""
        result = variance_analysis(
            budget={"收入": 1000, "成本": 600},
            actual={"收入": 1150, "成本": 620},
            threshold=0.10
        )

        # 收入差异15%，超过阈值
        revenue = next(v for v in result["variances"] if v["account"] == "收入")
        assert revenue["is_significant"] is True

        # 成本差异3.3%，未超过阈值
        cost = next(v for v in result["variances"] if v["account"] == "成本")
        assert cost["is_significant"] is False

        # 重大差异项只有1个
        assert len(result["significant_items"]) == 1

    def test_no_variance(self):
        """无差异情况"""
        result = variance_analysis(
            budget={"收入": 1000, "成本": 600},
            actual={"收入": 1000, "成本": 600}
        )

        assert result["summary"]["total_variance"] == 0
        assert result["summary"]["total_variance_pct"] == 0

    def test_missing_accounts(self):
        """科目缺失处理"""
        result = variance_analysis(
            budget={"收入": 1000, "成本": 600, "费用": 200},
            actual={"收入": 1100, "成本": 650}  # 缺少费用
        )

        # 应包含3个科目
        assert len(result["variances"]) == 3

        # 费用：预算200，实际0
        expense = next(v for v in result["variances"] if v["account"] == "费用")
        assert expense["budget"] == 200
        assert expense["actual"] == 0
        assert expense["variance"] == -200

    def test_summary_calculation(self):
        """汇总计算"""
        result = variance_analysis(
            budget={"收入": 1000, "成本": 600, "费用": 200},
            actual={"收入": 1100, "成本": 650, "费用": 180}
        )

        summary = result["summary"]
        assert summary["total_budget"] == 1800
        assert summary["total_actual"] == 1930
        assert summary["total_variance"] == 130


class TestFlexBudget:
    """弹性预算测试"""

    def test_variable_cost(self):
        """完全变动成本"""
        result = flex_budget(
            original_budget={"材料": 100},
            budget_volume=1000,
            actual_volume=1200,
            cost_behavior={"材料": "variable"}
        )

        # 业务量增加20%，变动成本也增加20%
        assert result["volume_ratio"] == 1.2
        assert result["flexed_budget"]["材料"] == 120

    def test_fixed_cost(self):
        """完全固定成本"""
        result = flex_budget(
            original_budget={"折旧": 50},
            budget_volume=1000,
            actual_volume=1200,
            cost_behavior={"折旧": "fixed"}
        )

        # 固定成本不变
        assert result["flexed_budget"]["折旧"] == 50

    def test_mixed_cost(self):
        """混合成本"""
        result = flex_budget(
            original_budget={"人工": 100},
            budget_volume=1000,
            actual_volume=1200,
            cost_behavior={"人工": "mixed:0.6"}  # 60%变动
        )

        # 固定部分: 100 * 0.4 = 40
        # 变动部分: 100 * 0.6 * 1.2 = 72
        # 合计: 112
        assert result["flexed_budget"]["人工"] == pytest.approx(112)

    def test_volume_decrease(self):
        """业务量减少"""
        result = flex_budget(
            original_budget={"材料": 100, "折旧": 50},
            budget_volume=1000,
            actual_volume=800,
            cost_behavior={"材料": "variable", "折旧": "fixed"}
        )

        assert result["volume_ratio"] == 0.8
        assert result["flexed_budget"]["材料"] == 80
        assert result["flexed_budget"]["折旧"] == 50

    def test_variance_decomposition(self):
        """差异分解"""
        result = flex_budget(
            original_budget={"材料": 100},
            budget_volume=1000,
            actual_volume=1200,
            cost_behavior={"材料": "variable"},
            actual={"材料": 130}  # 实际发生130
        )

        # 业务量差异 = 弹性预算 - 原预算 = 120 - 100 = 20
        # 效率差异 = 实际 - 弹性预算 = 130 - 120 = 10
        assert result["variances"]["volume_variance"] == 20
        assert result["variances"]["efficiency_variance"] == 10
        assert result["variances"]["total_variance"] == 30


class TestRollingForecast:
    """滚动预测测试"""

    def test_moving_average(self):
        """移动平均预测"""
        result = rolling_forecast(
            historical_data=[
                {"period": "2024-01", "revenue": 100},
                {"period": "2024-02", "revenue": 110},
                {"period": "2024-03", "revenue": 120}
            ],
            periods=2,
            method="moving_avg",
            window=3
        )

        assert len(result["forecast"]) == 2
        # 第一期预测：(100+110+120)/3 = 110
        assert result["forecast"][0]["revenue"] == pytest.approx(110)

    def test_linear_forecast(self):
        """线性回归预测"""
        result = rolling_forecast(
            historical_data=[
                {"period": "2024-01", "revenue": 100},
                {"period": "2024-02", "revenue": 110},
                {"period": "2024-03", "revenue": 120}
            ],
            periods=2,
            method="linear"
        )

        # 线性趋势，每期增加10
        assert result["forecast"][0]["revenue"] == pytest.approx(130)
        assert result["forecast"][1]["revenue"] == pytest.approx(140)

    def test_growth_rate_forecast(self):
        """增长率预测"""
        result = rolling_forecast(
            historical_data=[
                {"period": "2024-01", "revenue": 100},
                {"period": "2024-02", "revenue": 110},
                {"period": "2024-03", "revenue": 121}
            ],
            periods=1,
            method="growth_rate"
        )

        # 平均增长率约10%
        assert result["forecast"][0]["revenue"] == pytest.approx(133.1, rel=0.01)

    def test_trend_direction(self):
        """趋势方向判断"""
        # 上升趋势
        result_up = rolling_forecast(
            historical_data=[
                {"period": "1", "value": 100},
                {"period": "2", "value": 110},
                {"period": "3", "value": 120}
            ],
            periods=1
        )
        assert result_up["trend"]["value"]["direction"] == "up"

        # 下降趋势
        result_down = rolling_forecast(
            historical_data=[
                {"period": "1", "value": 120},
                {"period": "2", "value": 110},
                {"period": "3", "value": 100}
            ],
            periods=1
        )
        assert result_down["trend"]["value"]["direction"] == "down"

    def test_insufficient_data(self):
        """数据不足"""
        result = rolling_forecast(
            historical_data=[{"period": "1", "value": 100}],
            periods=1
        )
        assert "error" in result

    def test_empty_data(self):
        """空数据"""
        result = rolling_forecast(historical_data=[], periods=1)
        assert "error" in result


class TestTrendAnalysis:
    """趋势分析测试"""

    def test_basic_trend(self):
        """基本趋势分析"""
        result = trend_analysis([
            {"period": "2022", "revenue": 1000},
            {"period": "2023", "revenue": 1100},
            {"period": "2024", "revenue": 1200}
        ])

        assert "analysis" in result
        assert "revenue" in result["analysis"]

        revenue = result["analysis"]["revenue"]
        assert revenue["values"] == [1000, 1100, 1200]
        assert revenue["trend"] == "up"

    def test_yoy_growth(self):
        """同比增长计算"""
        result = trend_analysis([
            {"period": "2022", "revenue": 1000},
            {"period": "2023", "revenue": 1100},
            {"period": "2024", "revenue": 1210}
        ])

        revenue = result["analysis"]["revenue"]
        # 第一期无同比
        assert revenue["yoy_growth"][0] is None
        # 2023同比增长10%
        assert revenue["yoy_growth"][1] == pytest.approx(0.10)
        # 2024同比增长10%
        assert revenue["yoy_growth"][2] == pytest.approx(0.10)

    def test_indexed_values(self):
        """指数计算"""
        result = trend_analysis([
            {"period": "2022", "revenue": 1000},
            {"period": "2023", "revenue": 1100},
            {"period": "2024", "revenue": 1200}
        ])

        revenue = result["analysis"]["revenue"]
        assert revenue["indexed"][0] == pytest.approx(100)
        assert revenue["indexed"][1] == pytest.approx(110)
        assert revenue["indexed"][2] == pytest.approx(120)

    def test_cagr_calculation(self):
        """复合增长率计算"""
        result = trend_analysis([
            {"period": "2022", "revenue": 1000},
            {"period": "2023", "revenue": 1100},
            {"period": "2024", "revenue": 1210}
        ])

        revenue = result["analysis"]["revenue"]
        # CAGR = (1210/1000)^(1/2) - 1 ≈ 10%
        assert revenue["cagr"] == pytest.approx(0.10, rel=0.01)

    def test_custom_base_period(self):
        """自定义基期"""
        result = trend_analysis(
            periods_data=[
                {"period": "2022", "revenue": 1000},
                {"period": "2023", "revenue": 1100},
                {"period": "2024", "revenue": 1200}
            ],
            base_period=1  # 以2023为基期
        )

        assert result["base_period"] == "2023"
        revenue = result["analysis"]["revenue"]
        # 以1100为基期，指数应为 [90.9, 100, 109.1]
        assert revenue["indexed"][1] == pytest.approx(100)

    def test_multiple_metrics(self):
        """多指标分析"""
        result = trend_analysis([
            {"period": "2022", "revenue": 1000, "profit": 100},
            {"period": "2023", "revenue": 1100, "profit": 120},
            {"period": "2024", "revenue": 1200, "profit": 150}
        ])

        assert "revenue" in result["analysis"]
        assert "profit" in result["analysis"]
        assert result["metrics_analyzed"] == ["revenue", "profit"]

    def test_declining_trend(self):
        """下降趋势"""
        result = trend_analysis([
            {"period": "2022", "value": 1000},
            {"period": "2023", "value": 900},
            {"period": "2024", "value": 800}
        ])

        assert result["analysis"]["value"]["trend"] == "down"

    def test_stable_trend(self):
        """稳定趋势"""
        result = trend_analysis([
            {"period": "2022", "value": 1000},
            {"period": "2023", "value": 1010},
            {"period": "2024", "value": 1005}
        ])

        assert result["analysis"]["value"]["trend"] == "stable"

    def test_insufficient_data(self):
        """数据不足"""
        result = trend_analysis([{"period": "2024", "revenue": 1000}])
        assert "error" in result
