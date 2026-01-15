#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dimension model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Dimension:
    id: int | None
    type: str
    code: str
    name: str
    parent_id: int | None = None
    extra: str | None = None
    is_enabled: bool = True
