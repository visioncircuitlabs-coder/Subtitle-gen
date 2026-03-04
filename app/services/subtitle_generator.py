from pathlib import Path

from app.services.transcriber import Segment

MAX_WORDS_PER_CUE = 6


def _format_timestamp(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def _chunk_segment(seg: Segment) -> list[Segment]:
    """Split a segment into short phrase chunks using word timestamps."""
    if not seg.words or len(seg.words) <= MAX_WORDS_PER_CUE:
        return [seg]

    chunks = []
    words = seg.words
    for i in range(0, len(words), MAX_WORDS_PER_CUE):
        group = words[i : i + MAX_WORDS_PER_CUE]
        text = " ".join(w.word for w in group)
        chunks.append(Segment(
            start=group[0].start,
            end=group[-1].end,
            text=text,
        ))
    return chunks


def segments_to_srt(segments: list[Segment], output_path: Path) -> Path:
    cues: list[Segment] = []
    for seg in segments:
        cues.extend(_chunk_segment(seg))

    lines = []
    for i, cue in enumerate(cues, start=1):
        start = _format_timestamp(cue.start)
        end = _format_timestamp(cue.end)
        lines.append(f"{i}\n{start} --> {end}\n{cue.text}\n")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
