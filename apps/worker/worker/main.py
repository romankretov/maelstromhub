import logging
import time

from maelstromhub_core import ResearchRun, ResearchRunStatus

from worker.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("maelstromhub.worker")


def run_once() -> None:
    placeholder = ResearchRun(
        id="bootstrap",
        name="Worker bootstrap",
        status=ResearchRunStatus.PENDING,
    )
    logger.info("worker idle", extra={"research_run": placeholder.model_dump(mode="json")})


def main() -> None:
    logger.info("starting worker", extra={"redis_url": settings.redis_url})
    while True:
        run_once()
        time.sleep(settings.poll_interval_seconds)


if __name__ == "__main__":
    main()
