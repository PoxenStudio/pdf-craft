from pathlib import Path

# Server settings
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 80

# Storage
DATA_DIR = Path("/data")

# Task file retention (hours)
FILE_RETENTION_HOURS = 24

# Cleanup interval (seconds)
CLEANUP_INTERVAL_SECONDS = 3600  # every hour

# File names inside each task directory
TASK_META_FILENAME = "task.json"
INPUT_PDF_FILENAME = "input.pdf"
OUTPUT_EPUB_FILENAME = "output.epub"
