"""
Settings store: persists server configuration to disk.

Settings are stored at DATA_DIR/settings.json.
An in-memory cache is kept and protected by a lock for thread safety.

The api_key is stored on disk but NEVER returned to API clients
(callers receive an empty string instead).
"""

import threading
from pathlib import Path

from server.config import DATA_DIR
from server.models import ServerSettings, UpdateSettingsRequest

_SETTINGS_FILE = DATA_DIR / "settings.json"


class SettingsStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._settings = ServerSettings()
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self) -> ServerSettings:
        """Return current settings (api_key masked as empty string)."""
        with self._lock:
            s = self._settings
        return ServerSettings(
            toc_llm_enabled=s.toc_llm_enabled,
            toc_llm_api_key="",          # never expose the key
            toc_llm_api_url=s.toc_llm_api_url,
            toc_llm_model=s.toc_llm_model,
            toc_llm_token_encoding=s.toc_llm_token_encoding,
        )

    def get_raw(self) -> ServerSettings:
        """Return settings including the real api_key (for internal use only)."""
        with self._lock:
            return self._settings.model_copy()

    def update(self, req: UpdateSettingsRequest) -> ServerSettings:
        """Apply a partial update and persist. Returns masked settings."""
        with self._lock:
            current = self._settings.model_dump()
            patch = {k: v for k, v in req.model_dump().items() if v is not None}
            # Allow clearing api_key explicitly with empty string
            if req.toc_llm_api_key is not None:
                patch["toc_llm_api_key"] = req.toc_llm_api_key
            current.update(patch)
            self._settings = ServerSettings(**current)
            self._save(self._settings)
        return self.get()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if _SETTINGS_FILE.exists():
            try:
                self._settings = ServerSettings.model_validate_json(
                    _SETTINGS_FILE.read_text(encoding="utf-8")
                )
            except Exception:
                self._settings = ServerSettings()

    def _save(self, settings: ServerSettings) -> None:
        _SETTINGS_FILE.write_text(
            settings.model_dump_json(indent=2), encoding="utf-8"
        )


# Module-level singleton
settings_store = SettingsStore()
