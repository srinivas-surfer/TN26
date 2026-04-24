#!/usr/bin/env python3
"""
train.py — Offline training script.
Run ONCE before deployment:
  docker-compose run --rm backend python train.py

Trains ElectionEnsemble on historical seed data + any scraped data in MongoDB.
Saves model to /app/models/ensemble.pkl
"""
import os
import sys
import json
import logging
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent))

from app.ml.features import build_training_dataframe, FEATURE_COLS, PARTIES
from app.ml.ensemble import ElectionEnsemble

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train")

MODEL_DIR = Path(os.getenv("MODEL_DIR", "/app/models"))
SEED_DATA = Path("/app/data/seed_data.json")


def load_seed_polls() -> dict:
    """Load seed historical poll data."""
    with open(SEED_DATA) as f:
        data = json.load(f)

    polls_by_party: dict = {p: [] for p in PARTIES}
    for poll in data["historical_polls"]:
        party = poll["party"]
        if party in polls_by_party:
            polls_by_party[party].append({
                "source": poll["source"],
                "date": poll["date"],
                "vote_share": poll["vote_share"],
                "seat_low": poll["seat_low"],
                "seat_high": poll["seat_high"],
                "region": poll.get("region", "statewide"),
            })
    return polls_by_party


def augment_data(polls_by_party: dict, factor: int = 5) -> dict:
    """
    Augment sparse training data with small Gaussian noise.
    Important: we have few polls, need more samples for cross-val.
    """
    augmented = {p: list(polls) for p, polls in polls_by_party.items()}
    for party, polls in polls_by_party.items():
        for _ in range(factor):
            for poll in polls:
                noise = np.random.normal(0, 0.3)
                new_poll = poll.copy()
                new_poll["vote_share"] = round(
                    float(np.clip(poll["vote_share"] + noise, 1.0, 60.0)), 2
                )
                new_poll["seat_low"] = max(0, poll["seat_low"] + np.random.randint(-3, 4))
                new_poll["seat_high"] = max(0, poll["seat_high"] + np.random.randint(-3, 4))
                augmented[party].append(new_poll)
    return augmented


def train():
    logger.info("═══ TN2026 Election Intelligence — Model Training ═══")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load data
    logger.info("Loading seed data...")
    polls_by_party = load_seed_polls()
    for party, polls in polls_by_party.items():
        logger.info(f"  {party}: {len(polls)} polls")

    # 2. Augment
    logger.info("Augmenting training data...")
    augmented = augment_data(polls_by_party, factor=8)
    for party, polls in augmented.items():
        logger.info(f"  {party}: {len(polls)} samples after augmentation")

    # 3. Build feature matrix
    logger.info("Building feature matrix...")
    df = build_training_dataframe(augmented)
    logger.info(f"Training samples: {len(df)}")

    if len(df) < 5:
        logger.error("Not enough training data!")
        sys.exit(1)

    X = df[FEATURE_COLS].values
    y_vote = df["target_vote"].values
    y_seats = df["target_seats"].values

    # 4. Train ensemble
    logger.info("Training ElectionEnsemble...")
    model = ElectionEnsemble()
    model.fit(X, y_vote, y_seats)

    # 5. Evaluate
    logger.info(f"CV Results:")
    logger.info(f"  Vote R²:  {model.cv_scores.get('vote_r2', 0):.3f}")
    logger.info(f"  Seats R²: {model.cv_scores.get('seat_r2', 0):.3f}")
    logger.info(f"  Win Acc:  {model.cv_scores.get('win_acc', 0):.3f}")

    # 6. Sanity check predictions
    logger.info("Sanity check predictions:")
    from app.ml.predictor import predict_all_parties
    # Temporarily save for predictor to find
    temp_path = MODEL_DIR / "ensemble.pkl"
    joblib.dump(model, temp_path)

    preds = predict_all_parties(polls_by_party)
    total_seats = sum(p["predicted_seats"] for p in preds.values())
    for party, pred in sorted(preds.items(), key=lambda x: -x[1]["predicted_seats"]):
        logger.info(
            f"  {party:10s}: {pred['predicted_vote_share']:.1f}% vote | "
            f"{pred['predicted_seats']:3d} seats | "
            f"win_prob={pred['win_probability']:.2f}"
        )
    logger.info(f"  Total seats: {total_seats}/234")

    # 7. Save model metadata
    meta = {
        "trained_at": datetime.utcnow().isoformat(),
        "training_samples": len(df),
        "cv_scores": model.cv_scores,
        "parties": PARTIES,
        "feature_cols": FEATURE_COLS,
    }
    meta_path = MODEL_DIR / "model_meta.json"
    import json
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    logger.info(f"✓ Model saved to {temp_path}")
    logger.info(f"✓ Metadata saved to {meta_path}")
    logger.info("═══ Training complete ═══")


if __name__ == "__main__":
    train()
