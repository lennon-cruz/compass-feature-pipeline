"""Nightly-style batch feature computation, writing to the offline feature store.

Recomputes each customer's features from the full transaction log on every
run, so the offline store always reflects a fresh, exact recomputation as of
a given date.
"""

import argparse
from datetime import UTC, datetime, timedelta

import pandas as pd

from compass.config import TRANSACTIONS_PATH, TXN_AMOUNT_AVG_WINDOW_DAYS
from compass.store.offline_store import OfflineStore


def _load_transactions() -> pd.DataFrame:
    df = pd.read_csv(TRANSACTIONS_PATH, parse_dates=["event_timestamp"])
    if df["event_timestamp"].dt.tz is None:
        df["event_timestamp"] = df["event_timestamp"].dt.tz_localize("UTC")
    return df


def compute_txn_amount_avg_30d(df: pd.DataFrame, as_of: datetime) -> dict[str, float]:
    """Exact arithmetic mean of `amount` per customer over the trailing 30-day window."""
    window_start = as_of - timedelta(days=TXN_AMOUNT_AVG_WINDOW_DAYS)
    windowed = df[(df["event_timestamp"] >= window_start) & (df["event_timestamp"] <= as_of)]
    return windowed.groupby("customer_id")["amount"].mean().to_dict()


def run_batch_pipeline(as_of: datetime, store: OfflineStore | None = None) -> OfflineStore:
    """Recompute features for every customer as of `as_of` and persist them to the offline store."""
    df = _load_transactions()
    store = store or OfflineStore()

    averages = compute_txn_amount_avg_30d(df, as_of)
    computed_at = datetime.now(UTC)

    for customer_id, avg in averages.items():
        store.write_features(
            customer_id=customer_id,
            as_of=as_of,
            features={"txn_amount_avg_30d": avg},
            computed_at=computed_at,
        )

    return store


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Compass batch feature pipeline.")
    parser.add_argument(
        "--as-of",
        type=str,
        default=None,
        help="ISO 8601 date/time to compute features as of (default: now, UTC).",
    )
    args = parser.parse_args()

    as_of = datetime.fromisoformat(args.as_of) if args.as_of else datetime.now(UTC)
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=UTC)

    store = run_batch_pipeline(as_of)
    print(f"Batch pipeline computed features as of {as_of.isoformat()} and wrote to {store.db_path}")
    store.close()


if __name__ == "__main__":
    main()
