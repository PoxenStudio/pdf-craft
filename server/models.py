from enum import Enum
from typing import Any

from pydantic import BaseModel


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ApiResponse(BaseModel):
    code: int = 200
    msg: str = "ok"
    data: Any = None

    @classmethod
    def ok(cls, data: Any = None, msg: str = "ok") -> "ApiResponse":
        return cls(code=200, msg=msg, data=data)

    @classmethod
    def error(cls, code: int, msg: str, data: Any = None) -> "ApiResponse":
        return cls(code=code, msg=msg, data=data)


class TaskInfo(BaseModel):
    task_id: str
    status: TaskStatus
    filename: str
    created_at: str          # ISO 8601
    completed_at: str | None = None
    progress: float = 0.0    # 0.0 ~ 1.0
    file_size: int | None = None
    error_msg: str | None = None


class CreateTaskRequest(BaseModel):
    title: str | None = None
    authors: list[str] | None = None
    lan: str = "zh"
    includes_cover: bool = True
    includes_footnotes: bool = False


class ServerSettings(BaseModel):
    toc_llm_enabled: bool = False
    # api_key is never sent back to the client; kept as empty string in responses
    toc_llm_api_key: str = ""
    toc_llm_api_url: str = "https://api.openai.com/v1"
    toc_llm_model: str = "gpt-4"
    toc_llm_token_encoding: str = "cl100k_base"


class UpdateSettingsRequest(BaseModel):
    toc_llm_enabled: bool | None = None
    toc_llm_api_key: str | None = None
    toc_llm_api_url: str | None = None
    toc_llm_model: str | None = None
    toc_llm_token_encoding: str | None = None
