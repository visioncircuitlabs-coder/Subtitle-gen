import time
import uuid
from pathlib import Path

import aiofiles
from fastapi import HTTPException

CHUNK_SIZE = 8192


def generate_job_id() -> str:
    return uuid.uuid4().hex[:12]


async def save_upload(upload_file, dest_path: Path,
                      max_bytes: int = 0) -> None:
    written = 0
    try:
        async with aiofiles.open(dest_path, "wb") as f:
            while chunk := await upload_file.read(CHUNK_SIZE):
                written += len(chunk)
                if max_bytes and written > max_bytes:
                    raise HTTPException(
                        400,
                        f"File too large. Max: {max_bytes // (1024*1024)}MB"
                    )
                await f.write(chunk)
    except Exception:
        dest_path.unlink(missing_ok=True)
        raise


def cleanup_old_files(directory: Path, max_age_minutes: int,
                      protected_ids: set[str] | None = None) -> int:
    removed = 0
    cutoff = time.time() - (max_age_minutes * 60)
    if not directory.exists():
        return 0
    for file in directory.iterdir():
        if not file.is_file():
            continue
        # Don't delete files belonging to active jobs
        if protected_ids and file.stem in protected_ids:
            continue
        if file.stat().st_mtime < cutoff:
            file.unlink(missing_ok=True)
            removed += 1
    return removed
