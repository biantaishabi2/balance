import json
import threading
from http.client import HTTPConnection

from ledger.api_server import make_server
from ledger.database import get_db, init_db
from ledger.services import load_standard_accounts


BASIC_ACCOUNTS = [
    {"code": "1001", "name": "Cash", "level": 1, "type": "asset", "direction": "debit"},
    {"code": "2001", "name": "Loan", "level": 1, "type": "liability", "direction": "credit"},
]


def _request_json(host, port, method, path, body=None, token=None):
    conn = HTTPConnection(host, port, timeout=5)
    headers = {}
    payload = None
    if body is not None:
        payload = json.dumps(body)
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    conn.request(method, path, body=payload, headers=headers)
    response = conn.getresponse()
    data = response.read().decode("utf-8")
    conn.close()
    return response.status, json.loads(data) if data else {}


def test_http_api_voucher_flow_and_archive(tmp_path):
    db_path = tmp_path / "ledger_http.db"
    with get_db(str(db_path)) as conn:
        init_db(conn)
        load_standard_accounts(conn, BASIC_ACCOUNTS, tenant_id="t1", org_id="o1")
        load_standard_accounts(conn, BASIC_ACCOUNTS, tenant_id="t2", org_id="o2")

    server = make_server(str(db_path), host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, token_payload = _request_json(
            host,
            port,
            "POST",
            "/tokens",
            {"tenant_id": "t1", "org_id": "o1", "name": "tenant-a"},
        )
        assert status == 201
        token_a = token_payload["token"]

        status, token_payload = _request_json(
            host,
            port,
            "POST",
            "/tokens",
            {"tenant_id": "t2", "org_id": "o2", "name": "tenant-b"},
        )
        assert status == 201
        token_b = token_payload["token"]

        voucher_body = {
            "voucher": {"date": "2025-01-05", "description": "HTTP voucher"},
            "entries": [
                {
                    "account": "1001",
                    "debit": 500,
                    "credit": 0,
                },
                {
                    "account": "2001",
                    "debit": 0,
                    "credit": 500,
                },
            ],
            "status": "reviewed",
            "auto_confirm": True,
        }
        status, created = _request_json(
            host, port, "POST", "/vouchers", voucher_body, token=token_a
        )
        assert status == 201
        voucher_id = created["voucher_id"]

        status, fetched = _request_json(
            host, port, "GET", f"/vouchers/{voucher_id}", token=token_a
        )
        assert status == 200
        assert fetched["voucher_no"] == created["voucher_no"]
        assert fetched["entries"]

        status, denied = _request_json(
            host, port, "GET", f"/vouchers/{voucher_id}", token=token_b
        )
        assert status == 404
        assert denied["error"] == "VOUCHER_NOT_FOUND"

        status, archive_payload = _request_json(
            host,
            port,
            "POST",
            "/vouchers/archive",
            {"before_period": "2025-01"},
            token=token_a,
        )
        assert status == 200
        assert archive_payload["voucher_count"] == 1

        status, hidden = _request_json(
            host,
            port,
            "GET",
            f"/vouchers/{voucher_id}?include_archived=false",
            token=token_a,
        )
        assert status == 404
        assert hidden["error"] == "VOUCHER_NOT_FOUND"

        status, archived = _request_json(
            host,
            port,
            "GET",
            f"/vouchers/{voucher_id}?include_archived=true",
            token=token_a,
        )
        assert status == 200
        assert archived["voucher_no"] == created["voucher_no"]

        with get_db(str(db_path)) as conn:
            row = conn.execute(
                "SELECT action FROM audit_logs WHERE action = 'api.cross_tenant'"
            ).fetchone()
            assert row is not None
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
