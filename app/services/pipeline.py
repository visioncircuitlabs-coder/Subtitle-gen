import asyncio
from pathlib import Path
from typing import Callable

from app.config import SUBTITLE_DIR, OUTPUT_DIR, MAX_VIDEO_DURATION_SECONDS
from app.services.transcriber import Transcriber
from app.services.subtitle_generator import segments_to_srt
from app.services.video_processor import extract_audio, burn_subtitles
from app.utils.ffprobe import validate_video


async def process_video(
    job_id: str,
    video_path: Path,
    transcriber: Transcriber,
    progress_callback: Callable[[str, float], None],
) -> tuple[Path, Path]:
    # Step 1: Validate
    progress_callback("validating", 0.05)
    info = await validate_video(str(video_path))

    if not info.has_audio:
        raise ValueError("Video has no audio track — cannot generate subtitles")

    if info.duration > MAX_VIDEO_DURATION_SECONDS:
        raise ValueError(
            f"Video is too long ({info.duration / 60:.0f} min). "
            f"Max allowed: {MAX_VIDEO_DURATION_SECONDS / 60:.0f} min."
        )

    # Step 2: Extract audio
    progress_callback("extracting_audio", 0.10)
    audio_path = video_path.with_suffix(".wav")
    await extract_audio(video_path, audio_path)
    progress_callback("extracting_audio", 0.15)

    # Step 3: Transcribe (audio cleanup guaranteed via try/finally)
    try:
        progress_callback("transcribing", 0.15)
        segments = await asyncio.to_thread(
            transcriber.transcribe, str(audio_path)
        )

        if not segments:
            raise ValueError("No speech detected in the video")

        progress_callback("transcribing", 0.70)
    finally:
        audio_path.unlink(missing_ok=True)

    # Step 4: Generate SRT
    progress_callback("generating_subtitles", 0.72)
    srt_path = SUBTITLE_DIR / f"{job_id}.srt"
    segments_to_srt(segments, srt_path)
    progress_callback("generating_subtitles", 0.75)

    # Step 5: Burn subtitles
    progress_callback("burning_subtitles", 0.75)
    output_path = OUTPUT_DIR / f"{job_id}.mp4"

    def burn_progress(frac: float):
        progress_callback("burning_subtitles", 0.75 + frac * 0.25)

    await burn_subtitles(video_path, srt_path, output_path,
                         info.duration, burn_progress)

    progress_callback("complete", 1.0)
    return output_path, srt_path
