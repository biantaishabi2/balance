#!/usr/bin/env python3
"""
excel2json - 从 Excel 提取财务数据生成 input.json

用法:
    excel2json 财务报表.xlsx > input.json
    excel2json 财务报表.xlsx --mapping mapping.json > input.json
"""

import sys
import json
import argparse
from pathlib import Path

try:
    import openpyxl
except ImportError:
    print("错误: 需要安装 openpyxl (pip install openpyxl)", file=sys.stderr)
    sys.exit(1)


# 默认字段映射：Excel位置 -> JSON字段
# 格式: "sheet名.行号.列号" 或 "sheet名.科目名.列号"
DEFAULT_MAPPING = {
    # 资产负债表 - 期初数据
    "资产负债表": {
        "现金": "opening_cash",
        "应收账款": "opening_receivable",
        "存货": "opening_inventory",
        "固定资产原值": "fixed_asset_cost",
        "累计折旧": "accum_depreciation",
        "短期借款": "opening_debt",
        "应付账款": "opening_payable",
        "股本": "opening_equity",
        "留存收益": "opening_retained",
    },
    # 损益表
    "损益表": {
        "营业收入": "revenue",
        "营业成本": "cost",
        "其他费用": "other_expense",
    },
    # 参数表
    "参数": {
        "利率": "interest_rate",
        "税率": "tax_rate",
        "折旧年限": "fixed_asset_life",
        "残值": "fixed_asset_salvage",
        "分红": "dividend",
        "资本支出": "capex",
        "最低现金": "min_cash",
        "还款": "repayment",
        "新增股本": "new_equity",
    },
}


def find_value_by_label(sheet, label: str, value_col: int = 2) -> float | None:
    """
    在 sheet 中查找标签对应的值

    Args:
        sheet: openpyxl sheet 对象
        label: 要查找的标签（第一列）
        value_col: 值所在的列号（默认第2列，即B列）

    Returns:
        找到的数值，或 None
    """
    for row in sheet.iter_rows(min_row=1, max_row=100):
        cell_label = row[0].value
        if cell_label and str(cell_label).strip() == label:
            # 找到标签，取对应列的值
            if len(row) >= value_col:
                val = row[value_col - 1].value
                if val is not None:
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return None
    return None


def extract_from_excel(filepath: str, mapping: dict = None, value_col: int = 2) -> dict:
    """
    从 Excel 提取数据

    Args:
        filepath: Excel 文件路径
        mapping: 字段映射配置
        value_col: 值所在的列（默认2=B列，期初数据）

    Returns:
        提取的数据字典
    """
    if mapping is None:
        mapping = DEFAULT_MAPPING

    wb = openpyxl.load_workbook(filepath, data_only=True)
    result = {}

    for sheet_name, fields in mapping.items():
        # 尝试匹配 sheet 名（支持模糊匹配）
        target_sheet = None
        for name in wb.sheetnames:
            if sheet_name in name or name in sheet_name:
                target_sheet = wb[name]
                break

        if target_sheet is None:
            print(f"警告: 未找到 sheet '{sheet_name}'", file=sys.stderr)
            continue

        for label, json_field in fields.items():
            val = find_value_by_label(target_sheet, label, value_col)
            if val is not None:
                # 处理负数（累计折旧等）
                if "折旧" in label and val > 0:
                    val = abs(val)  # 确保累计折旧是正数
                if "成本" in label or "费用" in label:
                    val = abs(val)  # 确保成本费用是正数
                result[json_field] = val
            else:
                print(f"警告: 未找到 '{sheet_name}.{label}'", file=sys.stderr)

    wb.close()
    return result


def main():
    parser = argparse.ArgumentParser(
        description="从 Excel 提取财务数据生成 input.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    excel2json 财务报表.xlsx > input.json
    excel2json 财务报表.xlsx --col 3 > input.json  # 取C列数据
    excel2json 财务报表.xlsx --mapping my_mapping.json > input.json

Excel 格式要求:
    - Sheet "资产负债表": A列科目名, B列期初值
    - Sheet "损益表": A列科目名, B列金额
    - Sheet "参数": A列参数名, B列参数值
        """
    )
    parser.add_argument("excel_file", help="Excel 文件路径")
    parser.add_argument(
        "--col", "-c",
        type=int,
        default=2,
        help="数据所在列号 (默认2=B列)"
    )
    parser.add_argument(
        "--mapping", "-m",
        help="自定义映射配置文件 (JSON格式)"
    )
    parser.add_argument(
        "--pretty", "-p",
        action="store_true",
        default=True,
        help="格式化输出 (默认)"
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="紧凑输出"
    )

    args = parser.parse_args()

    # 检查文件存在
    if not Path(args.excel_file).exists():
        print(f"错误: 文件不存在 '{args.excel_file}'", file=sys.stderr)
        sys.exit(1)

    # 加载自定义映射
    mapping = None
    if args.mapping:
        with open(args.mapping) as f:
            mapping = json.load(f)

    # 提取数据
    data = extract_from_excel(args.excel_file, mapping, args.col)

    # 输出
    if args.compact:
        print(json.dumps(data, ensure_ascii=False))
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
