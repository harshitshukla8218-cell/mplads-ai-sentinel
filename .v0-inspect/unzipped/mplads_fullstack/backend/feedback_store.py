"""
feedback_store.py -- Unique Feature #3: Human-in-the-loop adaptive weighting.

Investigators mark a flagged project as "Confirmed" (a real issue) or
"False Positive" (turned out fine) from the dashboard. Each time that happens:
  - We record the feedback (persisted to feedback.json)
  - We nudge the risk engine's weights: signals that were strongly elevated on
    a CONFIRMED case get slightly more weight; signals that were strongly
    elevated on a FALSE POSITIVE case get slightly less weight.
  - Weights are re-normalized and clipped so no single signal can dominate or
    vanish completely.

This turns the "explainable risk score" from a fixed formula into a system
that visibly improves as investigators use it -- a concrete answer to the
explainer's own framing: "we are building an AI co-pilot that helps them find
the right cases faster," one that gets sharper with use.

This is intentionally simple (no ML framework needed) so it's easy to explain
on stage to judges -- the logic must be explainable, not just the output.
"""

import json
import os
from datetime import datetime, timezone

FEEDBACK_PATH = os.path.join(os.path.dirname(__file__), "data", "feedback.json")
WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "data", "weights.json")

DEFAULT_WEIGHTS = {
    "cost_anomaly_score": 0.30,
    "delay_anomaly_score": 0.25,
    "duplicate_score": 0.25,
    "progress_mismatch_score": 0.20,
}

LEARNING_RATE = 0.03
MIN_WEIGHT = 0.05
MAX_WEIGHT = 0.60


def _ensure_files():
    os.makedirs(os.path.dirname(FEEDBACK_PATH), exist_ok=True)
    if not os.path.exists(FEEDBACK_PATH):
        with open(FEEDBACK_PATH, "w") as f:
            json.dump([], f)
    if not os.path.exists(WEIGHTS_PATH):
        with open(WEIGHTS_PATH, "w") as f:
            json.dump(DEFAULT_WEIGHTS, f)


def load_weights():
    _ensure_files()
    with open(WEIGHTS_PATH) as f:
        return json.load(f)


def save_weights(weights):
    with open(WEIGHTS_PATH, "w") as f:
        json.dump(weights, f, indent=2)


def load_feedback():
    _ensure_files()
    with open(FEEDBACK_PATH) as f:
        return json.load(f)


def _normalize(weights):
    total = sum(weights.values())
    if total <= 0:
        return DEFAULT_WEIGHTS.copy()
    normed = {k: v / total for k, v in weights.items()}
    normed = {k: min(max(v, MIN_WEIGHT), MAX_WEIGHT) for k, v in normed.items()}
    total2 = sum(normed.values())
    return {k: round(v / total2, 4) for k, v in normed.items()}


def record_feedback(work_id, verdict, signal_scores):
    """
    work_id: the project's ID
    verdict: "confirmed" or "false_positive"
    signal_scores: dict like {"cost_anomaly_score": 82.0, "delay_anomaly_score": 10.0, ...}
                    -- the individual signal values for THIS project at the time of feedback
    Returns the updated weights dict.
    """
    _ensure_files()
    assert verdict in ("confirmed", "false_positive")

    feedback_log = load_feedback()
    feedback_log.append({
        "work_id": work_id,
        "verdict": verdict,
        "signal_scores": signal_scores,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    with open(FEEDBACK_PATH, "w") as f:
        json.dump(feedback_log, f, indent=2)

    weights = load_weights()
    direction = 1 if verdict == "confirmed" else -1

    for signal, value in signal_scores.items():
        if signal not in weights:
            continue
        # Only adjust for signals that actually contributed meaningfully.
        strength = max(0.0, min(value, 100.0)) / 100.0
        weights[signal] = weights[signal] + direction * LEARNING_RATE * strength

    weights = _normalize(weights)
    save_weights(weights)
    return weights


def feedback_summary():
    log = load_feedback()
    confirmed = sum(1 for f in log if f["verdict"] == "confirmed")
    false_positive = sum(1 for f in log if f["verdict"] == "false_positive")
    return {
        "total_feedback": len(log),
        "confirmed": confirmed,
        "false_positive": false_positive,
        "current_weights": load_weights(),
    }
