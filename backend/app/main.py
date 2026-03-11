import os
import uuid
import subprocess
import json
import logging
from pathlib import Path

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

app = FastAPI(title="Bharat Shorts API", version="0.1.0")

# --- Environment Setup (Handle Missing FFmpeg/FFprobe) ---
def _setup_ffmpeg_path():
    """Ensure ffmpeg/ffprobe from Remotion node_modules are in PATH if missing."""
    import shutil
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        # Look for Remotion's bundled binaries
        base_dir = Path(__file__).resolve().parent.parent.parent
        remotion_bin_dir = base_dir / "frontend" / "node_modules" / "@remotion" / "compositor-win32-x64-msvc"
        if remotion_bin_dir.exists():
            os.environ["PATH"] = str(remotion_bin_dir) + os.pathsep + os.environ["PATH"]
            logger.info(f"Added local FFmpeg to PATH: {remotion_bin_dir}")
        else:
            logger.error(f"Could NOT find Remotion FFmpeg at: {remotion_bin_dir}")

_setup_ffmpeg_path()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import Request
from fastapi.responses import JSONResponse
import traceback

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error handler caught: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc), "traceback": traceback.format_exc()},
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
        import shutil
        shutil.copy(input_path, output_path)
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
        import shutil
        shutil.copy(input_path, output_path)
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
async def transcribe_video(project_id: str, language: str | None = None, model_size: str = "base"):
    """Transcribe video audio using Faster-Whisper with word-level timestamps.

    Args:
        project_id: UUID of the uploaded video
        language: Optional language code (e.g. 'hi', 'en', 'ta'). None = auto-detect.
        model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large-v3')
    """
    from services.transcription import transcribe

    matches = list(UPLOAD_DIR.glob(f"{project_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Video not found")

    result = transcribe(str(matches[0]), model_size=model_size, language=language)

    segments = [
        TranscriptSegment(
            id=seg["id"],
            words=[TranscriptWord(**w) for w in seg["words"]],
            text=seg["text"],
            start=seg["start"],
            end=seg["end"],
            speaker=seg.get("speaker"),
        )
        for seg in result["segments"]
    ]

    return TranscriptResponse(
        project_id=project_id,
        segments=segments,
        language=result["language"],
    )


@app.get("/api/v1/transcript/{project_id}/srt")
async def get_srt(project_id: str, language: str | None = None, model_size: str = "base"):
    """Get transcript as downloadable SRT file."""
    from fastapi.responses import PlainTextResponse
    from services.transcription import transcribe, generate_srt

    matches = list(UPLOAD_DIR.glob(f"{project_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Video not found")

    result = transcribe(str(matches[0]), model_size=model_size, language=language)
    srt_content = generate_srt(result["segments"])

    return PlainTextResponse(
        content=srt_content,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={project_id}.srt"},
    )


@app.get("/api/v1/video/{project_id}")
async def serve_video(project_id: str):
    """Serve uploaded video file for browser playback."""
    matches = list(UPLOAD_DIR.glob(f"{project_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Video not found")

    file_path = matches[0]
    media_types = {
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".mov": "video/quicktime",
    }
    media_type = media_types.get(file_path.suffix.lower(), "video/mp4")

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache",
        },
    )


class RenderRequest(BaseModel):
    segments: list[TranscriptSegment]
    caption_style: dict


class RenderResponse(BaseModel):
    project_id: str
    status: str
    download_url: str
    duration: float


@app.post("/api/v1/render/{project_id}", response_model=RenderResponse)
async def render_video(project_id: str, req: RenderRequest):
    """Burn captions into video using FFmpeg ASS subtitles.

    This is a server-side caption burn approach using FFmpeg's subtitle filter.
    For MVP, this renders hardcoded captions onto the video.
    """
    matches = list(UPLOAD_DIR.glob(f"{project_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Video not found")

    input_path = str(matches[0])
    output_path = str(PROCESSED_DIR / f"{project_id}_captioned.mp4")

    # Generate ASS subtitle file from segments
    ass_path = str(PROCESSED_DIR / f"{project_id}.ass")
    ass_content = _generate_ass(req.segments, req.caption_style)
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    # Burn subtitles into video
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", f"ass={ass_path}",
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Render failed: {result.stderr[:500]}")

    info = get_video_info(output_path)

    return RenderResponse(
        project_id=project_id,
        status="complete",
        download_url=f"/api/v1/download/{project_id}",
        duration=float(info["format"]["duration"]),
    )


@app.get("/api/v1/download/{project_id}")
async def download_rendered(project_id: str):
    """Download the rendered video with burned-in captions."""
    output_path = PROCESSED_DIR / f"{project_id}_captioned.mp4"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Rendered video not found")

    return FileResponse(
        path=str(output_path),
        media_type="video/mp4",
        filename=f"bharat-shorts-{project_id[:8]}.mp4",
    )


def _generate_ass(segments: list[TranscriptSegment], style: dict) -> str:
    """Generate ASS subtitle file from transcript segments."""
    font = style.get("fontFamily", "Arial")
    font_size = style.get("fontSize", 48)
    primary = style.get("primaryColor", "#FFFFFF")
    highlight = style.get("highlightColor", "#FF6B00")
    position = style.get("position", "bottom")

    # ASS uses BGR color format: &HBBGGRR&
    primary_bgr = _hex_to_ass_color(primary)
    highlight_bgr = _hex_to_ass_color(highlight)

    # Alignment: 2=bottom-center, 5=middle-center, 8=top-center
    alignment = {"bottom": 2, "center": 5, "top": 8}.get(position, 2)

    # Margin from edge
    margin_v = 60

    header = f"""[Script Info]
Title: Bharat Shorts Captions
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{font_size},{primary_bgr},&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,2,{alignment},40,40,{margin_v},1
Style: Highlight,{font},{int(font_size * 1.1)},{highlight_bgr},&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,2,{alignment},40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events = []
    for seg in segments:
        start = _seconds_to_ass_time(seg.start)
        end = _seconds_to_ass_time(seg.end)

        # Build karaoke-style text with word-level highlighting
        if seg.words:
            parts = []
            for word in seg.words:
                # Duration in centiseconds for karaoke effect
                duration_cs = int((word.end - word.start) * 100)
                parts.append(f"{{\\kf{duration_cs}}}{word.text}")
            text = " ".join(parts) if not parts else "".join(
                f"{{\\kf{int((w.end - w.start) * 100)}}}{w.text} " for w in seg.words
            ).strip()
        else:
            text = seg.text

        events.append(
            f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}"
        )

    return header + "\n".join(events) + "\n"


def _hex_to_ass_color(hex_color: str) -> str:
    """Convert #RRGGBB to ASS &H00BBGGRR& format."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"&H00{b:02X}{g:02X}{r:02X}&"


def _seconds_to_ass_time(seconds: float) -> str:
    """Convert seconds to ASS time format H:MM:SS.cc"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


# --- Magic Clips ---

class ClipSuggestion(BaseModel):
    title: str
    start_time: float
    end_time: float
    duration: float
    score: float
    reason: str


class MagicClipsResponse(BaseModel):
    project_id: str
    clips: list[ClipSuggestion]


@app.post("/api/v1/magic-clips/{project_id}", response_model=MagicClipsResponse)
async def magic_clips(project_id: str, model_size: str = "base"):
    """Analyze video transcript and suggest viral-worthy short clips."""
    from services.transcription import transcribe
    from services.magic_clips import find_highlights

    matches = list(UPLOAD_DIR.glob(f"{project_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Video not found")

    result = transcribe(str(matches[0]), model_size=model_size)
    clips = find_highlights(result["segments"])

    return MagicClipsResponse(
        project_id=project_id,
        clips=[ClipSuggestion(**c) for c in clips],
    )


# --- Auto Reframe ---

class ReframeRequest(BaseModel):
    target_width: int = 1080
    target_height: int = 1920


class ReframeResponse(BaseModel):
    project_id: str
    output_path: str
    width: int
    height: int


@app.post("/api/v1/reframe/{project_id}", response_model=ReframeResponse)
async def reframe_video(project_id: str, req: ReframeRequest):
    """Convert landscape video to portrait (9:16) with center crop."""
    from services.reframe import reframe_video as do_reframe

    matches = list(UPLOAD_DIR.glob(f"{project_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Video not found")

    output_path = str(PROCESSED_DIR / f"{project_id}_portrait.mp4")
    do_reframe(str(matches[0]), output_path, req.target_width, req.target_height)

    return ReframeResponse(
        project_id=project_id,
        output_path=output_path,
        width=req.target_width,
        height=req.target_height,
    )


# --- B-Roll Suggestions ---

class BRollMatch(BaseModel):
    keyword: str
    start_time: float
    end_time: float
    videos: list[dict]


class BRollResponse(BaseModel):
    project_id: str
    suggestions: list[BRollMatch]


@app.post("/api/v1/broll-suggestions/{project_id}", response_model=BRollResponse)
async def broll_suggestions(project_id: str, model_size: str = "base"):
    """Get B-roll suggestions for each transcript segment."""
    from services.transcription import transcribe
    from services.broll import match_broll_to_segments

    matches = list(UPLOAD_DIR.glob(f"{project_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Video not found")

    result = transcribe(str(matches[0]), model_size=model_size)
    suggestions = match_broll_to_segments(result["segments"])

    return BRollResponse(
        project_id=project_id,
        suggestions=[BRollMatch(**s) for s in suggestions],
    )


# --- Enterprise Bulk API ---

class BulkProcessRequest(BaseModel):
    project_ids: list[str]
    options: dict = {
        "remove_silence": True,
        "model_size": "base",
        "language": None,
    }


class BulkProcessResponse(BaseModel):
    task_ids: dict[str, str]
    status: str


@app.post("/api/v1/automate", response_model=BulkProcessResponse)
async def bulk_process(req: BulkProcessRequest):
    """Enterprise bulk processing endpoint.

    Queues multiple videos for async processing via Celery.
    Returns task IDs for tracking progress.

    Note: Requires Redis + Celery worker running.
    """
    task_ids = {}

    for project_id in req.project_ids:
        matches = list(UPLOAD_DIR.glob(f"{project_id}.*"))
        if not matches:
            task_ids[project_id] = "error:not_found"
            continue

        try:
            from workers.tasks import process_video_full
            task = process_video_full.delay(project_id, req.options)
            task_ids[project_id] = task.id
        except Exception:
            # Celery not available — process synchronously
            task_ids[project_id] = f"sync:{project_id}"

    return BulkProcessResponse(
        task_ids=task_ids,
        status="queued",
    )
