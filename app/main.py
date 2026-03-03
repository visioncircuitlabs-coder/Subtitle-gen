import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import (
    UPLOAD_DIR, OUTPUT_DIR, SUBTITLE_DIR,
    MAX_FILE_SIZE_MB, ALLOWED_EXTENSIONS,
    WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE,
    CLEANUP_AGE_MINUTES, CLEANUP_INTERVAL_MINUTES, BASE_DIR,
)
from app.models.schemas import UploadResponse, ProgressEvent, ErrorResponse
from app.services.transcriber import Transcriber
from app.services.pipeline import process_video
from app.utils.file_manager import generate_job_id, save_upload, cleanup_old_files

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class JobState:
    status: str = "uploaded"
    stage: str = ""
    progress: float = 0.0
    error: str = ""
    output_path: Path | None = None
    srt_path: Path | None = None
    original_filename: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)


app = FastAPI(title="Subtitle Generator")

jobs: dict[str, JobState] = {}
transcriber: Transcriber | None = None
processing_semaphore = asyncio.Semaphore(1)


@app.on_event("startup")
async def startup():
    global transcriber
    for d in [UPLOAD_DIR, OUTPUT_DIR, SUBTITLE_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    logger.info(f"Loading Whisper model '{WHISPER_MODEL}' on {WHISPER_DEVICE}...")
    transcriber = Transcriber(WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE)
    logger.info("Whisper model loaded")

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _cleanup, "interval", minutes=CLEANUP_INTERVAL_MINUTES
    )
    scheduler.start()


def _cleanup():
    for d in [UPLOAD_DIR, OUTPUT_DIR, SUBTITLE_DIR]:
        removed = cleanup_old_files(d, CLEANUP_AGE_MINUTES)
        if removed:
            logger.info(f"Cleaned {removed} files from {d.name}")


@app.post("/api/upload", response_model=UploadResponse)
async def upload_video(file: UploadFile):
    if not file.filename:
        raise HTTPException(400, "No file provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            f"Unsupported format '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    job_id = generate_job_id()
    dest = UPLOAD_DIR / f"{job_id}{ext}"
    await save_upload(file, dest)

    size_mb = dest.stat().st_size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        dest.unlink(missing_ok=True)
        raise HTTPException(400, f"File too large ({size_mb:.0f}MB). Max: {MAX_FILE_SIZE_MB}MB")

    jobs[job_id] = JobState(original_filename=file.filename)
    logger.info(f"Uploaded {file.filename} as job {job_id} ({size_mb:.1f}MB)")
    return UploadResponse(job_id=job_id, filename=file.filename)


@app.post("/api/process/{job_id}")
async def start_processing(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")

    job = jobs[job_id]
    if job.status != "uploaded":
        raise HTTPException(400, f"Job already {job.status}")

    video_files = list(UPLOAD_DIR.glob(f"{job_id}.*"))
    if not video_files:
        raise HTTPException(404, "Upload file not found")

    video_path = video_files[0]
    job.status = "processing"

    asyncio.create_task(_run_pipeline(job_id, video_path))
    return {"status": "processing"}


async def _run_pipeline(job_id: str, video_path: Path):
    job = jobs[job_id]

    def progress_callback(stage: str, progress: float):
        job.stage = stage
        job.progress = progress
        job.queue.put_nowait(
            ProgressEvent(stage=stage, progress=progress).model_dump()
        )

    async with processing_semaphore:
        try:
            output_path, srt_path = await process_video(
                job_id, video_path, transcriber, progress_callback
            )
            job.status = "completed"
            job.output_path = output_path
            job.srt_path = srt_path
            job.queue.put_nowait(
                ProgressEvent(stage="complete", progress=1.0).model_dump()
            )
        except Exception as e:
            logger.exception(f"Job {job_id} failed")
            job.status = "failed"
            job.error = str(e)
            job.queue.put_nowait(
                ProgressEvent(stage="error", progress=0, message=str(e)).model_dump()
            )


@app.get("/api/progress/{job_id}")
async def progress_stream(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")

    job = jobs[job_id]

    async def event_generator():
        while True:
            try:
                event = await asyncio.wait_for(job.queue.get(), timeout=30)
                yield {"data": str(event).replace("'", '"')}
                if event.get("stage") in ("complete", "error"):
                    break
            except asyncio.TimeoutError:
                yield {"data": '{"stage": "heartbeat", "progress": ' + str(job.progress) + '}'}

    return EventSourceResponse(event_generator())


@app.get("/api/download/{job_id}/video")
async def download_video(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    job = jobs[job_id]
    if job.status != "completed" or not job.output_path or not job.output_path.exists():
        raise HTTPException(400, "Video not ready")

    name = Path(job.original_filename).stem + "_subtitled.mp4"
    return FileResponse(job.output_path, filename=name,
                        media_type="video/mp4")


@app.get("/api/download/{job_id}/subtitle")
async def download_subtitle(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    job = jobs[job_id]
    if job.status != "completed" or not job.srt_path or not job.srt_path.exists():
        raise HTTPException(400, "Subtitles not ready")

    name = Path(job.original_filename).stem + ".srt"
    return FileResponse(job.srt_path, filename=name,
                        media_type="application/x-subrip")


@app.delete("/api/job/{job_id}")
async def delete_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")

    job = jobs.pop(job_id)
    for pattern_dir in [UPLOAD_DIR, OUTPUT_DIR, SUBTITLE_DIR]:
        for f in pattern_dir.glob(f"{job_id}.*"):
            f.unlink(missing_ok=True)

    return {"status": "deleted"}


# Serve frontend — must be last
app.mount("/", StaticFiles(directory=str(BASE_DIR / "static"), html=True),
          name="static")
