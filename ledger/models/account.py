#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Account model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Account:
    code: str
    name: str
    level: int
    parent_code: str | None
    type: str
    direction: str
    cash_flow: str | None = None
    is_enabled: bool = True
    is_system: bool = False
