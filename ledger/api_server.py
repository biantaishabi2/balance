#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HTTP API server for ledger integrations."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from ledger import api as ledger_api
from ledger import services
from ledger.database import get_db
from ledger.utils import LedgerError


class LedgerAPIServer(ThreadingHTTPServer):
    def __init__(self, server_address, handler_cls, db_path: str):
        super().__init__(server_address, handler_cls)
        self.db_path = db_path


class LedgerAPIHandler(BaseHTTPRequestHandler):
    server_version = "LedgerAPI/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        if not raw.strip():
            return {}
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LedgerError("INVALID_JSON", f"Invalid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise LedgerError("INVALID_JSON", "Payload must be a JSON object")
        return payload

    def _require_token(self) -> str:
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise LedgerError("AUTH_REQUIRED", "Missing bearer token")
        return auth[len("Bearer ") :].strip()

    def _handle_error(self, exc: Exception, status: int = 400) -> None:
        if isinstance(exc, LedgerError):
            self._send_json(status, {"error": exc.code, "message": exc.message})
            return
        self._send_json(status, {"error": "SERVER_ERROR", "message": str(exc)})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        try:
            if path == "/tokens":
                payload = self._read_json()
                tenant_id = payload.get("tenant_id")
                org_id = payload.get("org_id")
                name = payload.get("name")
                if not tenant_id or not org_id:
                    raise LedgerError("TENANT_INVALID", "tenant_id/org_id required")
                with get_db(self.server.db_path) as conn:
                    token = ledger_api.issue_token(conn, tenant_id, org_id, name=name)
                self._send_json(
                    HTTPStatus.CREATED,
                    {"token": token, "tenant_id": tenant_id, "org_id": org_id},
                )
                return

            if path == "/vouchers":
                token = self._require_token()
                payload = self._read_json()
                voucher_data = payload.get("voucher") or payload.get("voucher_data")
                entries = payload.get("entries")
                if not isinstance(voucher_data, dict) or not isinstance(entries, list):
                    raise LedgerError("INVALID_PAYLOAD", "voucher and entries required")
                status = payload.get("status") or "draft"
                auto_confirm = bool(payload.get("auto_confirm"))
                with get_db(self.server.db_path) as conn:
                    api = ledger_api.LedgerAPI(conn)
                    result = api.create_voucher(
                        token,
                        voucher_data,
                        entries,
                        status=status,
                        auto_confirm=auto_confirm,
                    )
                self._send_json(HTTPStatus.CREATED, result)
                return

            if path == "/vouchers/archive":
                token = self._require_token()
                payload = self._read_json()
                cutoff = payload.get("before_period")
                if not cutoff:
                    raise LedgerError("ARCHIVE_PERIOD_REQUIRED", "before_period required")
                with get_db(self.server.db_path) as conn:
                    api = ledger_api.LedgerAPI(conn)
                    result = api.archive_vouchers(token, cutoff)
                self._send_json(HTTPStatus.OK, result)
                return

            self._send_json(HTTPStatus.NOT_FOUND, {"error": "NOT_FOUND"})
        except LedgerError as exc:
            status = HTTPStatus.BAD_REQUEST
            if exc.code.startswith("AUTH"):
                status = HTTPStatus.UNAUTHORIZED
            self._handle_error(exc, status=status)
        except Exception as exc:  # pragma: no cover - fallback
            self._handle_error(exc, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        try:
            if path.startswith("/vouchers/"):
                token = self._require_token()
                try:
                    voucher_id = int(path.split("/")[-1])
                except ValueError as exc:
                    raise LedgerError("INVALID_VOUCHER_ID", "Invalid voucher id") from exc
                query = parse_qs(parsed.query)
                include_entries = query.get("include_entries", ["true"])[0].lower() != "false"
                include_archived = query.get("include_archived", ["true"])[0].lower() != "false"
                with get_db(self.server.db_path) as conn:
                    api = ledger_api.LedgerAPI(conn)
                    try:
                        result = api.get_voucher(
                            token,
                            voucher_id,
                            include_entries=include_entries,
                            include_archived=include_archived,
                        )
                    except LedgerError as exc:
                        if exc.code == "VOUCHER_NOT_FOUND":
                            ctx = ledger_api.get_token_context(conn, token)
                            row = conn.execute(
                                "SELECT tenant_id, org_id FROM vouchers WHERE id = ?",
                                (voucher_id,),
                            ).fetchone()
                            if row and (
                                row["tenant_id"],
                                row["org_id"],
                            ) != (ctx["tenant_id"], ctx["org_id"]):
                                services.log_audit_event(
                                    conn,
                                    "api.cross_tenant",
                                    target_type="voucher",
                                    target_id=voucher_id,
                                    detail={
                                        "requested_tenant": ctx["tenant_id"],
                                        "requested_org": ctx["org_id"],
                                        "actual_tenant": row["tenant_id"],
                                        "actual_org": row["org_id"],
                                    },
                                    context={
                                        "tenant_id": ctx["tenant_id"],
                                        "org_id": ctx["org_id"],
                                    },
                                )
                            self._send_json(
                                HTTPStatus.NOT_FOUND,
                                {"error": exc.code, "message": exc.message},
                            )
                            return
                        raise
                self._send_json(HTTPStatus.OK, result)
                return

            self._send_json(HTTPStatus.NOT_FOUND, {"error": "NOT_FOUND"})
        except LedgerError as exc:
            status = HTTPStatus.BAD_REQUEST
            if exc.code.startswith("AUTH"):
                status = HTTPStatus.UNAUTHORIZED
            if exc.code == "VOUCHER_NOT_FOUND":
                status = HTTPStatus.NOT_FOUND
            self._handle_error(exc, status=status)
        except Exception as exc:  # pragma: no cover - fallback
            self._handle_error(exc, status=HTTPStatus.INTERNAL_SERVER_ERROR)


def make_server(db_path: str, host: str = "127.0.0.1", port: int = 0) -> LedgerAPIServer:
    return LedgerAPIServer((host, port), LedgerAPIHandler, db_path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ledger HTTP API server")
    parser.add_argument("--db-path", required=True, help="Database path")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    server = make_server(args.db_path, host=args.host, port=args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
