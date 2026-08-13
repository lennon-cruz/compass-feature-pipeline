"""Monitoring dashboard for the Compass feature-serving API.

Exercises `get_offline_features` and `get_online_features` for a sample of
customers and reports uptime and average request latency, the way an
on-call engineer would check the health of the serving path.
"""

import time
from datetime import datetime, timezone

from compass.serving.feature_api import get_offline_features, get_online_features
from compass.store.online_store import OnlineStore

SAMPLE_SIZE = 50


def _sample_customer_ids(limit: int = SAMPLE_SIZE) -> list[str]:
    store = OnlineStore()
    try:
        customer_ids = list(store.get_all_features().keys())
    finally:
        store.close()
    return customer_ids[:limit]


def _time_call(fn, *args) -> tuple[bool, float]:
    start = time.perf_counter()
    try:
        fn(*args)
        ok = True
    except Exception:
        ok = False
    elapsed_ms = (time.perf_counter() - start) * 1000
    return ok, elapsed_ms


def run_health_check() -> dict[str, float]:
    """Call both feature endpoints for a sample of customers and summarize uptime/latency."""
    customer_ids = _sample_customer_ids()
    as_of = datetime.now(timezone.utc)

    latencies_ms = []
    successes = 0
    total = 0

    for customer_id in customer_ids:
        for ok, elapsed_ms in (
            _time_call(get_offline_features, customer_id, as_of),
            _time_call(get_online_features, customer_id),
        ):
            total += 1
            successes += int(ok)
            latencies_ms.append(elapsed_ms)

    uptime_pct = (successes / total * 100) if total else 0.0
    avg_latency_ms = sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0

    return {
        "requests": total,
        "uptime_pct": uptime_pct,
        "avg_latency_ms": avg_latency_ms,
    }


def main() -> None:
    stats = run_health_check()
    print("Compass feature-serving API health")
    print(f"  requests checked : {stats['requests']}")
    print(f"  uptime           : {stats['uptime_pct']:.2f}%")
    print(f"  avg latency      : {stats['avg_latency_ms']:.2f} ms")


if __name__ == "__main__":
    main()
