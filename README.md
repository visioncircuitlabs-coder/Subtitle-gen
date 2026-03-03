# Subtitle Generator

A web app that automatically generates subtitles from video audio and burns them directly into the video. Upload a video, get a subtitled video back.

## What It Does

1. You upload a video file (MP4, MKV, AVI, MOV, WebM)
2. The app extracts the audio and transcribes speech using AI (Whisper)
3. Subtitles are generated and burned into the video
4. You download the subtitled video and/or the SRT subtitle file

Everything runs locally on your machine. No cloud services, no API keys, no data leaves your computer.

## Requirements

- **Python 3.10+**
- **FFmpeg** installed and on your PATH ([download](https://ffmpeg.org/download.html))
- **NVIDIA GPU** with CUDA support (for fast transcription)
  - The app uses your GPU's VRAM to run the AI model
  - Minimum 4GB VRAM recommended

### Check your setup

```bash
python --version    # Should show 3.10 or higher
ffmpeg -version     # Should show FFmpeg version info
nvidia-smi          # Should show your GPU info
```

## Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/Subtitle-gen.git
cd Subtitle-gen

# Install dependencies
pip install -r requirements.txt
```

> **Note:** The first run will download the Whisper AI model (~500MB). This only happens once.

## Usage

```bash
python run.py
```

Open your browser to **http://127.0.0.1:8000**

1. Drag and drop a video file (or click to browse)
2. Wait for processing (you'll see real-time progress)
3. Download your subtitled video and SRT file

## Supported Formats

| Input | Output |
|-------|--------|
| MP4, MKV, AVI, MOV, WebM, FLV | MP4 (with burned-in subtitles) |

## Limits

- Maximum file size: 500MB
- Maximum video duration: 1 hour
- One video processed at a time

## Troubleshooting

**"No speech detected"** - The video may not have clear spoken audio, or the audio track may be silent.

**Processing is slow** - If you don't have an NVIDIA GPU, transcription falls back to CPU which is much slower. The "small" model is the default balance of speed vs accuracy.

**FFmpeg errors** - Make sure FFmpeg is installed and accessible from your terminal. Run `ffmpeg -version` to check.

**Out of VRAM** - The default "small" model uses ~2GB VRAM. If your GPU has less than 4GB, consider editing `app/config.py` and changing `WHISPER_MODEL` to `"tiny"` or `"base"`.
