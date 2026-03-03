import asyncio
import re
from pathlib import Path
from typing import Callable


def _escape_ffmpeg_path(path: Path) -> str:
    s = str(path).replace("\\", "/")
    s = s.replace(":", "\\:")
    return s


async def _check_nvenc() -> bool:
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-hide_banner", "-encoders",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return b"h264_nvenc" in stdout


async def extract_audio(video_path: Path, output_path: Path) -> Path:
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        str(output_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"Audio extraction failed: {stderr.decode()[-500:]}")
    return output_path


async def burn_subtitles(
    video_path: Path,
    srt_path: Path,
    output_path: Path,
    duration: float,
    progress_callback: Callable[[float], None] | None = None,
) -> Path:
    escaped_srt = _escape_ffmpeg_path(srt_path)
    subtitle_filter = (
        f"subtitles={escaped_srt}:force_style='"
        "FontSize=24,FontName=Arial,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "Outline=2,Shadow=1,MarginV=30'"
    )

    nvenc = await _check_nvenc()
    if nvenc:
        codec_args = ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "23"]
    else:
        codec_args = ["-c:v", "libx264", "-preset", "medium", "-crf", "23"]

    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vf", subtitle_filter,
        *codec_args,
        "-c:a", "copy",
        str(output_path),
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")

    stderr_data = b""
    while True:
        chunk = await proc.stderr.read(1024)
        if not chunk:
            break
        stderr_data += chunk
        text = chunk.decode(errors="replace")
        match = time_pattern.search(text)
        if match and duration > 0 and progress_callback:
            h, m, s, cs = (int(x) for x in match.groups())
            current = h * 3600 + m * 60 + s + cs / 100
            progress_callback(min(current / duration, 1.0))

    await proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(
            f"Subtitle burning failed: {stderr_data.decode()[-500:]}"
        )
    return output_path
