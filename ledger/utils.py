#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared helpers for ledger CLI."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class LedgerError(Exception):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "error": True,
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        return payload


def load_json_input() -> Dict[str, Any]:
    """Load JSON object from stdin."""
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        raise LedgerError(
            code="INVALID_JSON",
            message=f"无效的 JSON 输入: {exc}",
        ) from exc

    if not isinstance(data, dict):
        raise LedgerError(
            code="INVALID_JSON",
            message="输入必须是 JSON 对象（键值对）",
        )
    return data


def print_json(data: Dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def print_error(err: LedgerError) -> None:
    print_json(err.to_dict())


def handle_error(err: LedgerError) -> None:
    print_error(err)
    sys.exit(1)
