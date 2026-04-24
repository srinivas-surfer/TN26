"""GET /region/{name} — region-level aggregated poll data."""
import logging
from fastapi import APIRouter, HTTPException
from app.utils.db import get_db
from app.utils.cache import cache_get, cache_set

router = APIRouter()
logger = logging.getLogger("tn2026.api.region")

VALID_REGIONS = {
    "statewide", "Chennai", "Western TN",
    "Southern TN", "Central TN", "Northern TN", "Delta TN"
}


@router.get("/region/{region_name}")
async def get_region(region_name: str):
    decoded = region_name.replace("-", " ").title()
    # fuzzy match
    match = next((r for r in VALID_REGIONS if r.lower() == decoded.lower()), None)
    if not match:
        raise HTTPException(status_code=404, detail=f"Region '{region_name}' not found")

    cache_key = f"region:{match}"
    hit = cache_get(cache_key, "medium")
    if hit:
        return hit

    db = get_db()

    pipeline = [
        {"$match": {"region": match}},
        {"$group": {
            "_id": "$party",
            "latest_vote": {"$last": "$vote_share"},
            "avg_vote": {"$avg": "$vote_share"},
            "poll_count": {"$sum": 1},
            "latest_date": {"$max": "$date"},
        }},
        {"$sort": {"latest_vote": -1}},
        {"$project": {
            "_id": 0,
            "party": "$_id",
            "latest_vote_share": {"$round": ["$latest_vote", 2]},
            "avg_vote_share": {"$round": ["$avg_vote", 2]},
            "poll_count": 1,
            "latest_date": 1,
        }},
    ]

    cursor = db.polls.aggregate(pipeline)
    parties = await cursor.to_list(length=20)

    # Get constituency count for this region
    const_count = await db.constituencies.count_documents({"region": match})

    result = {
        "region": match,
        "parties": parties,
        "constituency_count": const_count,
    }
    cache_set(cache_key, result, "medium")
    return result


@router.get("/regions")
async def list_regions():
    db = get_db()
    pipeline = [
        {"$group": {"_id": "$region", "poll_count": {"$sum": 1}}},
        {"$sort": {"poll_count": -1}},
    ]
    cursor = db.polls.aggregate(pipeline)
    regions = await cursor.to_list(length=20)
    return {"regions": [r["_id"] for r in regions if r["_id"]]}
