import os
import uuid
import subprocess
import json
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Bharat Shorts API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

PROCESSED_DIR = Path("processed")
PROCESSED_DIR.mkdir(exist_ok=True)


# --- Models ---

class VideoMetadata(BaseModel):
    project_id: str
    file_path: str
    duration: float
    width: int
    height: int


class TranscriptWord(BaseModel):
    text: str
    start: float
    end: float
    confidence: float


class TranscriptSegment(BaseModel):
    id: str
    words: list[TranscriptWord]
    text: str
    start: float
    end: float
    speaker: str | None = None


class TranscriptResponse(BaseModel):
    project_id: str
    segments: list[TranscriptSegment]
    language: str


class SilenceRemovalResult(BaseModel):
    project_id: str
    original_duration: float
    new_duration: float
    output_path: str


# --- Helpers ---

def get_video_info(file_path: str) -> dict:
    """Extract video metadata using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", file_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail="ffprobe failed")
    return json.loads(result.stdout)


def remove_silence(input_path: str, output_path: str, threshold_db: float = -30, min_silence_ms: int = 500) -> float:
    """Remove silent segments from video using FFmpeg silencedetect."""
    # Detect silence
    detect_cmd = [
        "ffmpeg", "-i", input_path,
        "-af", f"silencedetect=noise={threshold_db}dB:d={min_silence_ms / 1000}",
        "-f", "null", "-"
    ]
    result = subprocess.run(detect_cmd, capture_output=True, text=True)
    stderr = result.stderr

    # Parse silence intervals
    silence_starts = []
    silence_ends = []
    for line in stderr.split("\n"):
        if "silence_start:" in line:
            val = line.split("silence_start:")[1].strip().split()[0]
            silence_starts.append(float(val))
        if "silence_end:" in line:
            val = line.split("silence_end:")[1].strip().split()[0]
            silence_ends.append(float(val))

    if not silence_starts:
        # No silence found, copy as-is
        subprocess.run(["cp", input_path, output_path])
        info = get_video_info(output_path)
        return float(info["format"]["duration"])

    # Build non-silent segments
    info = get_video_info(input_path)
    total_duration = float(info["format"]["duration"])

    segments = []
    prev_end = 0.0
    for i, start in enumerate(silence_starts):
        if start > prev_end:
            segments.append((prev_end, start))
        if i < len(silence_ends):
            prev_end = silence_ends[i]
    if prev_end < total_duration:
        segments.append((prev_end, total_duration))

    if not segments:
        subprocess.run(["cp", input_path, output_path])
        return total_duration

    # Build FFmpeg filter for concatenating non-silent parts
    filter_parts = []
    for i, (s, e) in enumerate(segments):
        filter_parts.append(f"[0:v]trim=start={s}:end={e},setpts=PTS-STARTPTS[v{i}];")
        filter_parts.append(f"[0:a]atrim=start={s}:end={e},asetpts=PTS-STARTPTS[a{i}];")

    concat_v = "".join(f"[v{i}]" for i in range(len(segments)))
    concat_a = "".join(f"[a{i}]" for i in range(len(segments)))
    filter_parts.append(
        f"{concat_v}{concat_a}concat=n={len(segments)}:v=1:a=1[outv][outa]"
    )
    filter_complex = "".join(filter_parts)

    concat_cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac",
        output_path,
    ]
    subprocess.run(concat_cmd, capture_output=True)

    out_info = get_video_info(output_path)
    return float(out_info["format"]["duration"])


# --- Routes ---

@app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "service": "bharat-shorts"}


@app.post("/api/v1/process-video", response_model=VideoMetadata)
async def process_video(file: UploadFile = File(...)):
    """Upload and process a video file. Returns metadata."""
    project_id = str(uuid.uuid4())
    ext = Path(file.filename or "video.mp4").suffix
    file_path = UPLOAD_DIR / f"{project_id}{ext}"

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    info = get_video_info(str(file_path))
    video_stream = next(
        (s for s in info.get("streams", []) if s["codec_type"] == "video"),
        None,
    )
    if not video_stream:
        raise HTTPException(status_code=400, detail="No video stream found")

    return VideoMetadata(
        project_id=project_id,
        file_path=str(file_path),
        duration=float(info["format"]["duration"]),
        width=int(video_stream["width"]),
        height=int(video_stream["height"]),
    )


@app.post("/api/v1/remove-silence/{project_id}", response_model=SilenceRemovalResult)
async def api_remove_silence(project_id: str):
    """Remove silent segments from an uploaded video."""
    # Find the uploaded file
    matches = list(UPLOAD_DIR.glob(f"{project_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Video not found")

    input_path = str(matches[0])
    output_path = str(PROCESSED_DIR / f"{project_id}_no_silence.mp4")

    original_info = get_video_info(input_path)
    original_duration = float(original_info["format"]["duration"])

    new_duration = remove_silence(input_path, output_path)

    return SilenceRemovalResult(
        project_id=project_id,
        original_duration=original_duration,
        new_duration=new_duration,
        output_path=output_path,
    )


@app.post("/api/v1/transcribe/{project_id}", response_model=TranscriptResponse)
async def transcribe_video(project_id: str):
    """Transcribe video audio. Currently returns a placeholder.
    Will be replaced with Faster-Whisper / IndicWhisper in Phase 2.
    """
    matches = list(UPLOAD_DIR.glob(f"{project_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Video not found")

    # TODO: Replace with actual Whisper transcription in Phase 2
    # For now, return a placeholder to unblock frontend development
    return TranscriptResponse(
        project_id=project_id,
        segments=[
            TranscriptSegment(
                id=str(uuid.uuid4()),
                words=[
                    TranscriptWord(text="Placeholder", start=0.0, end=0.5, confidence=1.0),
                    TranscriptWord(text="transcript", start=0.5, end=1.0, confidence=1.0),
                ],
                text="Placeholder transcript - Whisper integration coming in Phase 2",
                start=0.0,
                end=2.0,
            )
        ],
        language="hi",
    )
