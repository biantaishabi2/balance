#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Webhook event helpers."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ledger.utils import LedgerError


def record_event(
    conn,
    tenant_id: str,
    org_id: str,
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
    status: str = "pending",
) -> int:
    if not tenant_id or not org_id:
        raise LedgerError("TENANT_INVALID", "Missing tenant or org context")
    if not event_type:
        raise LedgerError("EVENT_TYPE_INVALID", "Webhook event type is required")
    payload_json = json.dumps(payload or {}, ensure_ascii=True)
    cur = conn.execute(
        """
        INSERT INTO webhook_events (tenant_id, org_id, event_type, payload, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        (tenant_id, org_id, event_type, payload_json, status),
    )
    return int(cur.lastrowid)


def list_events(
    conn,
    tenant_id: str,
    org_id: str,
    status: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    conditions = ["tenant_id = ? AND org_id = ?"]
    params: List[Any] = [tenant_id, org_id]
    if status:
        conditions.append("status = ?")
        params.append(status)
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = (
        "SELECT * FROM webhook_events "
        f"{where_clause} ORDER BY id"
    )
    if limit:
        query += " LIMIT ?"
        params.append(limit)
    rows = conn.execute(query, params).fetchall()
    events: List[Dict[str, Any]] = []
    for row in rows:
        payload = {}
        if row["payload"]:
            payload = json.loads(row["payload"])
        events.append({**dict(row), "payload": payload})
    return events


def mark_event_delivered(conn, event_id: int) -> None:
    conn.execute(
        """
        UPDATE webhook_events
        SET status = 'delivered', delivered_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (event_id,),
    )
