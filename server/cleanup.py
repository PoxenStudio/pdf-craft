"""
Cleanup scheduler: periodically purges task directories older than the
retention window.  Runs as a single daemon thread.
"""

import logging
import threading

from server.config import CLEANUP_INTERVAL_SECONDS
from server.task_store import TaskStore

logger = logging.getLogger(__name__)


def _cleanup_loop(store: TaskStore, interval: int) -> None:
    while True:
        try:
            count = store.purge_expired()
            if count:
                logger.info("Cleanup: purged %d expired task(s).", count)
        except Exception:
            logger.exception("Cleanup loop encountered an error.")
        threading.Event().wait(interval)


def start_cleanup_scheduler(store: TaskStore) -> None:
    """Start the background cleanup thread (call once at application startup)."""
    thread = threading.Thread(
        target=_cleanup_loop,
        args=(store, CLEANUP_INTERVAL_SECONDS),
        daemon=True,
        name="cleanup-scheduler",
    )
    thread.start()
    logger.info(
        "Cleanup scheduler started (interval=%ds, retention=%d hours).",
        CLEANUP_INTERVAL_SECONDS,
        24,
    )
