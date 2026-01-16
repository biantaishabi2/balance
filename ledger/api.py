#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Token-based API helpers for ledger integrations."""

from __future__ import annotations

import secrets
from typing import Any, Dict, List, Optional

from ledger import services
from ledger.utils import LedgerError
from ledger.webhooks import record_event


def _ensure_tenant_org(conn, tenant_id: str, org_id: str) -> None:
    if not tenant_id or not org_id:
        raise LedgerError("TENANT_INVALID", "Missing tenant or org context")
    conn.execute(
        "INSERT OR IGNORE INTO tenants (id, name) VALUES (?, ?)",
        (tenant_id, tenant_id),
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO organizations (tenant_id, id, name)
        VALUES (?, ?, ?)
        """,
        (tenant_id, org_id, org_id),
    )


def issue_token(
    conn, tenant_id: str, org_id: str, name: Optional[str] = None
) -> str:
    _ensure_tenant_org(conn, tenant_id, org_id)
    token = secrets.token_urlsafe(24)
    conn.execute(
        """
        INSERT INTO api_tokens (token, tenant_id, org_id, name)
        VALUES (?, ?, ?, ?)
        """,
        (token, tenant_id, org_id, name),
    )
    return token


def revoke_token(conn, token: str) -> None:
    conn.execute(
        "UPDATE api_tokens SET revoked_at = CURRENT_TIMESTAMP WHERE token = ?",
        (token,),
    )


def get_token_context(conn, token: str) -> Dict[str, str]:
    row = conn.execute(
        "SELECT token, tenant_id, org_id, revoked_at FROM api_tokens WHERE token = ?",
        (token,),
    ).fetchone()
    if not row:
        raise LedgerError("AUTH_INVALID", "Invalid API token")
    if row["revoked_at"]:
        raise LedgerError("AUTH_REVOKED", "API token revoked")
    return {"tenant_id": row["tenant_id"], "org_id": row["org_id"], "token": row["token"]}


class LedgerAPI:
    """Lightweight integration API wrapper."""

    def __init__(self, conn):
        self.conn = conn

    def issue_token(self, tenant_id: str, org_id: str, name: Optional[str] = None) -> str:
        return issue_token(self.conn, tenant_id, org_id, name=name)

    def revoke_token(self, token: str) -> None:
        revoke_token(self.conn, token)

    def create_voucher(
        self,
        token: str,
        voucher_data: Dict[str, Any],
        entries: List[Dict[str, Any]],
        status: str = "draft",
        auto_confirm: bool = False,
    ) -> Dict[str, Any]:
        ctx = get_token_context(self.conn, token)
        tenant_id = ctx["tenant_id"]
        org_id = ctx["org_id"]

        built_entries, total_debit, total_credit = services.build_entries(
            self.conn,
            entries,
            tenant_id=tenant_id,
            org_id=org_id,
        )
        voucher_id, voucher_no, period, _ = services.insert_voucher(
            self.conn,
            voucher_data,
            built_entries,
            status,
            tenant_id=tenant_id,
            org_id=org_id,
        )
        result = {
            "voucher_id": voucher_id,
            "voucher_no": voucher_no,
            "period": period,
            "status": status,
            "debit_total": round(total_debit, 2),
            "credit_total": round(total_credit, 2),
        }

        record_event(
            self.conn,
            tenant_id,
            org_id,
            "voucher.created",
            {
                "voucher_id": voucher_id,
                "voucher_no": voucher_no,
                "period": period,
                "status": status,
            },
        )

        if auto_confirm:
            if status == "draft":
                services.review_voucher(
                    self.conn, voucher_id, tenant_id=tenant_id, org_id=org_id
                )
            if status in {"draft", "reviewed"}:
                confirmed = services.confirm_voucher(
                    self.conn, voucher_id, tenant_id=tenant_id, org_id=org_id
                )
                result["status"] = confirmed["status"]
                record_event(
                    self.conn,
                    tenant_id,
                    org_id,
                    "voucher.confirmed",
                    {
                        "voucher_id": voucher_id,
                        "voucher_no": voucher_no,
                        "period": period,
                    },
                )

        return result

    def get_voucher(
        self,
        token: str,
        voucher_id: int,
        include_entries: bool = True,
        include_archived: bool = True,
    ) -> Dict[str, Any]:
        ctx = get_token_context(self.conn, token)
        tenant_id = ctx["tenant_id"]
        org_id = ctx["org_id"]
        voucher = services.fetch_voucher(
            self.conn,
            voucher_id,
            tenant_id=tenant_id,
            org_id=org_id,
            include_archived=include_archived,
        )
        if not voucher:
            raise LedgerError("VOUCHER_NOT_FOUND", f"Voucher not found: {voucher_id}")
        if include_entries:
            voucher["entries"] = services.fetch_entries(
                self.conn,
                voucher_id,
                tenant_id=tenant_id,
                org_id=org_id,
                include_archived=include_archived,
            )
        return voucher

    def list_vouchers(
        self,
        token: str,
        period: Optional[str] = None,
        status: Optional[str] = None,
        include_archived: bool = False,
    ) -> List[Dict[str, Any]]:
        ctx = get_token_context(self.conn, token)
        tenant_id = ctx["tenant_id"]
        org_id = ctx["org_id"]
        conditions = ["tenant_id = ? AND org_id = ?"]
        params: List[Any] = [tenant_id, org_id]
        if period:
            conditions.append("period = ?")
            params.append(period)
        if status:
            conditions.append("status = ?")
            params.append(status)
        if not include_archived:
            conditions.append("archived_at IS NULL")
        where_clause = " AND ".join(conditions)
        rows = self.conn.execute(
            f"SELECT * FROM vouchers WHERE {where_clause} ORDER BY date, id",
            params,
        ).fetchall()
        return [dict(row) for row in rows]

    def archive_vouchers(self, token: str, before_period: str) -> Dict[str, Any]:
        ctx = get_token_context(self.conn, token)
        tenant_id = ctx["tenant_id"]
        org_id = ctx["org_id"]
        result = services.archive_vouchers(
            self.conn,
            before_period,
            tenant_id=tenant_id,
            org_id=org_id,
        )
        record_event(
            self.conn,
            tenant_id,
            org_id,
            "vouchers.archived",
            result,
        )
        return result
