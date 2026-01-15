#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Balance model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Balance:
    id: int | None
    account_code: str
    period: str
    dept_id: int = 0
    project_id: int = 0
    customer_id: int = 0
    supplier_id: int = 0
    employee_id: int = 0
    opening_balance: float = 0.0
    debit_amount: float = 0.0
    credit_amount: float = 0.0
    closing_balance: float = 0.0
