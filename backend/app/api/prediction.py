"""GET /prediction — ML-based vote share & seat projections."""
import logging
from fastapi import APIRouter, Query

from app.utils.db import get_db
from app.utils.cache import cached

router = APIRouter()
logger = logging.getLogger("tn2026.api.prediction")


async def _fetch_predictions(db) -> list:
    cursor = db.predictions.find({}, {"_id": 0})
    return await cursor.to_list(length=50)


@router.get("/prediction")
async def get_predictions():
    """Get ML predictions for all parties."""
    db = get_db()

    # Try cache
    from app.utils.cache import cache_get, cache_set
    cached_val = cache_get("predictions:all", "medium")
    if cached_val:
        return cached_val

    preds = await _fetch_predictions(db)

    if not preds:
        # Run on-demand if pipeline hasn't run yet
        logger.info("No predictions in DB — running on-demand")
        from app.pipeline.pipeline import run_predictions
        await run_predictions(db)
        preds = await _fetch_predictions(db)

    # Sort by predicted seats desc
    preds.sort(key=lambda x: x.get("predicted_seats", 0), reverse=True)

    result = {
        "predictions": preds,
        "majority_threshold": 118,
        "total_seats": 234,
    }
    cache_set("predictions:all", result, "medium")
    return result


@router.get("/prediction/{party}")
async def get_party_prediction(party: str):
    """Get prediction for a specific party."""
    db = get_db()
    pred = await db.predictions.find_one(
        {"party": party.upper()}, {"_id": 0}
    )
    if not pred:
        return {"error": f"No prediction for party '{party}'", "party": party}
    return pred
