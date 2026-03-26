"""
API routes for server settings.

Endpoints:
  GET   /api/settings   Return current settings (api_key masked)
  POST  /api/settings   Partially update settings
"""

import logging

from fastapi import APIRouter

from ..models import ApiResponse, UpdateSettingsRequest
from ..settings_store import settings_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings")


# ---------------------------------------------------------------------------
# GET /api/settings
# ---------------------------------------------------------------------------

@router.get("", response_model=ApiResponse)
def get_settings() -> ApiResponse:
    """Return current server settings. The api_key is always masked."""
    return ApiResponse.ok(data=settings_store.get().model_dump())


# ---------------------------------------------------------------------------
# POST /api/settings
# ---------------------------------------------------------------------------

@router.post("", response_model=ApiResponse)
def update_settings(req: UpdateSettingsRequest) -> ApiResponse:
    """
    Partially update server settings.

    When `toc_llm_enabled` is set to `true`, the fields
    `toc_llm_api_key`, `toc_llm_api_url`, and `toc_llm_model` must
    already be configured (either persisted previously or supplied now).
    """
    # Validate: if enabling, ensure required fields will be present
    if req.toc_llm_enabled:
        raw = settings_store.get_raw()
        effective_key = req.toc_llm_api_key if req.toc_llm_api_key is not None else raw.toc_llm_api_key
        effective_url = req.toc_llm_api_url if req.toc_llm_api_url is not None else raw.toc_llm_api_url
        effective_model = req.toc_llm_model if req.toc_llm_model is not None else raw.toc_llm_model
        missing = [
            name for name, val in [
                ("toc_llm_api_key", effective_key),
                ("toc_llm_api_url", effective_url),
                ("toc_llm_model", effective_model),
            ] if not val
        ]
        if missing:
            return ApiResponse.error(
                400,
                f"Cannot enable LLM TOC extraction: missing required fields: {', '.join(missing)}",
            )

    updated = settings_store.update(req)
    logger.info("Settings updated: toc_llm_enabled=%s", updated.toc_llm_enabled)
    return ApiResponse.ok(data=updated.model_dump(), msg="Settings saved.")
