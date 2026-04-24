"""
Predictor: loads saved .pkl models and serves predictions.
Models are loaded ONCE at startup and cached in memory.
"""
import os
import logging
import joblib
import numpy as np
from pathlib import Path
from typing import Dict, Optional

from app.ml.features import build_features, PARTIES, TOTAL_SEATS
from app.ml.ensemble import ElectionEnsemble

logger = logging.getLogger("tn2026.predictor")

MODEL_DIR = Path(os.getenv("MODEL_DIR", "/app/models"))
MODEL_PATH = MODEL_DIR / "ensemble.pkl"
FALLBACK_PREDICTIONS = {
    "DMK":     {"predicted_vote_share": 44.5, "predicted_seats": 140, "win_probability": 0.88, "confidence_score": 0.72},
    "AIADMK":  {"predicted_vote_share": 29.2, "predicted_seats": 68,  "win_probability": 0.05, "confidence_score": 0.68},
    "BJP":     {"predicted_vote_share": 12.0, "predicted_seats": 12,  "win_probability": 0.01, "confidence_score": 0.60},
    "PMK":     {"predicted_vote_share": 5.5,  "predicted_seats": 9,   "win_probability": 0.00, "confidence_score": 0.55},
    "Congress":{"predicted_vote_share": 4.8,  "predicted_seats": 4,   "win_probability": 0.00, "confidence_score": 0.50},
}

# Module-level model cache
_model: Optional[ElectionEnsemble] = None


def load_model() -> Optional[ElectionEnsemble]:
    global _model
    if _model is not None:
        return _model
    if MODEL_PATH.exists():
        try:
            _model = joblib.load(MODEL_PATH)
            logger.info(f"Ensemble model loaded from {MODEL_PATH}")
            return _model
        except Exception as e:
            logger.error(f"Model load failed: {e}")
    else:
        logger.warning(f"No model at {MODEL_PATH} — using fallbacks")
    return None


def predict_party(party: str, polls: list, region: str = "statewide") -> dict:
    """Run prediction for a single party given their poll history."""
    model = load_model()
    features = build_features(party, polls, region)
    recent_vote = polls[-1]["vote_share"] if polls else None

    if model is None:
        result = FALLBACK_PREDICTIONS.get(party, {
            "predicted_vote_share": 5.0,
            "predicted_seats": 2,
            "win_probability": 0.0,
            "confidence_score": 0.3,
        }).copy()
        result["using_fallback"] = True
        return result

    try:
        result = model.predict(features, recent_vote=recent_vote)
        result["using_fallback"] = False
        return result
    except Exception as e:
        logger.error(f"Prediction error for {party}: {e}")
        fallback = FALLBACK_PREDICTIONS.get(party, {}).copy()
        fallback["using_fallback"] = True
        return fallback


def predict_all_parties(polls_by_party: Dict[str, list]) -> Dict[str, dict]:
    """Predict for all parties and normalize seat totals."""
    results = {}
    for party in PARTIES:
        polls = polls_by_party.get(party, [])
        results[party] = predict_party(party, polls)
        results[party]["party"] = party

    # Normalize total seats to TOTAL_SEATS
    total = sum(r["predicted_seats"] for r in results.values())
    if total > 0 and total != TOTAL_SEATS:
        scale = TOTAL_SEATS / total
        for party in results:
            results[party]["predicted_seats"] = int(
                round(results[party]["predicted_seats"] * scale)
            )

    return results
