import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.database import DEFAULT_BACKUP_PATH
from app.main import create_app


def test_database_initializes_from_seed_once(tmp_path):
    database_path = tmp_path / "shiftswap.sqlite3"
    app = create_app(database_path)

    with TestClient(app) as client:
        health = client.get("/api/health")
        staff = client.get("/api/staff")
        shifts = client.get("/api/shifts")
        listings = client.get("/api/listings")
        history = client.get("/api/history")

    assert health.json() == {"status": "ok", "database": "sqlite"}
    assert len(staff.json()["staff"]) == 10
    assert len(shifts.json()["shifts"]) == 61
    assert listings.json() == {"listings": []}
    assert history.json()["history"][0]["action"] == "SEED_INITIALIZED"

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM staff").fetchone()[0] == 10
        assert connection.execute("SELECT COUNT(*) FROM shifts").fetchone()[0] == 61


def test_saved_state_survives_application_restart(tmp_path):
    database_path = tmp_path / "shiftswap.sqlite3"
    first_app = create_app(database_path)

    with TestClient(first_app) as client:
        client.get("/api/health")
        with sqlite3.connect(database_path) as connection:
            connection.execute(
                """
                INSERT INTO listings (shift_id, listed_by)
                VALUES (?, ?)
                """,
                ("SH001", "S2"),
            )
            connection.commit()

    restarted_app = create_app(database_path)
    with TestClient(restarted_app) as client:
        listings = client.get("/api/listings").json()["listings"]
        staff = client.get("/api/staff").json()["staff"]
        shifts = client.get("/api/shifts").json()["shifts"]
        history = client.get("/api/history").json()["history"]

    assert len(staff) == 10
    assert len(shifts) == 61
    assert len(listings) == 1
    assert listings[0]["shift_id"] == "SH001"
    assert [event["action"] for event in history].count("SEED_INITIALIZED") == 1


def test_missing_seed_uses_bundled_backup(tmp_path):
    assert Path(DEFAULT_BACKUP_PATH).exists()
    database_path = tmp_path / "shiftswap.sqlite3"
    missing_seed = tmp_path / "missing-seed.json"
    app = create_app(database_path, missing_seed)

    with TestClient(app) as client:
        assert len(client.get("/api/staff").json()["staff"]) == 10
        assert len(client.get("/api/shifts").json()["shifts"]) == 61


def test_deployed_frontend_origin_is_allowed(tmp_path):
    app = create_app(tmp_path / "shiftswap.sqlite3", tmp_path / "missing-seed.json")

    with TestClient(app) as client:
        response = client.options(
            "/api/health",
            headers={
                "Origin": "https://shiftswap-discover-dollar.vercel.app",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "https://shiftswap-discover-dollar.vercel.app"
    )
