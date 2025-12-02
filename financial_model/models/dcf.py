# -*- coding: utf-8 -*-
"""
DCF 估值工具

基于自由现金流折现法估算企业价值

工具清单:
- calc_fcff: 企业自由现金流
- calc_fcfe: 股权自由现金流
- calc_capm: 股权成本(CAPM)
- calc_wacc: 加权资本成本
- calc_terminal_value_perpetual: 终值(永续增长)
- calc_terminal_value_multiple: 终值(退出倍数)
- calc_enterprise_value: 企业价值
- calc_equity_value: 股权价值
- calc_per_share_value: 每股价值
- sensitivity_analysis: 敏感性分析
"""

from typing import Dict, List, Any, Optional
from ..core import ModelResult, FinancialModel


class DCFModel(FinancialModel):
    """
    DCF估值工具集

    使用方法:
        dcf = DCFModel()
        wacc = dcf.calc_wacc(...)
        ev = dcf.calc_enterprise_value(...)
    """

    def __init__(self, name: str = "DCF估值模型"):
        super().__init__(name=name, scenario="valuation")

    # ==================== 自由现金流计算 ====================

    def calc_fcff(self,
                  ebit: float,
                  tax_rate: float,
                  depreciation: float,
                  capex: float,
                  delta_nwc: float) -> ModelResult:
        """
        企业自由现金流 (Free Cash Flow to Firm)

        公式: FCFF = EBIT × (1-t) + D&A - CapEx - ΔNWC

        Args:
            ebit: 息税前利润
            tax_rate: 税率
            depreciation: 折旧与摊销
            capex: 资本支出
            delta_nwc: 净营运资本变动

        Returns:
            ModelResult
        """
        nopat = ebit * (1 - tax_rate)
        value = nopat + depreciation - capex - delta_nwc

        return ModelResult(
            value=value,
            formula="EBIT × (1-t) + D&A - CapEx - ΔNWC",
            inputs={
                "ebit": ebit,
                "tax_rate": tax_rate,
                "nopat": nopat,
                "depreciation": depreciation,
                "capex": capex,
                "delta_nwc": delta_nwc
            }
        )

    def calc_fcfe(self,
                  fcff: float,
                  interest: float,
                  tax_rate: float,
                  delta_debt: float) -> ModelResult:
        """
        股权自由现金流 (Free Cash Flow to Equity)

        公式: FCFE = FCFF - Interest × (1-t) + ΔDebt

        Args:
            fcff: 企业自由现金流
            interest: 利息费用
            tax_rate: 税率
            delta_debt: 净借款变动

        Returns:
            ModelResult
        """
        after_tax_interest = interest * (1 - tax_rate)
        value = fcff - after_tax_interest + delta_debt

        return ModelResult(
            value=value,
            formula="FCFF - Interest × (1-t) + ΔDebt",
            inputs={
                "fcff": fcff,
                "interest": interest,
                "tax_rate": tax_rate,
                "after_tax_interest": after_tax_interest,
                "delta_debt": delta_debt
            }
        )

    # ==================== 折现率计算 ====================

    def calc_capm(self,
                  risk_free_rate: float,
                  beta: float,
                  market_risk_premium: float) -> ModelResult:
        """
        CAPM计算股权成本

        公式: Re = Rf + β × MRP

        Args:
            risk_free_rate: 无风险利率 (如10年期国债收益率)
            beta: 贝塔系数 (系统性风险)
            market_risk_premium: 市场风险溢价 (Rm - Rf)

        Returns:
            ModelResult
        """
        value = risk_free_rate + beta * market_risk_premium

        return ModelResult(
            value=value,
            formula="Rf + β × MRP",
            inputs={
                "risk_free_rate": risk_free_rate,
                "beta": beta,
                "market_risk_premium": market_risk_premium
            }
        )

    def calc_wacc(self,
                  cost_of_equity: float,
                  cost_of_debt: float,
                  tax_rate: float,
                  debt_ratio: float) -> ModelResult:
        """
        加权平均资本成本 (WACC)

        公式: WACC = E/(D+E) × Re + D/(D+E) × Rd × (1-t)

        Args:
            cost_of_equity: 股权成本 (Re)
            cost_of_debt: 债务成本 (Rd)
            tax_rate: 税率
            debt_ratio: 负债率 D/(D+E)

        Returns:
            ModelResult
        """
        equity_ratio = 1 - debt_ratio
        after_tax_debt_cost = cost_of_debt * (1 - tax_rate)
        value = equity_ratio * cost_of_equity + debt_ratio * after_tax_debt_cost

        return ModelResult(
            value=value,
            formula="E/(D+E) × Re + D/(D+E) × Rd × (1-t)",
            inputs={
                "cost_of_equity": cost_of_equity,
                "cost_of_debt": cost_of_debt,
                "tax_rate": tax_rate,
                "debt_ratio": debt_ratio,
                "equity_ratio": equity_ratio,
                "after_tax_debt_cost": after_tax_debt_cost
            }
        )

    # ==================== 终值计算 ====================

    def calc_terminal_value_perpetual(self,
                                       final_fcf: float,
                                       wacc: float,
                                       terminal_growth: float) -> ModelResult:
        """
        永续增长法计算终值

        公式: TV = FCF × (1+g) / (WACC - g)

        Args:
            final_fcf: 预测期最后一年的FCF
            wacc: 加权平均资本成本
            terminal_growth: 永续增长率

        Returns:
            ModelResult

        注意:
            - terminal_growth 必须小于 wacc
            - 一般用GDP增速或通胀率作为参考 (1%-3%)
        """
        if terminal_growth >= wacc:
            raise ValueError(f"Terminal growth ({terminal_growth}) must be less than WACC ({wacc})")

        value = final_fcf * (1 + terminal_growth) / (wacc - terminal_growth)

        return ModelResult(
            value=value,
            formula="FCF × (1+g) / (WACC - g)",
            inputs={
                "final_fcf": final_fcf,
                "terminal_growth": terminal_growth,
                "wacc": wacc
            }
        )

    def calc_terminal_value_multiple(self,
                                      final_ebitda: float,
                                      exit_multiple: float) -> ModelResult:
        """
        退出倍数法计算终值

        公式: TV = EBITDA × Exit Multiple

        Args:
            final_ebitda: 预测期最后一年的EBITDA
            exit_multiple: 退出倍数 (行业可比公司的EV/EBITDA)

        Returns:
            ModelResult
        """
        value = final_ebitda * exit_multiple

        return ModelResult(
            value=value,
            formula="EBITDA × Exit_Multiple",
            inputs={
                "final_ebitda": final_ebitda,
                "exit_multiple": exit_multiple
            }
        )

    # ==================== 估值计算 ====================

    def calc_present_value(self,
                           cash_flow: float,
                           discount_rate: float,
                           year: int) -> ModelResult:
        """
        计算单期现值

        公式: PV = CF / (1 + r)^t
        """
        discount_factor = 1 / (1 + discount_rate) ** year
        value = cash_flow * discount_factor

        return ModelResult(
            value=value,
            formula="CF / (1 + r)^t",
            inputs={
                "cash_flow": cash_flow,
                "discount_rate": discount_rate,
                "year": year,
                "discount_factor": discount_factor
            }
        )

    def calc_enterprise_value(self,
                               fcf_list: List[float],
                               wacc: float,
                               terminal_value: float) -> ModelResult:
        """
        计算企业价值

        公式: EV = Σ FCF/(1+WACC)^t + TV/(1+WACC)^n

        Args:
            fcf_list: 各年FCF列表
            wacc: 折现率
            terminal_value: 终值

        Returns:
            ModelResult
        """
        # 计算各期FCF现值
        pv_fcf_list = []
        for t, fcf in enumerate(fcf_list):
            discount_factor = 1 / (1 + wacc) ** (t + 1)
            pv = fcf * discount_factor
            pv_fcf_list.append({
                "year": t + 1,
                "fcf": fcf,
                "discount_factor": round(discount_factor, 4),
                "present_value": round(pv, 2)
            })

        pv_fcf_total = sum(item["present_value"] for item in pv_fcf_list)

        # 计算终值现值
        n = len(fcf_list)
        pv_terminal = terminal_value / (1 + wacc) ** n

        # 企业价值
        value = pv_fcf_total + pv_terminal

        return ModelResult(
            value=value,
            formula="Σ FCF/(1+WACC)^t + TV/(1+WACC)^n",
            inputs={
                "pv_of_fcf": pv_fcf_total,
                "pv_of_terminal": pv_terminal,
                "terminal_value": terminal_value,
                "wacc": wacc,
                "projection_years": n,
                "fcf_details": pv_fcf_list
            }
        )

    def calc_equity_value(self,
                           enterprise_value: float,
                           debt: float,
                           cash: float,
                           minority_interest: float = 0) -> ModelResult:
        """
        计算股权价值

        公式: Equity = EV - Debt + Cash - Minority Interest

        Args:
            enterprise_value: 企业价值
            debt: 有息负债
            cash: 现金及等价物
            minority_interest: 少数股东权益

        Returns:
            ModelResult
        """
        value = enterprise_value - debt + cash - minority_interest

        return ModelResult(
            value=value,
            formula="EV - Debt + Cash - Minority",
            inputs={
                "enterprise_value": enterprise_value,
                "debt": debt,
                "cash": cash,
                "minority_interest": minority_interest
            }
        )

    def calc_per_share_value(self,
                              equity_value: float,
                              shares_outstanding: float) -> ModelResult:
        """
        计算每股价值

        公式: Per Share Value = Equity Value / Shares Outstanding
        """
        value = equity_value / shares_outstanding

        return ModelResult(
            value=value,
            formula="Equity Value / Shares Outstanding",
            inputs={
                "equity_value": equity_value,
                "shares_outstanding": shares_outstanding
            }
        )

    # ==================== 敏感性分析 ====================

    def sensitivity_analysis(self,
                              fcf_list: List[float],
                              wacc_range: List[float],
                              growth_range: List[float],
                              debt: float,
                              cash: float,
                              shares: float) -> Dict[str, Any]:
        """
        敏感性分析矩阵

        生成 WACC × Terminal Growth 的每股价值矩阵

        Args:
            fcf_list: 各年FCF
            wacc_range: WACC范围 [0.08, 0.09, 0.10, ...]
            growth_range: 永续增长率范围 [0.01, 0.02, ...]
            debt: 负债
            cash: 现金
            shares: 股数

        Returns:
            dict: 敏感性矩阵数据
        """
        matrix = []

        for wacc in wacc_range:
            row = {"wacc": f"{wacc:.1%}"}
            for g in growth_range:
                try:
                    # 终值
                    tv = self.calc_terminal_value_perpetual(fcf_list[-1], wacc, g)
                    # 企业价值
                    ev = self.calc_enterprise_value(fcf_list, wacc, tv.value)
                    # 股权价值
                    eq = self.calc_equity_value(ev.value, debt, cash)
                    # 每股价值
                    per_share = eq.value / shares
                    row[f"g={g:.1%}"] = round(per_share, 2)
                except ValueError:
                    row[f"g={g:.1%}"] = "N/A"

            matrix.append(row)

        return {
            "headers": {
                "rows": "WACC",
                "columns": "Terminal Growth"
            },
            "data": matrix
        }

    # ==================== 主估值方法 ====================

    def valuate(self, inputs: dict) -> dict:
        """
        执行完整DCF估值

        Args:
            inputs: DCF输入参数，包含：
                - fcf_projections: 各年FCF预测
                - wacc_inputs: WACC计算参数
                - terminal_inputs: 终值计算参数
                - balance_sheet_adjustments: 资产负债调整
                - sensitivity_config: 敏感性分析配置（可选）

        Returns:
            dict: 完整估值结果（带追溯）
        """
        # WACC计算
        wacc_inputs = inputs['wacc_inputs']

        re = self.calc_capm(
            wacc_inputs['risk_free_rate'],
            wacc_inputs['beta'],
            wacc_inputs['market_risk_premium']
        )

        wacc = self.calc_wacc(
            re.value,
            wacc_inputs['cost_of_debt'],
            wacc_inputs['tax_rate'],
            wacc_inputs['debt_ratio']
        )

        # FCF列表
        fcf_list = list(inputs['fcf_projections'].values())

        # 终值
        term_inputs = inputs['terminal_inputs']
        if term_inputs.get('method') == 'perpetual_growth':
            tv = self.calc_terminal_value_perpetual(
                fcf_list[-1],
                wacc.value,
                term_inputs['terminal_growth']
            )
        else:
            # 退出倍数法
            tv = self.calc_terminal_value_multiple(
                fcf_list[-1] * 1.2,  # 简化：假设EBITDA约为FCF的1.2倍
                term_inputs.get('exit_multiple', 10)
            )

        # 企业价值
        ev = self.calc_enterprise_value(fcf_list, wacc.value, tv.value)

        # 股权价值
        bs = inputs['balance_sheet_adjustments']
        equity = self.calc_equity_value(ev.value, bs['debt'], bs['cash'])

        # 每股价值
        per_share = self.calc_per_share_value(equity.value, bs['shares_outstanding'])

        # 敏感性分析（可选）
        sens_config = inputs.get('sensitivity_config')
        sensitivity = None
        if sens_config:
            sensitivity = self.sensitivity_analysis(
                fcf_list,
                sens_config['wacc_range'],
                sens_config['growth_range'],
                bs['debt'],
                bs['cash'],
                bs['shares_outstanding']
            )

        return {
            "_meta": {
                "model_name": self.name,
                "method": "DCF - FCFF"
            },
            "cost_of_equity": re.to_dict(),
            "wacc": wacc.to_dict(),
            "terminal_value": tv.to_dict(),
            "enterprise_value": ev.to_dict(),
            "equity_value": equity.to_dict(),
            "per_share_value": per_share.to_dict(),
            "sensitivity_matrix": sensitivity
        }
