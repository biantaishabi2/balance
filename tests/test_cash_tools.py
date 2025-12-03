# -*- coding: utf-8 -*-
"""
cash_tools 测试用例
"""

import pytest
from fin_tools.tools.cash_tools import (
    cash_forecast_13w,
    working_capital_cycle,
    cash_drivers
)


class TestCashForecast13w:
    """13周现金流预测测试"""

    def test_basic_forecast(self):
        """基本预测"""
        result = cash_forecast_13w(
            opening_cash=1000,
            receivables_schedule=[
                {"week": 1, "amount": 500},
                {"week": 3, "amount": 800}
            ],
            payables_schedule=[
                {"week": 2, "amount": 600}
            ]
        )

        assert len(result["weekly_forecast"]) == 13
        assert result["summary"]["opening_cash"] == 1000
        assert result["summary"]["total_inflows"] == 1300  # 500 + 800
        assert result["summary"]["total_outflows"] == 600

    def test_recurring_items(self):
        """固定收支项目"""
        result = cash_forecast_13w(
            opening_cash=1000,
            receivables_schedule=[],
            payables_schedule=[],
            recurring_inflows=[{"amount": 100, "description": "租金收入"}],
            recurring_outflows=[{"amount": 200, "description": "工资"}],
            weeks=4
        )

        # 每周净流出100，4周共400
        assert result["summary"]["total_inflows"] == 400  # 100 * 4
        assert result["summary"]["total_outflows"] == 800  # 200 * 4
        assert result["summary"]["ending_cash"] == 1000 - 400  # 1000 - 4*100

    def test_funding_gap_detection(self):
        """资金缺口检测"""
        result = cash_forecast_13w(
            opening_cash=500,
            receivables_schedule=[{"week": 5, "amount": 1000}],
            payables_schedule=[{"week": 2, "amount": 800}],
            weeks=6
        )

        # 第2周后余额为500-800=-300，有缺口
        assert result["has_funding_gap"] is True
        assert len(result["funding_gaps"]) > 0
        assert result["funding_gaps"][0]["week"] == 2

    def test_no_funding_gap(self):
        """无资金缺口"""
        result = cash_forecast_13w(
            opening_cash=2000,
            receivables_schedule=[{"week": 1, "amount": 500}],
            payables_schedule=[{"week": 2, "amount": 600}],
            weeks=4
        )

        assert result["has_funding_gap"] is False
        assert len(result["funding_gaps"]) == 0

    def test_min_balance_tracking(self):
        """最低余额追踪"""
        result = cash_forecast_13w(
            opening_cash=1000,
            receivables_schedule=[{"week": 4, "amount": 500}],
            payables_schedule=[
                {"week": 1, "amount": 300},
                {"week": 2, "amount": 400},
                {"week": 3, "amount": 200}
            ],
            weeks=5
        )

        # 追踪最低余额点
        assert "min_balance" in result
        assert result["min_balance"]["week"] == 3  # 1000-300-400-200=100
        assert result["min_balance"]["balance"] == 100

    def test_empty_schedules(self):
        """空收付款计划"""
        result = cash_forecast_13w(
            opening_cash=1000,
            receivables_schedule=[],
            payables_schedule=[],
            weeks=4
        )

        assert result["summary"]["total_inflows"] == 0
        assert result["summary"]["total_outflows"] == 0
        assert result["summary"]["ending_cash"] == 1000


class TestWorkingCapitalCycle:
    """营运资金周期测试"""

    def test_basic_calculation(self):
        """基本计算"""
        result = working_capital_cycle(
            accounts_receivable=1200,
            inventory=400,
            accounts_payable=900,
            revenue=13700,
            cogs=8900
        )

        assert "dso" in result
        assert "dio" in result
        assert "dpo" in result
        assert "ccc" in result

        # DSO = 1200 / (13700/365) ≈ 32天
        assert result["dso"] == pytest.approx(32, rel=0.1)

    def test_ccc_formula(self):
        """CCC计算公式验证"""
        result = working_capital_cycle(
            accounts_receivable=365,  # DSO = 1天 * (365/365)
            inventory=365,            # DIO = 1天 * (365/365)
            accounts_payable=365,     # DPO = 1天 * (365/365)
            revenue=365,
            cogs=365
        )

        # CCC = DSO + DIO - DPO = 365 + 365 - 365 = 365
        assert result["ccc"] == pytest.approx(365, rel=0.01)

    def test_negative_ccc(self):
        """负现金周期（预收款模式）"""
        result = working_capital_cycle(
            accounts_receivable=100,   # 低应收
            inventory=50,              # 低存货
            accounts_payable=500,      # 高应付
            revenue=3650,
            cogs=3650
        )

        # DPO > DSO + DIO，CCC为负
        assert result["ccc"] < 0
        assert "负现金周期" in result["interpretation"]

    def test_working_capital(self):
        """营运资金计算"""
        result = working_capital_cycle(
            accounts_receivable=1000,
            inventory=500,
            accounts_payable=800,
            revenue=10000,
            cogs=6000
        )

        # WC = AR + Inv - AP = 1000 + 500 - 800 = 700
        assert result["working_capital"] == 700

    def test_turnover_ratios(self):
        """周转率计算"""
        result = working_capital_cycle(
            accounts_receivable=1000,
            inventory=500,
            accounts_payable=600,
            revenue=10000,
            cogs=6000
        )

        # AR Turnover = 10000 / 1000 = 10
        assert result["analysis"]["ar_turnover"] == 10.0
        # Inv Turnover = 6000 / 500 = 12
        assert result["analysis"]["inventory_turnover"] == 12.0
        # AP Turnover = 6000 / 600 = 10
        assert result["analysis"]["ap_turnover"] == 10.0

    def test_zero_values(self):
        """零值处理"""
        result = working_capital_cycle(
            accounts_receivable=0,
            inventory=0,
            accounts_payable=0,
            revenue=10000,
            cogs=6000
        )

        assert result["dso"] == 0
        assert result["dio"] == 0
        assert result["dpo"] == 0
        assert result["ccc"] == 0


class TestCashDrivers:
    """现金流驱动因素测试"""

    def test_basic_changes(self):
        """基本变动计算"""
        result = cash_drivers(
            period1={
                "cash_flow_operating": 1000,
                "cash_flow_investing": -500,
                "cash_flow_financing": -200
            },
            period2={
                "cash_flow_operating": 1200,
                "cash_flow_investing": -800,
                "cash_flow_financing": -100
            }
        )

        assert result["changes"]["operating"] == 200   # 1200 - 1000
        assert result["changes"]["investing"] == -300  # -800 - (-500)
        assert result["changes"]["financing"] == 100   # -100 - (-200)
        assert result["changes"]["total"] == 0         # 200 - 300 + 100

    def test_impact_ranking(self):
        """影响因素排名"""
        result = cash_drivers(
            period1={
                "cash_flow_operating": 1000,
                "cash_flow_investing": -500,
                "cash_flow_financing": -200
            },
            period2={
                "cash_flow_operating": 1000,
                "cash_flow_investing": -1000,  # 大变动
                "cash_flow_financing": -200
            }
        )

        # 投资活动变动最大 (-500)
        assert result["impact_ranking"][0]["factor"] == "投资活动"
        assert result["impact_ranking"][0]["amount"] == -500

    def test_positive_total_change(self):
        """正向总变动"""
        result = cash_drivers(
            period1={
                "cash_flow_operating": 1000,
                "cash_flow_investing": -500,
                "cash_flow_financing": -200
            },
            period2={
                "cash_flow_operating": 1500,
                "cash_flow_investing": -500,
                "cash_flow_financing": -200
            }
        )

        assert result["changes"]["total"] == 500
        assert "改善" in result["analysis"]

    def test_negative_total_change(self):
        """负向总变动"""
        result = cash_drivers(
            period1={
                "cash_flow_operating": 1500,
                "cash_flow_investing": -500,
                "cash_flow_financing": -200
            },
            period2={
                "cash_flow_operating": 1000,
                "cash_flow_investing": -500,
                "cash_flow_financing": -200
            }
        )

        assert result["changes"]["total"] == -500
        assert "恶化" in result["analysis"]

    def test_detailed_drivers(self):
        """详细驱动因素"""
        result = cash_drivers(
            period1={
                "cash_flow_operating": 1000,
                "cash_flow_investing": -500,
                "cash_flow_financing": -200,
                "net_income": 800,
                "depreciation": 200
            },
            period2={
                "cash_flow_operating": 1200,
                "cash_flow_investing": -600,
                "cash_flow_financing": -100,
                "net_income": 900,
                "depreciation": 250
            }
        )

        assert "detailed_drivers" in result
        assert len(result["detailed_drivers"]) == 3  # 三大活动

    def test_stable_cash_flow(self):
        """现金流稳定"""
        result = cash_drivers(
            period1={
                "cash_flow_operating": 1000,
                "cash_flow_investing": -500,
                "cash_flow_financing": -200
            },
            period2={
                "cash_flow_operating": 1000,
                "cash_flow_investing": -500,
                "cash_flow_financing": -200
            }
        )

        assert result["changes"]["total"] == 0
        assert "稳定" in result["analysis"]
