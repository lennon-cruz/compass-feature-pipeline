# Compass

Compass is Solara Digital Bank's feature store and feature pipeline. It computes
features from customer transaction data and serves them to downstream credit
models — both in batch, for underwriting, and in near-real-time, for in-app
credit line adjustments.

## Setup

```bash
uv sync
```

## Quickstart

Each step below depends on the previous one, so run them in order the first
time through:

```bash
uv run generate-data
uv run batch-pipeline
uv run streaming-pipeline
uv run query-features --customer-id C0001
uv run monitor
```

## Running the pipeline

1. **Generate synthetic transaction data**

   ```bash
   uv run generate-data
   ```

   Writes `data/raw/transactions.csv`.

2. **Run the batch pipeline** (recomputes features from the full transaction
   log into the offline store)

   ```bash
   uv run batch-pipeline
   ```

3. **Run the streaming pipeline** (ingests transaction events and updates the
   online store incrementally)

   ```bash
   uv run streaming-pipeline
   ```

   The streaming pipeline can also run as a long-lived process that keeps
   ingesting for a fixed duration:

   ```bash
   uv run streaming-pipeline --stop-after-seconds 30
   ```

4. **Query a customer's features** from both stores

   ```bash
   uv run query-features --customer-id C0001
   ```

5. **Check the health of the feature-serving API**

   ```bash
   uv run monitor
   ```

## Architecture

- **Offline store** (`compass.store.offline_store`) — a SQLite-backed store
  holding point-in-time feature values produced by the batch pipeline, keyed
  by customer and the `as_of` date they were computed for. This is the source
  used for underwriting decisions, where a full, exact recomputation over
  historical data is expected.

- **Online store** (`compass.store.online_store`) — a SQLite-backed store
  holding the latest feature value per customer, maintained incrementally by
  the streaming pipeline as new transaction events arrive. This is the source
  used for near-real-time in-app credit line adjustments, where low-latency
  lookups matter more than recomputing from scratch.

- **Batch pipeline** (`compass.features.batch_pipeline`) — a nightly-style job
  that recomputes each customer's features from the full transaction log on
  every run and writes them to the offline store.

- **Streaming pipeline** (`compass.features.streaming_pipeline`) — ingests
  transaction events in order and updates each customer's features
  incrementally, writing to the online store as it goes.

- **Feature API** (`compass.serving.feature_api`) — `get_offline_features()`
  and `get_online_features()`, the interface downstream consumers use to read
  features without needing to know about storage details.

- **Credit scoring** (`compass.model.credit_score`) — a simple rule-based
  scoring function that consumes a features dict, standing in for the
  underwriting and in-app models that depend on Compass features.

- **Monitoring dashboard** (`compass.monitoring.dashboard`) — reports uptime
  and average request latency for the feature-serving API.

## Development

```bash
uv run pytest
```
