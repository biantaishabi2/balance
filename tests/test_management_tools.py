# -*- coding: utf-8 -*-
"""
management_tools 测试用例
"""

import pytest
from fin_tools.tools.management_tools import (
    dept_pnl,
    product_profitability,
    cost_allocation,
    cvp_analysis,
    breakeven
)


class TestDeptPnl:
    """部门损益表测试"""

    def test_zero_revenue_dept(self):
        """零收入部门"""
        result = dept_pnl(
            revenues=[{"dept": "销售部", "amount": 1000000}],
            direct_costs=[
                {"dept": "销售部", "amount": 300000},
                {"dept": "研发部", "amount": 500000}  # 只有成本没有收入
            ]
        )

        assert result["by_department"]["研发部"]["revenue"] == 0
        assert result["by_department"]["研发部"]["contribution_margin"] == -500000
        assert result["by_department"]["研发部"]["margin_rate"] == 0  # 零收入时利润率为0

    def test_negative_contribution(self):
        """负贡献毛利"""
        result = dept_pnl(
            revenues=[{"dept": "A", "amount": 100000}],
            direct_costs=[{"dept": "A", "amount": 150000}]  # 成本超过收入
        )

        assert result["by_department"]["A"]["contribution_margin"] == -50000
        assert result["by_department"]["A"]["operating_profit"] == -50000

    def test_basic_pnl(self):
        """基本损益计算"""
        result = dept_pnl(
            revenues=[
                {"dept": "销售部", "amount": 1000000},
                {"dept": "技术部", "amount": 500000}
            ],
            direct_costs=[
                {"dept": "销售部", "amount": 300000},
                {"dept": "技术部", "amount": 200000}
            ]
        )

        assert result["by_department"]["销售部"]["revenue"] == 1000000
        assert result["by_department"]["销售部"]["direct_costs"] == 300000
        assert result["by_department"]["销售部"]["contribution_margin"] == 700000
        assert result["by_department"]["技术部"]["contribution_margin"] == 300000

    def test_with_allocated_costs(self):
        """含分摊成本"""
        result = dept_pnl(
            revenues=[{"dept": "销售部", "amount": 1000000}],
            direct_costs=[{"dept": "销售部", "amount": 300000}],
            allocated_costs=[{"dept": "销售部", "amount": 100000, "category": "管理费分摊"}]
        )

        assert result["by_department"]["销售部"]["allocated_costs"] == 100000
        assert result["by_department"]["销售部"]["operating_profit"] == 600000

    def test_margin_rate(self):
        """利润率计算"""
        result = dept_pnl(
            revenues=[{"dept": "A", "amount": 1000000}],
            direct_costs=[{"dept": "A", "amount": 400000}]
        )

        assert result["by_department"]["A"]["contribution_margin_rate"] == pytest.approx(0.6)
        assert result["by_department"]["A"]["margin_rate"] == pytest.approx(0.6)

    def test_ranking(self):
        """排名功能"""
        result = dept_pnl(
            revenues=[
                {"dept": "A", "amount": 100000},
                {"dept": "B", "amount": 500000},
                {"dept": "C", "amount": 300000}
            ],
            direct_costs=[
                {"dept": "A", "amount": 20000},
                {"dept": "B", "amount": 100000},
                {"dept": "C", "amount": 50000}
            ]
        )

        # B部门贡献毛利最高(400000)，其次C(250000)，最后A(80000)
        assert result["ranking"] == ["B", "C", "A"]

    def test_summary(self):
        """汇总计算"""
        result = dept_pnl(
            revenues=[
                {"dept": "A", "amount": 100000},
                {"dept": "B", "amount": 200000}
            ],
            direct_costs=[
                {"dept": "A", "amount": 30000},
                {"dept": "B", "amount": 50000}
            ]
        )

        assert result["summary"]["total_revenue"] == 300000
        assert result["summary"]["total_direct_costs"] == 80000
        assert result["summary"]["total_contribution"] == 220000


class TestProductProfitability:
    """产品盈利分析测试"""

    def test_basic_analysis(self):
        """基本分析"""
        result = product_profitability([
            {"name": "产品A", "revenue": 1000000, "variable_costs": 400000},
            {"name": "产品B", "revenue": 500000, "variable_costs": 300000}
        ])

        # 按贡献毛利排序
        assert result["products"][0]["name"] == "产品A"
        assert result["products"][0]["contribution_margin"] == 600000
        assert result["products"][0]["cm_ratio"] == pytest.approx(0.6)

    def test_with_fixed_costs(self):
        """含固定成本"""
        result = product_profitability([
            {"name": "A", "revenue": 100000, "variable_costs": 40000, "fixed_costs": 30000}
        ])

        assert result["products"][0]["net_profit"] == 30000
        assert result["products"][0]["profit_margin"] == pytest.approx(0.3)

    def test_unit_calculation(self):
        """单位计算"""
        result = product_profitability([
            {"name": "A", "revenue": 100000, "variable_costs": 60000, "units_sold": 1000}
        ])

        assert result["products"][0]["unit_price"] == 100
        assert result["products"][0]["unit_variable_cost"] == 60
        assert result["products"][0]["unit_cm"] == 40

    def test_abc_classification(self):
        """ABC分类"""
        result = product_profitability([
            {"name": "A", "revenue": 1000000, "variable_costs": 400000},  # 贡献60万
            {"name": "B", "revenue": 500000, "variable_costs": 200000},   # 贡献30万
            {"name": "C", "revenue": 200000, "variable_costs": 100000},   # 贡献10万
            {"name": "D", "revenue": 50000, "variable_costs": 30000}      # 贡献2万
        ])

        # 总贡献102万，A占59%在A类，A+B占88%在B类范围
        assert "A" in result["abc_analysis"]["A"]
        assert "abc_class" in result["products"][0]

    def test_loss_product(self):
        """亏损产品"""
        result = product_profitability([
            {"name": "盈利", "revenue": 100000, "variable_costs": 40000, "fixed_costs": 20000},
            {"name": "亏损", "revenue": 100000, "variable_costs": 80000, "fixed_costs": 30000}
        ])

        assert result["summary"]["profitable_count"] == 1
        assert result["summary"]["loss_count"] == 1

    def test_disable_abc(self):
        """禁用ABC分类"""
        result = product_profitability(
            [{"name": "A", "revenue": 100000, "variable_costs": 40000}],
            include_abc=False
        )

        assert "abc_analysis" not in result
        assert "abc_class" not in result["products"][0]

    def test_empty_products(self):
        """空产品列表"""
        result = product_profitability([])

        assert result["products"] == []
        assert result["summary"]["total_revenue"] == 0
        assert result["summary"]["profitable_count"] == 0

    def test_negative_contribution_abc(self):
        """负贡献毛利产品的ABC分类"""
        result = product_profitability([
            {"name": "盈利A", "revenue": 100000, "variable_costs": 30000},
            {"name": "亏损B", "revenue": 50000, "variable_costs": 80000}  # 负贡献
        ])

        # 负贡献产品应归入C类
        assert "亏损B" in result["abc_analysis"]["C"]

    def test_zero_revenue_product(self):
        """零收入产品"""
        result = product_profitability([
            {"name": "A", "revenue": 0, "variable_costs": 1000}
        ])

        assert result["products"][0]["cm_ratio"] == 0
        assert result["products"][0]["profit_margin"] == 0


class TestCostAllocation:
    """成本分摊测试"""

    def test_direct_allocation(self):
        """直接分摊法"""
        result = cost_allocation(
            total_cost=100000,
            cost_objects=[
                {"name": "产品A", "base": 60},
                {"name": "产品B", "base": 40}
            ],
            method="direct"
        )

        assert result["method"] == "direct"
        assert result["allocations"][0]["allocated_cost"] == pytest.approx(60000)
        assert result["allocations"][1]["allocated_cost"] == pytest.approx(40000)
        assert result["total_allocated"] == pytest.approx(100000)

    def test_direct_equal_base(self):
        """等额分摊基础"""
        result = cost_allocation(
            total_cost=90000,
            cost_objects=[
                {"name": "A", "base": 100},
                {"name": "B", "base": 100},
                {"name": "C", "base": 100}
            ],
            method="direct"
        )

        for alloc in result["allocations"]:
            assert alloc["allocated_cost"] == pytest.approx(30000)
            assert alloc["percentage"] == pytest.approx(1/3)

    def test_step_allocation(self):
        """阶梯分摊法"""
        result = cost_allocation(
            total_cost=100000,
            cost_objects=[
                {"name": "IT部", "base": 50, "provides_to": ["生产部", "销售部"]},
                {"name": "生产部", "base": 60},
                {"name": "销售部", "base": 40}
            ],
            method="step"
        )

        assert result["method"] == "step"
        # 生产部门应该获得分摊
        assert any(a["name"] == "生产部" for a in result["allocations"])

    def test_abc_allocation(self):
        """作业成本法"""
        result = cost_allocation(
            total_cost=100000,
            cost_objects=[
                {"name": "产品A", "activities": {"机器小时": 100, "订单数": 5}},
                {"name": "产品B", "activities": {"机器小时": 50, "订单数": 10}}
            ],
            method="abc",
            drivers={"机器小时": 100, "订单数": 500}
        )

        assert result["method"] == "abc"
        # 产品A: 100*100 + 5*500 = 12500
        # 产品B: 50*100 + 10*500 = 10000
        assert result["allocations"][0]["allocated_cost"] == pytest.approx(12500)
        assert result["allocations"][1]["allocated_cost"] == pytest.approx(10000)

    def test_abc_driver_breakdown(self):
        """ABC动因明细"""
        result = cost_allocation(
            total_cost=50000,
            cost_objects=[
                {"name": "A", "activities": {"机器小时": 100}}
            ],
            method="abc",
            drivers={"机器小时": 200}
        )

        assert result["allocations"][0]["driver_breakdown"][0]["driver"] == "机器小时"
        assert result["allocations"][0]["driver_breakdown"][0]["cost"] == 20000

    def test_zero_base_direct(self):
        """零分摊基础-平均分摊"""
        result = cost_allocation(
            total_cost=90000,
            cost_objects=[
                {"name": "A", "base": 0},
                {"name": "B", "base": 0},
                {"name": "C", "base": 0}
            ],
            method="direct"
        )

        # 零基础时应平均分摊
        for alloc in result["allocations"]:
            assert alloc["allocated_cost"] == pytest.approx(30000)

    def test_invalid_method(self):
        """无效分摊方法"""
        with pytest.raises(ValueError, match="不支持的分摊方法"):
            cost_allocation(
                total_cost=100000,
                cost_objects=[{"name": "A", "base": 100}],
                method="invalid"
            )

    def test_multi_service_step(self):
        """多服务部门阶梯分摊"""
        result = cost_allocation(
            total_cost=120000,
            cost_objects=[
                {"name": "IT部", "base": 40, "provides_to": ["HR部", "生产部"]},
                {"name": "HR部", "base": 30, "provides_to": ["生产部"]},
                {"name": "生产部", "base": 100}
            ],
            method="step"
        )

        assert result["method"] == "step"
        # 生产部门应该收到所有分摊
        prod_alloc = next(a for a in result["allocations"] if a["name"] == "生产部")
        assert prod_alloc["allocated_cost"] > 0

    def test_abc_missing_driver(self):
        """ABC缺失动因费率"""
        result = cost_allocation(
            total_cost=100000,
            cost_objects=[
                {"name": "A", "activities": {"机器小时": 100, "不存在的动因": 50}}
            ],
            method="abc",
            drivers={"机器小时": 100}  # 缺少"不存在的动因"
        )

        # 缺失动因按0费率处理
        assert result["allocations"][0]["allocated_cost"] == 10000  # 只有机器小时


class TestCvpAnalysis:
    """本量利分析测试"""

    def test_basic_cvp(self):
        """基本CVP计算"""
        result = cvp_analysis(
            selling_price=100,
            variable_cost=60,
            fixed_costs=200000
        )

        assert result["unit_contribution_margin"] == 40
        assert result["cm_ratio"] == pytest.approx(0.4)
        assert result["breakeven_units"] == pytest.approx(5000)
        assert result["breakeven_sales"] == pytest.approx(500000)

    def test_current_volume(self):
        """当前销量分析"""
        result = cvp_analysis(
            selling_price=100,
            variable_cost=60,
            fixed_costs=200000,
            current_volume=10000
        )

        assert result["current_analysis"]["revenue"] == 1000000
        assert result["current_analysis"]["contribution_margin"] == 400000
        assert result["current_analysis"]["operating_profit"] == 200000
        assert result["current_analysis"]["margin_of_safety"] == pytest.approx(5000)
        assert result["current_analysis"]["margin_of_safety_rate"] == pytest.approx(0.5)

    def test_operating_leverage(self):
        """经营杠杆"""
        result = cvp_analysis(
            selling_price=100,
            variable_cost=60,
            fixed_costs=200000,
            current_volume=10000
        )

        # 杠杆 = 贡献毛利 / 营业利润 = 400000 / 200000 = 2
        assert result["current_analysis"]["operating_leverage"] == pytest.approx(2)

    def test_target_profit(self):
        """目标利润"""
        result = cvp_analysis(
            selling_price=100,
            variable_cost=60,
            fixed_costs=200000,
            target_profit=100000
        )

        # 需要销量 = (200000 + 100000) / 40 = 7500
        assert result["target_analysis"]["required_volume"] == pytest.approx(7500)
        assert result["target_analysis"]["required_sales"] == pytest.approx(750000)

    def test_target_profit_with_tax(self):
        """含税目标利润"""
        result = cvp_analysis(
            selling_price=100,
            variable_cost=60,
            fixed_costs=200000,
            target_profit=80000,
            tax_rate=0.2
        )

        # 税前利润 = 80000 / 0.8 = 100000
        assert result["target_analysis"]["pre_tax_profit_needed"] == pytest.approx(100000)

    def test_sensitivity(self):
        """敏感性分析"""
        result = cvp_analysis(
            selling_price=100,
            variable_cost=60,
            fixed_costs=200000,
            current_volume=10000
        )

        assert "sensitivity" in result
        assert "price_increase_1pct" in result["sensitivity"]
        assert "volume_increase_1pct" in result["sensitivity"]

    def test_negative_margin(self):
        """负毛利（售价低于变动成本）"""
        result = cvp_analysis(
            selling_price=50,
            variable_cost=80,  # 成本高于售价
            fixed_costs=100000
        )

        assert result["unit_contribution_margin"] == -30
        assert result["breakeven_units"] == float('inf')
        assert result["breakeven_sales"] == float('inf')

    def test_negative_margin_target_profit(self):
        """负毛利时的目标利润"""
        result = cvp_analysis(
            selling_price=50,
            variable_cost=80,
            fixed_costs=100000,
            target_profit=50000
        )

        assert "error" in result["target_analysis"]

    def test_loss_no_sensitivity(self):
        """亏损时无敏感性分析（利润为0）"""
        result = cvp_analysis(
            selling_price=100,
            variable_cost=60,
            fixed_costs=200000,
            current_volume=5000  # 刚好盈亏平衡
        )

        # 营业利润为0时不计算敏感性
        assert "sensitivity" not in result

    def test_below_breakeven(self):
        """销量低于盈亏平衡点"""
        result = cvp_analysis(
            selling_price=100,
            variable_cost=60,
            fixed_costs=200000,
            current_volume=3000  # 低于盈亏平衡点5000
        )

        assert result["current_analysis"]["operating_profit"] < 0
        assert result["current_analysis"]["margin_of_safety"] < 0
        assert result["current_analysis"]["margin_of_safety_rate"] < 0

    def test_zero_selling_price(self):
        """零售价"""
        result = cvp_analysis(
            selling_price=0,
            variable_cost=60,
            fixed_costs=200000
        )

        assert result["cm_ratio"] == 0
        assert result["variable_cost_ratio"] == 0


class TestBreakeven:
    """盈亏平衡点测试"""

    def test_single_product(self):
        """单产品"""
        result = breakeven(
            products=[{"name": "A", "selling_price": 100, "variable_cost": 60}],
            fixed_costs=200000
        )

        assert result["breakeven_sales"] == pytest.approx(500000)
        assert result["by_product"][0]["breakeven_units"] == pytest.approx(5000)

    def test_multi_product_weighted_avg(self):
        """多产品加权平均"""
        result = breakeven(
            products=[
                {"name": "A", "selling_price": 100, "variable_cost": 60, "sales_mix": 0.6},
                {"name": "B", "selling_price": 80, "variable_cost": 40, "sales_mix": 0.4}
            ],
            fixed_costs=200000,
            method="weighted_avg"
        )

        # A毛利率40%，B毛利率50%
        # 加权平均 = 0.4*0.6 + 0.5*0.4 = 0.44
        assert result["weighted_avg_cm_ratio"] == pytest.approx(0.44)
        assert result["breakeven_sales"] == pytest.approx(200000/0.44)

    def test_multi_product_sequential(self):
        """多产品顺序法"""
        result = breakeven(
            products=[
                {"name": "A", "selling_price": 100, "variable_cost": 60},
                {"name": "B", "selling_price": 80, "variable_cost": 40}
            ],
            fixed_costs=200000,
            method="sequential"
        )

        assert result["method"] == "sequential"
        # 先按毛利率排序（B 50% > A 40%）
        assert result["priority_order"][0] == "B"

    def test_equal_sales_mix(self):
        """默认平均销售组合"""
        result = breakeven(
            products=[
                {"name": "A", "selling_price": 100, "variable_cost": 60},
                {"name": "B", "selling_price": 100, "variable_cost": 60}
            ],
            fixed_costs=200000
        )

        # 销售组合应该各50%
        assert result["by_product"][0]["sales_mix"] == pytest.approx(0.5)
        assert result["by_product"][1]["sales_mix"] == pytest.approx(0.5)

    def test_analysis_text(self):
        """分析文本"""
        result = breakeven(
            products=[{"name": "A", "selling_price": 100, "variable_cost": 60}],
            fixed_costs=200000
        )

        assert "analysis" in result
        assert "盈亏平衡" in result["analysis"]

    def test_zero_margin_product(self):
        """零毛利产品"""
        result = breakeven(
            products=[
                {"name": "A", "selling_price": 100, "variable_cost": 100},  # 零毛利
                {"name": "B", "selling_price": 80, "variable_cost": 40}
            ],
            fixed_costs=200000
        )

        # A产品毛利率为0，B产品需要承担全部固定成本
        a_product = next(p for p in result["by_product"] if p["name"] == "A")
        assert a_product["cm_ratio"] == 0

    def test_all_negative_margin(self):
        """全部负毛利"""
        result = breakeven(
            products=[
                {"name": "A", "selling_price": 50, "variable_cost": 80},
                {"name": "B", "selling_price": 60, "variable_cost": 90}
            ],
            fixed_costs=200000
        )

        # 加权毛利率为负，盈亏平衡点为无穷大
        assert result["breakeven_sales"] == float('inf')

    def test_zero_fixed_costs(self):
        """零固定成本"""
        result = breakeven(
            products=[{"name": "A", "selling_price": 100, "variable_cost": 60}],
            fixed_costs=0
        )

        assert result["breakeven_sales"] == 0
        assert result["by_product"][0]["breakeven_units"] == 0

    def test_sales_mix_normalization(self):
        """销售组合标准化"""
        result = breakeven(
            products=[
                {"name": "A", "selling_price": 100, "variable_cost": 60, "sales_mix": 3},
                {"name": "B", "selling_price": 80, "variable_cost": 40, "sales_mix": 2}
            ],
            fixed_costs=200000
        )

        # 3:2 应标准化为 0.6:0.4
        a_product = next(p for p in result["by_product"] if p["name"] == "A")
        b_product = next(p for p in result["by_product"] if p["name"] == "B")
        assert a_product["sales_mix"] == pytest.approx(0.6)
        assert b_product["sales_mix"] == pytest.approx(0.4)
