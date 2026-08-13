"""Feature serving API consumed by downstream credit models and internal tooling.

Wraps the offline and online stores with a small, stable interface so that
callers don't need to know about storage details.
"""

from datetime import datetime

from compass.store.offline_store import OfflineStore
from compass.store.online_store import OnlineStore


def get_offline_features(customer_id: str, as_of: datetime) -> dict[str, float]:
    """Return a customer's batch-computed features as of a given date, for underwriting use cases."""
    store = OfflineStore()
    try:
        features = store.get_features(customer_id, as_of)
        return {name: info["value"] for name, info in features.items()}
    finally:
        store.close()


def get_online_features(customer_id: str) -> dict[str, float]:
    """Return a customer's latest streaming-computed features, for near-real-time use cases."""
    store = OnlineStore()
    try:
        features = store.get_features(customer_id)
        return {name: info["value"] for name, info in features.items()}
    finally:
        store.close()
