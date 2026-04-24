"""
Weighted ensemble combining Linear + Logistic regression predictions.
Lightweight — runs on scikit-learn only, no heavy frameworks.
"""
import numpy as np
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score
import logging

logger = logging.getLogger("tn2026.ensemble")

TOTAL_SEATS = 234


class ElectionEnsemble:
    """
    Three-model ensemble:
      1. LinearRegression  → vote share prediction
      2. Ridge Regression  → seat count prediction
      3. LogisticRegression → win probability (majority >117 seats)

    Final output is a weighted combination.
    """

    # Ensemble weights (vote_model, seat_model)
    WEIGHTS = {"linear": 0.4, "ridge": 0.4, "recent": 0.2}

    def __init__(self):
        self.vote_model = Pipeline([
            ("scaler", StandardScaler()),
            ("reg", LinearRegression()),
        ])
        self.seat_model = Pipeline([
            ("scaler", StandardScaler()),
            ("reg", Ridge(alpha=1.0)),
        ])
        self.win_model = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=200, C=1.0)),
        ])
        self.trained = False
        self.cv_scores: dict = {}

    def fit(self, X: np.ndarray, y_vote: np.ndarray, y_seats: np.ndarray):
        """Train all three models."""
        # Vote share regression
        self.vote_model.fit(X, y_vote)
        vote_cv = cross_val_score(self.vote_model, X, y_vote, cv=min(3, len(X)), scoring="r2")
        self.cv_scores["vote_r2"] = float(vote_cv.mean())

        # Seat count regression
        self.seat_model.fit(X, y_seats)
        seat_cv = cross_val_score(self.seat_model, X, y_seats, cv=min(3, len(X)), scoring="r2")
        self.cv_scores["seat_r2"] = float(seat_cv.mean())

        # Win probability (binary: majority or not)
        y_win = (y_seats >= 117).astype(int)
        if len(np.unique(y_win)) > 1:
            self.win_model.fit(X, y_win)
            win_cv = cross_val_score(self.win_model, X, y_win, cv=min(3, len(X)), scoring="accuracy")
            self.cv_scores["win_acc"] = float(win_cv.mean())
        else:
            # All same class — skip win model
            self.cv_scores["win_acc"] = 0.0

        self.trained = True
        logger.info(f"Ensemble trained. CV scores: {self.cv_scores}")
        return self

    def predict(self, X: np.ndarray, recent_vote: float = None) -> dict:
        """
        Returns:
          predicted_vote_share, predicted_seats, win_probability, confidence
        """
        if not self.trained:
            raise RuntimeError("Model not trained — run train.py first")

        X2d = X.reshape(1, -1) if X.ndim == 1 else X

        pred_vote = float(self.vote_model.predict(X2d)[0])
        pred_seats = float(self.seat_model.predict(X2d)[0])

        # Blend with recent poll if available (recency bias)
        if recent_vote is not None:
            pred_vote = (
                self.WEIGHTS["linear"] * pred_vote
                + self.WEIGHTS["recent"] * recent_vote
                + self.WEIGHTS["ridge"] * pred_vote  # ridge already factored above
            )
            pred_vote /= (self.WEIGHTS["linear"] + self.WEIGHTS["recent"] + self.WEIGHTS["ridge"])

        # Clip to valid ranges
        pred_vote = float(np.clip(pred_vote, 0.0, 60.0))
        pred_seats = int(np.clip(round(pred_seats), 0, TOTAL_SEATS))

        # Win probability
        try:
            win_prob = float(self.win_model.predict_proba(X2d)[0][1])
        except Exception:
            win_prob = float(pred_seats >= 117)

        # Confidence: average of CV R² scores
        confidence = float(np.mean([
            max(0, self.cv_scores.get("vote_r2", 0)),
            max(0, self.cv_scores.get("seat_r2", 0)),
        ]))

        return {
            "predicted_vote_share": round(pred_vote, 2),
            "predicted_seats": pred_seats,
            "win_probability": round(win_prob, 3),
            "confidence_score": round(confidence, 3),
        }
