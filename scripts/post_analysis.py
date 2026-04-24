#!/usr/bin/env python3
"""
post_analysis.py — Compare predicted vs actual results.
Run after election results are declared:
  python scripts/post_analysis.py --actual results.json
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

FALLBACK_ACTUAL = {
    "DMK":     {"seats": 145, "vote_share": 46.2},
    "AIADMK":  {"seats": 63,  "vote_share": 28.0},
    "BJP":     {"seats": 11,  "vote_share": 12.5},
    "PMK":     {"seats": 8,   "vote_share": 5.2},
    "Congress":{"seats": 4,   "vote_share": 4.6},
    "VCK":     {"seats": 3,   "vote_share": 2.1},
}


def load_predictions(api_url: str) -> dict:
    """Fetch predictions from running API."""
    import urllib.request
    import json
    try:
        with urllib.request.urlopen(f"{api_url}/prediction", timeout=5) as r:
            data = json.loads(r.read())
        return {p["party"]: p for p in data.get("predictions", [])}
    except Exception as e:
        print(f"Warning: Could not fetch from API ({e}). Using sample data.")
        return {
            "DMK":     {"predicted_seats": 142, "predicted_vote_share": 45.1},
            "AIADMK":  {"predicted_seats": 65,  "predicted_vote_share": 28.5},
            "BJP":     {"predicted_seats": 12,  "predicted_vote_share": 12.8},
            "PMK":     {"predicted_seats": 9,   "predicted_vote_share": 5.5},
            "Congress":{"predicted_seats": 4,   "predicted_vote_share": 4.8},
        }


def mae(a, b): return abs(a - b)

def accuracy_score(predicted: int, actual: int, tolerance: int = 10) -> float:
    """Seat accuracy: 1.0 if within tolerance, else scaled."""
    diff = abs(predicted - actual)
    if diff <= tolerance:
        return 1.0 - (diff / tolerance) * 0.3
    return max(0, 1.0 - diff / 234)


def analyze(predictions: dict, actuals: dict):
    rows = []
    for party, actual in actuals.items():
        pred = predictions.get(party, {})
        pred_seats = pred.get("predicted_seats", 0)
        pred_vote = pred.get("predicted_vote_share", 0)
        act_seats = actual["seats"]
        act_vote = actual["vote_share"]

        seat_error = mae(pred_seats, act_seats)
        vote_error = mae(pred_vote, act_vote)
        seat_acc = accuracy_score(pred_seats, act_seats)

        rows.append({
            "Party": party,
            "Pred Seats": pred_seats,
            "Actual Seats": act_seats,
            "Seat Error": seat_error,
            "Seat Accuracy": f"{seat_acc:.0%}",
            "Pred Vote%": f"{pred_vote:.1f}",
            "Actual Vote%": f"{act_vote:.1f}",
            "Vote MAE": f"{vote_error:.2f}",
        })

    df = pd.DataFrame(rows)
    print("\n" + "═" * 75)
    print("  TN2026 Election Intelligence — Post-Result Analysis")
    print("═" * 75)
    print(df.to_string(index=False))
    print("═" * 75)

    # Aggregate metrics
    avg_seat_err = np.mean([r["Seat Error"] for r in rows])
    avg_vote_err = np.mean([float(r["Vote MAE"]) for r in rows])
    avg_acc = np.mean([
        accuracy_score(r["Pred Seats"], r["Actual Seats"]) for r in rows
    ])

    print(f"\n  Overall Metrics:")
    print(f"    Mean Seat Error : {avg_seat_err:.1f} seats")
    print(f"    Mean Vote MAE   : {avg_vote_err:.2f}%")
    print(f"    Avg Seat Acc    : {avg_acc:.0%}")

    # Direction accuracy (did we get winner right?)
    top_pred = max(rows, key=lambda r: r["Pred Seats"])["Party"]
    top_actual = max(rows, key=lambda r: r["Actual Seats"])["Party"]
    print(f"\n  Winner Prediction: {'✓ CORRECT' if top_pred == top_actual else '✗ WRONG'}")
    print(f"    Predicted winner : {top_pred}")
    print(f"    Actual winner    : {top_actual}")
    print("═" * 75 + "\n")

    return df


def main():
    parser = argparse.ArgumentParser(description="TN2026 Post-Result Analysis")
    parser.add_argument("--actual", help="JSON file with actual results")
    parser.add_argument("--api", default="http://localhost:8000", help="API URL")
    args = parser.parse_args()

    if args.actual:
        with open(args.actual) as f:
            actuals = json.load(f)
    else:
        print("No --actual file provided. Using sample actual results.")
        actuals = FALLBACK_ACTUAL

    predictions = load_predictions(args.api)
    analyze(predictions, actuals)


if __name__ == "__main__":
    main()
