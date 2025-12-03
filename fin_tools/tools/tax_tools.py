# -*- coding: utf-8 -*-
"""
tax_tools.py - 税务筹划原子工具

提供增值税、企业所得税、个人所得税计算及优化功能。
基于中国现行税法（2024年）。
设计为无状态的原子函数，供 LLM 灵活调用组合。
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass


# ============================================================
# 增值税计算
# ============================================================

# 增值税税率
VAT_RATES = {
    "general": 0.13,      # 一般货物
    "low": 0.09,          # 农产品、交通运输等
    "service": 0.06,      # 现代服务业
    "zero": 0.0,          # 出口零税率
    "exempt": None,       # 免税
    "small_scale": 0.03,  # 小规模纳税人
}


def vat_calc(
    sales: List[Dict[str, Any]],
    purchases: List[Dict[str, Any]],
    taxpayer_type: str = "general"
) -> Dict[str, Any]:
    """
    增值税计算

    Args:
        sales: 销售明细
            [{"amount": 含税金额, "rate": 税率(0.13/0.09/0.06), "description": "描述"}, ...]
        purchases: 采购明细（可抵扣进项）
            [{"amount": 含税金额, "rate": 税率, "description": "描述"}, ...]
        taxpayer_type: 纳税人类型 "general"(一般纳税人) / "small_scale"(小规模)

    Returns:
        {
            "output_tax": 销项税额,
            "input_tax": 进项税额,
            "tax_payable": 应纳税额,
            "tax_burden_rate": 税负率,
            "details": {
                "sales_breakdown": [...],
                "purchase_breakdown": [...]
            }
        }

    Example:
        >>> vat_calc(
        ...     sales=[{"amount": 113000, "rate": 0.13}],
        ...     purchases=[{"amount": 56500, "rate": 0.13}]
        ... )
    """
    # 销项税计算
    sales_breakdown = []
    total_output_tax = 0
    total_sales_ex_tax = 0

    for item in sales:
        amount = item.get("amount", 0)
        rate = item.get("rate", 0.13)
        description = item.get("description", "销售")

        if taxpayer_type == "small_scale":
            rate = 0.03

        # 含税金额换算不含税
        amount_ex_tax = amount / (1 + rate) if rate else amount
        tax = amount_ex_tax * rate if rate else 0

        sales_breakdown.append({
            "description": description,
            "amount_inc_tax": amount,
            "amount_ex_tax": round(amount_ex_tax, 2),
            "rate": rate,
            "tax": round(tax, 2)
        })

        total_output_tax += tax
        total_sales_ex_tax += amount_ex_tax

    # 进项税计算（小规模不能抵扣）
    purchase_breakdown = []
    total_input_tax = 0
    total_purchase_ex_tax = 0

    if taxpayer_type == "general":
        for item in purchases:
            amount = item.get("amount", 0)
            rate = item.get("rate", 0.13)
            description = item.get("description", "采购")
            deductible = item.get("deductible", True)

            amount_ex_tax = amount / (1 + rate) if rate else amount
            tax = amount_ex_tax * rate if rate and deductible else 0

            purchase_breakdown.append({
                "description": description,
                "amount_inc_tax": amount,
                "amount_ex_tax": round(amount_ex_tax, 2),
                "rate": rate,
                "tax": round(tax, 2),
                "deductible": deductible
            })

            if deductible:
                total_input_tax += tax
            total_purchase_ex_tax += amount_ex_tax

    # 应纳税额
    tax_payable = max(0, total_output_tax - total_input_tax)

    # 税负率
    tax_burden_rate = tax_payable / total_sales_ex_tax if total_sales_ex_tax > 0 else 0

    return {
        "output_tax": round(total_output_tax, 2),
        "input_tax": round(total_input_tax, 2),
        "tax_payable": round(tax_payable, 2),
        "tax_burden_rate": round(tax_burden_rate, 4),
        "taxpayer_type": taxpayer_type,
        "total_sales_ex_tax": round(total_sales_ex_tax, 2),
        "total_purchase_ex_tax": round(total_purchase_ex_tax, 2),
        "details": {
            "sales_breakdown": sales_breakdown,
            "purchase_breakdown": purchase_breakdown
        }
    }


# ============================================================
# 企业所得税计算
# ============================================================

# 企业所得税税率
CIT_RATES = {
    "standard": 0.25,          # 标准税率
    "high_tech": 0.15,         # 高新技术企业
    "small_low_profit": 0.05,  # 小型微利企业实际税负（2024年政策）
    "western": 0.15,           # 西部大开发
}


def cit_calc(
    accounting_profit: float,
    adjustments: Optional[Dict[str, float]] = None,
    preference: str = "standard",
    prior_year_loss: float = 0
) -> Dict[str, Any]:
    """
    企业所得税计算

    Args:
        accounting_profit: 会计利润
        adjustments: 纳税调整项
            {
                "add": {"业务招待费超支": 10000, ...},  # 调增
                "subtract": {"研发加计扣除": 50000, ...}  # 调减
            }
        preference: 优惠政策
            - "standard": 标准25%
            - "high_tech": 高新技术15%
            - "small_low_profit": 小型微利企业
            - "western": 西部大开发15%
        prior_year_loss: 以前年度亏损结转

    Returns:
        {
            "accounting_profit": 会计利润,
            "taxable_income": 应纳税所得额,
            "tax_rate": 适用税率,
            "tax_payable": 应纳税额,
            "effective_rate": 实际税负率,
            "adjustments_detail": 调整明细
        }

    Example:
        >>> cit_calc(
        ...     accounting_profit=1000000,
        ...     adjustments={"add": {"招待费": 20000}, "subtract": {"研发加计": 100000}},
        ...     preference="high_tech"
        ... )
    """
    adjustments = adjustments or {"add": {}, "subtract": {}}

    # 纳税调整
    add_total = sum(adjustments.get("add", {}).values())
    subtract_total = sum(adjustments.get("subtract", {}).values())

    # 应纳税所得额
    taxable_income = accounting_profit + add_total - subtract_total - prior_year_loss
    taxable_income = max(0, taxable_income)

    # 确定税率
    if preference == "small_low_profit":
        # 小型微利企业分段计算（2024年政策）
        if taxable_income <= 3000000:
            # 300万以下：实际税负5%
            tax_rate = 0.05
            tax_payable = taxable_income * 0.05
        else:
            # 超过300万不适用小微优惠
            tax_rate = 0.25
            tax_payable = taxable_income * 0.25
    elif preference == "high_tech":
        tax_rate = 0.15
        tax_payable = taxable_income * tax_rate
    elif preference == "western":
        tax_rate = 0.15
        tax_payable = taxable_income * tax_rate
    else:
        tax_rate = 0.25
        tax_payable = taxable_income * tax_rate

    # 实际税负率
    effective_rate = tax_payable / accounting_profit if accounting_profit > 0 else 0

    return {
        "accounting_profit": accounting_profit,
        "adjustments": {
            "add_items": adjustments.get("add", {}),
            "add_total": add_total,
            "subtract_items": adjustments.get("subtract", {}),
            "subtract_total": subtract_total
        },
        "prior_year_loss": prior_year_loss,
        "taxable_income": round(taxable_income, 2),
        "preference": preference,
        "tax_rate": tax_rate,
        "tax_payable": round(tax_payable, 2),
        "effective_rate": round(effective_rate, 4)
    }


# ============================================================
# 个人所得税计算
# ============================================================

# 综合所得税率表（年度）
IIT_BRACKETS = [
    (36000, 0.03, 0),
    (144000, 0.10, 2520),
    (300000, 0.20, 16920),
    (420000, 0.25, 31920),
    (660000, 0.30, 52920),
    (960000, 0.35, 85920),
    (float('inf'), 0.45, 181920)
]

# 年终奖单独计税税率表
BONUS_BRACKETS = [
    (36000, 0.03, 0),
    (144000, 0.10, 210),
    (300000, 0.20, 1410),
    (420000, 0.25, 2660),
    (660000, 0.30, 4410),
    (960000, 0.35, 7160),
    (float('inf'), 0.45, 15160)
]


def iit_calc(
    annual_salary: float,
    social_insurance: float = 0,
    housing_fund: float = 0,
    special_deductions: float = 0,
    other_deductions: float = 0
) -> Dict[str, Any]:
    """
    个人所得税计算（综合所得年度）

    Args:
        annual_salary: 年工资薪金收入
        social_insurance: 年社保个人缴纳部分
        housing_fund: 年住房公积金个人缴纳部分
        special_deductions: 年专项附加扣除（子女教育、房贷等）
        other_deductions: 其他扣除

    Returns:
        {
            "gross_income": 年收入,
            "deductions": 各项扣除,
            "taxable_income": 应纳税所得额,
            "tax_rate": 适用税率,
            "quick_deduction": 速算扣除数,
            "tax_payable": 应纳税额,
            "net_income": 税后收入,
            "effective_rate": 实际税率
        }

    Example:
        >>> iit_calc(
        ...     annual_salary=300000,
        ...     social_insurance=12000,
        ...     housing_fund=12000,
        ...     special_deductions=24000
        ... )
    """
    # 基本扣除（每年6万）
    basic_deduction = 60000

    # 总扣除
    total_deductions = basic_deduction + social_insurance + housing_fund + special_deductions + other_deductions

    # 应纳税所得额
    taxable_income = max(0, annual_salary - total_deductions)

    # 查找适用税率
    tax_rate = 0
    quick_deduction = 0
    for bracket, rate, qd in IIT_BRACKETS:
        if taxable_income <= bracket:
            tax_rate = rate
            quick_deduction = qd
            break

    # 计算税额
    tax_payable = taxable_income * tax_rate - quick_deduction
    tax_payable = max(0, tax_payable)

    # 税后收入
    net_income = annual_salary - social_insurance - housing_fund - tax_payable

    # 实际税率
    effective_rate = tax_payable / annual_salary if annual_salary > 0 else 0

    return {
        "gross_income": annual_salary,
        "deductions": {
            "basic": basic_deduction,
            "social_insurance": social_insurance,
            "housing_fund": housing_fund,
            "special": special_deductions,
            "other": other_deductions,
            "total": total_deductions
        },
        "taxable_income": round(taxable_income, 2),
        "tax_rate": tax_rate,
        "quick_deduction": quick_deduction,
        "tax_payable": round(tax_payable, 2),
        "net_income": round(net_income, 2),
        "effective_rate": round(effective_rate, 4)
    }


# ============================================================
# 年终奖优化
# ============================================================

def bonus_optimize(
    annual_salary: float,
    total_bonus: float,
    social_insurance: float = 0,
    housing_fund: float = 0,
    special_deductions: float = 0
) -> Dict[str, Any]:
    """
    年终奖最优拆分

    计算年终奖与工资的最优拆分方案，最小化总税负。
    年终奖可选择单独计税或并入综合所得。

    Args:
        annual_salary: 年工资薪金（不含年终奖）
        total_bonus: 年终奖总额
        social_insurance: 年社保
        housing_fund: 年公积金
        special_deductions: 年专项附加扣除

    Returns:
        {
            "scenarios": [
                {"method": "全部单独计税", "salary_tax": x, "bonus_tax": y, "total_tax": z},
                {"method": "全部并入综合", "salary_tax": x, "bonus_tax": 0, "total_tax": z},
                {"method": "最优拆分", "bonus_separate": a, "bonus_combined": b, ...}
            ],
            "recommendation": 推荐方案,
            "optimal": {最优方案详情},
            "tax_saved": 节税金额
        }

    Example:
        >>> bonus_optimize(
        ...     annual_salary=200000,
        ...     total_bonus=100000,
        ...     special_deductions=24000
        ... )
    """
    scenarios = []

    # 方案1：年终奖全部单独计税
    salary_result = iit_calc(annual_salary, social_insurance, housing_fund, special_deductions)
    bonus_tax_separate = _calc_bonus_tax_separate(total_bonus)

    scenario1 = {
        "method": "年终奖单独计税",
        "salary_tax": salary_result["tax_payable"],
        "bonus_tax": bonus_tax_separate,
        "total_tax": salary_result["tax_payable"] + bonus_tax_separate
    }
    scenarios.append(scenario1)

    # 方案2：年终奖全部并入综合所得
    combined_result = iit_calc(
        annual_salary + total_bonus,
        social_insurance, housing_fund, special_deductions
    )

    scenario2 = {
        "method": "年终奖并入综合所得",
        "salary_tax": combined_result["tax_payable"],
        "bonus_tax": 0,
        "total_tax": combined_result["tax_payable"]
    }
    scenarios.append(scenario2)

    # 方案3：寻找最优拆分点
    # 年终奖单独计税的临界点：36000, 144000, 300000, 420000, 660000, 960000
    critical_points = [0, 36000, 144000, 300000, 420000, 660000, 960000]

    best_split = None
    min_total_tax = min(scenario1["total_tax"], scenario2["total_tax"])

    for bonus_separate in critical_points:
        if bonus_separate > total_bonus:
            break

        bonus_combined = total_bonus - bonus_separate

        # 工资+并入部分的税
        salary_tax = iit_calc(
            annual_salary + bonus_combined,
            social_insurance, housing_fund, special_deductions
        )["tax_payable"]

        # 单独计税部分的税
        bonus_tax = _calc_bonus_tax_separate(bonus_separate) if bonus_separate > 0 else 0

        total_tax = salary_tax + bonus_tax

        if total_tax < min_total_tax:
            min_total_tax = total_tax
            best_split = {
                "method": "最优拆分",
                "bonus_separate": bonus_separate,
                "bonus_combined": bonus_combined,
                "salary_tax": salary_tax,
                "bonus_tax": bonus_tax,
                "total_tax": total_tax
            }

    if best_split:
        scenarios.append(best_split)

    # 找出最优方案
    optimal = min(scenarios, key=lambda x: x["total_tax"])
    worst_tax = max(s["total_tax"] for s in scenarios)
    tax_saved = worst_tax - optimal["total_tax"]

    return {
        "scenarios": scenarios,
        "optimal": optimal,
        "recommendation": optimal["method"],
        "tax_saved": round(tax_saved, 2),
        "inputs": {
            "annual_salary": annual_salary,
            "total_bonus": total_bonus,
            "social_insurance": social_insurance,
            "housing_fund": housing_fund,
            "special_deductions": special_deductions
        }
    }


def _calc_bonus_tax_separate(bonus: float) -> float:
    """计算年终奖单独计税的税额"""
    if bonus <= 0:
        return 0

    # 年终奖单独计税：除以12找税率
    monthly = bonus / 12

    for bracket, rate, qd in BONUS_BRACKETS:
        if bonus <= bracket:
            tax = bonus * rate - qd
            return round(max(0, tax), 2)

    # 超过最高档
    return round(bonus * 0.45 - 15160, 2)


# ============================================================
# 研发加计扣除
# ============================================================

def rd_deduction(
    rd_expenses: Dict[str, float],
    deduction_rate: float = 1.0,
    industry: str = "manufacturing"
) -> Dict[str, Any]:
    """
    研发加计扣除计算

    Args:
        rd_expenses: 研发费用明细
            {
                "personnel": 人员人工费用,
                "materials": 直接投入费用,
                "depreciation": 折旧费用,
                "amortization": 无形资产摊销,
                "design": 新产品设计费,
                "equipment": 装备调试费,
                "other": 其他费用
            }
        deduction_rate: 加计扣除比例（制造业100%，其他行业100%）
        industry: 行业 "manufacturing"(制造业) / "other"(其他)

    Returns:
        {
            "total_rd_expense": 研发费用合计,
            "eligible_expense": 可加计金额,
            "deduction_rate": 加计比例,
            "additional_deduction": 加计扣除额,
            "tax_saving": 节税金额（按25%税率）,
            "breakdown": 费用明细
        }

    Example:
        >>> rd_deduction(
        ...     rd_expenses={"personnel": 500000, "materials": 200000, "depreciation": 100000},
        ...     industry="manufacturing"
        ... )
    """
    # 2023年起：制造业和其他行业都是100%加计扣除
    if industry == "manufacturing":
        deduction_rate = 1.0
    else:
        deduction_rate = 1.0

    # 计算各项费用
    breakdown = {}
    total_expense = 0

    for category, amount in rd_expenses.items():
        breakdown[category] = amount
        total_expense += amount

    # "其他费用"有限额（不超过可加计金额的10%）
    other_expense = rd_expenses.get("other", 0)
    other_categories = total_expense - other_expense
    other_limit = other_categories * 0.1 / 0.9  # 其他费用限额

    if other_expense > other_limit:
        eligible_other = other_limit
        breakdown["other_limited"] = other_expense - other_limit
    else:
        eligible_other = other_expense

    eligible_expense = other_categories + eligible_other

    # 加计扣除额
    additional_deduction = eligible_expense * deduction_rate

    # 节税金额（按25%企业所得税率）
    tax_saving = additional_deduction * 0.25

    return {
        "total_rd_expense": round(total_expense, 2),
        "eligible_expense": round(eligible_expense, 2),
        "deduction_rate": deduction_rate,
        "additional_deduction": round(additional_deduction, 2),
        "tax_saving_25": round(tax_saving, 2),
        "tax_saving_15": round(additional_deduction * 0.15, 2),  # 高新技术企业
        "industry": industry,
        "breakdown": breakdown
    }


# ============================================================
# 综合税负分析
# ============================================================

def tax_burden(
    revenue: float,
    vat_payable: float,
    cit_payable: float,
    other_taxes: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    综合税负分析

    Args:
        revenue: 营业收入
        vat_payable: 增值税
        cit_payable: 企业所得税
        other_taxes: 其他税费
            {
                "stamp_tax": 印花税,
                "urban_maintenance": 城建税,
                "education_surcharge": 教育费附加,
                "property_tax": 房产税,
                "land_use_tax": 土地使用税
            }

    Returns:
        {
            "total_tax": 税费总额,
            "burden_rate": 综合税负率,
            "breakdown": 各税种构成,
            "vat_burden_rate": 增值税税负率,
            "cit_burden_rate": 所得税税负率,
            "analysis": 分析结论
        }

    Example:
        >>> tax_burden(
        ...     revenue=10000000,
        ...     vat_payable=300000,
        ...     cit_payable=200000,
        ...     other_taxes={"urban_maintenance": 21000, "education_surcharge": 15000}
        ... )
    """
    other_taxes = other_taxes or {}

    # 附加税（基于增值税）
    urban_maintenance = other_taxes.get("urban_maintenance", vat_payable * 0.07)
    education_surcharge = other_taxes.get("education_surcharge", vat_payable * 0.03)
    local_education = other_taxes.get("local_education", vat_payable * 0.02)

    # 其他税费
    stamp_tax = other_taxes.get("stamp_tax", 0)
    property_tax = other_taxes.get("property_tax", 0)
    land_use_tax = other_taxes.get("land_use_tax", 0)
    other_amount = other_taxes.get("other", 0)

    # 税费汇总
    breakdown = {
        "增值税": vat_payable,
        "企业所得税": cit_payable,
        "城建税": urban_maintenance,
        "教育费附加": education_surcharge,
        "地方教育附加": local_education,
        "印花税": stamp_tax,
        "房产税": property_tax,
        "土地使用税": land_use_tax,
        "其他": other_amount
    }

    total_tax = sum(breakdown.values())

    # 税负率
    burden_rate = total_tax / revenue if revenue > 0 else 0
    vat_burden_rate = vat_payable / revenue if revenue > 0 else 0
    cit_burden_rate = cit_payable / revenue if revenue > 0 else 0

    # 分析
    if burden_rate < 0.03:
        analysis = "税负较轻，注意合规风险"
    elif burden_rate < 0.05:
        analysis = "税负正常，处于合理区间"
    elif burden_rate < 0.08:
        analysis = "税负偏高，可考虑税务筹划"
    else:
        analysis = "税负较重，建议全面审视税务策略"

    return {
        "revenue": revenue,
        "total_tax": round(total_tax, 2),
        "burden_rate": round(burden_rate, 4),
        "vat_burden_rate": round(vat_burden_rate, 4),
        "cit_burden_rate": round(cit_burden_rate, 4),
        "breakdown": {k: round(v, 2) for k, v in breakdown.items() if v > 0},
        "composition": {
            k: round(v / total_tax, 4) if total_tax > 0 else 0
            for k, v in breakdown.items() if v > 0
        },
        "analysis": analysis
    }


# ============================================================
# 工具注册（供 LLM 发现）
# ============================================================

TAX_TOOLS = {
    "vat_calc": {
        "function": vat_calc,
        "description": "增值税计算，支持一般纳税人和小规模",
        "parameters": ["sales", "purchases", "taxpayer_type"]
    },
    "cit_calc": {
        "function": cit_calc,
        "description": "企业所得税计算，支持各种优惠政策",
        "parameters": ["accounting_profit", "adjustments", "preference", "prior_year_loss"]
    },
    "iit_calc": {
        "function": iit_calc,
        "description": "个人所得税计算（综合所得）",
        "parameters": ["annual_salary", "social_insurance", "housing_fund", "special_deductions"]
    },
    "bonus_optimize": {
        "function": bonus_optimize,
        "description": "年终奖最优拆分，最小化总税负",
        "parameters": ["annual_salary", "total_bonus", "social_insurance", "housing_fund", "special_deductions"]
    },
    "rd_deduction": {
        "function": rd_deduction,
        "description": "研发加计扣除计算",
        "parameters": ["rd_expenses", "deduction_rate", "industry"]
    },
    "tax_burden": {
        "function": tax_burden,
        "description": "综合税负分析",
        "parameters": ["revenue", "vat_payable", "cit_payable", "other_taxes"]
    }
}
