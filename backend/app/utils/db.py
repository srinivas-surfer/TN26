"""
Lightweight async MongoDB client using Motor.
Connection is reused across requests — critical on t2.micro.
"""
import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING

logger = logging.getLogger("tn2026.db")

MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
DB_NAME = "tn2026"

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(
            MONGO_URL,
            maxPoolSize=5,       # low pool — we're on t2.micro
            minPoolSize=1,
            serverSelectionTimeoutMS=5000,
        )
    return _client


def get_db():
    return get_client()[DB_NAME]


async def setup_indexes():
    """Create indexes once at startup."""
    db = get_db()
    try:
        await db.polls.create_index([("date", DESCENDING), ("party", ASCENDING)])
        await db.polls.create_index([("source", ASCENDING)])
        await db.constituencies.create_index([("id", ASCENDING)], unique=True)
        await db.predictions.create_index([("party", ASCENDING), ("created_at", DESCENDING)])
        await db.live_results.create_index([("constituency_id", ASCENDING)], unique=True)
        logger.info("MongoDB indexes ready")
    except Exception as e:
        logger.warning(f"Index creation warning: {e}")


async def close_client():
    global _client
    if _client:
        _client.close()
        _client = None
