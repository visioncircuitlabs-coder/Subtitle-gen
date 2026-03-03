import time
import uuid
from pathlib import Path

import aiofiles

CHUNK_SIZE = 8192


def generate_job_id() -> str:
    return uuid.uuid4().hex[:12]


async def save_upload(upload_file, dest_path: Path) -> None:
    async with aiofiles.open(dest_path, "wb") as f:
        while chunk := await upload_file.read(CHUNK_SIZE):
            await f.write(chunk)


def cleanup_old_files(directory: Path, max_age_minutes: int) -> int:
    removed = 0
    cutoff = time.time() - (max_age_minutes * 60)
    if not directory.exists():
        return 0
    for file in directory.iterdir():
        if file.is_file() and file.stat().st_mtime < cutoff:
            file.unlink(missing_ok=True)
            removed += 1
    return removed
