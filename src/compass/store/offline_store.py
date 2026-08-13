"""SQLite-backed offline feature store.

Holds point-in-time feature values produced by the batch pipeline, keyed by
customer and the `as_of` date the feature was computed for.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

from compass.config import OFFLINE_STORE_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS offline_features (
    customer_id TEXT NOT NULL,
    as_of TEXT NOT NULL,
    feature_name TEXT NOT NULL,
    value REAL NOT NULL,
    computed_at TEXT NOT NULL,
    PRIMARY KEY (customer_id, as_of, feature_name)
);
"""


class OfflineStore:
    """Point-in-time feature values keyed by (customer_id, as_of)."""

    def __init__(self, db_path: Path = OFFLINE_STORE_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def write_features(
        self,
        customer_id: str,
        as_of: datetime,
        features: dict[str, float],
        computed_at: datetime,
    ) -> None:
        """Upsert a customer's feature values for a given `as_of` date."""
        rows = [
            (customer_id, as_of.isoformat(), name, value, computed_at.isoformat())
            for name, value in features.items()
        ]
        self._conn.executemany(
            """
            INSERT INTO offline_features (customer_id, as_of, feature_name, value, computed_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(customer_id, as_of, feature_name)
            DO UPDATE SET value = excluded.value, computed_at = excluded.computed_at
            """,
            rows,
        )
        self._conn.commit()

    def get_features(self, customer_id: str, as_of: datetime) -> dict[str, dict]:
        """Return `{feature_name: {"value": ..., "computed_at": ...}}` for the closest as_of at or before the given date."""
        cursor = self._conn.execute(
            """
            SELECT feature_name, value, computed_at
            FROM offline_features
            WHERE customer_id = ? AND as_of = (
                SELECT MAX(as_of) FROM offline_features
                WHERE customer_id = ? AND as_of <= ?
            )
            """,
            (customer_id, customer_id, as_of.isoformat()),
        )
        return {
            feature_name: {"value": value, "computed_at": computed_at}
            for feature_name, value, computed_at in cursor.fetchall()
        }

    def close(self) -> None:
        self._conn.close()
