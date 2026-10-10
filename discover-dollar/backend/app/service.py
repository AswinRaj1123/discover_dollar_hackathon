import json
from datetime import datetime

from .database import Database
from .rules import validate_claim


class DomainError(Exception):
    def __init__(self, message: str, status_code: int = 400, reasons: list[dict] | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.reasons = reasons or []


class ShiftSwapService:
    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def _staff(connection, staff_id: str):
        return connection.execute("SELECT * FROM staff WHERE id = ?", (staff_id,)).fetchone()

    @staticmethod
    def _shift(connection, shift_id: str):
        return connection.execute("SELECT * FROM shifts WHERE id = ?", (shift_id,)).fetchone()

    @staticmethod
    def _listing(connection, listing_id: int):
        return connection.execute("SELECT * FROM listings WHERE id = ?", (listing_id,)).fetchone()

    @staticmethod
    def _is_manager(staff) -> bool:
        return staff is not None and staff["role"] == "MANAGER"

    @staticmethod
    def _history(connection, actor_id, action, shift_id, outcome, details=None):
        connection.execute(
            """
            INSERT INTO action_history
                (action, actor_id, entity_type, entity_id, details_json)
            VALUES (?, ?, 'shift', ?, ?)
            """,
            (action, actor_id, shift_id, json.dumps({"outcome": outcome, **(details or {})})),
        )

    def _fail(self, connection, actor_id, action, shift_id, error: DomainError):
        self._history(connection, actor_id, action, shift_id, "REJECTED", {
            "message": error.message,
            "reasons": error.reasons,
        })
        connection.commit()
        raise error

    def post(self, actor_id: str, shift_id: str):
        with self.database.connection() as connection:
            actor = self._staff(connection, actor_id)
            shift = self._shift(connection, shift_id)
            if not shift:
                self._fail(connection, actor_id, "POST", shift_id, DomainError("shift not found", 404))
            if not actor:
                self._fail(connection, actor_id, "POST", shift_id, DomainError("staff not found", 404))
            if self._is_manager(actor):
                self._fail(connection, actor_id, "POST", shift_id, DomainError("managers cannot post shifts"))
            if shift["assigned_to"] != actor_id:
                self._fail(connection, actor_id, "POST", shift_id, DomainError("only the shift owner can post it"))
            active = connection.execute(
                "SELECT 1 FROM listings WHERE shift_id = ? AND status IN ('OPEN', 'CLAIMED')",
                (shift_id,),
            ).fetchone()
            if active:
                self._fail(connection, actor_id, "POST", shift_id, DomainError("shift already has an active listing"))
            cursor = connection.execute(
                "INSERT INTO listings (shift_id, listed_by) VALUES (?, ?)", (shift_id, actor_id)
            )
            self._history(connection, actor_id, "POST", shift_id, "SUCCESS")
            return dict(self._listing(connection, cursor.lastrowid))

    def _transition(self, actor_id: str, listing_id: int, action: str, expected_status: str, new_status: str):
        with self.database.connection() as connection:
            listing = self._listing(connection, listing_id)
            shift_id = listing["shift_id"] if listing else None
            actor = self._staff(connection, actor_id)
            if not listing:
                self._fail(connection, actor_id, action, None, DomainError("listing not found", 404))
            if not actor:
                self._fail(connection, actor_id, action, shift_id, DomainError("staff not found", 404))
            if listing["status"] != expected_status:
                self._fail(connection, actor_id, action, shift_id, DomainError("invalid listing status"))
            if action == "WITHDRAW" and listing["listed_by"] != actor_id:
                self._fail(connection, actor_id, action, shift_id, DomainError("only the owner can withdraw a listing"))
            if action == "UNCLAIM" and listing["claimed_by"] != actor_id:
                self._fail(connection, actor_id, action, shift_id, DomainError("only the claimer can unclaim"))
            connection.execute(
                "UPDATE listings SET status = ?, claimed_by = CASE WHEN ? = 'OPEN' THEN NULL ELSE claimed_by END WHERE id = ?",
                (new_status, new_status, listing_id),
            )
            self._history(connection, actor_id, action, shift_id, "SUCCESS")
            return dict(self._listing(connection, listing_id))

    def withdraw(self, actor_id, listing_id):
        return self._transition(actor_id, listing_id, "WITHDRAW", "OPEN", "WITHDRAWN")

    def unclaim(self, actor_id, listing_id):
        return self._transition(actor_id, listing_id, "UNCLAIM", "CLAIMED", "OPEN")

    def claim(self, actor_id: str, listing_id: int):
        with self.database.connection() as connection:
            listing = self._listing(connection, listing_id)
            shift_id = listing["shift_id"] if listing else None
            claimer = self._staff(connection, actor_id)
            if not listing:
                self._fail(connection, actor_id, "CLAIM", None, DomainError("listing not found", 404))
            if listing["status"] != "OPEN":
                self._fail(connection, actor_id, "CLAIM", shift_id, DomainError("no longer available"))
            if not claimer:
                self._fail(connection, actor_id, "CLAIM", shift_id, DomainError("staff not found", 404))
            if self._is_manager(claimer):
                self._fail(connection, actor_id, "CLAIM", shift_id, DomainError("managers cannot claim shifts"))
            target = dict(self._shift(connection, shift_id))
            if target["assigned_to"] == actor_id:
                error = DomainError(
                    "claim refused",
                    reasons=[{"rule": "different owner", "message": "claimer must differ from shift owner"}],
                )
                self._fail(connection, actor_id, "CLAIM", shift_id, error)
            assigned = [
                dict(row) for row in connection.execute(
                    "SELECT * FROM shifts WHERE assigned_to = ? AND id != ?",
                    (actor_id, shift_id),
                ).fetchall()
            ]
            reasons = validate_claim(dict(claimer), target, assigned)
            if reasons:
                self._fail(connection, actor_id, "CLAIM", shift_id, DomainError("claim refused", reasons=reasons))
            connection.execute(
                "UPDATE listings SET status = 'CLAIMED', claimed_by = ? WHERE id = ?",
                (actor_id, listing_id),
            )
            self._history(connection, actor_id, "CLAIM", shift_id, "SUCCESS")
            return dict(self._listing(connection, listing_id))

    def approve(self, actor_id: str, listing_id: int):
        with self.database.connection() as connection:
            listing = self._listing(connection, listing_id)
            shift_id = listing["shift_id"] if listing else None
            manager = self._staff(connection, actor_id)
            if not listing:
                self._fail(connection, actor_id, "APPROVE", None, DomainError("listing not found", 404))
            if not manager or not self._is_manager(manager):
                self._fail(connection, actor_id, "APPROVE", shift_id, DomainError("only managers can approve claims"))
            if listing["status"] != "CLAIMED":
                self._fail(connection, actor_id, "APPROVE", shift_id, DomainError("invalid listing status"))
            claimer = self._staff(connection, listing["claimed_by"])
            target = dict(self._shift(connection, shift_id))
            assigned = [
                dict(row) for row in connection.execute(
                    "SELECT * FROM shifts WHERE assigned_to = ? AND id != ?",
                    (listing["claimed_by"], shift_id),
                ).fetchall()
            ]
            reasons = validate_claim(dict(claimer), target, assigned)
            if reasons:
                error = DomainError("approval refused; claim is no longer valid", reasons=reasons)
                self._fail(connection, actor_id, "APPROVE", shift_id, error)
            connection.execute("UPDATE shifts SET assigned_to = ? WHERE id = ?", (listing["claimed_by"], shift_id))
            connection.execute("UPDATE listings SET status = 'APPROVED' WHERE id = ?", (listing_id,))
            self._history(connection, actor_id, "APPROVE", shift_id, "SUCCESS")
            return dict(self._listing(connection, listing_id))

    def reject(self, actor_id: str, listing_id: int):
        with self.database.connection() as connection:
            listing = self._listing(connection, listing_id)
            shift_id = listing["shift_id"] if listing else None
            manager = self._staff(connection, actor_id)
            if not listing:
                self._fail(connection, actor_id, "REJECT", None, DomainError("listing not found", 404))
            if not manager or not self._is_manager(manager):
                self._fail(connection, actor_id, "REJECT", shift_id, DomainError("only managers can reject claims"))
            if listing["status"] != "CLAIMED":
                self._fail(connection, actor_id, "REJECT", shift_id, DomainError("invalid listing status"))
            connection.execute("UPDATE listings SET status = 'REJECTED' WHERE id = ?", (listing_id,))
            self._history(connection, actor_id, "REJECT", shift_id, "SUCCESS")
            return dict(self._listing(connection, listing_id))
