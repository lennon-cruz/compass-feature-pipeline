"""Smoke tests for the Compass feature pipeline: nothing errors, expected shapes come out."""

from datetime import datetime, timezone

import pandas as pd
import pytest

from compass.data_generation import generate_transactions
from compass.features.batch_pipeline import run_batch_pipeline
from compass.features.streaming_pipeline import run_streaming_pipeline
from compass.model.credit_score import decide
from compass.serving.feature_api import get_offline_features, get_online_features
from compass.store.offline_store import OfflineStore
from compass.store.online_store import OnlineStore

CUSTOMER_ID = "C0001"


@pytest.fixture
def transactions_csv(tmp_path, monkeypatch):
    df = generate_transactions(num_customers=5, history_days=60, seed=1)
    path = tmp_path / "transactions.csv"
    df.to_csv(path, index=False)
    monkeypatch.setattr("compass.features.batch_pipeline.TRANSACTIONS_PATH", path)
    monkeypatch.setattr("compass.features.streaming_pipeline.TRANSACTIONS_PATH", path)
    return path


def test_generate_transactions_has_expected_columns():
    df = generate_transactions(num_customers=10, history_days=30, seed=1)
    assert not df.empty
    assert list(df.columns) == [
        "customer_id",
        "event_timestamp",
        "amount",
        "merchant_category",
        "channel",
    ]
    assert df["customer_id"].nunique() == 10


def test_batch_pipeline_populates_offline_store(transactions_csv, tmp_path):
    store = OfflineStore(db_path=tmp_path / "offline.db")
    as_of = datetime.now(timezone.utc)
    run_batch_pipeline(as_of, store=store)

    features = store.get_features(CUSTOMER_ID, as_of)
    assert "txn_amount_avg_30d" in features
    store.close()


def test_streaming_pipeline_populates_online_store(transactions_csv, tmp_path):
    store = OnlineStore(db_path=tmp_path / "online.db")
    processed = run_streaming_pipeline(store)

    assert processed > 0
    features = store.get_features(CUSTOMER_ID)
    assert "txn_amount_avg_30d" in features
    store.close()


def test_feature_api_returns_values_without_erroring(tmp_path, monkeypatch):
    offline_db = tmp_path / "offline.db"
    online_db = tmp_path / "online.db"
    monkeypatch.setattr("compass.serving.feature_api.OfflineStore", lambda: OfflineStore(db_path=offline_db))
    monkeypatch.setattr("compass.serving.feature_api.OnlineStore", lambda: OnlineStore(db_path=online_db))

    as_of = datetime.now(timezone.utc)
    offline_features = get_offline_features(CUSTOMER_ID, as_of)
    online_features = get_online_features(CUSTOMER_ID)

    assert isinstance(offline_features, dict)
    assert isinstance(online_features, dict)


def test_credit_score_decide_returns_score_and_decision():
    result = decide({"txn_amount_avg_30d": 42.0})
    assert "score" in result
    assert "approved" in result
