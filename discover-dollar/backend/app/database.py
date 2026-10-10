import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE_PATH = BASE_DIR.parent / "data" / "shiftswap.sqlite3"
DEFAULT_SEED_PATH = BASE_DIR / "SHiftSwap_seed.json"

SCHEMA = """
CREATE TABLE IF NOT EXISTS app_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS staff (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    certifications_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS shifts (
    id TEXT PRIMARY KEY,
    start TEXT NOT NULL,
    end TEXT NOT NULL,
    required_certification TEXT,
    assigned_to TEXT REFERENCES staff(id)
);

CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shift_id TEXT NOT NULL REFERENCES shifts(id),
    listed_by TEXT NOT NULL REFERENCES staff(id),
    status TEXT NOT NULL DEFAULT 'OPEN',
    claimed_by TEXT REFERENCES staff(id),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS action_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    actor_id TEXT,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS one_active_listing_per_shift
ON listings (shift_id)
WHERE status IN ('OPEN', 'CLAIMED');
"""


class Database:
    def __init__(
        self,
        database_path: Path | str = DEFAULT_DATABASE_PATH,
        seed_path: Path | str = DEFAULT_SEED_PATH,
    ) -> None:
        self.database_path = Path(database_path)
        self.seed_path = Path(seed_path)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> bool:
        """Create tables and seed only an empty database.

        Returns True when seed data was loaded during this call.
        """
        with self.connection() as connection:
            connection.executescript(SCHEMA)
            self._migrate_listings(connection)
            has_saved_state = any(
                connection.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone()
                for table in ("staff", "shifts", "listings", "action_history")
            )
            if has_saved_state:
                return False

            payload = json.loads(self.seed_path.read_text(encoding="utf-8"))
            connection.executemany(
                """
                INSERT INTO staff (id, name, role, certifications_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    (
                        staff["id"],
                        staff["name"],
                        staff["role"],
                        json.dumps(staff.get("certifications", [])),
                    )
                    for staff in payload["staff"]
                ),
            )
            connection.executemany(
                """
                INSERT INTO shifts
                    (id, start, end, required_certification, assigned_to)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    (
                        shift["id"],
                        shift["start"],
                        shift["end"],
                        shift.get("required_certification"),
                        shift.get("assigned_to"),
                    )
                    for shift in payload["shifts"]
                ),
            )
            connection.execute(
                """
                INSERT INTO action_history
                    (action, entity_type, details_json)
                VALUES (?, ?, ?)
                """,
                (
                    "SEED_INITIALIZED",
                    "application",
                    json.dumps(
                        {
                            "staff_count": len(payload["staff"]),
                            "shift_count": len(payload["shifts"]),
                        }
                    ),
                ),
            )
            return True

    @staticmethod
    def _migrate_listings(connection: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(listings)").fetchall()
        }
        if "claimed_by" not in columns:
            connection.execute("ALTER TABLE listings ADD COLUMN claimed_by TEXT REFERENCES staff(id)")

    def fetch_all(self, table: str) -> list[dict]:
        allowed_tables = {"staff", "shifts", "listings", "action_history"}
        if table not in allowed_tables:
            raise ValueError(f"Unsupported table: {table}")
        with self.connection() as connection:
            rows = connection.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
        return [dict(row) for row in rows]


def serialize_row(table: str, row: dict) -> dict:
    if table == "staff":
        row["certifications"] = json.loads(row.pop("certifications_json"))
    elif table == "listings":
        row["created_at"] = row["created_at"]
    elif table == "action_history":
        row["details"] = json.loads(row.pop("details_json"))
    return row
