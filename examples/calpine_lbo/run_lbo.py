#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apollo-Calpine LBO 测试案例

测试fm LBO工具的完整流程：
1. 读取财务数据和交易假设
2. 计算LBO回报
3. 输出5×5 IRR/MOIC敏感性报表
"""

import json
import sys
sys.path.insert(0, '/home/wangbo/document/balance')

from financial_model.tools import lbo_quick_build


def load_case():
    """加载测试案例"""
    with open('/home/wangbo/document/balance/examples/calpine_lbo/test_case.json') as f:
        return json.load(f)


def build_lbo_input(case):
    """将案例数据转换为LBO工具输入格式"""
    income = case["income_statement"]
    txn = case["transaction_assumptions"]
    debt = case["debt_structure"]
    ops = case["operating_assumptions"]
    exit_config = case["exit_assumptions"]

    # 计算债务占比（基于企业价值）
    ev = income["ebitda"] * txn["entry_multiple"]
    senior_pct = debt["senior_debt"]["amount"] / ev
    sub_pct = debt["subordinated_debt"]["amount"] / ev

    return {
        # 目标公司财务
        "entry_ebitda": income["ebitda"],
        "entry_multiple": txn["entry_multiple"],
        "exit_multiple": exit_config["exit_multiple_base"],
        "holding_period": exit_config["holding_period"],

        # 运营假设
        "revenue_growth": ops["revenue_growth"][0] if isinstance(ops["revenue_growth"], list) else ops["revenue_growth"],
        "ebitda_margin": ops["ebitda_margin"][0] if isinstance(ops["ebitda_margin"], list) else ops["ebitda_margin"],
        "capex_percent": ops["capex_percent_revenue"],
        "nwc_percent": ops["nwc_percent_revenue"],
        "tax_rate": ops["tax_rate"],

        # 债务结构（按比例）
        "debt_structure": {
            "senior": {
                "amount_percent": senior_pct,
                "interest_rate": debt["senior_debt"]["rate"],
                "amortization_rate": 0.05
            },
            "subordinated": {
                "amount_percent": sub_pct,
                "interest_rate": debt["subordinated_debt"]["rate"],
                "amortization_rate": 0,
                "pik_rate": 0.02
            }
        },

        # 费用率
        "transaction_fee_rate": txn["transaction_fees"] / ev,
        "financing_fee_rate": txn["financing_fees"] / ev,

        # 现金扫荡
        "sweep_percent": 0.75
    }


def run_sensitivity(case):
    """运行5×5敏感性分析"""
    sens = case["sensitivity_config"]
    entry_range = sens["entry_multiple_range"]
    exit_range = sens["exit_multiple_range"]

    print("\n" + "="*70)
    print("Apollo-Calpine LBO 敏感性分析")
    print("="*70)

    # IRR矩阵
    print("\n【IRR敏感性矩阵】Entry Multiple vs Exit Multiple\n")
    print(f"{'Entry \\ Exit':>12}", end="")
    for exit_mult in exit_range:
        print(f"{exit_mult:.1f}x".rjust(10), end="")
    print()
    print("-" * 62)

    irr_matrix = []
    for entry in entry_range:
        row = [f"{entry:.1f}x"]
        irr_row = []
        for exit_mult in exit_range:
            lbo_input = build_lbo_input(case)
            lbo_input["entry_multiple"] = entry
            lbo_input["exit_multiple"] = exit_mult

            try:
                result = lbo_quick_build(lbo_input)
                irr = result["returns"]["irr"]["value"]
                irr_row.append(irr)
                row.append(f"{irr:.1%}")
            except Exception as e:
                irr_row.append(None)
                row.append("N/A")

        irr_matrix.append(irr_row)
        print(f"{row[0]:>12}", end="")
        for val in row[1:]:
            print(f"{val:>10}", end="")
        print()

    # MOIC矩阵
    print("\n\n【MOIC敏感性矩阵】Entry Multiple vs Exit Multiple\n")
    print(f"{'Entry \\ Exit':>12}", end="")
    for exit_mult in exit_range:
        print(f"{exit_mult:.1f}x".rjust(10), end="")
    print()
    print("-" * 62)

    moic_matrix = []
    for entry in entry_range:
        row = [f"{entry:.1f}x"]
        moic_row = []
        for exit_mult in exit_range:
            lbo_input = build_lbo_input(case)
            lbo_input["entry_multiple"] = entry
            lbo_input["exit_multiple"] = exit_mult

            try:
                result = lbo_quick_build(lbo_input)
                moic = result["returns"]["moic"]["value"]
                moic_row.append(moic)
                row.append(f"{moic:.2f}x")
            except Exception as e:
                moic_row.append(None)
                row.append("N/A")

        moic_matrix.append(moic_row)
        print(f"{row[0]:>12}", end="")
        for val in row[1:]:
            print(f"{val:>10}", end="")
        print()

    return irr_matrix, moic_matrix


def run_base_case(case):
    """运行基准案例"""
    print("\n" + "="*70)
    print("【基准案例分析】")
    print("="*70)

    lbo_input = build_lbo_input(case)
    result = lbo_quick_build(lbo_input)

    # 从结果提取数据
    purchase_price = result['transaction']['purchase_price']['value']
    sources_uses = result['transaction']['sources_uses']
    equity_invested = result['transaction']['equity_invested']

    print(f"\n交易概览:")
    print(f"  目标公司EBITDA:     ${case['income_statement']['ebitda']:,.0f}M")
    print(f"  入场倍数:           {lbo_input['entry_multiple']:.1f}x")
    print(f"  企业价值:           ${purchase_price:,.0f}M")
    print(f"  股权投资:           ${equity_invested:,.0f}M")

    print(f"\n融资结构:")
    total_debt = sources_uses['sources']['total_debt']
    print(f"  Total Debt:         ${total_debt:,.0f}M")
    print(f"  Equity:             ${equity_invested:,.0f}M")
    print(f"  Debt/Equity:        {total_debt/equity_invested:.1%}")

    print(f"\n退出分析 (Year {lbo_input['holding_period']}):")
    print(f"  退出倍数:           {lbo_input['exit_multiple']:.1f}x")
    print(f"  退出企业价值:       ${result['exit_analysis']['exit_value']['value']:,.0f}M")
    print(f"  剩余债务:           ${result['exit_analysis']['ending_debt']:,.0f}M")
    print(f"  股权所得:           ${result['exit_analysis']['equity_proceeds']['value']:,.0f}M")

    print(f"\n回报指标:")
    print(f"  IRR:                {result['returns']['irr']['value']:.1%}")
    print(f"  MOIC:               {result['returns']['moic']['value']:.2f}x")

    return result


def main():
    print("\n" + "#"*70)
    print("#" + " Apollo-Calpine $16.5B LBO 测试案例 ".center(68) + "#")
    print("#"*70)

    # 加载案例
    case = load_case()

    print(f"\n案例说明: {case['_meta']['description']}")
    print(f"数据来源: {case['_meta']['data_source']}")

    # 显示输入数据摘要
    print("\n【输入数据摘要】")
    print(f"  Revenue:            ${case['income_statement']['revenue']:,.0f}M")
    print(f"  EBITDA:             ${case['income_statement']['ebitda']:,.0f}M")
    print(f"  EBITDA Margin:      {case['income_statement']['ebitda']/case['income_statement']['revenue']:.1%}")
    print(f"  Net Income:         ${case['income_statement']['net_income']:,.0f}M")
    print(f"  Total Debt:         ${case['balance_sheet']['long_term_debt']:,.0f}M")
    print(f"  Total Equity:       ${case['balance_sheet']['total_equity']:,.0f}M")

    # 运行基准案例
    run_base_case(case)

    # 运行敏感性分析
    run_sensitivity(case)

    print("\n" + "="*70)
    print("测试完成!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
