# -*- coding: utf-8 -*-
"""
场景管理器

支持多情景切换、对比和敏感性分析

功能:
- 保存/加载场景
- 场景对比
- 单参数敏感性分析
- 双参数敏感性矩阵
"""

from typing import Dict, List, Any, Optional
from .three_statement import ThreeStatementModel


class ScenarioManager:
    """
    场景管理器

    功能:
      - 保存/加载场景
      - 场景对比
      - 参数联动（改一个自动重算）
      - 敏感性分析

    使用方法:
        sm = ScenarioManager(base_data)
        sm.add_scenario("base_case", assumptions, "维持当前趋势")
        sm.add_scenario("bull_case", bull_assumptions, "乐观情景")

        # 运行单个场景
        result = sm.run_scenario("base_case")

        # 对比多个场景
        comparison = sm.compare_scenarios(["base_case", "bull_case", "bear_case"])

        # 敏感性分析
        sens = sm.sensitivity_1d("growth_rate", [0.05, 0.09, 0.12, 0.15])
    """

    def __init__(self, base_data: dict):
        """
        初始化场景管理器

        Args:
            base_data: 基础财报数据（上期数据）
        """
        self.base_data = base_data
        self.scenarios: Dict[str, Dict[str, Any]] = {}
        self.results: Dict[str, Dict[str, Any]] = {}

    def add_scenario(self,
                     name: str,
                     assumptions: dict,
                     description: str = "") -> None:
        """
        添加场景

        Args:
            name: 场景名称（如 "base_case", "bull_case"）
            assumptions: 假设参数字典
            description: 场景描述
        """
        self.scenarios[name] = {
            "name": name,
            "description": description,
            "assumptions": assumptions.copy()
        }

    def get_scenario(self, name: str) -> Optional[dict]:
        """
        获取场景假设

        Args:
            name: 场景名称

        Returns:
            dict: 场景信息，包含 name, description, assumptions
        """
        return self.scenarios.get(name)

    def update_assumption(self,
                          scenario_name: str,
                          param: str,
                          value: float) -> None:
        """
        更新场景中的单个假设参数

        Args:
            scenario_name: 场景名称
            param: 参数名
            value: 新值
        """
        if scenario_name in self.scenarios:
            self.scenarios[scenario_name]["assumptions"][param] = value
            # 清除缓存的结果
            if scenario_name in self.results:
                del self.results[scenario_name]

    def run_scenario(self, name: str, use_cache: bool = True) -> dict:
        """
        运行单个场景，返回完整三表

        Args:
            name: 场景名称
            use_cache: 是否使用缓存结果

        Returns:
            dict: 三表模型结果
        """
        if use_cache and name in self.results:
            return self.results[name]

        scenario = self.scenarios.get(name)
        if not scenario:
            raise ValueError(f"场景不存在: {name}")

        model = ThreeStatementModel(self.base_data, scenario=name)
        result = model.build(scenario["assumptions"])

        # 添加场景信息
        result["_scenario"] = {
            "name": name,
            "description": scenario["description"]
        }

        # 缓存结果
        self.results[name] = result

        return result

    def run_all_scenarios(self) -> Dict[str, dict]:
        """
        运行所有场景

        Returns:
            dict: {场景名: 结果}
        """
        results = {}
        for name in self.scenarios:
            results[name] = self.run_scenario(name)
        return results

    def compare_scenarios(self,
                          names: List[str] = None,
                          metrics: List[str] = None) -> Dict[str, Any]:
        """
        对比多个场景

        Args:
            names: 要对比的场景名称列表，默认所有场景
            metrics: 要对比的指标列表，默认常用指标

        Returns:
            dict: 对比结果
        """
        if names is None:
            names = list(self.scenarios.keys())

        if metrics is None:
            metrics = [
                ("revenue", "营业收入"),
                ("cost", "营业成本"),
                ("gross_profit", "毛利"),
                ("ebit", "营业利润"),
                ("net_income", "净利润"),
                ("gross_margin", "毛利率"),
                ("net_margin", "净利率"),
            ]

        # 运行所有需要的场景
        results = {name: self.run_scenario(name) for name in names}

        # 构建对比表
        comparison = {
            "headers": ["指标"] + names,
            "rows": []
        }

        for metric_key, metric_label in metrics:
            row = {"metric": metric_label}

            for name in names:
                result = results[name]
                income = result["income_statement"]

                if metric_key == "gross_margin":
                    # 毛利率
                    value = income["gross_profit"]["value"] / income["revenue"]["value"]
                    row[name] = f"{value:.1%}"
                elif metric_key == "net_margin":
                    # 净利率
                    value = income["net_income"]["value"] / income["revenue"]["value"]
                    row[name] = f"{value:.1%}"
                elif metric_key in income:
                    value = income[metric_key]["value"]
                    row[name] = round(value, 0)
                else:
                    row[name] = "N/A"

            comparison["rows"].append(row)

        # 验证排序（Bull > Base > Bear）
        if all(n in results for n in ["bull_case", "base_case", "bear_case"]):
            bull_ni = results["bull_case"]["income_statement"]["net_income"]["value"]
            base_ni = results["base_case"]["income_statement"]["net_income"]["value"]
            bear_ni = results["bear_case"]["income_statement"]["net_income"]["value"]

            comparison["validation"] = {
                "is_valid": bull_ni > base_ni > bear_ni,
                "message": "Bull > Base > Bear" if bull_ni > base_ni > bear_ni else "排序不符合预期"
            }

        return comparison

    def sensitivity_1d(self,
                       param: str,
                       values: List[float],
                       base_scenario: str = "base_case",
                       output_metric: str = "net_income") -> Dict[str, Any]:
        """
        单参数敏感性分析

        Args:
            param: 要变动的参数名（如 "growth_rate"）
            values: 参数值列表
            base_scenario: 基准场景名称
            output_metric: 输出指标

        Returns:
            dict: 敏感性分析结果
        """
        base = self.scenarios.get(base_scenario)
        if not base:
            raise ValueError(f"基准场景不存在: {base_scenario}")

        results = []

        for value in values:
            # 复制基准假设
            assumptions = base["assumptions"].copy()
            assumptions[param] = value

            # 运行模型
            model = ThreeStatementModel(self.base_data)
            result = model.build(assumptions)

            # 提取输出指标
            if output_metric in result["income_statement"]:
                output_value = result["income_statement"][output_metric]["value"]
            elif output_metric in result["cash_flow"]:
                output_value = result["cash_flow"][output_metric]["value"]
            else:
                output_value = None

            results.append({
                param: value,
                output_metric: output_value
            })

        return {
            "param": param,
            "output_metric": output_metric,
            "base_scenario": base_scenario,
            "data": results
        }

    def sensitivity_2d(self,
                       param1: str,
                       values1: List[float],
                       param2: str,
                       values2: List[float],
                       base_scenario: str = "base_case",
                       output_metric: str = "net_income") -> Dict[str, Any]:
        """
        双参数敏感性矩阵

        Args:
            param1: 第一个参数（行）
            values1: 第一个参数的值列表
            param2: 第二个参数（列）
            values2: 第二个参数的值列表
            base_scenario: 基准场景名称
            output_metric: 输出指标

        Returns:
            dict: 敏感性矩阵
        """
        base = self.scenarios.get(base_scenario)
        if not base:
            raise ValueError(f"基准场景不存在: {base_scenario}")

        matrix = []

        for v1 in values1:
            row = {param1: v1}

            for v2 in values2:
                # 复制基准假设
                assumptions = base["assumptions"].copy()
                assumptions[param1] = v1
                assumptions[param2] = v2

                # 运行模型
                model = ThreeStatementModel(self.base_data)
                result = model.build(assumptions)

                # 提取输出指标
                if output_metric in result["income_statement"]:
                    output_value = result["income_statement"][output_metric]["value"]
                else:
                    output_value = None

                # 格式化列键
                col_key = f"{param2}={v2}"
                row[col_key] = round(output_value, 0) if output_value else "N/A"

            matrix.append(row)

        return {
            "headers": {
                "rows": param1,
                "columns": param2
            },
            "output_metric": output_metric,
            "data": matrix
        }

    def print_comparison(self, names: List[str] = None) -> None:
        """
        打印场景对比表

        Args:
            names: 要对比的场景名称列表
        """
        comparison = self.compare_scenarios(names)

        # 打印表头
        headers = comparison["headers"]
        print(f"\n{'指标':<15}", end="")
        for name in headers[1:]:
            print(f"{name:>18}", end="")
        print("\n" + "-" * (15 + 18 * len(headers[1:])))

        # 打印数据行
        for row in comparison["rows"]:
            print(f"{row['metric']:<15}", end="")
            for name in headers[1:]:
                value = row[name]
                if isinstance(value, (int, float)):
                    print(f"{value:>18,.0f}", end="")
                else:
                    print(f"{value:>18}", end="")
            print()

        # 打印验证结果
        if "validation" in comparison:
            v = comparison["validation"]
            status = "✅" if v["is_valid"] else "❌"
            print(f"\n场景合理性检验: {status} {v['message']}")

    def print_sensitivity_1d(self, param: str, values: List[float],
                              output_metric: str = "net_income") -> None:
        """
        打印单参数敏感性分析结果
        """
        result = self.sensitivity_1d(param, values, output_metric=output_metric)

        print(f"\n敏感性分析: {param} vs {output_metric}")
        print("-" * 40)

        for row in result["data"]:
            param_val = row[param]
            metric_val = row[output_metric]
            if isinstance(param_val, float) and param_val < 1:
                print(f"  {param}={param_val:.1%}:  {metric_val:>15,.0f}")
            else:
                print(f"  {param}={param_val}:  {metric_val:>15,.0f}")

    def print_sensitivity_2d(self, param1: str, values1: List[float],
                              param2: str, values2: List[float],
                              output_metric: str = "net_income") -> None:
        """
        打印双参数敏感性矩阵
        """
        result = self.sensitivity_2d(param1, values1, param2, values2,
                                      output_metric=output_metric)

        print(f"\n敏感性矩阵: {output_metric}")
        print(f"{param1} \\ {param2}", end="")

        # 打印列头
        for v2 in values2:
            if isinstance(v2, float) and v2 < 1:
                print(f"{v2:>12.1%}", end="")
            else:
                print(f"{v2:>12}", end="")
        print()
        print("-" * (15 + 12 * len(values2)))

        # 打印数据
        for row in result["data"]:
            v1 = row[param1]
            if isinstance(v1, float) and v1 < 1:
                print(f"{v1:<12.1%}", end="")
            else:
                print(f"{v1:<12}", end="")

            for v2 in values2:
                col_key = f"{param2}={v2}"
                val = row.get(col_key, "N/A")
                if isinstance(val, (int, float)):
                    print(f"{val:>12,.0f}", end="")
                else:
                    print(f"{val:>12}", end="")
            print()
