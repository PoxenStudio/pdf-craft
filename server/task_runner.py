"""
Task runner: executes transform_epub in a background thread.

Each call to `submit` spawns a daemon thread that:
  1. Marks the task as RUNNING
  2. Calls pdf_craft.transform_epub, reporting OCR page events as progress
  3. Marks the task COMPLETED or FAILED
"""

import threading
import traceback
import logging
from pathlib import Path
from typing import Literal

from pdf_craft import LLM, OCREvent, OCREventKind, transform_epub
from epub_generator import BookMeta

from server.models import TaskStatus
from server.settings_store import settings_store
from server.task_store import TaskStore


def _make_on_ocr_event(task_id: str, store: TaskStore):
    """Return a callback that maps OCREvent -> task progress."""

    def handler(event: OCREvent) -> None:
        if event.total_pages == 0:
            return
        if event.kind in (OCREventKind.COMPLETE,):
            store.update_completed(task_id)
            return
        progress = min(event.page_index / event.total_pages, 0.99)
        store.update_running(task_id, progress)

    return handler


def _build_toc_llm() -> LLM | None:
    """Build a LLM instance from current settings, or return None if disabled."""
    s = settings_store.get_raw()
    if not s.toc_llm_enabled:
        return None
    if not s.toc_llm_api_key or not s.toc_llm_api_url or not s.toc_llm_model:
        return None
    return LLM(
        key=s.toc_llm_api_key,
        url=s.toc_llm_api_url,
        model=s.toc_llm_model,
        token_encoding=s.toc_llm_token_encoding or "cl100k_base",
    )


def _run_task(
    task_id: str,
    store: TaskStore,
    title: str | None,
    authors: list[str] | None,
    lan: Literal["zh", "en"],
    includes_cover: bool,
    includes_footnotes: bool,
) -> None:
    store.update_running(task_id, 0.0)
    pdf_path: Path = store.input_pdf_path(task_id)
    epub_path: Path = store.output_epub_path(task_id)

    book_meta: BookMeta | None = None
    if title or authors:
        book_meta = BookMeta(
            title=title or "",
            authors=authors or [],
        )

    try:
        toc_llm = _build_toc_llm()
        transform_epub(
            pdf_path=pdf_path,
            epub_path=epub_path,
            book_meta=book_meta,
            lan=lan,
            includes_cover=includes_cover,
            includes_footnotes=includes_footnotes,
            toc_llm=toc_llm,
            toc_assumed=toc_llm is not None,  # auto-enable TOC detection when LLM is set
            on_ocr_event=_make_on_ocr_event(task_id, store),
        )
        # If OCREventKind.COMPLETE was not fired (no pages), mark completed here
        task = store.get(task_id)
        if task and task.status == TaskStatus.RUNNING:
            store.update_completed(task_id)
    except Exception:
        error_msg = traceback.format_exc()
        logging.error("Task %s failed: %s", task_id, error_msg)
        logging.error(" Call stack:\n%s", error_msg)
        store.update_failed(task_id, error_msg)


def submit(
    task_id: str,
    store: TaskStore,
    title: str | None = None,
    authors: list[str] | None = None,
    lan: Literal["zh", "en"] = "zh",
    includes_cover: bool = True,
    includes_footnotes: bool = False,
) -> None:
    """Submit a task for background execution."""
    thread = threading.Thread(
        target=_run_task,
        args=(task_id, store, title, authors, lan, includes_cover, includes_footnotes),
        daemon=True,
        name=f"task-{task_id}",
    )
    thread.start()
