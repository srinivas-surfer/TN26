"""GET /constituency/{id} — per-constituency data and prediction."""
import logging
from fastapi import APIRouter, HTTPException
from app.utils.db import get_db
from app.utils.cache import cache_get, cache_set

router = APIRouter()
logger = logging.getLogger("tn2026.api.constituency")

PARTY_COLORS = {
    "DMK": "#E63946", "AIADMK": "#2A9D8F", "BJP": "#F4A261",
    "Congress": "#457B9D", "PMK": "#8338EC", "VCK": "#06D6A0", "NTK": "#FFB703",
}


@router.get("/constituency/{constituency_id}")
async def get_constituency(constituency_id: int):
    cache_key = f"constituency:{constituency_id}"
    hit = cache_get(cache_key, "medium")
    if hit:
        return hit

    db = get_db()
    c = await db.constituencies.find_one({"id": constituency_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail=f"Constituency {constituency_id} not found")

    # Get live result if available
    live = await db.live_results.find_one({"constituency_id": constituency_id}, {"_id": 0})

    # Get regional polls for this constituency's region
    region = c.get("region", "statewide")
    polls_cursor = db.polls.find(
        {"region": {"$in": [region, "statewide"]}},
        {"_id": 0, "party": 1, "vote_share": 1, "date": 1, "source": 1},
        sort=[("date", -1)],
    ).limit(30)
    recent_polls = await polls_cursor.to_list(length=30)

    result = {
        "constituency": c,
        "region": region,
        "recent_polls": recent_polls,
        "live_result": live,
        "party_colors": PARTY_COLORS,
    }
    cache_set(cache_key, result, "medium")
    return result


@router.get("/constituencies")
async def list_constituencies():
    cache_key = "constituencies:all"
    hit = cache_get(cache_key, "long")
    if hit:
        return hit

    db = get_db()
    cursor = db.constituencies.find({}, {"_id": 0}, sort=[("id", 1)])
    items = await cursor.to_list(length=250)
    result = {"constituencies": items, "total": len(items)}
    cache_set(cache_key, result, "long")
    return result
