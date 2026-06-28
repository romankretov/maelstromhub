import logging

import asyncio

from app.db.research_repositories import run_next_queued_ingestion_job
from app.db.session import async_session_factory
from app.providers.candles import HyperliquidCandleProvider

from worker.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("maelstromhub.worker")


async def run_once() -> None:
    async with async_session_factory() as session:
        job = await run_next_queued_ingestion_job(session, HyperliquidCandleProvider())
        if job is None:
            logger.info("worker idle")
            return
        logger.info("processed ingestion job", extra={"job_id": job.id, "status": job.status})


def main() -> None:
    asyncio.run(run_forever())


async def run_forever() -> None:
    logger.info("starting worker", extra={"redis_url": settings.redis_url})
    while True:
        await run_once()
        await asyncio.sleep(settings.poll_interval_seconds)


if __name__ == "__main__":
    main()
