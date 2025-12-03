# -*- coding: utf-8 -*-
"""
高级功能模块

包含:
- DeferredTax: 税损递延计算
- Impairment: 资产减值测试
- LeaseCapitalization: 租赁资本化 (IFRS 16)
"""

from typing import Dict, List, Any
from ..core import ModelResult


class DeferredTax:
    """
    税损递延工具

    当公司亏损时，税法允许用亏损抵扣未来的应税收入。
    会计上需要确认"递延税资产"(DTA)。

    使用方法:
        dt = DeferredTax()
        result = dt.calc_deferred_tax(ebt, prior_loss, tax_rate, dta_balance)
    """

    def calc_deferred_tax(self,
                          ebt: float,
                          prior_tax_loss: float,
                          tax_rate: float,
                          dta_balance: float) -> Dict[str, Any]:
        """
        计算递延税资产和当期所得税

        逻辑:
          1. 如果 EBT < 0 (亏损):
             - 当期税 = 0
             - 新增递延税资产 = |EBT| × 税率
             - 累计亏损增加

          2. 如果 EBT > 0 且有累计亏损:
             - 可抵扣金额 = min(EBT, 累计亏损)
             - 当期税 = (EBT - 可抵扣) × 税率
             - 递延税资产减少 = 可抵扣 × 税率
             - 累计亏损减少

          3. 如果 EBT > 0 且无累计亏损:
             - 当期税 = EBT × 税率
             - 递延税资产不变

        Args:
            ebt: 当期税前利润
            prior_tax_loss: 累计可抵扣亏损（正数）
            tax_rate: 税率
            dta_balance: 期初递延税资产余额

        Returns:
            dict: 包含当期税、DTA变动、期末DTA、期末累计亏损
        """
        if ebt < 0:
            # 情况1: 当期亏损
            current_loss = abs(ebt)
            current_tax = ModelResult(
                value=0,
                formula="EBT < 0, 无需缴税",
                inputs={"ebt": ebt}
            )
            dta_change = ModelResult(
                value=current_loss * tax_rate,
                formula="|EBT| × tax_rate",
                inputs={"current_loss": current_loss, "tax_rate": tax_rate}
            )
            closing_dta = ModelResult(
                value=dta_balance + dta_change.value,
                formula="opening_dta + dta_change",
                inputs={"opening_dta": dta_balance, "dta_change": dta_change.value}
            )
            closing_tax_loss = ModelResult(
                value=prior_tax_loss + current_loss,
                formula="prior_loss + current_loss",
                inputs={"prior_loss": prior_tax_loss, "current_loss": current_loss}
            )

        elif ebt > 0 and prior_tax_loss > 0:
            # 情况2: 盈利且有累计亏损可抵扣
            deductible = min(ebt, prior_tax_loss)
            taxable_income = ebt - deductible

            current_tax = ModelResult(
                value=taxable_income * tax_rate,
                formula="(EBT - 可抵扣) × tax_rate",
                inputs={
                    "ebt": ebt,
                    "deductible": deductible,
                    "taxable_income": taxable_income,
                    "tax_rate": tax_rate
                }
            )
            dta_change = ModelResult(
                value=-deductible * tax_rate,  # 负数表示减少
                formula="-可抵扣 × tax_rate (DTA减少)",
                inputs={"deductible": deductible, "tax_rate": tax_rate}
            )
            closing_dta = ModelResult(
                value=dta_balance + dta_change.value,
                formula="opening_dta + dta_change",
                inputs={"opening_dta": dta_balance, "dta_change": dta_change.value}
            )
            closing_tax_loss = ModelResult(
                value=prior_tax_loss - deductible,
                formula="prior_loss - deductible",
                inputs={"prior_loss": prior_tax_loss, "deductible": deductible}
            )

        else:
            # 情况3: 盈利且无累计亏损
            current_tax = ModelResult(
                value=ebt * tax_rate,
                formula="EBT × tax_rate",
                inputs={"ebt": ebt, "tax_rate": tax_rate}
            )
            dta_change = ModelResult(
                value=0,
                formula="无累计亏损，DTA不变",
                inputs={}
            )
            closing_dta = ModelResult(
                value=dta_balance,
                formula="opening_dta (不变)",
                inputs={"opening_dta": dta_balance}
            )
            closing_tax_loss = ModelResult(
                value=0,
                formula="无累计亏损",
                inputs={}
            )

        # 计算所得税费用（利润表）= 当期税 - DTA变动
        # 注意：DTA增加时，所得税费用减少（贷方）
        tax_expense = ModelResult(
            value=current_tax.value - dta_change.value,
            formula="当期税 - DTA变动",
            inputs={
                "current_tax": current_tax.value,
                "dta_change": dta_change.value
            }
        )

        return {
            "current_tax": current_tax.to_dict(),
            "dta_change": dta_change.to_dict(),
            "closing_dta": closing_dta.to_dict(),
            "closing_tax_loss": closing_tax_loss.to_dict(),
            "tax_expense": tax_expense.to_dict(),
            "impact": {
                "income_statement": "所得税费用 = 当期税 ± DTA变动",
                "balance_sheet": f"递延税资产: {dta_balance:.2f} → {closing_dta.value:.2f}",
                "cash_flow": "递延税是非现金项目，经营现金流需加回"
            }
        }


class Impairment:
    """
    资产减值工具

    当资产的可回收金额低于账面价值时，需要计提减值损失。
    适用于固定资产、无形资产、商誉等。

    使用方法:
        imp = Impairment()
        result = imp.calc_impairment(carrying_value, fair_value, value_in_use)
    """

    def calc_value_in_use(self,
                          future_cash_flows: List[float],
                          discount_rate: float) -> ModelResult:
        """
        计算使用价值 (Value in Use)

        公式: VIU = Σ CF / (1+r)^t

        Args:
            future_cash_flows: 未来各期现金流列表
            discount_rate: 折现率

        Returns:
            ModelResult
        """
        pv_list = []
        total_pv = 0

        for t, cf in enumerate(future_cash_flows):
            discount_factor = 1 / (1 + discount_rate) ** (t + 1)
            pv = cf * discount_factor
            pv_list.append({
                "year": t + 1,
                "cash_flow": cf,
                "discount_factor": round(discount_factor, 4),
                "present_value": round(pv, 2)
            })
            total_pv += pv

        return ModelResult(
            value=total_pv,
            formula="Σ CF / (1+r)^t",
            inputs={
                "discount_rate": discount_rate,
                "years": len(future_cash_flows),
                "cash_flow_details": pv_list
            }
        )

    def calc_impairment(self,
                        asset_name: str,
                        carrying_value: float,
                        fair_value: float,
                        value_in_use: float) -> Dict[str, Any]:
        """
        资产减值测试

        逻辑:
          可回收金额 = max(公允价值-处置费用, 使用价值)

          如果 账面价值 > 可回收金额:
            减值损失 = 账面价值 - 可回收金额
            新账面价值 = 可回收金额
          否则:
            无需减值

        Args:
            asset_name: 资产名称
            carrying_value: 资产账面价值
            fair_value: 公允价值减处置费用
            value_in_use: 使用价值（未来现金流折现）

        Returns:
            dict: 包含可回收金额、是否减值、减值损失、新账面价值
        """
        recoverable_amount = max(fair_value, value_in_use)

        recoverable_result = ModelResult(
            value=recoverable_amount,
            formula="max(fair_value, value_in_use)",
            inputs={
                "fair_value": fair_value,
                "value_in_use": value_in_use
            }
        )

        is_impaired = carrying_value > recoverable_amount

        if is_impaired:
            impairment_loss = carrying_value - recoverable_amount
            new_carrying_value = recoverable_amount

            loss_result = ModelResult(
                value=impairment_loss,
                formula="carrying_value - recoverable_amount",
                inputs={
                    "carrying_value": carrying_value,
                    "recoverable_amount": recoverable_amount
                }
            )
            new_cv_result = ModelResult(
                value=new_carrying_value,
                formula="recoverable_amount",
                inputs={"recoverable_amount": recoverable_amount}
            )
        else:
            loss_result = ModelResult(
                value=0,
                formula="无需减值 (账面价值 <= 可回收金额)",
                inputs={
                    "carrying_value": carrying_value,
                    "recoverable_amount": recoverable_amount
                }
            )
            new_cv_result = ModelResult(
                value=carrying_value,
                formula="账面价值不变",
                inputs={"carrying_value": carrying_value}
            )

        return {
            "asset_name": asset_name,
            "carrying_value": carrying_value,
            "recoverable_amount": recoverable_result.to_dict(),
            "is_impaired": is_impaired,
            "impairment_loss": loss_result.to_dict(),
            "new_carrying_value": new_cv_result.to_dict(),
            "impact": {
                "income_statement": f"资产减值损失: {loss_result.value:,.2f} (费用增加)",
                "balance_sheet": f"{asset_name}净值: {carrying_value:,.2f} → {new_cv_result.value:,.2f}",
                "cash_flow": "减值是非现金项目，经营现金流需加回"
            }
        }


class LeaseCapitalization:
    """
    租赁资本化工具 (IFRS 16 / ASC 842)

    IFRS 16 要求将经营租赁资本化：
    - 确认"使用权资产"（Right-of-Use Asset）
    - 确认"租赁负债"（Lease Liability）
    - 原租金费用 → 折旧 + 利息

    使用方法:
        lease = LeaseCapitalization()
        result = lease.capitalize_lease(annual_rent, lease_term, discount_rate)
    """

    def capitalize_lease(self,
                         annual_rent: float,
                         lease_term: int,
                         discount_rate: float,
                         payment_timing: str = "end") -> Dict[str, Any]:
        """
        租赁资本化计算

        逻辑:
          1. 租赁负债 = Σ 租金 / (1+r)^t  (租金现值)
          2. 使用权资产 = 租赁负债 (初始确认)
          3. 每期:
             - 折旧 = 使用权资产 / 租赁期限
             - 利息 = 期初负债 × 折现率
             - 负债减少 = 租金 - 利息

        Args:
            annual_rent: 年租金
            lease_term: 租赁期限（年）
            discount_rate: 增量借款利率
            payment_timing: 付款时点 "end"(期末) 或 "begin"(期初)

        Returns:
            dict: 包含初始确认、年度明细表、影响汇总
        """
        # 计算租赁负债（租金现值）
        if payment_timing == "end":
            # 普通年金现值
            pv_factor = (1 - (1 + discount_rate) ** (-lease_term)) / discount_rate
        else:
            # 先付年金现值
            pv_factor = (1 - (1 + discount_rate) ** (-lease_term)) / discount_rate * (1 + discount_rate)

        lease_liability = annual_rent * pv_factor
        rou_asset = lease_liability  # 初始确认时相等

        initial_recognition = {
            "lease_liability": ModelResult(
                value=lease_liability,
                formula=f"Σ rent / (1+r)^t, t=1..{lease_term}",
                inputs={
                    "annual_rent": annual_rent,
                    "discount_rate": discount_rate,
                    "lease_term": lease_term,
                    "pv_factor": round(pv_factor, 4)
                }
            ).to_dict(),
            "rou_asset": ModelResult(
                value=rou_asset,
                formula="= lease_liability at inception",
                inputs={"lease_liability": lease_liability}
            ).to_dict()
        }

        # 年度折旧（直线法）
        annual_depreciation = rou_asset / lease_term

        # 生成年度明细表
        annual_schedule = []
        opening_liability = lease_liability
        opening_rou = rou_asset

        for year in range(1, lease_term + 1):
            # 利息费用
            interest_expense = opening_liability * discount_rate

            # 本金偿还
            principal_payment = annual_rent - interest_expense

            # 期末负债
            closing_liability = opening_liability - principal_payment

            # 期末使用权资产
            closing_rou = opening_rou - annual_depreciation

            annual_schedule.append({
                "year": year,
                "opening_liability": round(opening_liability, 2),
                "interest_expense": round(interest_expense, 2),
                "rent_payment": annual_rent,
                "principal_payment": round(principal_payment, 2),
                "closing_liability": round(max(closing_liability, 0), 2),
                "depreciation": round(annual_depreciation, 2),
                "opening_rou_asset": round(opening_rou, 2),
                "closing_rou_asset": round(max(closing_rou, 0), 2)
            })

            # 下期期初
            opening_liability = max(closing_liability, 0)
            opening_rou = max(closing_rou, 0)

        # 第一年的影响汇总
        year1 = annual_schedule[0]
        impact_summary = {
            "old_rent_expense": annual_rent,
            "new_depreciation": round(annual_depreciation, 2),
            "new_interest": round(year1["interest_expense"], 2),
            "total_new_expense": round(annual_depreciation + year1["interest_expense"], 2),
            "ebitda_improvement": annual_rent,  # EBITDA不再扣除租金
            "net_income_impact": round(annual_rent - (annual_depreciation + year1["interest_expense"]), 2)
        }

        return {
            "initial_recognition": initial_recognition,
            "annual_schedule": annual_schedule,
            "impact_summary": impact_summary,
            "impact": {
                "income_statement": f"租金费用 {annual_rent:,.0f} → 折旧 {annual_depreciation:,.0f} + 利息 {year1['interest_expense']:,.0f}",
                "ebitda": f"EBITDA 改善 {annual_rent:,.0f} (租金不再扣除)",
                "balance_sheet": f"使用权资产 {rou_asset:,.0f} / 租赁负债 {lease_liability:,.0f}",
                "cash_flow": f"经营流出 {year1['interest_expense']:,.0f}(利息) + 筹资流出 {year1['principal_payment']:,.0f}(本金)"
            }
        }
