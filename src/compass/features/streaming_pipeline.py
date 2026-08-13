"""Incremental near-real-time feature computation, writing to the online feature store.

Ingests transaction events in order and maintains a running per-customer
average incrementally, rather than recomputing a full window on every event.
This keeps the online path cheap enough to serve in-app credit line
adjustments without rescanning the transaction log on every update.
"""

import argparse
import time
from datetime import datetime, timezone

import pandas as pd

from compass.config import EWMA_ALPHA, STREAMING_POLL_INTERVAL_SECONDS, TRANSACTIONS_PATH
from compass.store.online_store import OnlineStore

FEATURE_NAME = "txn_amount_avg_30d"
_SEQ_STATE_KEY = "last_processed_seq"
_BATCH_SIZE = 50


def _load_ordered_events() -> pd.DataFrame:
    df = pd.read_csv(TRANSACTIONS_PATH, parse_dates=["event_timestamp"])
    df.sort_values(["event_timestamp", "customer_id"], inplace=True, kind="stable")
    df.reset_index(drop=True, inplace=True)
    df["seq"] = df.index
    return df


def _load_running_averages(store: OnlineStore) -> dict[str, float]:
    return {
        customer_id: features[FEATURE_NAME]["value"]
        for customer_id, features in store.get_all_features().items()
        if FEATURE_NAME in features
    }


def run_streaming_pipeline(store: OnlineStore, stop_after_seconds: float | None = None) -> int:
    """Ingest pending events and update the online store's running averages.

    Returns the number of events processed. If `stop_after_seconds` is given,
    processing halts once that many seconds have elapsed, whether or not the
    full backlog has been consumed.
    """
    events = _load_ordered_events()

    last_seq = store.get_state(_SEQ_STATE_KEY)
    start_seq = int(last_seq) + 1 if last_seq is not None else 0
    pending = events[events["seq"] >= start_seq]

    running_avg = _load_running_averages(store)
    started_at = time.monotonic()
    processed = 0

    for batch_start in range(0, len(pending), _BATCH_SIZE):
        if stop_after_seconds is not None and time.monotonic() - started_at >= stop_after_seconds:
            break

        batch = pending.iloc[batch_start : batch_start + _BATCH_SIZE]
        now = datetime.now(timezone.utc)

        for _, event in batch.iterrows():
            customer_id = event["customer_id"]
            amount = float(event["amount"])

            if customer_id in running_avg:
                running_avg[customer_id] = EWMA_ALPHA * amount + (1 - EWMA_ALPHA) * running_avg[customer_id]
            else:
                running_avg[customer_id] = amount

            store.upsert_feature(customer_id, FEATURE_NAME, running_avg[customer_id], now)
            store.set_state(_SEQ_STATE_KEY, str(int(event["seq"])))
            processed += 1

        if stop_after_seconds is not None:
            time.sleep(STREAMING_POLL_INTERVAL_SECONDS)

    return processed


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Compass streaming feature pipeline.")
    parser.add_argument(
        "--stop-after-seconds",
        type=float,
        default=None,
        help="Halt ingestion after this many seconds, even if events remain in the backlog.",
    )
    args = parser.parse_args()

    store = OnlineStore()
    processed = run_streaming_pipeline(store, stop_after_seconds=args.stop_after_seconds)
    print(f"Streaming pipeline processed {processed} event(s) and wrote to {store.db_path}")
    store.close()


if __name__ == "__main__":
    main()
