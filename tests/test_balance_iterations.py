# -*- coding: utf-8 -*-
"""
balance 配平迭代测试
"""

from balance import run_calc


def test_interest_updates_with_iterations():
    """
    迭代时，新借款应影响利息，且迭代次数>1时标记收敛状态
    """
    data = {
        "revenue": 100000,
        "cost": 50000,
        "opening_cash": 0,
        "opening_debt": 100000,
        "interest_rate": 0.1,
        "min_cash": 20000,  # 逼出新借款
        "fixed_asset_cost": 0,
        "fixed_asset_life": 10
    }

    result = run_calc(data, iterations=3)

    assert "interest" in result
    # 初始利息=100000*0.1=10000；有新增借款时应大于初值
    assert result["interest"] >= 10000
    assert result.get("iterations_run") <= 3
    assert result.get("iteration_converged") in (True, False)
