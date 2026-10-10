import json
import sqlite3
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


STAFF = [
    {"id": "S1", "name": "Owner", "role": "STAFF", "certifications": []},
    {"id": "S2", "name": "Claimer", "role": "STAFF", "certifications": ["ICU"]},
    {"id": "S3", "name": "Uncertified", "role": "STAFF", "certifications": []},
    {"id": "M1", "name": "Manager", "role": "MANAGER", "certifications": []},
]


def make_app(tmp_path, shifts):
    seed_path = tmp_path / "seed.json"
    seed_path.write_text(json.dumps({"staff": STAFF, "shifts": shifts}), encoding="utf-8")
    return create_app(tmp_path / "db.sqlite3", seed_path)


def shift(shift_id, start, end, required=None, owner="S1"):
    return {
        "id": shift_id,
        "start": start,
        "end": end,
        "required_certification": required,
        "assigned_to": owner,
    }


def post(client, path, actor):
    return client.post(path, json={"actor_id": actor})


def test_status_transitions_and_manager_restrictions(tmp_path):
    shifts = [shift("T1", "2026-03-02T07:00", "2026-03-02T15:00")]
    with TestClient(make_app(tmp_path, shifts)) as client:
        assert post(client, "/api/shifts/T1/listings", "M1").status_code == 400
        listing = post(client, "/api/shifts/T1/listings", "S1").json()
        listing_id = listing["id"]
        assert post(client, f"/api/listings/{listing_id}/claim", "M1").status_code == 400
        assert post(client, f"/api/listings/{listing_id}/claim", "S2").status_code == 200
        assert post(client, f"/api/listings/{listing_id}/unclaim", "S2").json()["status"] == "OPEN"
        assert post(client, f"/api/listings/{listing_id}/withdraw", "S1").json()["status"] == "WITHDRAWN"
        assert post(client, f"/api/listings/{listing_id}/claim", "S2").status_code == 400


def test_one_active_listing_and_approval_rejection(tmp_path):
    shifts = [shift("T1", "2026-03-02T07:00", "2026-03-02T15:00")]
    with TestClient(make_app(tmp_path, shifts)) as client:
        first = post(client, "/api/shifts/T1/listings", "S1")
        assert first.status_code == 201
        assert post(client, "/api/shifts/T1/listings", "S1").status_code == 400
        listing_id = first.json()["id"]
        assert post(client, f"/api/listings/{listing_id}/claim", "S2").status_code == 200
        assert post(client, f"/api/listings/{listing_id}/reject", "M1").json()["status"] == "REJECTED"


@pytest.mark.parametrize(
    ("target", "assigned", "expected_rule"),
    [
        (shift("T1", "2026-03-02T07:00", "2026-03-02T15:00", "ICU"), [], "required certification"),
        (
            shift("T1", "2026-03-02T10:00", "2026-03-02T18:00"),
            [shift("A1", "2026-03-02T09:00", "2026-03-02T17:00", owner="S2")],
            "overlap",
        ),
        (
            shift("T1", "2026-03-02T20:00", "2026-03-03T04:00"),
            [shift("A1", "2026-03-02T07:00", "2026-03-02T15:00", owner="S2")],
            "11-hour rest",
        ),
        (
            shift("T1", "2026-03-02T23:00", "2026-03-03T07:00"),
            [
                shift("A1", "2026-03-02T07:00", "2026-03-02T15:00", owner="S2"),
                shift("A2", "2026-03-02T15:00", "2026-03-02T23:00", owner="S2"),
                shift("A3", "2026-03-03T07:00", "2026-03-03T15:00", owner="S2"),
                shift("A4", "2026-03-04T07:00", "2026-03-04T15:00", owner="S2"),
                shift("A5", "2026-03-05T07:00", "2026-03-05T15:00", owner="S2"),
            ],
            "40-hour weekly limit",
        ),
    ],
)
def test_each_claim_rule(tmp_path, target, assigned, expected_rule):
    all_shifts = [target, shift("OWNER", "2026-03-01T07:00", "2026-03-01T15:00")]
    all_shifts.extend(assigned)
    with TestClient(make_app(tmp_path, all_shifts)) as client:
        listing_id = post(client, f"/api/shifts/{target['id']}/listings", "S1").json()["id"]
        claimer = "S3" if expected_rule == "required certification" else "S2"
        response = post(client, f"/api/listings/{listing_id}/claim", claimer)
        assert response.status_code == 400
        assert expected_rule in {reason["rule"] for reason in response.json()["reasons"]}


def test_same_owner_reports_only_rule_one(tmp_path):
    target = shift("T1", "2026-03-02T07:00", "2026-03-02T15:00", "ICU")
    with TestClient(make_app(tmp_path, [target])) as client:
        listing_id = post(client, "/api/shifts/T1/listings", "S1").json()["id"]
        response = post(client, f"/api/listings/{listing_id}/claim", "S1")
        assert response.json()["reasons"] == [
            {"rule": "different owner", "message": "claimer must differ from shift owner"}
        ]


def test_multiple_violations_and_no_longer_available_short_circuit(tmp_path):
    target = shift("T1", "2026-03-02T10:00", "2026-03-02T18:00", "PEDS")
    assigned = shift("A1", "2026-03-02T09:00", "2026-03-02T17:00", owner="S2")
    with TestClient(make_app(tmp_path, [target, assigned])) as client:
        listing_id = post(client, "/api/shifts/T1/listings", "S1").json()["id"]
        response = post(client, f"/api/listings/{listing_id}/claim", "S2")
        rules = {reason["rule"] for reason in response.json()["reasons"]}
        assert {"required certification", "overlap"}.issubset(rules)
        assert post(client, f"/api/listings/{listing_id}/withdraw", "S1").status_code == 200
        unavailable = post(client, f"/api/listings/{listing_id}/claim", "S2")
        assert unavailable.json()["detail"] == "no longer available"
        assert "reasons" not in unavailable.json()


def test_exactly_eleven_hours_is_allowed_and_week_uses_shift_start(tmp_path):
    target = shift("T1", "2026-03-02T23:00", "2026-03-03T07:00")
    prior = shift("A1", "2026-03-02T07:00", "2026-03-02T12:00", owner="S2")
    sunday = shift("A2", "2026-03-08T07:00", "2026-03-08T15:00", owner="S2")
    with TestClient(make_app(tmp_path, [target, prior, sunday])) as client:
        listing_id = post(client, "/api/shifts/T1/listings", "S1").json()["id"]
        response = post(client, f"/api/listings/{listing_id}/claim", "S2")
        assert response.status_code == 200


def test_approval_revalidates_current_assignments_and_history(tmp_path):
    target = shift("T1", "2026-03-02T07:00", "2026-03-02T15:00", "ICU")
    with TestClient(make_app(tmp_path, [target])) as client:
        listing_id = post(client, "/api/shifts/T1/listings", "S1").json()["id"]
        assert post(client, f"/api/listings/{listing_id}/claim", "S2").status_code == 200
        with sqlite3.connect(tmp_path / "db.sqlite3") as connection:
            connection.execute(
                "INSERT INTO shifts VALUES (?, ?, ?, ?, ?)",
                ("A1", "2026-03-02T08:00", "2026-03-02T16:00", None, "S2"),
            )
            connection.commit()
        response = post(client, f"/api/listings/{listing_id}/approve", "M1")
        assert response.status_code == 400
        assert response.json()["reasons"][0]["rule"] == "overlap"
        assert client.get("/api/history").json()["history"][-1]["action"] == "APPROVE"
