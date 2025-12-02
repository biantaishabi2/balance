# -*- coding: utf-8 -*-
"""
三表模型工具

提供利润表、资产负债表、现金流量表的预测和联动计算
每个工具都带追溯信息

工具清单:
- forecast_revenue: 收入预测
- forecast_cost: 成本预测
- forecast_opex: 费用预测
- calc_working_capital: 营运资本计算
- calc_depreciation: 折旧计算
- calc_interest: 利息计算
- calc_tax: 所得税计算
- check_balance: 配平检验
"""

from typing import Dict, Any, Optional
from ..core import ModelResult, ModelCell, FinancialModel


class ThreeStatementModel(FinancialModel):
    """
    三表模型工具集

    使用方法:
        model = ThreeStatementModel(base_data)
        result = model.build(assumptions)
    """

    def __init__(self, base_data: dict, scenario: str = "base_case"):
        """
        初始化模型

        Args:
            base_data: 基础财报数据（上期数据）
            scenario: 情景名称
        """
        company = base_data.get('company', '财务模型')
        super().__init__(name=f"{company}三表模型", scenario=scenario)
        self.base = base_data

    # ==================== 利润表工具 ====================

    def forecast_revenue(self, growth_rate: float) -> ModelResult:
        """
        收入预测

        公式: revenue = last_revenue × (1 + growth_rate)

        Args:
            growth_rate: 收入增长率 (如 0.09 表示 9%)

        Returns:
            ModelResult: 包含值、公式、输入的结果对象
        """
        last_rev = self.base['last_revenue']
        value = last_rev * (1 + growth_rate)

        return ModelResult(
            value=value,
            formula="last_revenue × (1 + growth_rate)",
            inputs={"last_revenue": last_rev, "growth_rate": growth_rate}
        )

    def forecast_cost(self, revenue: float, gross_margin: float) -> ModelResult:
        """
        成本预测

        公式: cost = revenue × (1 - gross_margin)

        Args:
            revenue: 营业收入
            gross_margin: 毛利率 (如 0.253 表示 25.3%)

        Returns:
            ModelResult
        """
        value = revenue * (1 - gross_margin)

        return ModelResult(
            value=value,
            formula="revenue × (1 - gross_margin)",
            inputs={"revenue": revenue, "gross_margin": gross_margin}
        )

    def forecast_opex(self, revenue: float, opex_ratio: float) -> ModelResult:
        """
        费用预测

        公式: opex = revenue × opex_ratio

        Args:
            revenue: 营业收入
            opex_ratio: 费用率

        Returns:
            ModelResult
        """
        value = revenue * opex_ratio

        return ModelResult(
            value=value,
            formula="revenue × opex_ratio",
            inputs={"revenue": revenue, "opex_ratio": opex_ratio}
        )

    def calc_gross_profit(self, revenue: float, cost: float) -> ModelResult:
        """
        毛利计算

        公式: gross_profit = revenue - cost
        """
        value = revenue - cost

        return ModelResult(
            value=value,
            formula="revenue - cost",
            inputs={"revenue": revenue, "cost": cost}
        )

    def calc_ebit(self, gross_profit: float, opex: float) -> ModelResult:
        """
        营业利润计算

        公式: ebit = gross_profit - opex
        """
        value = gross_profit - opex

        return ModelResult(
            value=value,
            formula="gross_profit - opex",
            inputs={"gross_profit": gross_profit, "opex": opex}
        )

    def calc_interest(self, debt: float, interest_rate: float) -> ModelResult:
        """
        利息计算

        公式: interest = debt × interest_rate

        Args:
            debt: 有息负债
            interest_rate: 利率

        Returns:
            ModelResult
        """
        value = debt * interest_rate

        return ModelResult(
            value=value,
            formula="debt × interest_rate",
            inputs={"debt": debt, "interest_rate": interest_rate}
        )

    def calc_ebt(self, ebit: float, interest: float) -> ModelResult:
        """
        税前利润计算

        公式: ebt = ebit - interest
        """
        value = ebit - interest

        return ModelResult(
            value=value,
            formula="ebit - interest",
            inputs={"ebit": ebit, "interest": interest}
        )

    def calc_tax(self, ebt: float, tax_rate: float) -> ModelResult:
        """
        所得税计算

        公式: tax = max(ebt, 0) × tax_rate
        注意: 亏损时税为0（简化处理，不考虑递延税）

        Args:
            ebt: 税前利润
            tax_rate: 税率

        Returns:
            ModelResult
        """
        value = max(ebt, 0) * tax_rate

        return ModelResult(
            value=value,
            formula="max(ebt, 0) × tax_rate",
            inputs={"ebt": ebt, "tax_rate": tax_rate}
        )

    def calc_net_income(self, ebt: float, tax: float) -> ModelResult:
        """
        净利润计算

        公式: net_income = ebt - tax
        """
        value = ebt - tax

        return ModelResult(
            value=value,
            formula="ebt - tax",
            inputs={"ebt": ebt, "tax": tax}
        )

    # ==================== 资产负债表工具 ====================

    def calc_working_capital(self,
                             revenue: float,
                             cost: float,
                             ar_days: float,
                             ap_days: float,
                             inv_days: float) -> Dict[str, ModelResult]:
        """
        营运资本预测

        公式:
            AR = revenue / 365 × ar_days
            AP = cost / 365 × ap_days
            Inv = cost / 365 × inv_days

        Args:
            revenue: 营业收入
            cost: 营业成本
            ar_days: 应收账款周转天数
            ap_days: 应付账款周转天数
            inv_days: 存货周转天数

        Returns:
            Dict[str, ModelResult]: 包含 receivable, payable, inventory
        """
        ar = revenue / 365 * ar_days
        ap = cost / 365 * ap_days
        inv = cost / 365 * inv_days

        return {
            "receivable": ModelResult(
                value=ar,
                formula="revenue / 365 × ar_days",
                inputs={"revenue": revenue, "ar_days": ar_days}
            ),
            "payable": ModelResult(
                value=ap,
                formula="cost / 365 × ap_days",
                inputs={"cost": cost, "ap_days": ap_days}
            ),
            "inventory": ModelResult(
                value=inv,
                formula="cost / 365 × inv_days",
                inputs={"cost": cost, "inv_days": inv_days}
            )
        }

    def calc_depreciation(self,
                          fixed_assets: float,
                          useful_life: float,
                          salvage: float = 0) -> ModelResult:
        """
        折旧计算（直线法）

        公式: depreciation = (fixed_assets - salvage) / useful_life

        Args:
            fixed_assets: 固定资产原值
            useful_life: 使用年限
            salvage: 残值

        Returns:
            ModelResult
        """
        value = (fixed_assets - salvage) / useful_life

        return ModelResult(
            value=value,
            formula="(fixed_assets - salvage) / useful_life",
            inputs={
                "fixed_assets": fixed_assets,
                "salvage": salvage,
                "useful_life": useful_life
            }
        )

    def calc_capex(self, revenue: float, capex_ratio: float) -> ModelResult:
        """
        资本支出计算

        公式: capex = revenue × capex_ratio
        """
        value = revenue * capex_ratio

        return ModelResult(
            value=value,
            formula="revenue × capex_ratio",
            inputs={"revenue": revenue, "capex_ratio": capex_ratio}
        )

    # ==================== 现金流量表工具 ====================

    def calc_operating_cash_flow(self,
                                  net_income: float,
                                  depreciation: float,
                                  delta_ar: float,
                                  delta_inv: float,
                                  delta_ap: float) -> ModelResult:
        """
        经营现金流计算（间接法）

        公式: OCF = net_income + depreciation - Δar - Δinv + Δap

        Args:
            net_income: 净利润
            depreciation: 折旧
            delta_ar: 应收账款变动（增加为正）
            delta_inv: 存货变动（增加为正）
            delta_ap: 应付账款变动（增加为正）

        Returns:
            ModelResult
        """
        delta_nwc = delta_ar + delta_inv - delta_ap
        value = net_income + depreciation - delta_nwc

        return ModelResult(
            value=value,
            formula="net_income + depreciation - ΔNWC",
            inputs={
                "net_income": net_income,
                "depreciation": depreciation,
                "delta_ar": delta_ar,
                "delta_inv": delta_inv,
                "delta_ap": delta_ap,
                "delta_nwc": delta_nwc
            }
        )

    def calc_investing_cash_flow(self, capex: float) -> ModelResult:
        """
        投资现金流计算

        公式: ICF = -capex（资本支出为负）
        """
        value = -capex

        return ModelResult(
            value=value,
            formula="-capex",
            inputs={"capex": capex}
        )

    def calc_financing_cash_flow(self,
                                  interest: float,
                                  dividend: float,
                                  delta_debt: float = 0) -> ModelResult:
        """
        筹资现金流计算

        公式: FCF = -interest - dividend + Δdebt
        """
        value = -interest - dividend + delta_debt

        return ModelResult(
            value=value,
            formula="-interest - dividend + Δdebt",
            inputs={
                "interest": interest,
                "dividend": dividend,
                "delta_debt": delta_debt
            }
        )

    # ==================== 配平检验 ====================

    def check_balance(self,
                      total_assets: float,
                      total_liabilities: float,
                      total_equity: float) -> Dict[str, Any]:
        """
        资产负债表配平检验

        公式: assets = liabilities + equity

        Returns:
            dict: 包含 is_balanced, difference 等
        """
        diff = total_assets - (total_liabilities + total_equity)
        is_balanced = abs(diff) < 0.01  # 允许0.01的误差

        return {
            "is_balanced": is_balanced,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "total_equity": total_equity,
            "difference": diff
        }

    # ==================== 主构建方法 ====================

    def build(self, assumptions: dict) -> dict:
        """
        构建完整三表模型

        Args:
            assumptions: 驱动假设字典，包含：
                - growth_rate: 收入增长率
                - gross_margin: 毛利率
                - opex_ratio: 费用率
                - ar_days, ap_days, inv_days: 周转天数
                - capex_ratio: 资本支出比率
                - interest_rate: 利率
                - tax_rate: 税率
                - dividend_ratio: 分红比率

        Returns:
            dict: 完整的三表数据（带追溯信息）
        """
        # 保存假设参数
        for key, value in assumptions.items():
            if isinstance(value, (int, float)):
                self.set_assumption(key, value)

        # ========== 利润表计算 ==========
        revenue_r = self.forecast_revenue(assumptions['growth_rate'])
        revenue = revenue_r.value

        cost_r = self.forecast_cost(revenue, assumptions['gross_margin'])
        cost = cost_r.value

        opex_r = self.forecast_opex(revenue, assumptions['opex_ratio'])
        opex = opex_r.value

        gross_profit_r = self.calc_gross_profit(revenue, cost)
        gross_profit = gross_profit_r.value

        ebit_r = self.calc_ebit(gross_profit, opex)
        ebit = ebit_r.value

        # 利息（基于期初负债）
        opening_debt = self.base.get('closing_debt', 0)
        interest_r = self.calc_interest(opening_debt, assumptions['interest_rate'])
        interest = interest_r.value

        ebt_r = self.calc_ebt(ebit, interest)
        ebt = ebt_r.value

        tax_r = self.calc_tax(ebt, assumptions['tax_rate'])
        tax = tax_r.value

        net_income_r = self.calc_net_income(ebt, tax)
        net_income = net_income_r.value

        # 保存利润表单元格
        self.add_cell(ModelCell.from_result("revenue", revenue_r, "利润表"))
        self.add_cell(ModelCell.from_result("cost", cost_r, "利润表"))
        self.add_cell(ModelCell.from_result("gross_profit", gross_profit_r, "利润表"))
        self.add_cell(ModelCell.from_result("opex", opex_r, "利润表"))
        self.add_cell(ModelCell.from_result("ebit", ebit_r, "利润表"))
        self.add_cell(ModelCell.from_result("interest", interest_r, "利润表"))
        self.add_cell(ModelCell.from_result("ebt", ebt_r, "利润表"))
        self.add_cell(ModelCell.from_result("tax", tax_r, "利润表"))
        self.add_cell(ModelCell.from_result("net_income", net_income_r, "利润表"))

        # ========== 营运资本计算 ==========
        wc = self.calc_working_capital(
            revenue, cost,
            assumptions['ar_days'],
            assumptions['ap_days'],
            assumptions['inv_days']
        )

        # 期初营运资本
        opening_ar = self.base.get('closing_receivable', 0)
        opening_ap = self.base.get('closing_payable', 0)
        opening_inv = self.base.get('closing_inventory', 0)

        # 期末营运资本
        closing_ar = wc['receivable'].value
        closing_ap = wc['payable'].value
        closing_inv = wc['inventory'].value

        # 变动额
        delta_ar = closing_ar - opening_ar
        delta_ap = closing_ap - opening_ap
        delta_inv = closing_inv - opening_inv

        # ========== 固定资产和折旧 ==========
        fixed_assets_gross = self.base.get('fixed_asset_gross', 0)
        useful_life = self.base.get('fixed_asset_life', 10)

        capex_r = self.calc_capex(revenue, assumptions['capex_ratio'])
        capex = capex_r.value

        # 新的固定资产原值
        new_fixed_assets = fixed_assets_gross + capex

        depreciation_r = self.calc_depreciation(new_fixed_assets, useful_life)
        depreciation = depreciation_r.value

        # 累计折旧
        opening_accum_dep = self.base.get('accum_depreciation', 0)
        closing_accum_dep = opening_accum_dep + depreciation

        # 固定资产净值
        closing_fixed_net = new_fixed_assets - closing_accum_dep

        self.add_cell(ModelCell.from_result("capex", capex_r, "投资"))
        self.add_cell(ModelCell.from_result("depreciation", depreciation_r, "折旧"))

        # ========== 现金流量表计算 ==========
        ocf_r = self.calc_operating_cash_flow(
            net_income, depreciation,
            delta_ar, delta_inv, delta_ap
        )
        ocf = ocf_r.value

        icf_r = self.calc_investing_cash_flow(capex)
        icf = icf_r.value

        # 分红
        dividend_ratio = assumptions.get('dividend_ratio', 0.3)
        dividend = max(net_income, 0) * dividend_ratio

        fcf_r = self.calc_financing_cash_flow(interest, dividend)
        fcf = fcf_r.value

        self.add_cell(ModelCell.from_result("operating_cf", ocf_r, "现金流量表"))
        self.add_cell(ModelCell.from_result("investing_cf", icf_r, "现金流量表"))
        self.add_cell(ModelCell.from_result("financing_cf", fcf_r, "现金流量表"))

        # 净现金变动
        net_cash_change = ocf + icf + fcf

        # 期末现金
        opening_cash = self.base.get('closing_cash', 0)
        closing_cash = opening_cash + net_cash_change

        # ========== 资产负债表计算 ==========
        # 资产
        total_assets = closing_cash + closing_ar + closing_inv + closing_fixed_net

        # 负债
        closing_debt = opening_debt  # 假设不变
        total_liabilities = closing_debt + closing_ap

        # 权益
        opening_equity = self.base.get('closing_equity', 0)
        retained_change = net_income - dividend
        closing_equity = opening_equity + retained_change

        # 配平检验
        balance_check = self.check_balance(total_assets, total_liabilities, closing_equity)

        # ========== 组装结果 ==========
        result = {
            "_meta": {
                "model_name": self.name,
                "scenario": self.scenario,
                "base_period": self.base.get('period', ''),
                "company": self.base.get('company', '')
            },

            "income_statement": {
                "revenue": revenue_r.to_dict(),
                "cost": cost_r.to_dict(),
                "gross_profit": gross_profit_r.to_dict(),
                "opex": opex_r.to_dict(),
                "ebit": ebit_r.to_dict(),
                "interest": interest_r.to_dict(),
                "ebt": ebt_r.to_dict(),
                "tax": tax_r.to_dict(),
                "net_income": net_income_r.to_dict()
            },

            "balance_sheet": {
                "assets": {
                    "cash": {"value": closing_cash, "formula": "opening_cash + net_cash_change"},
                    "receivable": wc['receivable'].to_dict(),
                    "inventory": wc['inventory'].to_dict(),
                    "fixed_assets_net": {"value": closing_fixed_net, "formula": "fixed_assets - accum_dep"},
                    "total_assets": {"value": total_assets}
                },
                "liabilities": {
                    "payable": wc['payable'].to_dict(),
                    "debt": {"value": closing_debt},
                    "total_liabilities": {"value": total_liabilities}
                },
                "equity": {
                    "opening_equity": {"value": opening_equity},
                    "retained_change": {"value": retained_change, "formula": "net_income - dividend"},
                    "total_equity": {"value": closing_equity}
                }
            },

            "cash_flow": {
                "operating": ocf_r.to_dict(),
                "investing": icf_r.to_dict(),
                "financing": fcf_r.to_dict(),
                "net_change": {"value": net_cash_change, "formula": "OCF + ICF + FCF"},
                "closing_cash": {"value": closing_cash}
            },

            "validation": balance_check,

            "working_capital": {
                "receivable": wc['receivable'].to_dict(),
                "payable": wc['payable'].to_dict(),
                "inventory": wc['inventory'].to_dict(),
                "delta_ar": {"value": delta_ar},
                "delta_ap": {"value": delta_ap},
                "delta_inv": {"value": delta_inv}
            }
        }

        return result

    def get_fcff(self, assumptions: dict) -> ModelResult:
        """
        计算企业自由现金流 (FCFF)

        公式: FCFF = EBIT × (1-t) + D&A - CapEx - ΔNWC

        用于 DCF 估值
        """
        # 先构建三表
        result = self.build(assumptions)

        ebit = result['income_statement']['ebit']['value']
        tax_rate = assumptions['tax_rate']
        depreciation = result['cash_flow']['operating']['inputs']['depreciation']
        capex = result['balance_sheet']['assets']['fixed_assets_net']['value']  # 简化
        delta_nwc = result['cash_flow']['operating']['inputs']['delta_nwc']

        nopat = ebit * (1 - tax_rate)
        fcff = nopat + depreciation - abs(result['cash_flow']['investing']['value']) - delta_nwc

        return ModelResult(
            value=fcff,
            formula="EBIT × (1-t) + D&A - CapEx - ΔNWC",
            inputs={
                "ebit": ebit,
                "tax_rate": tax_rate,
                "nopat": nopat,
                "depreciation": depreciation,
                "capex": abs(result['cash_flow']['investing']['value']),
                "delta_nwc": delta_nwc
            }
        )
