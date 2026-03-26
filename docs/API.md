# PDF Craft Server — API Reference

The HTTP server runs on port **80** by default.
All API endpoints are prefixed with `/api`.

---

## Common Response Envelope

Every API response (except binary downloads) uses the following JSON structure:

```json
{
  "code": 200,
  "msg": "ok",
  "data": {}
}
```

| Field  | Type    | Description                                      |
|--------|---------|--------------------------------------------------|
| `code` | integer | `200` for success, non-200 for errors            |
| `msg`  | string  | Human-readable message or error detail           |
| `data` | object  | Payload; `null` when not applicable              |

---

## Task Object

```json
{
  "task_id":      "a3f2c1...",
  "status":       "running",
  "filename":     "book.pdf",
  "created_at":   "2026-03-26T08:00:00+00:00",
  "completed_at": null,
  "progress":     0.42,
  "file_size":    null,
  "error_msg":    null
}
```

| Field          | Type            | Description                                        |
|----------------|-----------------|----------------------------------------------------|
| `task_id`      | string          | Unique hex identifier for the task                 |
| `status`       | string          | `pending` · `running` · `completed` · `failed`     |
| `filename`     | string          | Original uploaded PDF filename                     |
| `created_at`   | string (ISO 8601) | UTC creation timestamp                           |
| `completed_at` | string \| null  | UTC completion timestamp (success or failure)      |
| `progress`     | float           | Conversion progress `[0.0 – 1.0]`                 |
| `file_size`    | integer \| null | Output EPUB size in bytes (set on completion)      |
| `error_msg`    | string \| null  | Error traceback (set on failure)                   |

---

## Settings Object

```json
{
  "toc_llm_enabled": false,
  "toc_llm_api_key": "",
  "toc_llm_api_url": "https://api.openai.com/v1",
  "toc_llm_model":   "gpt-4"
}
```

| Field               | Type    | Description                                             |
|---------------------|---------|---------------------------------------------------------|
| `toc_llm_enabled`   | boolean | Enable LLM-enhanced TOC extraction for new tasks        |
| `toc_llm_api_key`   | string  | API key for the LLM provider                            |
| `toc_llm_api_url`   | string  | Base URL of the LLM API                                 |
| `toc_llm_model`     | string  | Model name (e.g. `gpt-4`, `deepseek-chat`)              |

> **Security note**: `toc_llm_api_key` is never returned in GET responses (masked as empty string). Submit a POST to update it.

---

## Task Endpoints

### POST `/api/tasks` — Create & start task

Upload a PDF file and immediately start the EPUB conversion.
The request must use `multipart/form-data`.

**Form fields**

| Field               | Type    | Required | Default | Description                             |
|---------------------|---------|----------|---------|-----------------------------------------|
| `file`              | file    | ✓        | —       | PDF file to convert                     |
| `title`             | string  |          | —       | Book title (auto-detected if omitted)   |
| `authors`           | string  |          | —       | Comma-separated author names            |
| `lan`               | string  |          | `zh`    | Language: `zh` or `en`                 |
| `includes_cover`    | boolean |          | `true`  | Whether to include the cover page       |
| `includes_footnotes`| boolean |          | `false` | Whether to include footnotes            |

**Success response** `200`

```json
{
  "code": 200,
  "msg": "Task created and started.",
  "data": {
    "task_id": "a3f2c1d4e5f6...",
    "status": "running"
  }
}
```

**Error responses**

| `code` | Condition                          |
|--------|------------------------------------|
| `400`  | No file provided or not a PDF      |
| `500`  | Failed to save uploaded file       |

---

### GET `/api/tasks` — List recent tasks

Returns all tasks created within the last 24 hours, sorted newest first.

**Response** `200`

```json
{
  "code": 200,
  "msg": "ok",
  "data": {
    "tasks": [ /* array of Task objects */ ]
  }
}
```

---

### GET `/api/tasks/{task_id}/progress` — Query task progress

**Path parameter**: `task_id` — hex task identifier returned by the create endpoint.

**Success response** `200`

```json
{
  "code": 200,
  "msg": "ok",
  "data": {
    "task_id":      "a3f2c1...",
    "status":       "running",
    "progress":     0.65,
    "file_size":    null,
    "error_msg":    null,
    "created_at":   "2026-03-26T08:00:00+00:00",
    "completed_at": null
  }
}
```

**Error responses**

| `code` | Condition            |
|--------|----------------------|
| `404`  | Task ID not found    |

---

### GET `/api/tasks/{task_id}/download` — Download EPUB

Streams the converted EPUB file as a binary download.

**Path parameter**: `task_id`

**Success response** `200`
`Content-Type: application/epub+zip`
`Content-Disposition: attachment; filename="<original_name>.epub"`

**Error responses** *(standard HTTP, not JSON envelope)*

| Status | Condition                                     |
|--------|-----------------------------------------------|
| `404`  | Task ID not found, or output file missing     |
| `409`  | Task is still `pending` or `running`          |
| `422`  | Task has `failed` (detail includes error msg) |

---

## Settings Endpoints

### GET `/api/settings` — Get current settings

**Success response** `200`

```json
{
  "code": 200,
  "msg": "ok",
  "data": {
    "toc_llm_enabled": false,
    "toc_llm_api_key": "",
    "toc_llm_api_url": "https://api.openai.com/v1",
    "toc_llm_model":   "gpt-4"
  }
}
```

> `toc_llm_api_key` is always returned as an empty string for security. A non-empty stored key is indicated by `toc_llm_enabled: true` together with a non-empty `toc_llm_model`.

---

### POST `/api/settings` — Update settings

**Request body** `application/json`

```json
{
  "toc_llm_enabled": true,
  "toc_llm_api_key": "sk-...",
  "toc_llm_api_url": "https://api.openai.com/v1",
  "toc_llm_model":   "gpt-4"
}
```

All fields are optional. Only supplied fields are updated.

**Success response** `200`

```json
{
  "code": 200,
  "msg": "Settings saved.",
  "data": {
    "toc_llm_enabled": true,
    "toc_llm_api_key": "",
    "toc_llm_api_url": "https://api.openai.com/v1",
    "toc_llm_model":   "gpt-4"
  }
}
```

**Error responses**

| `code` | Condition                                   |
|--------|---------------------------------------------|
| `400`  | `toc_llm_enabled` is `true` but `api_key`, `api_url`, or `model` are missing |

---

## File Storage

Task files are stored under `/data/<task_id>/`:

```
/data/<task_id>/
├── task.json       # Task metadata (persisted TaskInfo)
├── input.pdf       # Uploaded PDF
└── output.epub     # Converted EPUB (present only when completed)
```

Task directories are automatically deleted **24 hours** after creation by a background cleanup scheduler.

---

## Running the Server

```bash
# Install dependencies
pip install -r server/requirements.txt

# Start from the project root
python -m server.main
```

The interactive Web UI is served at `http://localhost/`.
Auto-generated OpenAPI docs are available at `http://localhost/docs`.
