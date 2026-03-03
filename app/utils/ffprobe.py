import asyncio
import json
from dataclasses import dataclass


@dataclass
class VideoInfo:
    duration: float
    has_audio: bool
    video_codec: str
    audio_codec: str | None
    resolution: str


async def validate_video(filepath: str) -> VideoInfo:
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(filepath),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise ValueError(f"ffprobe failed: {stderr.decode().strip()}")

    data = json.loads(stdout.decode())

    video_stream = None
    audio_stream = None
    for stream in data.get("streams", []):
        if stream["codec_type"] == "video" and video_stream is None:
            video_stream = stream
        elif stream["codec_type"] == "audio" and audio_stream is None:
            audio_stream = stream

    if video_stream is None:
        raise ValueError("No video stream found in file")

    duration = float(data.get("format", {}).get("duration", 0))
    width = video_stream.get("width", 0)
    height = video_stream.get("height", 0)

    return VideoInfo(
        duration=duration,
        has_audio=audio_stream is not None,
        video_codec=video_stream.get("codec_name", "unknown"),
        audio_codec=audio_stream.get("codec_name") if audio_stream else None,
        resolution=f"{width}x{height}",
    )
