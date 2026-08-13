"""Simple rule-based credit scoring consuming Compass features.

Stands in for the downstream underwriting and in-app credit line models that
consume `txn_amount_avg_30d` and similar features from the feature stores.
"""

# Logistic-style weighting; not a trained model, just a stable illustrative formula.
_INTERCEPT = 1.5
_TXN_AMOUNT_AVG_WEIGHT = -0.01

DECISION_THRESHOLD = 0.5


def score(features: dict[str, float]) -> float:
    """Return a score in (0, 1) where higher means lower estimated credit risk."""
    txn_amount_avg_30d = features.get("txn_amount_avg_30d", 0.0)
    logit = _INTERCEPT + _TXN_AMOUNT_AVG_WEIGHT * txn_amount_avg_30d
    return 1 / (1 + pow(2.718281828, -logit))


def decide(features: dict[str, float]) -> dict[str, float | bool]:
    """Return the score alongside a boolean approve/decline decision."""
    risk_score = score(features)
    return {"score": risk_score, "approved": risk_score >= DECISION_THRESHOLD}
