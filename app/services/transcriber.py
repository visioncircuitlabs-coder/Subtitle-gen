from dataclasses import dataclass


@dataclass
class Segment:
    start: float
    end: float
    text: str


class Transcriber:
    def __init__(self, model_size: str = "small", device: str = "cuda",
                 compute_type: str = "float16"):
        from faster_whisper import WhisperModel
        self.model = WhisperModel(model_size, device=device,
                                  compute_type=compute_type)

    def transcribe(self, audio_path: str,
                   language: str | None = None) -> list[Segment]:
        kwargs = {"beam_size": 5, "vad_filter": True}
        if language:
            kwargs["language"] = language

        segments_iter, info = self.model.transcribe(audio_path, **kwargs)

        segments = []
        for seg in segments_iter:
            text = seg.text.strip()
            if text:
                segments.append(Segment(start=seg.start, end=seg.end,
                                        text=text))
        return segments
