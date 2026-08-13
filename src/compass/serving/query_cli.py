"""CLI to look up a customer's features from both the offline and online stores."""

import argparse
from datetime import UTC, datetime

from compass.store.offline_store import OfflineStore
from compass.store.online_store import OnlineStore


def _format_value(value) -> str:
    return f"{value:.4f}" if isinstance(value, float) else str(value)


def _print_table(customer_id: str, offline: dict[str, dict], online: dict[str, dict]) -> None:
    feature_names = sorted(set(offline) | set(online))

    print(f"Features for {customer_id}")
    print(f"{'feature':<20}{'offline value':<16}{'offline computed_at':<36}{'online value':<16}{'online computed_at'}")
    for name in feature_names:
        off = offline.get(name, {})
        on = online.get(name, {})
        print(
            f"{name:<20}"
            f"{_format_value(off.get('value', '-')):<16}"
            f"{off.get('computed_at', '-'):<36}"
            f"{_format_value(on.get('value', '-')):<16}"
            f"{on.get('computed_at', '-')}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Look up a customer's features from the Compass feature stores.")
    parser.add_argument("--customer-id", required=True, help="Customer identifier, e.g. C0001")
    parser.add_argument(
        "--as-of",
        type=str,
        default=None,
        help="ISO 8601 date/time to look up offline features as of (default: now, UTC).",
    )
    args = parser.parse_args()

    as_of = datetime.fromisoformat(args.as_of) if args.as_of else datetime.now(UTC)
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=UTC)

    offline_store = OfflineStore()
    online_store = OnlineStore()
    try:
        offline_features = offline_store.get_features(args.customer_id, as_of)
        online_features = online_store.get_features(args.customer_id)
    finally:
        offline_store.close()
        online_store.close()

    _print_table(args.customer_id, offline_features, online_features)


if __name__ == "__main__":
    main()
