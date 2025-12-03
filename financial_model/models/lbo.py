# -*- coding: utf-8 -*-
"""
LBO 模型（杠杆收购）

私募股权基金收购分析工具

本模块提供两种使用方式:

1. 原子工具（推荐LLM使用）:
   from financial_model.tools import calc_purchase_price, calc_sources_uses, ...
   每个工具独立运行，可自由组合

2. LBOModel类（封装接口）:
   lbo = LBOModel()
   result = lbo.build(inputs)
   内部调用原子工具，提供统一接口
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from ..core import ModelResult, FinancialModel
from ..tools import lbo_tools


@dataclass
class DebtTranche:
    """
    单笔债务

    支持:
    - 现金利息
    - PIK利息（加到本金）
    - 强制摊销
    - 现金扫荡还款
    """
    name: str
    initial_amount: float
    interest_rate: float
    amortization_rate: float = 0.0  # 每年强制还本比例
    pik_rate: float = 0.0  # PIK利息率
    term: int = 7  # 期限（年）
    priority: int = 1  # 还款优先级（1最高）

    # 运行时状态
    balance: float = field(init=False)

    def __post_init__(self):
        self.balance = self.initial_amount

    def reset(self):
        """重置余额"""
        self.balance = self.initial_amount

    def calc_period(self, cash_sweep: float = 0) -> Dict[str, float]:
        """
        计算一期的还本付息

        Args:
            cash_sweep: 现金扫荡还款金额

        Returns:
            dict: 包含期初余额、利息、还本、期末余额
        """
        opening = self.balance

        # 现金利息
        cash_interest = opening * self.interest_rate

        # PIK利息（加到本金，不付现金）
        pik_interest = opening * self.pik_rate

        # 强制还本（基于初始金额）
        mandatory_amort = self.initial_amount * self.amortization_rate

        # 实际可还本金
        available_principal = opening + pik_interest
        actual_amort = min(mandatory_amort, available_principal)
        actual_sweep = min(cash_sweep, available_principal - actual_amort)

        # 期末余额
        closing = opening + pik_interest - actual_amort - actual_sweep
        self.balance = max(closing, 0)

        return {
            "opening_balance": opening,
            "cash_interest": cash_interest,
            "pik_interest": pik_interest,
            "mandatory_amort": actual_amort,
            "cash_sweep": actual_sweep,
            "total_principal_payment": actual_amort + actual_sweep,
            "closing_balance": self.balance
        }


class LBOModel(FinancialModel):
    """
    LBO估值工具集

    使用方法:
        lbo = LBOModel()
        result = lbo.build(inputs)
    """

    def __init__(self, name: str = "LBO模型"):
        super().__init__(name=name, scenario="lbo_analysis")
        self.debt_tranches: List[DebtTranche] = []

    # ==================== 交易结构计算 ====================

    def calc_purchase_price(self,
                            ebitda: float,
                            entry_multiple: float) -> ModelResult:
        """
        计算收购价格

        公式: Purchase Price = EBITDA × Entry Multiple

        Args:
            ebitda: 入场EBITDA
            entry_multiple: 入场倍数

        Returns:
            ModelResult
        """
        value = ebitda * entry_multiple

        return ModelResult(
            value=value,
            formula="EBITDA × Entry Multiple",
            inputs={
                "ebitda": ebitda,
                "entry_multiple": entry_multiple
            }
        )

    def calc_sources_uses(self,
                          purchase_price: float,
                          transaction_fee_rate: float,
                          financing_fee_rate: float,
                          debt_amounts: Dict[str, float],
                          existing_cash: float = 0) -> ModelResult:
        """
        计算资金来源与用途

        Args:
            purchase_price: 收购价格
            transaction_fee_rate: 交易费用率
            financing_fee_rate: 融资费用率
            debt_amounts: 各笔债务金额 {"senior": 1000, "sub": 500}
            existing_cash: 目标公司可用现金

        Returns:
            ModelResult
        """
        # 用途
        transaction_fees = purchase_price * transaction_fee_rate
        financing_fees = sum(debt_amounts.values()) * financing_fee_rate
        total_uses = purchase_price + transaction_fees + financing_fees

        # 来源
        total_debt = sum(debt_amounts.values())
        equity_required = total_uses - total_debt - existing_cash

        sources = {
            **{f"debt_{k}": v for k, v in debt_amounts.items()},
            "total_debt": total_debt,
            "existing_cash": existing_cash,
            "equity": equity_required,
            "total_sources": total_uses
        }

        uses = {
            "purchase_price": purchase_price,
            "transaction_fees": transaction_fees,
            "financing_fees": financing_fees,
            "total_uses": total_uses
        }

        return ModelResult(
            value=equity_required,
            formula="Total Uses - Total Debt - Existing Cash",
            inputs={
                "sources": sources,
                "uses": uses
            }
        )

    # ==================== 运营预测 ====================

    def project_operations(self,
                           base_revenue: float,
                           revenue_growth_rates: List[float],
                           ebitda_margins: List[float],
                           capex_percent: float,
                           nwc_percent: float,
                           tax_rate: float,
                           da_percent: float = 0.03) -> List[Dict[str, float]]:
        """
        预测运营数据

        Args:
            base_revenue: 基期收入
            revenue_growth_rates: 各年收入增长率
            ebitda_margins: 各年EBITDA利润率
            capex_percent: 资本支出占收入比例
            nwc_percent: 营运资本占收入比例
            tax_rate: 税率
            da_percent: 折旧摊销占收入比例

        Returns:
            List[dict]: 各年运营数据
        """
        projections = []
        revenue = base_revenue
        last_nwc = base_revenue * nwc_percent

        for i, (growth, margin) in enumerate(zip(revenue_growth_rates, ebitda_margins)):
            revenue = revenue * (1 + growth)
            ebitda = revenue * margin
            da = revenue * da_percent
            ebit = ebitda - da
            capex = revenue * capex_percent
            nwc = revenue * nwc_percent
            delta_nwc = nwc - last_nwc
            last_nwc = nwc

            # 自由现金流（税前，利息前）
            # UFCF = EBITDA - Capex - ΔNWC
            ufcf = ebitda - capex - delta_nwc

            projections.append({
                "year": i + 1,
                "revenue": revenue,
                "ebitda": ebitda,
                "depreciation": da,
                "ebit": ebit,
                "capex": capex,
                "nwc": nwc,
                "delta_nwc": delta_nwc,
                "ufcf": ufcf,  # Unlevered FCF
                "tax_rate": tax_rate
            })

        return projections

    # ==================== 债务计划 ====================

    def add_debt_tranche(self, tranche: DebtTranche):
        """添加债务层级"""
        self.debt_tranches.append(tranche)
        # 按优先级排序
        self.debt_tranches.sort(key=lambda x: x.priority)

    def clear_debt_tranches(self):
        """清空债务层级"""
        self.debt_tranches = []

    def build_debt_schedule(self,
                            operations: List[Dict[str, float]],
                            sweep_percent: float = 0.75,
                            min_cash: float = 0) -> Dict[str, Any]:
        """
        构建债务计划表

        Args:
            operations: 运营预测数据
            sweep_percent: 现金扫荡比例（多余现金用于还债）
            min_cash: 最低现金保留

        Returns:
            dict: 完整债务计划表
        """
        # 重置所有债务余额
        for tranche in self.debt_tranches:
            tranche.reset()

        schedule = {tranche.name: [] for tranche in self.debt_tranches}
        annual_summary = []

        for ops in operations:
            year = ops["year"]
            ufcf = ops["ufcf"]
            ebit = ops["ebit"]
            tax_rate = ops["tax_rate"]

            # 第一轮：计算利息（不还本）
            total_interest = 0
            for tranche in self.debt_tranches:
                interest = tranche.balance * tranche.interest_rate
                total_interest += interest

            # 计算税后现金流
            ebt = ebit - total_interest
            taxes = max(ebt * tax_rate, 0)  # 亏损不退税（简化）
            net_income = ebt - taxes

            # 可用于还债的现金 = UFCF - 利息 - 税
            # 注意：UFCF已经是EBITDA - Capex - ΔNWC
            # 还需要减去利息和税
            cash_for_debt = ufcf - total_interest - taxes

            # 强制还本
            total_mandatory = 0
            for tranche in self.debt_tranches:
                mandatory = tranche.initial_amount * tranche.amortization_rate
                total_mandatory += min(mandatory, tranche.balance)

            # 现金扫荡金额
            excess_cash = max(cash_for_debt - total_mandatory - min_cash, 0)
            sweep_amount = excess_cash * sweep_percent

            # 第二轮：按优先级还款
            remaining_sweep = sweep_amount
            year_details = {
                "year": year,
                "ufcf": ufcf,
                "total_interest": total_interest,
                "taxes": taxes,
                "net_income": net_income,
                "cash_for_debt": cash_for_debt,
                "mandatory_amort": 0,
                "cash_sweep": 0,
                "total_debt_paydown": 0,
                "ending_debt": 0
            }

            for tranche in self.debt_tranches:
                # 分配现金扫荡（按优先级）
                tranche_sweep = min(remaining_sweep, max(tranche.balance - tranche.initial_amount * tranche.amortization_rate, 0))

                period = tranche.calc_period(cash_sweep=tranche_sweep)
                schedule[tranche.name].append({
                    "year": year,
                    **period
                })

                remaining_sweep -= period["cash_sweep"]
                year_details["mandatory_amort"] += period["mandatory_amort"]
                year_details["cash_sweep"] += period["cash_sweep"]
                year_details["total_debt_paydown"] += period["total_principal_payment"]
                year_details["ending_debt"] += period["closing_balance"]

            # 自由现金流（扣除还本）
            year_details["fcf_to_equity"] = cash_for_debt - year_details["total_debt_paydown"]

            annual_summary.append(year_details)

        return {
            "tranches": schedule,
            "annual_summary": annual_summary,
            "final_debt": sum(t.balance for t in self.debt_tranches)
        }

    # ==================== 退出与回报 ====================

    def calc_exit_value(self,
                        exit_ebitda: float,
                        exit_multiple: float) -> ModelResult:
        """
        计算退出价值

        公式: Exit Value = Exit EBITDA × Exit Multiple

        Args:
            exit_ebitda: 退出时EBITDA
            exit_multiple: 退出倍数

        Returns:
            ModelResult
        """
        value = exit_ebitda * exit_multiple

        return ModelResult(
            value=value,
            formula="Exit EBITDA × Exit Multiple",
            inputs={
                "exit_ebitda": exit_ebitda,
                "exit_multiple": exit_multiple
            }
        )

    def calc_equity_proceeds(self,
                             exit_value: float,
                             ending_debt: float,
                             ending_cash: float = 0) -> ModelResult:
        """
        计算股权所得

        公式: Equity Proceeds = Exit Value - Net Debt

        Args:
            exit_value: 退出价值
            ending_debt: 退出时剩余债务
            ending_cash: 退出时现金

        Returns:
            ModelResult
        """
        net_debt = ending_debt - ending_cash
        value = exit_value - net_debt

        return ModelResult(
            value=value,
            formula="Exit Value - Net Debt",
            inputs={
                "exit_value": exit_value,
                "ending_debt": ending_debt,
                "ending_cash": ending_cash,
                "net_debt": net_debt
            }
        )

    def calc_irr(self, cash_flows: List[float]) -> ModelResult:
        """
        计算内部收益率 (IRR)

        Args:
            cash_flows: 现金流序列 [-投入, cf1, cf2, ..., 退出所得]

        Returns:
            ModelResult
        """
        # 牛顿迭代法求IRR
        def npv(rate: float, cfs: List[float]) -> float:
            return sum(cf / (1 + rate) ** t for t, cf in enumerate(cfs))

        def npv_derivative(rate: float, cfs: List[float]) -> float:
            return sum(-t * cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cfs))

        # 初始猜测
        irr = 0.10
        for _ in range(100):
            npv_val = npv(irr, cash_flows)
            npv_deriv = npv_derivative(irr, cash_flows)

            if abs(npv_deriv) < 1e-10:
                break

            irr_new = irr - npv_val / npv_deriv

            if abs(irr_new - irr) < 1e-8:
                irr = irr_new
                break

            irr = irr_new

        return ModelResult(
            value=irr,
            formula="IRR(Cash Flows)",
            inputs={
                "cash_flows": cash_flows,
                "years": len(cash_flows) - 1
            }
        )

    def calc_moic(self,
                  equity_invested: float,
                  equity_proceeds: float,
                  interim_distributions: float = 0) -> ModelResult:
        """
        计算投资倍数 (MOIC - Multiple on Invested Capital)

        公式: MOIC = (退出所得 + 期间分红) / 投入资金

        Args:
            equity_invested: 股权投入
            equity_proceeds: 退出所得
            interim_distributions: 期间分红

        Returns:
            ModelResult
        """
        total_return = equity_proceeds + interim_distributions
        value = total_return / equity_invested

        return ModelResult(
            value=value,
            formula="(Exit Proceeds + Distributions) / Equity Invested",
            inputs={
                "equity_invested": equity_invested,
                "equity_proceeds": equity_proceeds,
                "interim_distributions": interim_distributions,
                "total_return": total_return
            }
        )

    # ==================== 敏感性分析 ====================

    def sensitivity_entry_exit(self,
                               base_inputs: dict,
                               entry_range: List[float],
                               exit_range: List[float]) -> Dict[str, Any]:
        """
        入场/退出倍数敏感性分析

        Args:
            base_inputs: 基础输入参数
            entry_range: 入场倍数范围 [7.0, 7.5, 8.0, ...]
            exit_range: 退出倍数范围

        Returns:
            dict: IRR和MOIC敏感性矩阵
        """
        irr_matrix = []
        moic_matrix = []

        for entry in entry_range:
            irr_row = {"entry_multiple": f"{entry:.1f}x"}
            moic_row = {"entry_multiple": f"{entry:.1f}x"}

            for exit_mult in exit_range:
                # 修改倍数
                inputs = base_inputs.copy()
                inputs["entry_multiple"] = entry
                inputs["exit_multiple"] = exit_mult

                # 计算
                result = self.build(inputs)
                irr = result["returns"]["irr"]["value"]
                moic = result["returns"]["moic"]["value"]

                irr_row[f"exit_{exit_mult:.1f}x"] = f"{irr:.1%}"
                moic_row[f"exit_{exit_mult:.1f}x"] = f"{moic:.2f}x"

            irr_matrix.append(irr_row)
            moic_matrix.append(moic_row)

        return {
            "irr_sensitivity": {
                "headers": {"rows": "Entry Multiple", "columns": "Exit Multiple"},
                "data": irr_matrix
            },
            "moic_sensitivity": {
                "headers": {"rows": "Entry Multiple", "columns": "Exit Multiple"},
                "data": moic_matrix
            }
        }

    # ==================== 主构建方法 ====================

    def build(self, inputs: dict) -> Dict[str, Any]:
        """
        构建完整LBO模型

        内部调用原子工具实现，保持接口兼容。

        Args:
            inputs: LBO输入参数，包含：
                - entry_ebitda: 入场EBITDA
                - entry_multiple: 入场倍数
                - exit_multiple: 退出倍数
                - holding_period: 持有期
                - revenue_growth: 各年收入增长率
                - ebitda_margin: 各年EBITDA利润率
                - capex_percent: 资本支出率
                - nwc_percent: 营运资本率
                - tax_rate: 税率
                - transaction_fee_rate: 交易费用率
                - financing_fee_rate: 融资费用率
                - debt_structure: 债务结构
                - sweep_percent: 现金扫荡比例

        Returns:
            dict: 完整LBO分析结果
        """
        # 使用原子工具快捷构建
        result = lbo_tools.lbo_quick_build(inputs)

        # 转换为与旧接口兼容的格式
        result["_meta"]["model_name"] = self.name

        # 同步内部状态（保持兼容）
        self.clear_debt_tranches()
        for name, config in inputs["debt_structure"].items():
            purchase_price = result["transaction"]["purchase_price"]["value"]
            amount = purchase_price * config["amount_percent"]
            tranche = DebtTranche(
                name=name,
                initial_amount=amount,
                interest_rate=config["interest_rate"],
                amortization_rate=config.get("amortization_rate", 0),
                pik_rate=config.get("pik_rate", 0),
                term=config.get("term", 7),
                priority=config.get("priority", 1)
            )
            self.add_debt_tranche(tranche)

        # 转换 ModelResult 格式
        def to_model_result_dict(d: dict) -> dict:
            """转换为 ModelResult.to_dict() 格式"""
            return {
                "value": d.get("value"),
                "formula": d.get("formula"),
                "inputs": d.get("inputs", {})
            }

        # 转换各个结果
        result["transaction"]["purchase_price"] = to_model_result_dict(
            result["transaction"]["purchase_price"]
        )
        result["transaction"]["sources_uses"] = {
            "value": result["transaction"]["sources_uses"]["equity_required"],
            "formula": result["transaction"]["sources_uses"]["formula"],
            "inputs": {
                "sources": result["transaction"]["sources_uses"]["sources"],
                "uses": result["transaction"]["sources_uses"]["uses"]
            }
        }
        result["exit_analysis"]["exit_value"] = to_model_result_dict(
            result["exit_analysis"]["exit_value"]
        )
        result["exit_analysis"]["equity_proceeds"] = to_model_result_dict(
            result["exit_analysis"]["equity_proceeds"]
        )
        result["returns"]["irr"] = to_model_result_dict(result["returns"]["irr"])
        result["returns"]["moic"] = to_model_result_dict(result["returns"]["moic"])

        # operating_model 保持原子工具的格式 {"projections": [...], "summary": {...}}

        return result
