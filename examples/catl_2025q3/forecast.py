#!/usr/bin/env python3
"""
财务三表预测模型

用法:
    python forecast.py                      # 运行所有情景
    python forecast.py --scenario base_case # 运行单个情景
    python forecast.py --compare            # 对比所有情景
    python forecast.py --help               # 显示帮助

驱动因子在 assumptions.json 中定义，只需修改参数即可预测不同情景。
"""

import json
import argparse
import subprocess
import sys
from pathlib import Path

# 获取脚本所在目录
SCRIPT_DIR = Path(__file__).parent
BALANCE_SCRIPT = SCRIPT_DIR.parent.parent / "balance.py"


def load_json(filepath):
    """加载JSON文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data, filepath):
    """保存JSON文件"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def forecast(base_data: dict, assumptions: dict) -> dict:
    """
    核心预测公式

    输入:
        base_data: 基础数据（上期财报）
        assumptions: 驱动因子（情景假设）

    输出:
        input_data: 完整的配平工具输入
    """

    # ========== 驱动因子 ==========
    growth_rate = assumptions['growth_rate']
    gross_margin = assumptions['gross_margin']
    opex_ratio = assumptions['opex_ratio']
    capex_ratio = assumptions['capex_ratio']
    ar_days = assumptions['ar_days']
    ap_days = assumptions['ap_days']
    inv_days = assumptions['inv_days']
    interest_rate = assumptions['interest_rate']
    tax_rate = assumptions['tax_rate']
    dividend_ratio = assumptions['dividend_ratio']

    # ========== 损益表预测 ==========
    # 公式: 收入 = 上期收入 × (1 + 增长率)
    revenue = base_data['last_revenue'] * (1 + growth_rate)

    # 公式: 成本 = 收入 × (1 - 毛利率)
    cost = revenue * (1 - gross_margin)

    # 公式: 费用 = 收入 × 费用率
    other_expense = revenue * opex_ratio

    # 公式: 毛利 = 收入 - 成本
    gross_profit = revenue - cost

    # ========== 资本支出预测 ==========
    # 公式: CAPEX = 收入 × 资本支出比率
    capex = revenue * capex_ratio

    # ========== 营运资本预测 ==========
    # 公式: 应收账款 = 收入 / 365 × 应收周转天数
    target_receivable = revenue / 365 * ar_days
    delta_receivable = target_receivable - base_data['closing_receivable']

    # 公式: 应付账款 = 成本 / 365 × 应付周转天数
    target_payable = cost / 365 * ap_days
    delta_payable = target_payable - base_data['closing_payable']

    # 公式: 存货 = 成本 / 365 × 存货周转天数
    target_inventory = cost / 365 * inv_days
    delta_inventory = target_inventory - base_data['closing_inventory']

    # ========== 构建输入数据 ==========
    input_data = {
        "_scenario": assumptions.get('name', 'forecast'),
        "_description": assumptions.get('description', ''),
        "_formula_driven": True,

        # 损益表输入
        "revenue": round(revenue, 2),
        "cost": round(cost, 2),
        "other_expense": round(other_expense, 2),

        # 期初数据（上期期末）
        "opening_cash": base_data['closing_cash'],
        "opening_debt": base_data['closing_debt'],
        "opening_equity": base_data['closing_equity'],
        "opening_retained": base_data['closing_retained'],

        "opening_receivable": base_data['closing_receivable'],
        "opening_payable": base_data['closing_payable'],
        "opening_inventory": base_data['closing_inventory'],

        # 营运资本变动
        "delta_receivable": round(delta_receivable, 2),
        "delta_payable": round(delta_payable, 2),
        "delta_inventory": round(delta_inventory, 2),

        # 固定资产
        "fixed_asset_cost": base_data['fixed_asset_gross'] + capex,
        "accum_depreciation": base_data['accum_depreciation'],
        "fixed_asset_life": base_data['fixed_asset_life'],
        "fixed_asset_salvage": 0,

        # 资本支出
        "capex": round(capex, 2),

        # 利率和税率
        "interest_rate": interest_rate,
        "tax_rate": tax_rate,

        # 分红（基于预估净利润）
        # 简化估算: 净利润 ≈ 毛利 × 0.5（扣除费用、利息、税后）
        "dividend": round(gross_profit * 0.5 * dividend_ratio, 2),

        # 最低现金
        "min_cash": 5000000
    }

    return input_data


def run_balance_calc(input_data: dict) -> dict:
    """调用 balance calc 进行配平计算"""
    input_json = json.dumps(input_data)

    result = subprocess.run(
        ['python3', str(BALANCE_SCRIPT), 'calc'],
        input=input_json,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
        return None

    return json.loads(result.stdout)


def run_balance_diagnose(output_data: dict) -> dict:
    """调用 balance diagnose 进行诊断"""
    output_json = json.dumps(output_data)

    result = subprocess.run(
        ['python3', str(BALANCE_SCRIPT), 'diagnose'],
        input=output_json,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return None

    return json.loads(result.stdout)


def print_scenario_result(name: str, assumptions: dict, output: dict, diagnose: dict):
    """打印单个情景结果"""
    print(f"\n{'='*60}")
    print(f"【{name}】{assumptions.get('description', '')}")
    print(f"{'='*60}")

    print(f"\n驱动因子:")
    print(f"  收入增长率: {assumptions['growth_rate']*100:.1f}%")
    print(f"  毛利率:     {assumptions['gross_margin']*100:.1f}%")
    print(f"  费用率:     {assumptions['opex_ratio']*100:.1f}%")
    print(f"  CAPEX比率:  {assumptions['capex_ratio']*100:.1f}%")

    print(f"\n计算结果:")
    print(f"  营业收入:   {output['revenue']:>15,.2f} 万元")
    print(f"  营业成本:   {output['cost']:>15,.2f} 万元")
    print(f"  毛利:       {output['gross_profit']:>15,.2f} 万元")
    print(f"  净利润:     {output['net_income']:>15,.2f} 万元")
    print(f"  期末现金:   {output['closing_cash']:>15,.2f} 万元")

    print(f"\n验证结果:")
    print(f"  资产负债表配平: {'✅ PASS' if output['is_balanced'] else '❌ FAIL'}")
    print(f"  现金流量表配平: {'✅ PASS' if output['cash_balanced'] else '❌ FAIL'}")

    if diagnose:
        mismatches = diagnose.get('mismatches', [])
        if not mismatches:
            print(f"  德尔塔法检验:   ✅ PASS (全部匹配)")
        else:
            print(f"  德尔塔法检验:   ❌ FAIL ({len(mismatches)}项不匹配)")


def compare_scenarios(results: dict):
    """对比所有情景"""
    print(f"\n{'='*80}")
    print("三种情景对比")
    print(f"{'='*80}")

    # 表头
    print(f"\n{'指标':<20} {'Base Case':>18} {'Bull Case':>18} {'Bear Case':>18}")
    print("-" * 80)

    scenarios = ['base_case', 'bull_case', 'bear_case']

    # 收入
    row = "营业收入(万元)"
    for s in scenarios:
        row += f" {results[s]['output']['revenue']:>17,.0f}"
    print(row)

    # 毛利
    row = "毛利(万元)"
    for s in scenarios:
        row += f" {results[s]['output']['gross_profit']:>17,.0f}"
    print(row)

    # 净利润
    row = "净利润(万元)"
    for s in scenarios:
        row += f" {results[s]['output']['net_income']:>17,.0f}"
    print(row)

    # 期末现金
    row = "期末现金(万元)"
    for s in scenarios:
        row += f" {results[s]['output']['closing_cash']:>17,.0f}"
    print(row)

    # 毛利率
    row = "毛利率"
    for s in scenarios:
        gm = results[s]['output']['gross_profit'] / results[s]['output']['revenue'] * 100
        row += f" {gm:>16.1f}%"
    print(row)

    # 净利率
    row = "净利率"
    for s in scenarios:
        nm = results[s]['output']['net_income'] / results[s]['output']['revenue'] * 100
        row += f" {nm:>16.1f}%"
    print(row)

    # 配平状态
    row = "是否配平"
    for s in scenarios:
        status = "✅" if results[s]['output']['is_balanced'] else "❌"
        row += f" {status:>17}"
    print(row)

    print("-" * 80)

    # 验证 Bull > Base > Bear
    bull_ni = results['bull_case']['output']['net_income']
    base_ni = results['base_case']['output']['net_income']
    bear_ni = results['bear_case']['output']['net_income']

    print(f"\n情景合理性检验: ", end="")
    if bull_ni > base_ni > bear_ni:
        print("✅ PASS (Bull > Base > Bear)")
    else:
        print("❌ FAIL (排序不符合预期)")


def main():
    parser = argparse.ArgumentParser(description='财务三表预测模型')
    parser.add_argument('--scenario', '-s',
                        choices=['base_case', 'bull_case', 'bear_case'],
                        help='运行单个情景')
    parser.add_argument('--compare', '-c', action='store_true',
                        help='对比所有情景')
    parser.add_argument('--output-dir', '-o', default=str(SCRIPT_DIR),
                        help='输出目录')

    args = parser.parse_args()

    # 加载基础数据和假设
    base_data = load_json(SCRIPT_DIR / 'base_data.json')
    assumptions_all = load_json(SCRIPT_DIR / 'assumptions.json')

    # 确定要运行的情景
    if args.scenario:
        scenarios_to_run = [args.scenario]
    else:
        scenarios_to_run = ['base_case', 'bull_case', 'bear_case']

    results = {}

    for scenario_name in scenarios_to_run:
        assumptions = assumptions_all['scenarios'][scenario_name]

        # 1. 用公式计算预测输入
        input_data = forecast(base_data, assumptions)

        # 2. 保存输入文件
        input_file = Path(args.output_dir) / f'{scenario_name}_input.json'
        save_json(input_data, input_file)

        # 3. 调用 balance calc 配平
        output_data = run_balance_calc(input_data)

        if output_data:
            # 4. 保存输出文件
            output_file = Path(args.output_dir) / f'{scenario_name}_output.json'
            save_json(output_data, output_file)

            # 5. 诊断检验
            diagnose_data = run_balance_diagnose(output_data)

            # 6. 打印结果
            print_scenario_result(
                assumptions['name'],
                assumptions,
                output_data,
                diagnose_data
            )

            results[scenario_name] = {
                'assumptions': assumptions,
                'input': input_data,
                'output': output_data,
                'diagnose': diagnose_data
            }

    # 对比所有情景
    if len(results) == 3 or args.compare:
        compare_scenarios(results)

    print(f"\n输出文件保存在: {args.output_dir}/")


if __name__ == '__main__':
    main()
