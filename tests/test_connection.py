from ledger.database import get_db, init_db


def test_connection_commit(tmp_path):
    db_path = tmp_path / "ledger.db"
    with get_db(str(db_path)) as conn:
        init_db(conn)
        conn.execute(
            "INSERT INTO periods (period, status) VALUES ('2025-01', 'open')"
        )

    with get_db(str(db_path)) as conn:
        row = conn.execute("SELECT period FROM periods").fetchone()
        assert row["period"] == "2025-01"


def test_connection_rollback(tmp_path):
    db_path = tmp_path / "ledger.db"
    try:
        with get_db(str(db_path)) as conn:
            init_db(conn)
            conn.execute(
                "INSERT INTO periods (period, status) VALUES ('2025-02', 'open')"
            )
            raise RuntimeError("force rollback")
    except RuntimeError:
        pass

    with get_db(str(db_path)) as conn:
        rows = conn.execute("SELECT * FROM periods").fetchall()
        assert rows == []
