# -*- coding: utf-8 -*-
"""
DCF 原子工具测试
"""

import pytest
from financial_model.tools.dcf_tools import (
    calc_capm,
    calc_wacc,
    calc_fcff,
    calc_terminal_value,
    calc_enterprise_value,
    calc_equity_value,
    calc_per_share_value,
    dcf_sensitivity,
    dcf_quick_valuate,
)


class TestCalcCapm:
    """测试 calc_capm: CAPM计算股权成本"""

    def test_basic_capm(self):
        """基础CAPM计算"""
        result = calc_capm(0.03, 1.2, 0.06)
        assert round(result["value"], 3) == 0.102
        assert result["formula"] == "Rf + β × MRP"
        assert result["source"] == "tool"

    def test_high_beta(self):
        """高贝塔股票"""
        result = calc_capm(0.03, 2.0, 0.06)
        assert round(result["value"], 2) == 0.15

    def test_low_beta(self):
        """低贝塔股票"""
        result = calc_capm(0.03, 0.5, 0.06)
        assert round(result["value"], 2) == 0.06

    def test_zero_beta(self):
        """无系统性风险"""
        result = calc_capm(0.03, 0, 0.06)
        assert result["value"] == 0.03


class TestCalcWacc:
    """测试 calc_wacc: 加权平均资本成本"""

    def test_basic_wacc(self):
        """基础WACC计算"""
        result = calc_wacc(0.102, 0.05, 0.25, 0.30)
        assert round(result["value"], 4) == 0.0826
        assert result["formula"] == "E/(D+E) × Re + D/(D+E) × Rd × (1-t)"

    def test_all_equity(self):
        """全股权（无杠杆）"""
        result = calc_wacc(0.10, 0.05, 0.25, 0)
        assert result["value"] == 0.10

    def test_high_leverage(self):
        """高杠杆"""
        result = calc_wacc(0.12, 0.06, 0.25, 0.60)
        wacc = 0.40 * 0.12 + 0.60 * 0.06 * 0.75
        assert round(result["value"], 4) == round(wacc, 4)


class TestCalcFcff:
    """测试 calc_fcff: 企业自由现金流"""

    def test_basic_fcff(self):
        """基础FCFF计算"""
        result = calc_fcff(100_000_000, 0.25, 15_000_000, 20_000_000, 5_000_000)
        # FCFF = 100M × 0.75 + 15M - 20M - 5M = 75M + 15M - 20M - 5M = 65M
        assert result["value"] == 65_000_000
        assert result["inputs"]["nopat"] == 75_000_000

    def test_negative_fcff(self):
        """负FCFF（高投资期）"""
        result = calc_fcff(50_000_000, 0.25, 10_000_000, 80_000_000, 10_000_000)
        # FCFF = 50M × 0.75 + 10M - 80M - 10M = 37.5M + 10M - 80M - 10M = -42.5M
        assert result["value"] == -42_500_000

    def test_zero_tax(self):
        """零税率"""
        result = calc_fcff(100_000_000, 0, 10_000_000, 20_000_000, 5_000_000)
        assert result["value"] == 85_000_000


class TestCalcTerminalValue:
    """测试 calc_terminal_value: 终值计算"""

    def test_perpetual_growth(self):
        """永续增长法"""
        result = calc_terminal_value(
            "perpetual",
            final_fcf=80_000_000,
            wacc=0.09,
            terminal_growth=0.02
        )
        # TV = 80M × 1.02 / (0.09 - 0.02) = 81.6M / 0.07 ≈ 1165.71M
        expected = 80_000_000 * 1.02 / 0.07
        assert round(result["value"], 2) == round(expected, 2)

    def test_exit_multiple(self):
        """退出倍数法"""
        result = calc_terminal_value(
            "multiple",
            final_ebitda=120_000_000,
            exit_multiple=8.0
        )
        assert result["value"] == 960_000_000

    def test_invalid_growth(self):
        """增长率 >= WACC 应报错"""
        with pytest.raises(ValueError):
            calc_terminal_value(
                "perpetual",
                final_fcf=80_000_000,
                wacc=0.05,
                terminal_growth=0.06
            )

    def test_invalid_method(self):
        """无效方法应报错"""
        with pytest.raises(ValueError):
            calc_terminal_value("invalid")


class TestCalcEnterpriseValue:
    """测试 calc_enterprise_value: 企业价值"""

    def test_basic_ev(self):
        """基础企业价值计算"""
        fcf_list = [50_000_000, 55_000_000, 60_000_000, 65_000_000, 70_000_000]
        result = calc_enterprise_value(fcf_list, 0.09, 1_000_000_000)

        assert result["value"] > 0
        assert result["inputs"]["projection_years"] == 5
        assert len(result["inputs"]["fcf_details"]) == 5

    def test_single_year(self):
        """单年预测"""
        result = calc_enterprise_value([100_000_000], 0.10, 500_000_000)
        # PV of FCF = 100M / 1.1 = 90.91M
        # PV of TV = 500M / 1.1 = 454.55M
        pv_fcf = 100_000_000 / 1.1
        pv_tv = 500_000_000 / 1.1
        expected = pv_fcf + pv_tv
        # 使用较宽松的精度比较，避免浮点数精度问题
        assert abs(result["value"] - expected) < 1


class TestCalcEquityValue:
    """测试 calc_equity_value: 股权价值"""

    def test_basic_equity(self):
        """基础股权价值计算"""
        result = calc_equity_value(893_000_000, 200_000_000, 50_000_000)
        assert result["value"] == 743_000_000

    def test_with_minority(self):
        """包含少数股东权益"""
        result = calc_equity_value(1_000_000_000, 300_000_000, 100_000_000, 50_000_000)
        assert result["value"] == 750_000_000

    def test_negative_equity(self):
        """负股权价值（资不抵债）"""
        result = calc_equity_value(500_000_000, 600_000_000, 50_000_000)
        assert result["value"] == -50_000_000


class TestCalcPerShareValue:
    """测试 calc_per_share_value: 每股价值"""

    def test_basic_per_share(self):
        """基础每股价值计算"""
        result = calc_per_share_value(743_000_000, 100_000_000)
        assert result["value"] == 7.43

    def test_large_shares(self):
        """大量流通股"""
        result = calc_per_share_value(10_000_000_000, 2_000_000_000)
        assert result["value"] == 5.0

    def test_zero_shares(self):
        """零股数"""
        result = calc_per_share_value(1_000_000_000, 0)
        assert result["value"] == 0


class TestDcfSensitivity:
    """测试 dcf_sensitivity: 敏感性分析"""

    def test_basic_sensitivity(self):
        """基础敏感性分析"""
        fcf_list = [50_000_000, 55_000_000, 60_000_000, 65_000_000, 70_000_000]
        result = dcf_sensitivity(
            fcf_list,
            wacc_range=[0.08, 0.09, 0.10],
            growth_range=[0.01, 0.02, 0.03],
            debt=200_000_000,
            cash=50_000_000,
            shares=100_000_000
        )

        assert len(result["matrix"]) == 3  # 3个WACC值
        assert "wacc" in result["matrix"][0]
        assert result["headers"]["rows"] == "WACC"

    def test_invalid_growth(self):
        """增长率接近WACC时应返回N/A"""
        fcf_list = [50_000_000]
        result = dcf_sensitivity(
            fcf_list,
            wacc_range=[0.05],
            growth_range=[0.05, 0.06],
            debt=0,
            cash=0,
            shares=100_000_000
        )

        # 当 g >= wacc 时，应该返回 N/A
        assert result["matrix"][0]["g=5.0%"] == "N/A"
        assert result["matrix"][0]["g=6.0%"] == "N/A"


class TestDcfQuickValuate:
    """测试 dcf_quick_valuate: 快捷估值"""

    def test_with_wacc_provided(self):
        """直接提供WACC"""
        inputs = {
            "wacc": 0.09,
            "fcf_list": [50_000_000, 55_000_000, 60_000_000, 65_000_000, 70_000_000],
            "terminal_method": "perpetual",
            "terminal_growth": 0.02,
            "debt": 200_000_000,
            "cash": 50_000_000,
            "shares_outstanding": 100_000_000
        }
        result = dcf_quick_valuate(inputs)

        assert result["_meta"]["model_type"] == "dcf"
        assert result["_meta"]["built_with"] == "atomic_tools"
        assert result["per_share_value"]["value"] > 0
        assert "cost_of_equity" not in result  # 因为直接提供了WACC

    def test_with_wacc_inputs(self):
        """通过WACC输入计算"""
        inputs = {
            "wacc_inputs": {
                "risk_free_rate": 0.03,
                "beta": 1.2,
                "market_risk_premium": 0.06,
                "cost_of_debt": 0.05,
                "debt_ratio": 0.30,
                "tax_rate": 0.25
            },
            "fcf_list": [50_000_000, 55_000_000, 60_000_000],
            "terminal_method": "perpetual",
            "terminal_growth": 0.02,
            "debt": 100_000_000,
            "cash": 30_000_000,
            "shares_outstanding": 50_000_000
        }
        result = dcf_quick_valuate(inputs)

        assert "cost_of_equity" in result
        assert result["wacc"]["value"] > 0

    def test_exit_multiple_method(self):
        """退出倍数法"""
        inputs = {
            "wacc": 0.10,
            "fcf_list": [40_000_000, 45_000_000, 50_000_000],
            "terminal_method": "multiple",
            "final_ebitda": 80_000_000,
            "exit_multiple": 8.0,
            "debt": 150_000_000,
            "cash": 25_000_000,
            "shares_outstanding": 75_000_000
        }
        result = dcf_quick_valuate(inputs)

        assert result["terminal_value"]["inputs"]["method"] == "exit_multiple"
        assert result["terminal_value"]["value"] == 640_000_000

    def test_with_sensitivity(self):
        """包含敏感性分析"""
        inputs = {
            "wacc": 0.09,
            "fcf_list": [50_000_000, 55_000_000, 60_000_000],
            "terminal_method": "perpetual",
            "terminal_growth": 0.02,
            "debt": 100_000_000,
            "cash": 20_000_000,
            "shares_outstanding": 50_000_000,
            "sensitivity_config": {
                "wacc_range": [0.08, 0.09, 0.10],
                "growth_range": [0.01, 0.02, 0.03]
            }
        }
        result = dcf_quick_valuate(inputs)

        assert "sensitivity_matrix" in result
        assert len(result["sensitivity_matrix"]["matrix"]) == 3


class TestIntegration:
    """集成测试"""

    def test_full_dcf_workflow(self):
        """完整DCF工作流程"""
        # 1. 计算CAPM
        re = calc_capm(0.03, 1.1, 0.055)

        # 2. 计算WACC
        wacc = calc_wacc(re["value"], 0.045, 0.25, 0.25)

        # 3. 计算FCFF序列
        fcf_list = []
        ebit_base = 100_000_000
        for i in range(5):
            ebit = ebit_base * (1.05 ** i)
            fcff = calc_fcff(ebit, 0.25, 10_000_000, 15_000_000, 3_000_000)
            fcf_list.append(fcff["value"])

        # 4. 计算终值
        tv = calc_terminal_value("perpetual", final_fcf=fcf_list[-1], wacc=wacc["value"], terminal_growth=0.02)

        # 5. 计算企业价值
        ev = calc_enterprise_value(fcf_list, wacc["value"], tv["value"])

        # 6. 计算股权价值
        equity = calc_equity_value(ev["value"], 200_000_000, 50_000_000)

        # 7. 计算每股价值
        per_share = calc_per_share_value(equity["value"], 100_000_000)

        assert per_share["value"] > 0
        assert equity["value"] > 0
        assert ev["value"] > equity["value"]  # EV应大于股权价值（因为有净债务）

    def test_llm_override_scenario(self):
        """LLM覆盖场景：用户直接提供WACC"""
        # 模拟LLM跳过WACC计算，直接使用用户提供的值
        wacc_user_provided = {
            "value": 0.085,
            "formula": "user_provided",
            "inputs": {"note": "用户根据行业经验提供"},
            "source": "llm_override"
        }

        fcf_list = [60_000_000, 65_000_000, 70_000_000, 75_000_000, 80_000_000]
        tv = calc_terminal_value("perpetual", final_fcf=fcf_list[-1], wacc=wacc_user_provided["value"], terminal_growth=0.025)
        ev = calc_enterprise_value(fcf_list, wacc_user_provided["value"], tv["value"])

        assert ev["value"] > 0
        # 追溯信息应该保留用户提供的来源
        assert wacc_user_provided["source"] == "llm_override"
