"""Shared paths, constants, and tuning parameters for the Compass feature pipeline."""

from datetime import timedelta
from pathlib import Path

# --- Paths -----------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "raw"
TRANSACTIONS_PATH = DATA_DIR / "transactions.csv"

OFFLINE_STORE_PATH = DATA_DIR / "offline_store.db"
ONLINE_STORE_PATH = DATA_DIR / "online_store.db"

# --- Data generation ---------------------------------------------------------

NUM_CUSTOMERS = 300
HISTORY_DAYS = 180
RANDOM_SEED = 42

# --- Feature windows ---------------------------------------------------------

TXN_AMOUNT_AVG_WINDOW_DAYS = 30

# --- Streaming pipeline ------------------------------------------------------

EWMA_ALPHA = 0.2
STREAMING_POLL_INTERVAL_SECONDS = 2.0

# --- Online store freshness --------------------------------------------------

FRESHNESS_TTL = timedelta(hours=6)
