"""
Background scheduler: runs pipeline every 6 hours.
Uses APScheduler — lightweight, no Celery needed.
"""
import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger("tn2026.scheduler")

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(
            job_defaults={"coalesce": True, "max_instances": 1},
        )
    return _scheduler


async def start_scheduler():
    from app.pipeline.pipeline import run_pipeline

    scheduler = get_scheduler()

    # Run pipeline every 6 hours
    scheduler.add_job(
        run_pipeline,
        trigger=IntervalTrigger(hours=6),
        id="election_pipeline",
        name="Election Data Pipeline",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started — pipeline every 6h")

    # Run immediately on startup
    asyncio.create_task(_run_initial_pipeline())


async def _run_initial_pipeline():
    """Run pipeline once at startup after a short delay."""
    await asyncio.sleep(5)  # wait for DB to be ready
    from app.pipeline.pipeline import run_pipeline
    logger.info("Running initial pipeline...")
    await run_pipeline()


def stop_scheduler():
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
