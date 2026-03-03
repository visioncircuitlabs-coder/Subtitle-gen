from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
SUBTITLE_DIR = BASE_DIR / "subtitles"

MAX_FILE_SIZE_MB = 500
MAX_VIDEO_DURATION_SECONDS = 3600  # 1 hour

ALLOWED_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv"}

WHISPER_MODEL = "small"
WHISPER_DEVICE = "cuda"
WHISPER_COMPUTE_TYPE = "float16"

CLEANUP_AGE_MINUTES = 60
CLEANUP_INTERVAL_MINUTES = 15
