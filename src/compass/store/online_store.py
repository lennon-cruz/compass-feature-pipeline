"""SQLite-backed online feature store.

Holds the latest feature value per customer as maintained by the streaming
pipeline, along with the timestamp at which it was last computed.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

from compass.config import ONLINE_STORE_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS online_features (
    customer_id TEXT NOT NULL,
    feature_name TEXT NOT NULL,
    value REAL NOT NULL,
    computed_at TEXT NOT NULL,
    PRIMARY KEY (customer_id, feature_name)
);
CREATE TABLE IF NOT EXISTS pipeline_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class OnlineStore:
    """Latest feature value per customer, updated incrementally by the streaming pipeline."""

    def __init__(self, db_path: Path = ONLINE_STORE_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def upsert_feature(
        self,
        customer_id: str,
        feature_name: str,
        value: float,
        computed_at: datetime,
    ) -> None:
        """Write or overwrite a customer's current value for a feature."""
        self._conn.execute(
            """
            INSERT INTO online_features (customer_id, feature_name, value, computed_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(customer_id, feature_name)
            DO UPDATE SET value = excluded.value, computed_at = excluded.computed_at
            """,
            (customer_id, feature_name, value, computed_at.isoformat()),
        )
        self._conn.commit()

    def get_features(self, customer_id: str) -> dict[str, dict]:
        """Return `{feature_name: {"value": ..., "computed_at": ...}}` for whatever is currently stored."""
        cursor = self._conn.execute(
            "SELECT feature_name, value, computed_at FROM online_features WHERE customer_id = ?",
            (customer_id,),
        )
        return {
            feature_name: {"value": value, "computed_at": computed_at}
            for feature_name, value, computed_at in cursor.fetchall()
        }

    def get_all_features(self) -> dict[str, dict[str, dict]]:
        """Return every stored feature, grouped by customer_id."""
        cursor = self._conn.execute("SELECT customer_id, feature_name, value, computed_at FROM online_features")
        result: dict[str, dict[str, dict]] = {}
        for customer_id, feature_name, value, computed_at in cursor.fetchall():
            result.setdefault(customer_id, {})[feature_name] = {"value": value, "computed_at": computed_at}
        return result

    def get_state(self, key: str) -> str | None:
        """Read a piece of pipeline bookkeeping state (e.g. last-processed offset)."""
        cursor = self._conn.execute("SELECT value FROM pipeline_state WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else None

    def set_state(self, key: str, value: str) -> None:
        """Persist a piece of pipeline bookkeeping state."""
        self._conn.execute(
            """
            INSERT INTO pipeline_state (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
