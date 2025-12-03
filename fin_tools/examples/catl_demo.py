#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
宁德时代财务建模完整演示

使用 2025Q3 财报数据，演示所有建模工具：
1. 三表模型
2. DCF估值
3. 递延税计算
4. 资产减值测试
5. 租赁资本化
6. 场景管理
7. 与 balance.py 配平工具集成
"""

import json
import subprocess
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fin_tools.models import (
    ThreeStatementModel,
    DCFModel,
    DeferredTax,
    Impairment,
    LeaseCapitalization,
    ScenarioManager
)


# 路径配置
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent.parent / "examples" / "catl_2025q3"
BALANCE_SCRIPT = SCRIPT_DIR.parent.parent / "balance.py"


def load_catl_data():
    """加载宁德时代数据"""
    base_data = json.loads((DATA_DIR / "base_data.json").read_text())
    assumptions = json.loads((DATA_DIR / "assumptions.json").read_text())
    return base_data, assumptions


# ============================================================
# 1. 三表模型演示
# ============================================================

def run_three_statement_demo():
    """三表模型演示"""
    print("=" * 70)
    print("1. 三表模型演示")
    print("=" * 70)

    base_data, assumptions_all = load_catl_data()
    assumptions = assumptions_all["scenarios"]["base_case"]

    model = ThreeStatementModel(base_data, scenario="base_case")
    result = model.build(assumptions)

    # 打印利润表
    income = result["income_statement"]
    print("\n📊 利润表预测 (基准情景):")
    print(f"  营业收入:   {income['revenue']['value']:>15,.2f} 万元")
    print(f"  营业成本:  ({income['cost']['value']:>14,.2f}) 万元")
    print(f"  毛利:       {income['gross_profit']['value']:>15,.2f} 万元")
    print(f"  营业费用:  ({income['opex']['value']:>14,.2f}) 万元")
    print(f"  营业利润:   {income['ebit']['value']:>15,.2f} 万元")
    print(f"  利息费用:  ({income['interest']['value']:>14,.2f}) 万元")
    print(f"  税前利润:   {income['ebt']['value']:>15,.2f} 万元")
    print(f"  所得税:    ({income['tax']['value']:>14,.2f}) 万元")
    print(f"  净利润:     {income['net_income']['value']:>15,.2f} 万元")

    # 打印资产负债表
    bs = result["balance_sheet"]
    print("\n📊 资产负债表:")
    print(f"  资产合计:   {bs['assets']['total_assets']['value']:>15,.2f} 万元")
    print(f"  负债合计:   {bs['liabilities']['total_liabilities']['value']:>15,.2f} 万元")
    print(f"  权益合计:   {bs['equity']['total_equity']['value']:>15,.2f} 万元")

    # 打印现金流量表
    cf = result["cash_flow"]
    print("\n📊 现金流量表:")
    print(f"  经营活动:   {cf['operating']['value']:>15,.2f} 万元")
    print(f"  投资活动:   {cf['investing']['value']:>15,.2f} 万元")
    print(f"  筹资活动:   {cf['financing']['value']:>15,.2f} 万元")
    print(f"  现金净变动: {cf['net_change']['value']:>15,.2f} 万元")

    # 配平检验
    validation = result["validation"]
    status = "✅ PASS" if validation["is_balanced"] else "❌ FAIL"
    print(f"\n✓ 配平检验: {status} (差额: {validation['difference']:.2f})")

    return result


# ============================================================
# 2. 递延税演示
# ============================================================

def run_deferred_tax_demo():
    """递延税演示"""
    print("\n" + "=" * 70)
    print("2. 递延税计算演示")
    print("=" * 70)

    dt = DeferredTax()

    # 情景1: 公司亏损
    print("\n📋 情景1: 公司亏损 (EBT = -500万)")
    result1 = dt.calc_deferred_tax(
        ebt=-5000000,
        prior_tax_loss=0,
        tax_rate=0.25,
        dta_balance=0
    )
    print(f"  当期税:         {result1['current_tax']['value']:>12,.2f} 万元")
    print(f"  DTA变动:        {result1['dta_change']['value']:>12,.2f} 万元 (新增)")
    print(f"  期末DTA:        {result1['closing_dta']['value']:>12,.2f} 万元")
    print(f"  累计可抵扣亏损: {result1['closing_tax_loss']['value']:>12,.2f} 万元")
    print(f"  所得税费用:     {result1['tax_expense']['value']:>12,.2f} 万元")
    print(f"  └─ 公式: {result1['tax_expense']['formula']}")

    # 情景2: 公司盈利，有累计亏损可抵扣
    print("\n📋 情景2: 公司盈利 (EBT = 800万), 有累计亏损500万")
    result2 = dt.calc_deferred_tax(
        ebt=8000000,
        prior_tax_loss=5000000,
        tax_rate=0.25,
        dta_balance=1250000  # 500万 * 25%
    )
    print(f"  当期税:         {result2['current_tax']['value']:>12,.2f} 万元")
    print(f"  └─ 公式: {result2['current_tax']['formula']}")
    print(f"  DTA变动:        {result2['dta_change']['value']:>12,.2f} 万元 (减少)")
    print(f"  期末DTA:        {result2['closing_dta']['value']:>12,.2f} 万元")
    print(f"  剩余亏损:       {result2['closing_tax_loss']['value']:>12,.2f} 万元")

    # 对三表的影响
    print("\n📝 递延税对三表的影响:")
    print(f"  利润表: {result1['impact']['income_statement']}")
    print(f"  资产负债表: {result1['impact']['balance_sheet']}")
    print(f"  现金流量表: {result1['impact']['cash_flow']}")


# ============================================================
# 3. 资产减值演示
# ============================================================

def run_impairment_demo():
    """资产减值演示"""
    print("\n" + "=" * 70)
    print("3. 资产减值测试演示")
    print("=" * 70)

    imp = Impairment()

    # 先计算使用价值
    print("\n📋 商誉减值测试:")
    print("  账面价值: 10,000,000 万元")

    # 假设未来5年现金流
    future_cf = [2000000, 2100000, 2200000, 2300000, 2400000]
    viu = imp.calc_value_in_use(future_cf, discount_rate=0.10)
    print(f"\n  使用价值计算:")
    print(f"    未来现金流: {future_cf}")
    print(f"    折现率: 10%")
    print(f"    使用价值: {viu.value:,.2f} 万元")
    print(f"    公式: {viu.formula}")

    # 减值测试
    result = imp.calc_impairment(
        asset_name="商誉",
        carrying_value=10000000,
        fair_value=7500000,
        value_in_use=viu.value
    )

    print(f"\n  减值测试结果:")
    print(f"    公允价值-处置费用: 7,500,000 万元")
    print(f"    使用价值:          {viu.value:,.2f} 万元")
    print(f"    可回收金额:        {result['recoverable_amount']['value']:,.2f} 万元")
    print(f"    └─ 公式: {result['recoverable_amount']['formula']}")
    print(f"    是否需要减值:      {'是' if result['is_impaired'] else '否'}")
    print(f"    减值损失:          {result['impairment_loss']['value']:,.2f} 万元")
    print(f"    新账面价值:        {result['new_carrying_value']['value']:,.2f} 万元")

    # 对三表的影响
    print(f"\n📝 减值对三表的影响:")
    print(f"  {result['impact']['income_statement']}")
    print(f"  {result['impact']['balance_sheet']}")
    print(f"  {result['impact']['cash_flow']}")


# ============================================================
# 4. 租赁资本化演示
# ============================================================

def run_lease_demo():
    """租赁资本化演示 (IFRS 16)"""
    print("\n" + "=" * 70)
    print("4. 租赁资本化演示 (IFRS 16)")
    print("=" * 70)

    lease = LeaseCapitalization()

    # 假设宁德时代有一笔5年期厂房租赁
    print("\n📋 厂房租赁资本化:")
    print("  年租金: 1,000,000 万元")
    print("  租赁期: 5 年")
    print("  增量借款利率: 5%")

    result = lease.capitalize_lease(
        annual_rent=1000000,
        lease_term=5,
        discount_rate=0.05
    )

    # 初始确认
    init = result["initial_recognition"]
    print(f"\n  初始确认:")
    print(f"    租赁负债:     {init['lease_liability']['value']:>12,.2f} 万元")
    print(f"    └─ 公式: {init['lease_liability']['formula']}")
    print(f"    使用权资产:   {init['rou_asset']['value']:>12,.2f} 万元")

    # 年度明细表
    print(f"\n  年度明细表:")
    print(f"  {'年份':>4} {'期初负债':>12} {'利息':>10} {'本金':>10} {'期末负债':>12} {'折旧':>10} {'ROU期末':>12}")
    print("  " + "-" * 78)
    for row in result["annual_schedule"]:
        print(f"  {row['year']:>4} {row['opening_liability']:>12,.0f} {row['interest_expense']:>10,.0f} "
              f"{row['principal_payment']:>10,.0f} {row['closing_liability']:>12,.0f} "
              f"{row['depreciation']:>10,.0f} {row['closing_rou_asset']:>12,.0f}")

    # 影响汇总
    impact = result["impact_summary"]
    print(f"\n  影响汇总 (第一年):")
    print(f"    旧准则租金费用:   {impact['old_rent_expense']:>10,.0f} 万元")
    print(f"    新准则折旧:       {impact['new_depreciation']:>10,.0f} 万元")
    print(f"    新准则利息:       {impact['new_interest']:>10,.0f} 万元")
    print(f"    新准则费用合计:   {impact['total_new_expense']:>10,.0f} 万元")
    print(f"    EBITDA改善:       {impact['ebitda_improvement']:>10,.0f} 万元")
    print(f"    净利润影响:       {impact['net_income_impact']:>10,.0f} 万元")

    # 对三表的影响
    print(f"\n📝 租赁资本化对三表的影响:")
    for key, val in result["impact"].items():
        print(f"  {key}: {val}")


# ============================================================
# 5. 场景管理演示
# ============================================================

def run_scenario_demo():
    """场景管理演示"""
    print("\n" + "=" * 70)
    print("5. 场景管理演示")
    print("=" * 70)

    base_data, assumptions_all = load_catl_data()

    # 创建场景管理器
    sm = ScenarioManager(base_data)

    # 添加三种情景
    for name, config in assumptions_all["scenarios"].items():
        sm.add_scenario(name, config, config.get("description", ""))

    # 场景对比
    print("\n📊 三种情景对比:")
    sm.print_comparison(["base_case", "bull_case", "bear_case"])

    # 单参数敏感性分析
    print("\n📊 单参数敏感性分析 (增长率 vs 净利润):")
    sm.print_sensitivity_1d(
        param="growth_rate",
        values=[0.05, 0.07, 0.09, 0.12, 0.15],
        output_metric="net_income"
    )

    # 双参数敏感性矩阵
    print("\n📊 双参数敏感性矩阵 (增长率 × 毛利率):")
    sm.print_sensitivity_2d(
        param1="growth_rate",
        values1=[0.05, 0.09, 0.12, 0.15],
        param2="gross_margin",
        values2=[0.23, 0.25, 0.27, 0.30],
        output_metric="net_income"
    )


# ============================================================
# 6. DCF估值演示
# ============================================================

def run_dcf_demo():
    """DCF估值演示"""
    print("\n" + "=" * 70)
    print("6. DCF估值演示")
    print("=" * 70)

    base_data, assumptions_all = load_catl_data()
    assumptions = assumptions_all["scenarios"]["base_case"]

    # 用三表模型预测5年FCF
    base_revenue = base_data["last_revenue"]
    growth_rate = assumptions["growth_rate"]

    fcf_projections = {}
    for year in range(1, 6):
        revenue = base_revenue * (1 + growth_rate) ** year
        # 简化：FCF ≈ EBIT * (1-t) * 0.7
        ebit_margin = assumptions["gross_margin"] - assumptions["opex_ratio"]
        ebit = revenue * ebit_margin
        fcf = ebit * (1 - assumptions["tax_rate"]) * 0.7
        fcf_projections[f"year_{year}"] = round(fcf, 2)

    print("\n📈 5年FCF预测:")
    for year, fcf in fcf_projections.items():
        print(f"  {year}: {fcf:>15,.2f} 万元")

    # DCF估值
    dcf_inputs = {
        "fcf_projections": fcf_projections,
        "wacc_inputs": {
            "risk_free_rate": 0.025,
            "beta": 1.1,
            "market_risk_premium": 0.06,
            "cost_of_debt": 0.04,
            "tax_rate": assumptions["tax_rate"],
            "debt_ratio": 0.25
        },
        "terminal_inputs": {
            "method": "perpetual_growth",
            "terminal_growth": 0.03
        },
        "balance_sheet_adjustments": {
            "cash": base_data["closing_cash"],
            "debt": base_data["closing_debt"],
            "shares_outstanding": 2436926
        },
        "sensitivity_config": {
            "wacc_range": [0.07, 0.08, 0.09, 0.10, 0.11],
            "growth_range": [0.02, 0.025, 0.03, 0.035, 0.04]
        }
    }

    dcf = DCFModel(name="宁德时代DCF估值")
    result = dcf.valuate(dcf_inputs)

    print(f"\n📊 DCF估值结果:")
    print(f"  WACC:           {result['wacc']['value']:.2%}")
    print(f"  终值:           {result['terminal_value']['value']:>15,.2f} 万元")
    print(f"  企业价值:       {result['enterprise_value']['value']:>15,.2f} 万元")
    print(f"  股权价值:       {result['equity_value']['value']:>15,.2f} 万元")
    print(f"  💰 每股价值:    {result['per_share_value']['value']:.2f} 元")

    # 敏感性分析
    if result.get("sensitivity_matrix"):
        print("\n📊 敏感性分析矩阵 (每股价值):")
        sens = result["sensitivity_matrix"]
        print(f"\n  WACC \\ g    ", end="")
        for key in sens["data"][0].keys():
            if key != "wacc":
                print(f"{key:>10}", end="")
        print()
        print("  " + "-" * 60)
        for row in sens["data"]:
            print(f"  {row['wacc']:>8}  ", end="")
            for key, val in row.items():
                if key != "wacc":
                    if isinstance(val, (int, float)):
                        print(f"{val:>10.2f}", end="")
                    else:
                        print(f"{val:>10}", end="")
            print()


# ============================================================
# 7. 与 balance.py 配平工具集成
# ============================================================

def run_balance_integration():
    """与 balance.py 配平工具集成"""
    print("\n" + "=" * 70)
    print("7. 与 balance.py 配平工具集成")
    print("=" * 70)

    base_data, assumptions_all = load_catl_data()
    assumptions = assumptions_all["scenarios"]["base_case"]

    # 用我们的工具生成输入
    model = ThreeStatementModel(base_data, scenario="base_case")
    result = model.build(assumptions)

    # 构建 balance.py 需要的输入格式
    income = result["income_statement"]
    wc = result["working_capital"]

    balance_input = {
        "revenue": income["revenue"]["value"],
        "cost": income["cost"]["value"],
        "other_expense": income["opex"]["value"],

        "opening_cash": base_data["closing_cash"],
        "opening_debt": base_data["closing_debt"],
        "opening_equity": base_data["closing_equity"],
        "opening_retained": base_data.get("closing_retained", 15171504.90),

        "opening_receivable": base_data["closing_receivable"],
        "opening_payable": base_data["closing_payable"],
        "opening_inventory": base_data["closing_inventory"],

        "delta_receivable": wc["delta_ar"]["value"],
        "delta_payable": wc["delta_ap"]["value"],
        "delta_inventory": wc["delta_inv"]["value"],

        "fixed_asset_cost": base_data["fixed_asset_gross"] + abs(result["cash_flow"]["investing"]["value"]),
        "accum_depreciation": base_data["accum_depreciation"],
        "fixed_asset_life": base_data["fixed_asset_life"],
        "fixed_asset_salvage": 0,

        "capex": abs(result["cash_flow"]["investing"]["value"]),
        "interest_rate": assumptions["interest_rate"],
        "tax_rate": assumptions["tax_rate"],
        "dividend": income["net_income"]["value"] * assumptions["dividend_ratio"],
        "min_cash": 5000000
    }

    print("\n📋 生成 balance.py 输入:")
    print(f"  收入: {balance_input['revenue']:,.2f}")
    print(f"  成本: {balance_input['cost']:,.2f}")
    print(f"  费用: {balance_input['other_expense']:,.2f}")
    print(f"  资本支出: {balance_input['capex']:,.2f}")

    # 调用 balance.py calc
    if BALANCE_SCRIPT.exists():
        print("\n📋 调用 balance.py calc 进行配平计算...")

        input_json = json.dumps(balance_input)
        proc = subprocess.run(
            ['python3', str(BALANCE_SCRIPT), 'calc'],
            input=input_json,
            capture_output=True,
            text=True
        )

        if proc.returncode == 0:
            output = json.loads(proc.stdout)
            print(f"\n  配平计算结果:")
            print(f"    净利润:     {output.get('net_income', 0):>15,.2f} 万元")
            print(f"    期末现金:   {output.get('closing_cash', 0):>15,.2f} 万元")
            print(f"    总资产:     {output.get('total_assets', 0):>15,.2f} 万元")
            print(f"    总负债:     {output.get('total_liabilities', 0):>15,.2f} 万元")
            print(f"    总权益:     {output.get('total_equity', 0):>15,.2f} 万元")
            print(f"    配平差额:   {output.get('balance_diff', 0):>15,.2f}")

            status = "✅ PASS" if output.get('is_balanced', False) else "❌ FAIL"
            print(f"\n  配平检验: {status}")

            # 调用 diagnose
            print("\n📋 调用 balance.py diagnose 进行德尔塔法检验...")
            proc2 = subprocess.run(
                ['python3', str(BALANCE_SCRIPT), 'diagnose'],
                input=json.dumps(output),
                capture_output=True,
                text=True
            )

            if proc2.returncode == 0:
                diag = json.loads(proc2.stdout)
                mismatches = diag.get('mismatches', [])
                if not mismatches:
                    print("  德尔塔法检验: ✅ PASS (全部匹配)")
                else:
                    print(f"  德尔塔法检验: ❌ FAIL ({len(mismatches)}项不匹配)")
                    for m in mismatches[:3]:
                        print(f"    - {m['field']}: 计算值={m['computed']:.2f}, 实际值={m['actual']:.2f}")
        else:
            print(f"  ❌ balance.py 调用失败: {proc.stderr}")
    else:
        print(f"  ⚠️ balance.py 不存在: {BALANCE_SCRIPT}")


# ============================================================
# 主函数
# ============================================================

def main():
    """主函数"""
    print("\n" + "═" * 70)
    print("  财务建模工具完整演示 - 宁德时代 2025Q3")
    print("═" * 70)

    # 1. 三表模型
    run_three_statement_demo()

    # 2. 递延税
    run_deferred_tax_demo()

    # 3. 资产减值
    run_impairment_demo()

    # 4. 租赁资本化
    run_lease_demo()

    # 5. 场景管理
    run_scenario_demo()

    # 6. DCF估值
    run_dcf_demo()

    # 7. 与 balance.py 集成
    run_balance_integration()

    print("\n" + "═" * 70)
    print("  演示完成 - 所有功能已验证")
    print("═" * 70 + "\n")


if __name__ == "__main__":
    main()
