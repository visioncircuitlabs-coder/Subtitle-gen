import os
import sys
from dataclasses import dataclass
from pathlib import Path


def _register_cuda_dlls():
    """Add pip-installed NVIDIA DLL directories to the DLL search path."""
    if sys.platform != "win32":
        return
    site_packages = [Path(p) for p in sys.path if "site-packages" in p]
    for sp in site_packages:
        nvidia_dir = sp / "nvidia"
        if not nvidia_dir.is_dir():
            continue
        for pkg in nvidia_dir.iterdir():
            bin_dir = pkg / "bin"
            if bin_dir.is_dir():
                os.add_dll_directory(str(bin_dir))


@dataclass
class Word:
    start: float
    end: float
    word: str


@dataclass
class Segment:
    start: float
    end: float
    text: str
    words: list[Word] | None = None


class Transcriber:
    def __init__(self, model_size: str = "small", device: str = "cuda",
                 compute_type: str = "float16"):
        _register_cuda_dlls()
        from faster_whisper import WhisperModel
        self.model = WhisperModel(model_size, device=device,
                                  compute_type=compute_type)

    def transcribe(self, audio_path: str,
                   language: str | None = None) -> list[Segment]:
        kwargs = {"beam_size": 5, "vad_filter": True, "word_timestamps": True}
        if language:
            kwargs["language"] = language

        segments_iter, info = self.model.transcribe(audio_path, **kwargs)

        segments = []
        for seg in segments_iter:
            text = seg.text.strip()
            if text:
                words = None
                if seg.words:
                    words = [
                        Word(start=w.start, end=w.end, word=w.word.strip())
                        for w in seg.words if w.word.strip()
                    ]
                segments.append(Segment(start=seg.start, end=seg.end,
                                        text=text, words=words))
        return segments
