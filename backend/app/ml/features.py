"""
Feature engineering for election prediction.
Runs fast — no heavy computation, designed for t2.micro.
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Any


PARTIES = ["DMK", "AIADMK", "BJP", "Congress", "PMK", "VCK", "NTK"]

REGIONAL_BASELINE = {
    "DMK":     {"Chennai": 0.48, "Western TN": 0.40, "Southern TN": 0.42, "Central TN": 0.44, "Northern TN": 0.41, "Delta TN": 0.46},
    "AIADMK":  {"Chennai": 0.25, "Western TN": 0.32, "Southern TN": 0.30, "Central TN": 0.28, "Northern TN": 0.33, "Delta TN": 0.27},
    "BJP":     {"Chennai": 0.10, "Western TN": 0.15, "Southern TN": 0.08, "Central TN": 0.11, "Northern TN": 0.14, "Delta TN": 0.09},
    "PMK":     {"Chennai": 0.04, "Western TN": 0.06, "Southern TN": 0.04, "Central TN": 0.05, "Northern TN": 0.08, "Delta TN": 0.04},
    "Congress":{"Chennai": 0.05, "Western TN": 0.04, "Southern TN": 0.06, "Central TN": 0.05, "Northern TN": 0.04, "Delta TN": 0.06},
}

TOTAL_SEATS = 234  # TN Assembly seats


def compute_momentum(polls: List[Dict]) -> float:
    """Linear trend slope over last N polls."""
    if len(polls) < 2:
        return 0.0
    votes = [p["vote_share"] for p in sorted(polls, key=lambda x: x["date"])]
    x = np.arange(len(votes), dtype=float)
    if x.std() == 0:
        return 0.0
    slope = np.polyfit(x, votes, 1)[0]
    return float(np.clip(slope, -5.0, 5.0))


def build_features(party: str, polls: List[Dict], region: str = "statewide") -> np.ndarray:
    """
    Returns feature vector:
    [latest_vote_share, historical_avg, momentum, regional_strength,
     poll_count, days_since_last_poll, source_diversity]
    """
    if not polls:
        return np.zeros(7)

    sorted_polls = sorted(polls, key=lambda x: x["date"])
    latest = sorted_polls[-1]["vote_share"]
    hist_avg = float(np.mean([p["vote_share"] for p in sorted_polls]))
    momentum = compute_momentum(sorted_polls)

    # Regional strength factor
    regional = REGIONAL_BASELINE.get(party, {}).get(region, latest / 100)

    # Poll freshness (days since last poll, capped at 180)
    try:
        from datetime import datetime, date
        last_date = sorted_polls[-1]["date"]
        if isinstance(last_date, str):
            last_date = datetime.fromisoformat(last_date).date()
        days_ago = (date.today() - last_date).days
    except Exception:
        days_ago = 30
    freshness = min(days_ago, 180) / 180.0

    # Source diversity (0-1)
    sources = set(p.get("source", "") for p in polls)
    diversity = min(len(sources) / 4.0, 1.0)

    return np.array([
        latest,
        hist_avg,
        momentum,
        regional * 100,   # scale to % range
        min(len(polls), 20),
        freshness,
        diversity,
    ], dtype=float)


def build_training_dataframe(polls_by_party: Dict[str, List[Dict]]) -> pd.DataFrame:
    """Build training dataset from poll history."""
    rows = []
    for party, polls in polls_by_party.items():
        if len(polls) < 2:
            continue
        # Walk through history using expanding window
        sorted_polls = sorted(polls, key=lambda x: x["date"])
        for i in range(1, len(sorted_polls)):
            window = sorted_polls[:i]
            target_vote = sorted_polls[i]["vote_share"]
            target_seats = (sorted_polls[i]["seat_low"] + sorted_polls[i]["seat_high"]) / 2
            feats = build_features(party, window)
            row = {
                "party": party,
                "f_latest_vote": feats[0],
                "f_hist_avg": feats[1],
                "f_momentum": feats[2],
                "f_regional": feats[3],
                "f_poll_count": feats[4],
                "f_freshness": feats[5],
                "f_diversity": feats[6],
                "target_vote": target_vote,
                "target_seats": target_seats,
                "target_win": 1 if target_seats > 117 else 0,  # majority threshold
            }
            rows.append(row)
    return pd.DataFrame(rows)


FEATURE_COLS = [
    "f_latest_vote", "f_hist_avg", "f_momentum",
    "f_regional", "f_poll_count", "f_freshness", "f_diversity"
]
