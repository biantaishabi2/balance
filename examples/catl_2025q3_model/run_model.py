#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
宁德时代 2025Q3 完整财务建模

运行此脚本生成所有建模结果并保存到当前目录
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from financial_model.models import (
    ThreeStatementModel,
    DCFModel,
    DeferredTax,
    Impairment,
    LeaseCapitalization,
    ScenarioManager
)
from financial_model.io import ExcelWriter

# 路径配置
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "catl_2025q3"
BALANCE_SCRIPT = SCRIPT_DIR.parent.parent / "balance.py"


def load_data():
    """加载数据"""
    base_data = json.loads((DATA_DIR / "base_data.json").read_text())
    assumptions = json.loads((DATA_DIR / "assumptions.json").read_text())
    return base_data, assumptions


def save_json(data, filename):
    """保存JSON"""
    filepath = SCRIPT_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  ✓ 保存: {filename}")


def run_three_statement_model():
    """运行三表模型"""
    print("\n" + "=" * 60)
    print("1. 三表模型")
    print("=" * 60)

    base_data, assumptions_all = load_data()
    results = {}

    for scenario_name in ["base_case", "bull_case", "bear_case"]:
        assumptions = assumptions_all["scenarios"][scenario_name]
        model = ThreeStatementModel(base_data, scenario=scenario_name)
        result = model.build(assumptions)

        # 添加元信息
        result["_meta"]["generated_at"] = datetime.now().isoformat()
        result["_meta"]["assumptions"] = assumptions

        results[scenario_name] = result

        print(f"\n  【{assumptions['name']}】")
        income = result["income_statement"]
        print(f"    收入: {income['revenue']['value']:,.0f} 万元")
        print(f"    净利润: {income['net_income']['value']:,.0f} 万元")
        print(f"    配平: {'✅' if result['validation']['is_balanced'] else '❌'}")

        # 保存单个场景
        save_json(result, f"three_statement_{scenario_name}.json")

    # 保存汇总
    save_json(results, "three_statement_all.json")
    return results


def run_dcf_valuation():
    """运行DCF估值"""
    print("\n" + "=" * 60)
    print("2. DCF估值")
    print("=" * 60)

    base_data, assumptions_all = load_data()
    assumptions = assumptions_all["scenarios"]["base_case"]

    # 预测5年FCF
    base_revenue = base_data["last_revenue"]
    growth_rate = assumptions["growth_rate"]

    fcf_projections = {}
    for year in range(1, 6):
        revenue = base_revenue * (1 + growth_rate) ** year
        ebit_margin = assumptions["gross_margin"] - assumptions["opex_ratio"]
        ebit = revenue * ebit_margin
        fcf = ebit * (1 - assumptions["tax_rate"]) * 0.7
        fcf_projections[f"year_{year}"] = round(fcf, 2)

    # DCF输入
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

    # 添加输入信息
    result["_inputs"] = dcf_inputs
    result["_generated_at"] = datetime.now().isoformat()

    print(f"\n  WACC: {result['wacc']['value']:.2%}")
    print(f"  企业价值: {result['enterprise_value']['value']:,.0f} 万元")
    print(f"  股权价值: {result['equity_value']['value']:,.0f} 万元")
    print(f"  每股价值: {result['per_share_value']['value']:.2f} 元")

    save_json(result, "dcf_valuation.json")
    return result


def run_deferred_tax_examples():
    """递延税示例"""
    print("\n" + "=" * 60)
    print("3. 递延税计算")
    print("=" * 60)

    dt = DeferredTax()
    results = {}

    # 情景1: 亏损
    results["loss_scenario"] = dt.calc_deferred_tax(
        ebt=-5000000,
        prior_tax_loss=0,
        tax_rate=0.25,
        dta_balance=0
    )
    print(f"\n  情景1-亏损: DTA新增 {results['loss_scenario']['dta_change']['value']:,.0f}")

    # 情景2: 盈利抵扣
    results["profit_with_loss"] = dt.calc_deferred_tax(
        ebt=8000000,
        prior_tax_loss=5000000,
        tax_rate=0.25,
        dta_balance=1250000
    )
    print(f"  情景2-盈利抵扣: 当期税 {results['profit_with_loss']['current_tax']['value']:,.0f}")

    # 情景3: 正常盈利
    results["normal_profit"] = dt.calc_deferred_tax(
        ebt=10000000,
        prior_tax_loss=0,
        tax_rate=0.25,
        dta_balance=0
    )
    print(f"  情景3-正常盈利: 当期税 {results['normal_profit']['current_tax']['value']:,.0f}")

    save_json(results, "deferred_tax.json")
    return results


def run_impairment_test():
    """资产减值测试"""
    print("\n" + "=" * 60)
    print("4. 资产减值测试")
    print("=" * 60)

    imp = Impairment()

    # 计算使用价值
    future_cf = [2000000, 2100000, 2200000, 2300000, 2400000]
    viu = imp.calc_value_in_use(future_cf, discount_rate=0.10)

    # 减值测试
    result = imp.calc_impairment(
        asset_name="商誉",
        carrying_value=10000000,
        fair_value=7500000,
        value_in_use=viu.value
    )

    # 组合结果
    output = {
        "value_in_use_calculation": viu.to_dict(),
        "impairment_test": result,
        "_inputs": {
            "future_cash_flows": future_cf,
            "discount_rate": 0.10,
            "carrying_value": 10000000,
            "fair_value": 7500000
        }
    }

    print(f"\n  使用价值: {viu.value:,.0f} 万元")
    print(f"  可回收金额: {result['recoverable_amount']['value']:,.0f} 万元")
    print(f"  减值损失: {result['impairment_loss']['value']:,.0f} 万元")

    save_json(output, "impairment_test.json")
    return output


def run_lease_capitalization():
    """租赁资本化"""
    print("\n" + "=" * 60)
    print("5. 租赁资本化 (IFRS 16)")
    print("=" * 60)

    lease = LeaseCapitalization()
    result = lease.capitalize_lease(
        annual_rent=1000000,
        lease_term=5,
        discount_rate=0.05
    )

    result["_inputs"] = {
        "annual_rent": 1000000,
        "lease_term": 5,
        "discount_rate": 0.05
    }

    print(f"\n  租赁负债: {result['initial_recognition']['lease_liability']['value']:,.0f} 万元")
    print(f"  使用权资产: {result['initial_recognition']['rou_asset']['value']:,.0f} 万元")
    print(f"  EBITDA改善: {result['impact_summary']['ebitda_improvement']:,.0f} 万元")

    save_json(result, "lease_capitalization.json")
    return result


def run_scenario_comparison():
    """场景对比"""
    print("\n" + "=" * 60)
    print("6. 场景对比分析")
    print("=" * 60)

    base_data, assumptions_all = load_data()
    sm = ScenarioManager(base_data)

    for name, config in assumptions_all["scenarios"].items():
        sm.add_scenario(name, config, config.get("description", ""))

    # 场景对比
    comparison = sm.compare_scenarios(["base_case", "bull_case", "bear_case"])

    # 敏感性分析
    sens_1d = sm.sensitivity_1d(
        param="growth_rate",
        values=[0.05, 0.07, 0.09, 0.12, 0.15],
        output_metric="net_income"
    )

    sens_2d = sm.sensitivity_2d(
        param1="growth_rate",
        values1=[0.05, 0.09, 0.12, 0.15],
        param2="gross_margin",
        values2=[0.23, 0.25, 0.27, 0.30],
        output_metric="net_income"
    )

    output = {
        "scenario_comparison": comparison,
        "sensitivity_1d": sens_1d,
        "sensitivity_2d": sens_2d
    }

    print(f"\n  三种情景净利润:")
    for row in comparison["rows"]:
        if row["metric"] == "净利润":
            print(f"    Base: {row['base_case']:,.0f}")
            print(f"    Bull: {row['bull_case']:,.0f}")
            print(f"    Bear: {row['bear_case']:,.0f}")

    print(f"  排序验证: {'✅' if comparison['validation']['is_valid'] else '❌'}")

    save_json(output, "scenario_analysis.json")
    return output


def run_balance_integration():
    """与 balance.py 集成"""
    print("\n" + "=" * 60)
    print("7. 与 balance.py 配平集成")
    print("=" * 60)

    base_data, assumptions_all = load_data()
    assumptions = assumptions_all["scenarios"]["base_case"]

    model = ThreeStatementModel(base_data, scenario="base_case")
    result = model.build(assumptions)

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

    save_json(balance_input, "balance_input.json")

    output = {"input": balance_input}

    if BALANCE_SCRIPT.exists():
        # 调用 balance calc
        proc = subprocess.run(
            ['python3', str(BALANCE_SCRIPT), 'calc'],
            input=json.dumps(balance_input),
            capture_output=True,
            text=True
        )

        if proc.returncode == 0:
            calc_result = json.loads(proc.stdout)
            output["calc_result"] = calc_result

            print(f"\n  净利润: {calc_result.get('net_income', 0):,.0f} 万元")
            print(f"  配平差额: {calc_result.get('balance_diff', 0):.2f}")
            print(f"  配平检验: {'✅ PASS' if calc_result.get('is_balanced') else '❌ FAIL'}")

            save_json(calc_result, "balance_output.json")

            # 调用 diagnose
            proc2 = subprocess.run(
                ['python3', str(BALANCE_SCRIPT), 'diagnose'],
                input=json.dumps(calc_result),
                capture_output=True,
                text=True
            )

            if proc2.returncode == 0:
                diag_result = json.loads(proc2.stdout)
                output["diagnose_result"] = diag_result
                mismatches = diag_result.get('mismatches', [])
                print(f"  德尔塔法: {'✅ PASS' if not mismatches else f'❌ FAIL ({len(mismatches)}项)'}")

                save_json(diag_result, "balance_diagnose.json")

    save_json(output, "balance_integration.json")
    return output


def main():
    """主函数"""
    print("\n" + "═" * 60)
    print("  宁德时代 2025Q3 完整财务建模")
    print("  生成时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("═" * 60)

    # 运行所有模型
    results = {}
    results["three_statement"] = run_three_statement_model()
    results["dcf"] = run_dcf_valuation()
    results["deferred_tax"] = run_deferred_tax_examples()
    results["impairment"] = run_impairment_test()
    results["lease"] = run_lease_capitalization()
    results["scenario"] = run_scenario_comparison()
    results["balance"] = run_balance_integration()

    # ===== 8. 导出 Excel =====
    print("\n" + "=" * 60)
    print("8. 导出 Excel 报告")
    print("=" * 60)

    try:
        writer = ExcelWriter()

        # 三表模型 - 三种情景（值模式）
        for scenario in ["base_case", "bull_case", "bear_case"]:
            writer.write_three_statement(
                results["three_statement"][scenario],
                f"三表-{scenario}"
            )

        # 三表模型 - 公式模式（基准情景）
        # 用户可以在 Excel 中直接修改参数，自动重算
        _, assumptions_data = load_data()
        base_result = results["three_statement"]["base_case"]
        base_result["_meta"]["assumptions"] = assumptions_data["scenarios"]["base_case"]
        writer.write_three_statement_formula(base_result, "三表-公式模式")

        # DCF 估值
        writer.write_dcf(results["dcf"], "DCF估值")

        # 场景对比
        writer.write_scenario_comparison(results["scenario"], "场景对比")

        # 敏感性分析
        writer.write_sensitivity_2d(results["scenario"]["sensitivity_2d"], "敏感性分析")

        # 高级功能
        writer.write_advanced_features(
            deferred_tax=results["deferred_tax"],
            impairment=results["impairment"],
            lease=results["lease"],
            sheet_name="高级功能"
        )

        # 保存
        excel_path = SCRIPT_DIR / "财务建模报告.xlsx"
        writer.save(str(excel_path))
        print(f"  Excel 报告已生成!")

    except ImportError as e:
        print(f"  ⚠️ 跳过 Excel 导出: {e}")
    except Exception as e:
        print(f"  ❌ Excel 导出失败: {e}")

    # 生成汇总报告
    summary = {
        "_meta": {
            "company": "宁德时代",
            "period": "2025Q3",
            "generated_at": datetime.now().isoformat(),
            "model_version": "1.0"
        },
        "key_metrics": {
            "base_case": {
                "revenue": results["three_statement"]["base_case"]["income_statement"]["revenue"]["value"],
                "net_income": results["three_statement"]["base_case"]["income_statement"]["net_income"]["value"],
                "per_share_value": results["dcf"]["per_share_value"]["value"]
            }
        },
        "files_generated": [
            "三表模型报告.xlsx",
            "three_statement_base_case.json",
            "three_statement_bull_case.json",
            "three_statement_bear_case.json",
            "three_statement_all.json",
            "dcf_valuation.json",
            "deferred_tax.json",
            "impairment_test.json",
            "lease_capitalization.json",
            "scenario_analysis.json",
            "balance_input.json",
            "balance_output.json",
            "balance_diagnose.json",
            "balance_integration.json",
            "summary.json"
        ]
    }

    save_json(summary, "summary.json")

    print("\n" + "═" * 60)
    print("  建模完成！")
    print(f"  输出目录: {SCRIPT_DIR}")
    print(f"  生成文件: {len(summary['files_generated'])} 个")
    print("═" * 60 + "\n")


if __name__ == "__main__":
    main()
