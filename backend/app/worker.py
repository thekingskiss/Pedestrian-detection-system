"""
Entrypoint for the detection-pipeline worker process (separate from the
FastAPI/uvicorn process — see services/pipeline_orchestrator.py's module
docstring for the rationale). Run with:

    python -m app.worker

In docker-compose.yml this is the `worker` service. It polls for active
cameras and runs one CameraPipeline per camera. Runs as a persistent loop:
each pass re-queries for active cameras and re-launches any camera whose
pipeline has stopped (e.g. a finite video file reached its end, or the
pass raised an exception) after a short pause, rather than exiting after
a single pass.
"""
import asyncio
import logging
import signal

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.services.pipeline_orchestrator import run_all_active_cameras

logger = logging.getLogger(__name__)
settings = get_settings()

_shutdown_event: asyncio.Event | None = None


def _request_shutdown() -> None:
    logger.info("Shutdown signal received, worker will stop after the current pass")
    if _shutdown_event is not None:
        _shutdown_event.set()


async def main() -> None:
    global _shutdown_event
    configure_logging()

    _shutdown_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_shutdown)
        except NotImplementedError:
            # add_signal_handler isn't available on Windows's default loop;
            # Ctrl+C still raises KeyboardInterrupt, which we catch below.
            pass

    poll_interval_s = getattr(settings, "WORKER_POLL_INTERVAL_SECONDS", 10)
    logger.info("Detection worker starting (poll interval: %ss)", poll_interval_s)

    while not _shutdown_event.is_set():
        db = SessionLocal()
        try:
            await run_all_active_cameras(db)
        except Exception:
            logger.exception("Worker pass failed; will retry after pause")
        finally:
            db.close()

        try:
            await asyncio.wait_for(_shutdown_event.wait(), timeout=poll_interval_s)
        except asyncio.TimeoutError:
            pass  # normal case: timed out waiting, loop again

    logger.info("Detection worker stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Detection worker interrupted")