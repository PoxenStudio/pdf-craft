"""
Task store: manages task lifecycle and persists task metadata to disk.

Each task has its own directory under DATA_DIR/<task_id>/ containing:
  - task.json   — serialised TaskInfo (ground truth on disk)
  - input.pdf   — uploaded PDF
  - output.epub — generated EPUB (only when completed)

An in-memory dict acts as a fast cache.  On startup the store loads any
existing task directories so progress survives a server restart.
"""

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import (
    DATA_DIR,
    FILE_RETENTION_HOURS,
    INPUT_PDF_FILENAME,
    OUTPUT_EPUB_FILENAME,
    TASK_META_FILENAME,
)
from .models import TaskInfo, TaskStatus


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskStore:
    """Thread-safe in-memory + disk task registry."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tasks: dict[str, TaskInfo] = {}
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._load_existing()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create(self, filename: str) -> TaskInfo:
        """Create a new task entry, persist it, and return it."""
        task_id = uuid.uuid4().hex
        task_dir = self._task_dir(task_id)
        task_dir.mkdir(parents=True, exist_ok=True)

        task = TaskInfo(
            task_id=task_id,
            status=TaskStatus.PENDING,
            filename=filename,
            created_at=_now_iso(),
        )
        self._save(task)
        with self._lock:
            self._tasks[task_id] = task
        return task

    def get(self, task_id: str) -> Optional[TaskInfo]:
        with self._lock:
            return self._tasks.get(task_id)

    def list_recent(self) -> list[TaskInfo]:
        """Return all tasks created within the retention window, newest first."""
        cutoff = self._cutoff_dt()
        with self._lock:
            tasks = list(self._tasks.values())
        result = [t for t in tasks if _parse_iso(t.created_at) >= cutoff]
        result.sort(key=lambda t: t.created_at, reverse=True)
        return result

    def update_running(self, task_id: str, progress: float) -> None:
        self._update(task_id, status=TaskStatus.RUNNING, progress=progress)

    def update_completed(self, task_id: str) -> None:
        file_size = self._output_size(task_id)
        self._update(
            task_id,
            status=TaskStatus.COMPLETED,
            progress=1.0,
            completed_at=_now_iso(),
            file_size=file_size,
        )

    def update_failed(self, task_id: str, error_msg: str) -> None:
        self._update(
            task_id,
            status=TaskStatus.FAILED,
            completed_at=_now_iso(),
            error_msg=error_msg,
        )

    # ------------------------------------------------------------------
    # File path helpers (used by runner and routes)
    # ------------------------------------------------------------------

    def task_dir(self, task_id: str) -> Path:
        return self._task_dir(task_id)

    def input_pdf_path(self, task_id: str) -> Path:
        return self._task_dir(task_id) / INPUT_PDF_FILENAME

    def output_epub_path(self, task_id: str) -> Path:
        return self._task_dir(task_id) / OUTPUT_EPUB_FILENAME

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def purge_expired(self) -> int:
        """Delete task directories older than the retention window. Returns count purged."""
        import shutil

        cutoff = self._cutoff_dt()
        purged = 0
        with self._lock:
            expired = [
                tid
                for tid, t in self._tasks.items()
                if _parse_iso(t.created_at) < cutoff
            ]
        for tid in expired:
            try:
                shutil.rmtree(self._task_dir(tid), ignore_errors=True)
            finally:
                with self._lock:
                    self._tasks.pop(tid, None)
                purged += 1
        return purged

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _task_dir(self, task_id: str) -> Path:
        return DATA_DIR / task_id

    def _output_size(self, task_id: str) -> Optional[int]:
        path = self.output_epub_path(task_id)
        return path.stat().st_size if path.exists() else None

    def _update(self, task_id: str, **fields) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return
            updated = task.model_copy(update=fields)
            self._tasks[task_id] = updated
        self._save(updated)

    def _save(self, task: TaskInfo) -> None:
        meta_path = self._task_dir(task.task_id) / TASK_META_FILENAME
        meta_path.write_text(task.model_dump_json(indent=2), encoding="utf-8")

    def _load_existing(self) -> None:
        """Load previously persisted tasks from disk into memory."""
        cutoff = self._cutoff_dt()
        for meta_path in DATA_DIR.glob(f"*/{TASK_META_FILENAME}"):
            try:
                task = TaskInfo.model_validate_json(meta_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if _parse_iso(task.created_at) < cutoff:
                continue
            # A task that was running when the server died is now failed
            if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                task = task.model_copy(
                    update={
                        "status": TaskStatus.FAILED,
                        "error_msg": "Server restarted while task was in progress.",
                        "completed_at": _now_iso(),
                    }
                )
                self._save(task)
            self._tasks[task.task_id] = task

    @staticmethod
    def _cutoff_dt() -> datetime:
        from datetime import timedelta

        return datetime.now(timezone.utc) - timedelta(hours=FILE_RETENTION_HOURS)


def _parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s)


# Module-level singleton
task_store = TaskStore()
