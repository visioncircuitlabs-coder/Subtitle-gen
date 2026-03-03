from pathlib import Path

from app.services.transcriber import Segment


def _format_timestamp(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def _split_long_line(text: str, max_len: int = 42) -> str:
    if len(text) <= max_len:
        return text
    mid = len(text) // 2
    best = mid
    for i in range(mid, -1, -1):
        if text[i] == " ":
            best = i
            break
    return text[:best] + "\n" + text[best:].lstrip()


def segments_to_srt(segments: list[Segment], output_path: Path) -> Path:
    lines = []
    for i, seg in enumerate(segments, start=1):
        start = _format_timestamp(seg.start)
        end = _format_timestamp(seg.end)
        text = _split_long_line(seg.text)
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
