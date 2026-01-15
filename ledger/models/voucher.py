#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Voucher models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class VoucherEntry:
    account_code: str
    debit_amount: float = 0.0
    credit_amount: float = 0.0
    description: str | None = None
    account_name: str | None = None
    dept_id: int | None = None
    project_id: int | None = None
    customer_id: int | None = None
    supplier_id: int | None = None
    employee_id: int | None = None


@dataclass
class Voucher:
    id: int | None = None
    voucher_no: str | None = None
    date: str | None = None
    period: str | None = None
    description: str | None = None
    status: str = "draft"
    entries: List[VoucherEntry] | None = None

    def is_balanced(self, tolerance: float = 0.01) -> bool:
        entries = self.entries or []
        total_debit = sum(e.debit_amount for e in entries)
        total_credit = sum(e.credit_amount for e in entries)
        return abs(total_debit - total_credit) < tolerance
