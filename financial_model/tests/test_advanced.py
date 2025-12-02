# -*- coding: utf-8 -*-
"""
高级功能模块测试
"""

import unittest
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from financial_model.models import DeferredTax, Impairment, LeaseCapitalization


class TestDeferredTax(unittest.TestCase):
    """递延税测试"""

    def setUp(self):
        self.dt = DeferredTax()

    def test_loss_creates_dta(self):
        """测试亏损时创建递延税资产"""
        result = self.dt.calc_deferred_tax(
            ebt=-1000000,       # 当期亏损100万
            prior_tax_loss=0,   # 无累计亏损
            tax_rate=0.25,
            dta_balance=0       # 无期初DTA
        )

        # 当期税应为0
        self.assertEqual(result["current_tax"]["value"], 0)

        # 应新增DTA = 100万 * 25% = 25万
        self.assertEqual(result["dta_change"]["value"], 250000)

        # 期末DTA = 25万
        self.assertEqual(result["closing_dta"]["value"], 250000)

        # 累计亏损 = 100万
        self.assertEqual(result["closing_tax_loss"]["value"], 1000000)

    def test_profit_uses_tax_loss(self):
        """测试盈利时使用累计亏损抵扣"""
        result = self.dt.calc_deferred_tax(
            ebt=800000,            # 当期盈利80万
            prior_tax_loss=500000, # 累计亏损50万
            tax_rate=0.25,
            dta_balance=125000     # 期初DTA = 50万 * 25%
        )

        # 可抵扣 = min(80万, 50万) = 50万
        # 应税所得 = 80万 - 50万 = 30万
        # 当期税 = 30万 * 25% = 7.5万
        self.assertEqual(result["current_tax"]["value"], 75000)

        # DTA减少 = 50万 * 25% = 12.5万（负数）
        self.assertEqual(result["dta_change"]["value"], -125000)

        # 期末DTA = 12.5万 - 12.5万 = 0
        self.assertEqual(result["closing_dta"]["value"], 0)

        # 剩余累计亏损 = 50万 - 50万 = 0
        self.assertEqual(result["closing_tax_loss"]["value"], 0)

    def test_profit_no_loss(self):
        """测试盈利且无累计亏损"""
        result = self.dt.calc_deferred_tax(
            ebt=1000000,
            prior_tax_loss=0,
            tax_rate=0.25,
            dta_balance=0
        )

        # 正常纳税
        self.assertEqual(result["current_tax"]["value"], 250000)
        self.assertEqual(result["dta_change"]["value"], 0)

    def test_tax_expense_calculation(self):
        """测试所得税费用计算"""
        # 亏损情况：所得税费用 = 0 - 25万 = -25万（贷方，减少费用）
        result = self.dt.calc_deferred_tax(
            ebt=-1000000,
            prior_tax_loss=0,
            tax_rate=0.25,
            dta_balance=0
        )
        self.assertEqual(result["tax_expense"]["value"], -250000)


class TestImpairment(unittest.TestCase):
    """资产减值测试"""

    def setUp(self):
        self.imp = Impairment()

    def test_calc_value_in_use(self):
        """测试使用价值计算"""
        cash_flows = [100000, 100000, 100000, 100000, 100000]
        result = self.imp.calc_value_in_use(cash_flows, 0.10)

        # 5年年金现值，每年10万，10%折现
        # PV = 100000 * (1 - 1.1^-5) / 0.1 ≈ 379079
        self.assertAlmostEqual(result.value, 379078.68, places=0)

    def test_impairment_required(self):
        """测试需要减值的情况"""
        result = self.imp.calc_impairment(
            asset_name="商誉",
            carrying_value=10000000,  # 账面1000万
            fair_value=7000000,       # 公允价值700万
            value_in_use=8000000      # 使用价值800万
        )

        # 可回收金额 = max(700, 800) = 800万
        self.assertEqual(result["recoverable_amount"]["value"], 8000000)

        # 需要减值
        self.assertTrue(result["is_impaired"])

        # 减值损失 = 1000 - 800 = 200万
        self.assertEqual(result["impairment_loss"]["value"], 2000000)

        # 新账面价值 = 800万
        self.assertEqual(result["new_carrying_value"]["value"], 8000000)

    def test_no_impairment_needed(self):
        """测试不需要减值的情况"""
        result = self.imp.calc_impairment(
            asset_name="设备",
            carrying_value=5000000,
            fair_value=6000000,
            value_in_use=5500000
        )

        # 可回收金额 = max(600, 550) = 600万 > 账面500万
        self.assertFalse(result["is_impaired"])
        self.assertEqual(result["impairment_loss"]["value"], 0)
        self.assertEqual(result["new_carrying_value"]["value"], 5000000)


class TestLeaseCapitalization(unittest.TestCase):
    """租赁资本化测试"""

    def setUp(self):
        self.lease = LeaseCapitalization()

    def test_initial_recognition(self):
        """测试初始确认"""
        result = self.lease.capitalize_lease(
            annual_rent=1000000,
            lease_term=5,
            discount_rate=0.05
        )

        # 租赁负债 = 租金现值
        # PV = 1000000 * (1 - 1.05^-5) / 0.05 ≈ 4329477
        lease_liability = result["initial_recognition"]["lease_liability"]["value"]
        self.assertAlmostEqual(lease_liability, 4329477, delta=100)

        # 使用权资产 = 租赁负债
        rou_asset = result["initial_recognition"]["rou_asset"]["value"]
        self.assertEqual(rou_asset, lease_liability)

    def test_annual_schedule(self):
        """测试年度明细表"""
        result = self.lease.capitalize_lease(
            annual_rent=1000000,
            lease_term=5,
            discount_rate=0.05
        )

        schedule = result["annual_schedule"]

        # 应该有5年的明细
        self.assertEqual(len(schedule), 5)

        # 第一年
        year1 = schedule[0]
        self.assertEqual(year1["year"], 1)
        self.assertEqual(year1["rent_payment"], 1000000)

        # 利息 = 期初负债 * 5%
        expected_interest = year1["opening_liability"] * 0.05
        self.assertAlmostEqual(year1["interest_expense"], expected_interest, delta=1)

        # 本金 = 租金 - 利息
        expected_principal = 1000000 - year1["interest_expense"]
        self.assertAlmostEqual(year1["principal_payment"], expected_principal, delta=1)

        # 最后一年期末负债应接近0
        year5 = schedule[4]
        self.assertAlmostEqual(year5["closing_liability"], 0, delta=1)

    def test_impact_summary(self):
        """测试影响汇总"""
        result = self.lease.capitalize_lease(
            annual_rent=1000000,
            lease_term=5,
            discount_rate=0.05
        )

        impact = result["impact_summary"]

        # 原租金费用
        self.assertEqual(impact["old_rent_expense"], 1000000)

        # EBITDA改善 = 原租金
        self.assertEqual(impact["ebitda_improvement"], 1000000)

        # 新费用 = 折旧 + 利息
        self.assertEqual(
            impact["total_new_expense"],
            impact["new_depreciation"] + impact["new_interest"]
        )


if __name__ == '__main__':
    unittest.main()
