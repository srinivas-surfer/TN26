"""
GET /live-results — election day live seat tracker.
LIVE_MODE=true enables real-time simulation / actual result ingestion.
"""
import os
import random
import logging
import asyncio
from datetime import datetime
from fastapi import APIRouter, Query
from app.utils.db import get_db
from app.utils.cache import cache_get, cache_set

router = APIRouter()
logger = logging.getLogger("tn2026.api.live")

LIVE_MODE = os.getenv("LIVE_MODE", "false").lower() == "true"
TOTAL_SEATS = 234
MAJORITY = 118

# Seat distribution for simulation (based on latest predictions)
SIM_DISTRIBUTION = {
    "DMK":     {"expected": 142, "variance": 12},
    "AIADMK":  {"expected": 65,  "variance": 10},
    "BJP":     {"expected": 12,  "variance": 5},
    "PMK":     {"expected": 9,   "variance": 3},
    "Congress":{"expected": 4,   "variance": 2},
    "VCK":     {"expected": 2,   "variance": 1},
}

PARTY_COLORS = {
    "DMK": "#E63946", "AIADMK": "#2A9D8F", "BJP": "#F4A261",
    "Congress": "#457B9D", "PMK": "#8338EC", "VCK": "#06D6A0", "NTK": "#FFB703",
}

# In-memory simulation state (resets on restart)
_sim_state: dict = {"initialized": False, "constituencies": {}}


def _init_simulation():
    """Initialize constituency-level simulation state."""
    if _sim_state["initialized"]:
        return

    parties = list(SIM_DISTRIBUTION.keys())
    for cid in range(1, TOTAL_SEATS + 1):
        # Assign a "winner" based on party probabilities
        weights = [SIM_DISTRIBUTION[p]["expected"] / TOTAL_SEATS for p in parties]
        winner = random.choices(parties, weights=weights)[0]
        _sim_state["constituencies"][cid] = {
            "constituency_id": cid,
            "winner": winner,
            "status": "pending",       # pending → leading → won
            "votes_counted": 0,
            "total_votes": random.randint(160000, 230000),
            "lead_margin": random.randint(2000, 25000),
        }
    _sim_state["initialized"] = True


def _advance_simulation(tick: int):
    """
    Each tick, advance ~15 constituencies from pending→leading→won.
    tick = seconds since election counting started // 60
    """
    _init_simulation()
    expected_done = min(int(tick * 3.5), TOTAL_SEATS)  # ~3.5 seats declared/min
    done_so_far = sum(
        1 for c in _sim_state["constituencies"].values()
        if c["status"] == "won"
    )
    leading_so_far = sum(
        1 for c in _sim_state["constituencies"].values()
        if c["status"] == "leading"
    )

    # Move some from pending → leading
    pending = [c for c in _sim_state["constituencies"].values() if c["status"] == "pending"]
    to_lead = max(0, min(expected_done - done_so_far - leading_so_far, len(pending), 20))
    for c in random.sample(pending, to_lead):
        c["status"] = "leading"
        c["votes_counted"] = int(c["total_votes"] * random.uniform(0.3, 0.7))

    # Move some from leading → won
    leading = [c for c in _sim_state["constituencies"].values() if c["status"] == "leading"]
    to_win = max(0, min(done_so_far + len(leading) - expected_done + 10, len(leading), 10))
    for c in random.sample(leading, min(to_win, len(leading))):
        c["status"] = "won"
        c["votes_counted"] = c["total_votes"]


@router.get("/live-results")
async def get_live_results(
    tick: int = Query(0, description="Simulation tick (minutes since counting started)"),
):
    """
    Returns live/simulated seat counts.
    In LIVE_MODE: reads from DB (populated by actual data ingestion).
    Otherwise: returns deterministic simulation.
    """
    if LIVE_MODE:
        return await _get_db_live_results()
    else:
        return _get_simulated_results(tick)


async def _get_db_live_results():
    cache_key = "live:db"
    hit = cache_get(cache_key, "short")
    if hit:
        return hit

    db = get_db()
    cursor = db.live_results.find({}, {"_id": 0})
    results = await cursor.to_list(length=250)

    tally = {}
    for r in results:
        party = r.get("leading_party") or r.get("winner")
        status = r.get("status", "pending")
        if party:
            if party not in tally:
                tally[party] = {"leading": 0, "won": 0, "color": PARTY_COLORS.get(party, "#999")}
            if status == "leading":
                tally[party]["leading"] += 1
            elif status == "won":
                tally[party]["won"] += 1

    result = {
        "mode": "live",
        "timestamp": datetime.utcnow().isoformat(),
        "tally": tally,
        "total_declared": sum(
            v["leading"] + v["won"] for v in tally.values()
        ),
        "total_seats": TOTAL_SEATS,
        "majority": MAJORITY,
    }
    cache_set(cache_key, result, "short")
    return result


def _get_simulated_results(tick: int):
    _advance_simulation(tick)

    tally: dict = {}
    for c in _sim_state["constituencies"].values():
        party = c["winner"]
        if party not in tally:
            tally[party] = {
                "leading": 0, "won": 0,
                "color": PARTY_COLORS.get(party, "#999"),
                "party": party,
            }
        if c["status"] == "leading":
            tally[party]["leading"] += 1
        elif c["status"] == "won":
            tally[party]["won"] += 1

    total_declared = sum(v["leading"] + v["won"] for v in tally.values())

    # Sort by total (leading + won)
    sorted_tally = dict(
        sorted(tally.items(), key=lambda x: -(x[1]["leading"] + x[1]["won"]))
    )

    return {
        "mode": "simulation",
        "tick": tick,
        "timestamp": datetime.utcnow().isoformat(),
        "tally": sorted_tally,
        "total_declared": total_declared,
        "total_seats": TOTAL_SEATS,
        "majority": MAJORITY,
        "counting_complete": total_declared >= TOTAL_SEATS,
    }


@router.post("/live-results/reset")
async def reset_simulation():
    """Reset simulation state (dev/testing only)."""
    _sim_state["initialized"] = False
    _sim_state["constituencies"] = {}
    return {"status": "simulation reset"}
