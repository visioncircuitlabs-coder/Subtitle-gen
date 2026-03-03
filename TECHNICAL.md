# Technical Documentation

## Architecture Overview

```
Client (Browser)                    Server (FastAPI)
    |                                    |
    |--- POST /api/upload ------------->|  Save video to uploads/
    |<-- { job_id } --------------------|
    |                                    |
    |--- POST /api/process/{id} ------->|  Start background pipeline
    |<-- 202 Accepted ------------------|
    |                                    |
    |--- GET /api/progress/{id} ------->|  SSE stream
    |<-- stage/progress events ---------|  (real-time updates)
    |                                    |
    |--- GET /api/download/{id}/video ->|  Serve subtitled MP4
    |--- GET /api/download/{id}/subtitle|  Serve SRT file
```

## Processing Pipeline

```
Input Video
    |
    v
[1. Validate] ---- ffprobe: check format, duration, audio track
    |
    v
[2. Extract Audio] ---- ffmpeg: video -> 16kHz mono WAV
    |
    v
[3. Transcribe] ---- faster-whisper (CUDA/float16): WAV -> segments(start, end, text)
    |
    v
[4. Generate SRT] ---- segments -> SRT format (with line splitting at 42 chars)
    |
    v
[5. Burn Subtitles] ---- ffmpeg: video + SRT -> output MP4 (NVENC or libx264)
    |
    v
Output Video + SRT File
```

## Project Structure

```
app/
  main.py                 # FastAPI app, routes, SSE endpoint, job state, startup/shutdown
  config.py               # All constants: paths, limits, model config
  services/
    transcriber.py         # Whisper model wrapper (singleton, GPU inference)
    subtitle_generator.py  # Segment list -> SRT file conversion
    video_processor.py     # FFmpeg subprocess calls (extract audio, burn subtitles)
    pipeline.py            # Orchestrator: chains all services, reports progress
  models/
    schemas.py             # Pydantic models for API request/response
  utils/
    ffprobe.py             # Video validation via ffprobe subprocess
    file_manager.py        # File I/O helpers, cleanup, job ID generation
static/
  index.html              # Single-page UI (3 states: upload, processing, complete)
  css/style.css           # Dark theme styling
  js/
    app.js                # Main controller: state transitions, SSE handling, downloads
    upload.js             # Drag-and-drop + file input with XHR upload progress
```

## Key Components

### `app/main.py` — API Server

**Routes:**
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/upload` | Accept multipart file upload, validate, save, return job_id |
| POST | `/api/process/{job_id}` | Start background processing pipeline |
| GET | `/api/progress/{job_id}` | SSE stream for real-time progress events |
| GET | `/api/download/{job_id}/video` | Serve the subtitled video file |
| GET | `/api/download/{job_id}/subtitle` | Serve the SRT file |
| DELETE | `/api/job/{job_id}` | Clean up all files for a job |

**Job State Machine:**
```
UPLOADED --> PROCESSING --> COMPLETED
                  |
                  +--> FAILED
```

Job state is stored in-memory (`dict[str, JobState]`). Each job has an `asyncio.Queue` for SSE event delivery.

**Concurrency:** A `asyncio.Semaphore(1)` ensures only one video is processed at a time (GPU constraint). Additional requests queue up.

**Startup:** Loads the Whisper model into GPU VRAM (takes ~5-10s), creates temp directories, starts APScheduler for periodic file cleanup.

### `app/services/transcriber.py` — Speech-to-Text

- Uses `faster-whisper` with CTranslate2 backend
- Model loaded once at app startup (singleton pattern)
- Runs on CUDA with float16 compute type
- VAD (Voice Activity Detection) enabled to skip silence
- Returns `list[Segment(start, end, text)]`
- Called via `asyncio.to_thread()` since it's CPU/GPU-bound

**Whisper Model Sizes (VRAM usage):**
| Model | VRAM | Speed | Accuracy |
|-------|------|-------|----------|
| tiny | ~1GB | 32x | Basic |
| base | ~1GB | 16x | Good |
| small | ~2GB | 6x | Very good (default) |
| medium | ~5GB | 2x | Excellent |

### `app/services/video_processor.py` — FFmpeg Integration

**Audio extraction:**
```
ffmpeg -i input.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 output.wav
```
Whisper expects 16kHz mono WAV. Converting here avoids Whisper's internal ffmpeg dependency.

**Subtitle burning:**
```
ffmpeg -i input.mp4 -vf "subtitles=subs.srt:force_style='...'" -c:v h264_nvenc -c:a copy output.mp4
```

**Windows path escaping:** FFmpeg's `subtitles` filter uses libass which interprets `\` and `:` specially. The `_escape_ffmpeg_path()` function converts `C:\Users\...` to `C\:/Users/...`.

**NVENC detection:** At runtime, checks `ffmpeg -encoders` for `h264_nvenc`. Uses hardware encoding when available (3-5x faster), falls back to `libx264`.

**Progress parsing:** Reads FFmpeg stderr for `time=HH:MM:SS.ss` patterns to calculate encoding progress.

### `app/services/pipeline.py` — Orchestrator

Chains all services and maps progress to a 0-100% scale:

| Stage | Progress Range |
|-------|---------------|
| Validating | 0% - 5% |
| Extracting audio | 5% - 15% |
| Transcribing | 15% - 70% |
| Generating SRT | 70% - 75% |
| Burning subtitles | 75% - 100% |

Progress callback writes events to the job's `asyncio.Queue`, which the SSE endpoint reads.

### `app/services/subtitle_generator.py` — SRT Generation

Converts Whisper segments to standard SRT format:
```
1
00:00:00,000 --> 00:00:04,520
Hello and welcome to this tutorial
```

Lines longer than 42 characters are split at the nearest word boundary for readability.

### Frontend (`static/`)

**State machine:** Upload → Processing → Complete (or Error)

**Upload (`upload.js`):**
- Drag-and-drop zone with file input fallback
- Client-side validation (extension, size) before upload
- XHR used for upload progress tracking (fetch API doesn't support upload progress)
- Calls `onComplete(jobId)` when upload finishes

**Processing (`app.js`):**
- Starts processing via `POST /api/process/{jobId}`
- Opens `EventSource` (SSE) to `/api/progress/{jobId}`
- Updates progress bar and step indicators from SSE events
- Heartbeat events (every 30s) keep the connection alive

## Configuration — `app/config.py`

| Setting | Default | Description |
|---------|---------|-------------|
| `MAX_FILE_SIZE_MB` | 500 | Maximum upload file size |
| `MAX_VIDEO_DURATION_SECONDS` | 3600 | Maximum video duration (1 hour) |
| `WHISPER_MODEL` | "small" | Whisper model size |
| `WHISPER_DEVICE` | "cuda" | Inference device |
| `WHISPER_COMPUTE_TYPE` | "float16" | CUDA compute precision |
| `CLEANUP_AGE_MINUTES` | 60 | Auto-delete files after this age |
| `CLEANUP_INTERVAL_MINUTES` | 15 | How often cleanup runs |

## Temp File Layout

```
uploads/{job_id}.mp4     # Original uploaded video
uploads/{job_id}.wav     # Extracted audio (deleted after transcription)
subtitles/{job_id}.srt   # Generated subtitle file
outputs/{job_id}.mp4     # Final subtitled video
```

All temp directories are gitignored. Files auto-delete after 60 minutes via APScheduler.

## Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | Async web framework |
| `uvicorn` | ASGI server |
| `python-multipart` | Multipart file upload parsing |
| `faster-whisper` | Speech-to-text (CTranslate2 backend) |
| `sse-starlette` | Server-Sent Events for FastAPI |
| `aiofiles` | Async file I/O |
| `apscheduler` | Periodic file cleanup |

**System dependencies:** FFmpeg (with libass for subtitle filter), NVIDIA CUDA toolkit.

## Adding Features

**To change subtitle styling:** Edit the `force_style` string in `app/services/video_processor.py`. Uses ASS/SSA style format.

**To add a new output format:** Add a conversion function in `video_processor.py` and a new download route in `main.py`.

**To support VTT output:** Add a `segments_to_vtt()` function in `subtitle_generator.py` alongside the existing `segments_to_srt()`.

**To add language selection UI:** The `transcriber.transcribe()` already accepts a `language` parameter. Add a dropdown to the frontend and pass it via the process endpoint.
