"""
Pipeline: scrape → clean → store → predict.
Runs every 6 hours via APScheduler.
"""
import asyncio
import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Path fix for running as module
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scraper.ndtv_scraper import NDTVScraper
from scraper.abp_scraper import ABPCVoterScraper, News18Scraper
from scraper.normalizer import normalize_records, aggregate_poll_of_polls
from app.utils.db import get_db
from app.utils.cache import cache_invalidate
from app.ml.predictor import predict_all_parties

logger = logging.getLogger("tn2026.pipeline")


async def run_scrapers() -> List[Dict]:
    """Run all scrapers concurrently."""
    scrapers = [NDTVScraper(), ABPCVoterScraper(), News18Scraper()]
    all_records = []

    async def scrape_one(scraper):
        async with scraper:
            return await scraper.scrape()

    results = await asyncio.gather(
        *[scrape_one(s) for s in scrapers],
        return_exceptions=True,
    )

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Scraper {scrapers[i].name} failed: {result}")
        else:
            logger.info(f"Scraper {scrapers[i].name}: {len(result)} records")
            all_records.extend(result)

    return all_records


async def store_polls(db, records: List[Dict]) -> int:
    """Upsert poll records into MongoDB."""
    stored = 0
    for rec in records:
        try:
            await db.polls.update_one(
                {"_hash": rec["_hash"]},
                {"$set": rec},
                upsert=True,
            )
            stored += 1
        except Exception as e:
            logger.warning(f"Store error: {e}")
    return stored


async def run_predictions(db) -> None:
    """Run ML predictions and store results."""
    # Fetch all polls grouped by party
    polls_by_party: Dict[str, List] = {}
    cursor = db.polls.find(
        {"region": "statewide"},
        {"party": 1, "vote_share": 1, "seat_low": 1, "seat_high": 1,
         "date": 1, "source": 1, "_id": 0},
        sort=[("date", -1)],
    ).limit(200)

    async for doc in cursor:
        party = doc["party"]
        if party not in polls_by_party:
            polls_by_party[party] = []
        polls_by_party[party].append(doc)

    if not polls_by_party:
        logger.warning("No polls in DB — skipping predictions")
        return

    predictions = predict_all_parties(polls_by_party)

    # Store predictions
    for party, pred in predictions.items():
        pred["created_at"] = datetime.utcnow().isoformat()
        await db.predictions.update_one(
            {"party": party},
            {"$set": pred},
            upsert=True,
        )

    logger.info(f"Predictions stored for {len(predictions)} parties")


async def seed_db_if_empty(db) -> None:
    """Load seed data on first run."""
    count = await db.polls.count_documents({})
    if count > 0:
        return

    logger.info("DB empty — loading seed data...")
    import json
    seed_path = Path("/app/data/seed_data.json")
    if not seed_path.exists():
        return

    with open(seed_path) as f:
        seed = json.load(f)

    # Seed constituencies
    for c in seed["constituencies"]:
        await db.constituencies.update_one(
            {"id": c["id"]}, {"$set": c}, upsert=True
        )

    # Seed historical polls
    from scraper.normalizer import normalize_records
    records = normalize_records(seed["historical_polls"])
    for rec in records:
        await db.polls.insert_one(rec)

    logger.info(f"Seeded {len(records)} historical polls")


async def run_pipeline():
    """Full pipeline: scrape → normalize → store → predict."""
    start = datetime.utcnow()
    logger.info("═══ Pipeline run started ═══")
    db = get_db()

    try:
        # 1. Seed if empty
        await seed_db_if_empty(db)

        # 2. Scrape
        raw_records = await run_scrapers()
        logger.info(f"Total raw records: {len(raw_records)}")

        # 3. Normalize
        clean_records = normalize_records(raw_records)

        # 4. Store
        stored = await store_polls(db, clean_records)
        logger.info(f"Stored {stored} poll records")

        # 5. Predict
        await run_predictions(db)

        # 6. Invalidate caches
        cache_invalidate("medium")
        cache_invalidate("short")

        elapsed = (datetime.utcnow() - start).total_seconds()
        logger.info(f"═══ Pipeline complete in {elapsed:.1f}s ═══")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(run_pipeline())
