"""GET /trends — vote share trends over time by party."""
import logging
from typing import Optional
from fastapi import APIRouter, Query, HTTPException

from app.utils.db import get_db
from app.utils.cache import cached

router = APIRouter()
logger = logging.getLogger("tn2026.api.trends")


@router.get("/trends")
@cached(tier="medium", key_fn=lambda region="statewide", party=None: f"trends:{region}:{party}")
async def get_trends(
    region: str = Query("statewide", description="Region filter"),
    party: Optional[str] = Query(None, description="Filter by party"),
):
    """Vote share trends across all polls, grouped by party and date."""
    db = get_db()

    match_filter: dict = {"region": region}
    if party:
        match_filter["party"] = party

    pipeline = [
        {"$match": match_filter},
        {"$sort": {"date": 1}},
        {"$group": {
            "_id": {"party": "$party", "date": "$date"},
            "vote_share_avg": {"$avg": "$vote_share"},
            "seat_low_avg": {"$avg": "$seat_low"},
            "seat_high_avg": {"$avg": "$seat_high"},
            "source_count": {"$sum": 1},
        }},
        {"$sort": {"_id.date": 1}},
        {"$project": {
            "_id": 0,
            "party": "$_id.party",
            "date": "$_id.date",
            "vote_share": {"$round": ["$vote_share_avg", 2]},
            "seat_low": {"$round": ["$seat_low_avg", 0]},
            "seat_high": {"$round": ["$seat_high_avg", 0]},
            "source_count": 1,
        }},
    ]

    cursor = db.polls.aggregate(pipeline)
    trends = await cursor.to_list(length=500)

    # Group by party for frontend convenience
    by_party: dict = {}
    for t in trends:
        p = t["party"]
        if p not in by_party:
            by_party[p] = []
        by_party[p].append({
            "date": t["date"],
            "vote_share": t["vote_share"],
            "seat_low": int(t.get("seat_low", 0)),
            "seat_high": int(t.get("seat_high", 0)),
        })

    return {
        "region": region,
        "parties": by_party,
        "total_datapoints": len(trends),
    }
