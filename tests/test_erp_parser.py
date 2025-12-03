# -*- coding: utf-8 -*-
"""
erp_parser 测试用例
"""

import pytest
from fin_tools.tools.erp_parser import (
    normalize_column_name,
    parse_number,
    detect_account_type,
    parse_trial_balance,
    parse_budget,
    parse_ar_aging,
    parse_ap_aging,
    parse_voucher,
    parse_cash_flow
)


class TestNormalizeColumnName:
    """列名标准化测试"""

    def test_kingdee_columns(self):
        """金蝶列名"""
        assert normalize_column_name("科目代码") == "account_code"
        assert normalize_column_name("科目名称") == "account_name"
        assert normalize_column_name("期初借方") == "opening_debit"
        assert normalize_column_name("期末贷方") == "closing_credit"

    def test_yonyou_columns(self):
        """用友列名"""
        assert normalize_column_name("会计科目") == "account_code"
        assert normalize_column_name("本期借方发生额") == "period_debit"

    def test_sap_columns(self):
        """SAP列名"""
        assert normalize_column_name("GL Account") == "account_code"
        assert normalize_column_name("Account Name") == "account_name"
        assert normalize_column_name("Beginning Debit") == "opening_debit"
        assert normalize_column_name("Ending Credit") == "closing_credit"

    def test_whitespace_handling(self):
        """空白处理"""
        assert normalize_column_name("  科目代码  ") == "account_code"
        assert normalize_column_name("科目 代码") == "account_code"

    def test_empty_column(self):
        """空列名"""
        assert normalize_column_name("") == ""
        assert normalize_column_name(None) == ""

    def test_unknown_column(self):
        """未知列名"""
        result = normalize_column_name("SomeUnknownColumn")
        assert result == "someunknowncolumn"


class TestParseNumber:
    """数值解析测试"""

    def test_basic_numbers(self):
        """基本数值"""
        assert parse_number(100) == 100.0
        assert parse_number(100.5) == 100.5
        assert parse_number("100") == 100.0
        assert parse_number("100.50") == 100.50

    def test_formatted_numbers(self):
        """格式化数值"""
        assert parse_number("1,000") == 1000.0
        assert parse_number("1,000,000.50") == 1000000.50
        assert parse_number("1，000") == 1000.0  # 中文逗号

    def test_currency_symbols(self):
        """货币符号"""
        assert parse_number("¥100") == 100.0
        assert parse_number("$1,000") == 1000.0
        assert parse_number("￥500.00") == 500.0
        assert parse_number("100元") == 100.0

    def test_negative_numbers(self):
        """负数"""
        assert parse_number("-100") == -100.0
        assert parse_number("(100)") == -100.0  # 括号表示负数
        assert parse_number("(1,000.50)") == -1000.50

    def test_empty_values(self):
        """空值"""
        assert parse_number(None) == 0.0
        assert parse_number("") == 0.0
        assert parse_number("-") == 0.0
        assert parse_number("--") == 0.0
        assert parse_number("N/A") == 0.0
        assert parse_number("无") == 0.0


class TestDetectAccountType:
    """科目类型识别测试"""

    def test_by_code(self):
        """按编码识别"""
        assert detect_account_type("1001") == "asset"
        assert detect_account_type("1002") == "asset"
        assert detect_account_type("2001") == "liability"
        assert detect_account_type("3001") == "equity"
        assert detect_account_type("4001") == "cost"
        assert detect_account_type("5001") == "revenue"
        assert detect_account_type("6001") == "expense"

    def test_by_name(self):
        """按名称识别"""
        assert detect_account_type("", "库存现金") == "asset"
        assert detect_account_type("", "银行存款") == "asset"
        assert detect_account_type("", "应收账款") == "asset"
        assert detect_account_type("", "应付账款") == "liability"
        assert detect_account_type("", "短期借款") == "liability"
        assert detect_account_type("", "实收资本") == "equity"
        assert detect_account_type("", "营业收入") == "revenue"
        assert detect_account_type("", "管理费用") == "expense"

    def test_unknown(self):
        """未知类型"""
        assert detect_account_type("", "") == "unknown"
        assert detect_account_type("9999", "其他") == "unknown"


class TestParseTrialBalance:
    """科目余额表解析测试"""

    def test_basic_parsing(self):
        """基本解析"""
        rows = [
            {
                "account_code": "1001",
                "account_name": "库存现金",
                "opening_debit": 10000,
                "opening_credit": 0,
                "period_debit": 50000,
                "period_credit": 45000,
                "closing_debit": 15000,
                "closing_credit": 0
            },
            {
                "account_code": "2001",
                "account_name": "应付账款",
                "opening_debit": 0,
                "opening_credit": 80000,
                "period_debit": 60000,
                "period_credit": 70000,
                "closing_debit": 0,
                "closing_credit": 90000
            }
        ]

        result = parse_trial_balance(rows, period="2025-11", company="测试公司")

        assert result["template"] == "trial_balance"
        assert result["period"] == "2025-11"
        assert len(result["accounts"]) == 2
        assert result["accounts"][0]["code"] == "1001"
        assert result["accounts"][0]["type"] == "asset"
        assert result["accounts"][1]["type"] == "liability"

    def test_balance_column(self):
        """合并余额列"""
        rows = [
            {
                "account_code": "1001",
                "account_name": "现金",
                "opening_balance": 10000,
                "closing_balance": 15000,
                "direction": "借"
            }
        ]

        result = parse_trial_balance(rows)
        assert result["accounts"][0]["opening_debit"] == 10000
        assert result["accounts"][0]["closing_debit"] == 15000

    def test_skip_summary_rows(self):
        """跳过汇总行"""
        rows = [
            {"account_code": "1001", "account_name": "现金", "closing_debit": 10000, "closing_credit": 0},
            {"account_code": "合计", "account_name": "", "closing_debit": 10000, "closing_credit": 0}
        ]

        result = parse_trial_balance(rows)
        assert len(result["accounts"]) == 1

    def test_summary_calculation(self):
        """汇总计算"""
        rows = [
            {"account_code": "1001", "account_name": "现金", "closing_debit": 10000, "closing_credit": 0},
            {"account_code": "1002", "account_name": "银行", "closing_debit": 20000, "closing_credit": 0}
        ]

        result = parse_trial_balance(rows)
        assert result["summary"]["account_count"] == 2
        assert result["summary"]["total_closing_debit"] == 30000

    def test_empty_rows(self):
        """空数据"""
        result = parse_trial_balance([])
        assert result["accounts"] == []
        assert result["summary"]["account_count"] == 0


class TestParseBudget:
    """预算对比表解析测试"""

    def test_basic_parsing(self):
        """基本解析"""
        rows = [
            {"account_name": "营业收入", "actual": 1000000, "budget": 1100000, "prior_year": 900000},
            {"account_name": "营业成本", "actual": 600000, "budget": 650000, "prior_year": 550000}
        ]

        result = parse_budget(rows, period="2025-11")

        assert result["template"] == "budget"
        assert len(result["line_items"]) == 2
        assert result["line_items"][0]["variance"] == -100000  # 1000000 - 1100000
        assert result["line_items"][0]["variance_pct"] == pytest.approx(-0.0909, rel=0.01)

    def test_yoy_calculation(self):
        """同比计算"""
        rows = [
            {"account_name": "收入", "actual": 1000, "budget": 900, "prior_year": 800}
        ]

        result = parse_budget(rows)
        assert result["line_items"][0]["yoy_change"] == 200
        assert result["line_items"][0]["yoy_pct"] == 0.25

    def test_zero_budget(self):
        """零预算处理"""
        rows = [
            {"account_name": "收入", "actual": 1000, "budget": 0, "prior_year": 0}
        ]

        result = parse_budget(rows)
        assert result["line_items"][0]["variance_pct"] == 0


class TestParseArAging:
    """应收账龄表解析测试"""

    def test_basic_parsing(self):
        """基本解析"""
        rows = [
            {"customer_name": "客户A", "0_30": 50000, "31_60": 20000, "61_90": 10000},
            {"customer_name": "客户B", "0_30": 30000, "31_60": 0, "61_90": 5000}
        ]

        result = parse_ar_aging(rows, as_of_date="2025-12-01")

        assert result["template"] == "ar_aging"
        assert len(result["customers"]) == 2
        assert result["customers"][0]["total"] == 80000
        assert result["summary"]["total_receivable"] == 115000

    def test_bucket_summary(self):
        """账龄汇总"""
        rows = [
            {"customer_name": "A", "0_30": 100, "31_60": 50},
            {"customer_name": "B", "0_30": 200, "31_60": 100}
        ]

        result = parse_ar_aging(rows)
        assert result["summary"]["by_bucket"]["0_30"] == 300
        assert result["summary"]["by_bucket"]["31_60"] == 150


class TestParseApAging:
    """应付账龄表解析测试"""

    def test_basic_parsing(self):
        """基本解析"""
        rows = [
            {"supplier_name": "供应商A", "0_30": 40000, "31_60": 15000}
        ]

        result = parse_ap_aging(rows, as_of_date="2025-12-01")

        assert result["template"] == "ap_aging"
        assert len(result["suppliers"]) == 1
        assert result["suppliers"][0]["total"] == 55000


class TestParseVoucher:
    """凭证解析测试"""

    def test_basic_parsing(self):
        """基本解析"""
        rows = [
            {"voucher_no": "记-001", "voucher_date": "2025-11-01", "account_code": "1001",
             "account_name": "现金", "description": "收款", "period_debit": 1000, "period_credit": 0},
            {"voucher_no": "记-001", "voucher_date": "2025-11-01", "account_code": "1122",
             "account_name": "应收账款", "description": "收款", "period_debit": 0, "period_credit": 1000}
        ]

        result = parse_voucher(rows, period="2025-11")

        assert result["template"] == "voucher"
        assert len(result["vouchers"]) == 1
        assert result["vouchers"][0]["voucher_no"] == "记-001"
        assert len(result["vouchers"][0]["entries"]) == 2
        assert result["vouchers"][0]["total_debit"] == 1000
        assert result["vouchers"][0]["total_credit"] == 1000

    def test_multiple_vouchers(self):
        """多张凭证"""
        rows = [
            {"voucher_no": "记-001", "period_debit": 100, "period_credit": 0},
            {"voucher_no": "记-001", "period_debit": 0, "period_credit": 100},
            {"voucher_no": "记-002", "period_debit": 200, "period_credit": 0},
            {"voucher_no": "记-002", "period_debit": 0, "period_credit": 200}
        ]

        result = parse_voucher(rows)
        assert len(result["vouchers"]) == 2
        assert result["summary"]["voucher_count"] == 2
        assert result["summary"]["entry_count"] == 4


class TestParseCashFlow:
    """现金流数据解析测试"""

    def test_basic_parsing(self):
        """基本解析"""
        rows = [
            {"description": "销售回款", "amount": 100000, "date": "2025-12-01"},
            {"description": "采购付款", "amount": -60000, "date": "2025-12-02"}
        ]

        result = parse_cash_flow(rows, period="2025-12")

        assert result["template"] == "cash_flow"
        assert len(result["items"]) == 2
        assert result["summary"]["total_inflow"] == 100000
        assert result["summary"]["total_outflow"] == -60000
        assert result["summary"]["net_flow"] == 40000


# ============================================================
# 边界情况测试
# ============================================================

class TestEdgeCases:
    """边界情况测试"""

    def test_string_numbers(self):
        """字符串数值"""
        rows = [
            {
                "account_code": "1001",
                "account_name": "现金",
                "opening_debit": "10,000.00",
                "closing_debit": "¥15,000"
            }
        ]

        result = parse_trial_balance(rows)
        assert result["accounts"][0]["opening_debit"] == 10000.0
        assert result["accounts"][0]["closing_debit"] == 15000.0

    def test_mixed_data_types(self):
        """混合数据类型"""
        rows = [
            {"account_code": 1001, "account_name": "现金", "closing_debit": 10000}
        ]

        result = parse_trial_balance(rows)
        assert result["accounts"][0]["code"] == "1001"

    def test_none_values(self):
        """None值处理"""
        rows = [
            {"account_code": "1001", "account_name": None, "closing_debit": None}
        ]

        result = parse_trial_balance(rows)
        assert result["accounts"][0]["name"] == ""
        assert result["accounts"][0]["closing_debit"] == 0.0

    def test_special_characters(self):
        """特殊字符"""
        rows = [
            {"customer_name": "客户A（深圳）", "0_30": 1000}
        ]

        result = parse_ar_aging(rows)
        assert result["customers"][0]["customer"] == "客户A（深圳）"

    def test_large_numbers(self):
        """大数值"""
        rows = [
            {"account_code": "1001", "account_name": "现金", "closing_debit": 1e12}
        ]

        result = parse_trial_balance(rows)
        assert result["accounts"][0]["closing_debit"] == 1e12
