"""
API routes for task management.

Endpoints:
  POST   /api/tasks                      Create and start a conversion task
  GET    /api/tasks                      List recent tasks (within 24 h)
  GET    /api/tasks/{task_id}/progress   Query task progress
  GET    /api/tasks/{task_id}/download   Download the converted EPUB file
"""

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..models import ApiResponse, TaskStatus
from ..task_runner import submit
from ..task_store import task_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tasks")

# ---------------------------------------------------------------------------
# 1. Create task
# ---------------------------------------------------------------------------

@router.post("", response_model=ApiResponse)
async def create_task(
    file: UploadFile,
    title: Annotated[str | None, Form()] = None,
    authors: Annotated[str | None, Form()] = None,
    lan: Annotated[Literal["zh", "en"], Form()] = "zh",
    includes_cover: Annotated[bool, Form()] = True,
    includes_footnotes: Annotated[bool, Form()] = False,
) -> ApiResponse:
    """
    Upload a PDF and start an EPUB conversion task.

    Form fields:
      - file              (required) PDF file
      - title             Book title (optional)
      - authors           Comma-separated author names (optional)
      - lan               Language: "zh" | "en"  (default: "zh")
      - includes_cover    Include cover page (default: true)
      - includes_footnotes Include footnotes (default: false)
    """
    if not file.filename:
        return ApiResponse.error(400, "No file provided.")
    if not file.filename.lower().endswith(".pdf"):
        return ApiResponse.error(400, "Only PDF files are accepted.")

    task = task_store.create(filename=file.filename)
    pdf_path = task_store.input_pdf_path(task.task_id)

    # Save uploaded PDF to disk
    try:
        contents = await file.read()
        pdf_path.write_bytes(contents)
    except Exception as exc:
        task_store.update_failed(task.task_id, str(exc))
        logger.exception("Failed to save uploaded file for task %s", task.task_id)
        return ApiResponse.error(500, f"Failed to save uploaded file: {exc}")

    author_list = [a.strip() for a in authors.split(",")] if authors else None

    submit(
        task_id=task.task_id,
        store=task_store,
        title=title,
        authors=author_list,
        lan=lan,
        includes_cover=includes_cover,
        includes_footnotes=includes_footnotes,
    )

    logger.info("Task %s created for file '%s'", task.task_id, file.filename)
    return ApiResponse.ok(
        data={"task_id": task.task_id, "status": TaskStatus.RUNNING},
        msg="Task created and started.",
    )


# ---------------------------------------------------------------------------
# 2. List tasks
# ---------------------------------------------------------------------------

@router.get("", response_model=ApiResponse)
def list_tasks() -> ApiResponse:
    """List all tasks created within the last 24 hours."""
    tasks = task_store.list_recent()
    return ApiResponse.ok(data={"tasks": [t.model_dump() for t in tasks]})


# ---------------------------------------------------------------------------
# 3. Progress query
# ---------------------------------------------------------------------------

@router.get("/{task_id}/progress", response_model=ApiResponse)
def get_progress(task_id: str) -> ApiResponse:
    """Return current status and progress for the given task."""
    task = task_store.get(task_id)
    if task is None:
        return ApiResponse.error(404, f"Task '{task_id}' not found.")

    return ApiResponse.ok(
        data={
            "task_id": task.task_id,
            "status": task.status,
            "progress": task.progress,
            "file_size": task.file_size,
            "error_msg": task.error_msg,
            "created_at": task.created_at,
            "completed_at": task.completed_at,
        }
    )


# ---------------------------------------------------------------------------
# 4. Download result
# ---------------------------------------------------------------------------

@router.get("/{task_id}/download")
def download_file(task_id: str):
    """Download the converted EPUB.  Returns 4xx if task is not yet complete."""
    task = task_store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    if task.status == TaskStatus.RUNNING or task.status == TaskStatus.PENDING:
        raise HTTPException(status_code=409, detail="Task is not yet completed.")

    if task.status == TaskStatus.FAILED:
        raise HTTPException(
            status_code=422,
            detail=f"Task failed: {task.error_msg or 'unknown error'}",
        )

    epub_path = task_store.output_epub_path(task_id)
    if not epub_path.exists():
        raise HTTPException(status_code=404, detail="Output file not found.")

    download_name = task.filename.removesuffix(".pdf").removesuffix(".PDF") + ".epub"
    return FileResponse(
        path=str(epub_path),
        media_type="application/epub+zip",
        filename=download_name,
    )
