"""Synthetic transaction data generator for Compass.

Produces a reproducible transaction log for a population of customers with
varied activity patterns (daily, weekly, and sparse/bursty), consumed by the
batch and streaming feature pipelines.
"""

import random
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd

from compass.config import (
    HISTORY_DAYS,
    NUM_CUSTOMERS,
    RANDOM_SEED,
    TRANSACTIONS_PATH,
)

MERCHANT_CATEGORIES = [
    "groceries",
    "restaurants",
    "transport",
    "utilities",
    "entertainment",
    "online_retail",
    "travel",
    "healthcare",
]

CHANNELS = ["card_present", "card_not_present", "pix", "app_transfer"]

ACTIVITY_PATTERNS = ["daily", "weekly", "sparse"]
ACTIVITY_PATTERN_WEIGHTS = [0.4, 0.35, 0.25]


def _customer_ids(num_customers: int) -> list[str]:
    return [f"C{i:04d}" for i in range(1, num_customers + 1)]


def _generate_event_days(pattern: str, history_days: int, rng: np.random.Generator) -> list[int]:
    """Return the set of day offsets (0 = history start) on which a customer transacts."""
    if pattern == "daily":
        active_mask = rng.random(history_days) < 0.85
        return [day for day, active in enumerate(active_mask) if active]

    if pattern == "weekly":
        days = []
        day = int(rng.integers(0, 7))
        while day < history_days:
            days.append(day)
            day += int(rng.integers(5, 10))
        return days

    # sparse: a handful of short bursts separated by long gaps of inactivity
    days = []
    day = int(rng.integers(0, 14))
    while day < history_days:
        burst_length = int(rng.integers(1, 4))
        for offset in range(burst_length):
            if day + offset < history_days:
                days.append(day + offset)
        day += int(rng.integers(20, 60))
    return days


def _amounts_for_day(num_txns: int, rng: np.random.Generator) -> np.ndarray:
    """Lognormal amounts centered on everyday purchases, with occasional larger ones."""
    amounts = rng.lognormal(mean=3.2, sigma=0.9, size=num_txns)
    if rng.random() < 0.05:
        amounts[rng.integers(0, num_txns)] *= rng.uniform(5, 15)
    return np.round(amounts, 2)


def generate_transactions(
    num_customers: int = NUM_CUSTOMERS,
    history_days: int = HISTORY_DAYS,
    seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    """Generate a synthetic transaction log for `num_customers` over `history_days`."""
    rng = np.random.default_rng(seed)
    py_rng = random.Random(seed)

    end = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=history_days)

    records = []
    for customer_id in _customer_ids(num_customers):
        pattern = py_rng.choices(ACTIVITY_PATTERNS, weights=ACTIVITY_PATTERN_WEIGHTS, k=1)[0]
        event_days = _generate_event_days(pattern, history_days, rng)

        for day in event_days:
            num_txns_today = 1 if pattern != "daily" else int(rng.integers(1, 3))
            amounts = _amounts_for_day(num_txns_today, rng)
            for amount in amounts:
                seconds_into_day = int(rng.integers(0, 24 * 60 * 60))
                event_timestamp = start + timedelta(days=day, seconds=seconds_into_day)
                records.append(
                    {
                        "customer_id": customer_id,
                        "event_timestamp": event_timestamp.isoformat(),
                        "amount": float(amount),
                        "merchant_category": py_rng.choice(MERCHANT_CATEGORIES),
                        "channel": py_rng.choice(CHANNELS),
                    }
                )

    df = pd.DataFrame.from_records(records)
    df.sort_values(["customer_id", "event_timestamp"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def main() -> None:
    df = generate_transactions()
    TRANSACTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(TRANSACTIONS_PATH, index=False)
    print(f"Wrote {len(df):,} transactions for {df['customer_id'].nunique()} customers to {TRANSACTIONS_PATH}")


if __name__ == "__main__":
    main()
