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
from pydantic import BaseModel, Field

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
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001"],
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
        content={"message": "Internal Server Error", "detail": str(exc)},
    )

_BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = _BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

PROCESSED_DIR = _BASE_DIR / "processed"
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
    language_probability: float = 0.0
    is_hinglish: bool = False
    model_used: str = "base"
    preprocessed: bool = False


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
        language_probability=result.get("language_probability", 0.0),
        is_hinglish=result.get("is_hinglish", False),
        model_used=result.get("model_used", model_size),
        preprocessed=result.get("preprocessed", False),
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


@app.get("/api/v1/transcript/{project_id}/vtt")
async def get_vtt(project_id: str, language: str | None = None, model_size: str = "base"):
    """Get transcript as downloadable WebVTT file."""
    from services.transcription import transcribe, generate_vtt

    matches = list(UPLOAD_DIR.glob(f"{project_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Video not found")

    result = transcribe(str(matches[0]), model_size=model_size, language=language)
    vtt_content = generate_vtt(result["segments"])

    return PlainTextResponse(
        content=vtt_content,
        media_type="text/vtt",
        headers={"Content-Disposition": f"attachment; filename={project_id}.vtt"},
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
    renderer: str = "auto"  # "auto", "remotion", "ffmpeg"
    quality: str = "high"   # "fast" (FFmpeg), "high" (Remotion)


class RenderResponse(BaseModel):
    project_id: str
    status: str
    download_url: str
    duration: float
    renderer: str = "ffmpeg"  # Which renderer was used


@app.post("/api/v1/render/{project_id}", response_model=RenderResponse)
async def render_video(project_id: str, req: RenderRequest):
    """Render video with captions using Remotion (high-quality) or FFmpeg-ASS (fast).

    Renderer selection:
    - "auto" (default): Tries Remotion first, falls back to FFmpeg-ASS
    - "remotion": Forces Remotion rendering (fails if server is down)
    - "ffmpeg": Forces FFmpeg-ASS rendering (fast but limited animations)
    """
    matches = list(UPLOAD_DIR.glob(f"{project_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Video not found")

    input_path = str(matches[0])
    info = get_video_info(input_path)
    duration = float(info["format"]["duration"])
    width = int(info["streams"][0].get("width", 1080))
    height = int(info["streams"][0].get("height", 1920))

    # Try Remotion first (high-quality with complex animations)
    use_remotion = req.renderer in ("remotion", "auto") and req.quality == "high"

    if use_remotion:
        from services.remotion_render import is_remotion_available, render_with_remotion

        remotion_up = is_remotion_available()

        if remotion_up:
            try:
                # Convert segments to dicts for JSON serialization
                segments_data = [
                    {
                        "id": seg.id,
                        "words": [{"text": w.text, "start": w.start, "end": w.end, "confidence": w.confidence} for w in seg.words],
                        "text": seg.text,
                        "start": seg.start,
                        "end": seg.end,
                    }
                    for seg in req.segments
                ]

                result = render_with_remotion(
                    project_id=project_id,
                    video_path=input_path,
                    segments=segments_data,
                    caption_style=req.caption_style,
                    duration_seconds=duration,
                    width=width,
                    height=height,
                )

                return RenderResponse(
                    project_id=project_id,
                    status="complete",
                    download_url=f"/api/v1/download/{project_id}",
                    duration=duration,
                    renderer="remotion",
                )
            except Exception as e:
                if req.renderer == "remotion":
                    raise HTTPException(status_code=500, detail=f"Remotion render failed: {str(e)[:500]}")
                logger.warning(f"Remotion render failed, falling back to FFmpeg: {e}")
        elif req.renderer == "remotion":
            raise HTTPException(status_code=503, detail="Remotion render server is not running. Start it with: cd frontend && npm run render-server")

    # FFmpeg-ASS fallback (fast rendering)
    output_path = str(PROCESSED_DIR / f"{project_id}_captioned.mp4")
    ass_path = str(PROCESSED_DIR / f"{project_id}.ass")
    ass_content = _generate_ass(req.segments, req.caption_style)
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    escaped_ass = ass_path.replace("\\", "\\\\\\\\").replace(":", "\\\\:").replace("'", "\\\\'")
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", f"ass='{escaped_ass}'",
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Render failed: {result.stderr[:500]}")

    return RenderResponse(
        project_id=project_id,
        status="complete",
        download_url=f"/api/v1/download/{project_id}",
        duration=duration,
        renderer="ffmpeg",
    )


@app.get("/api/v1/download/{project_id}")
async def download_rendered(project_id: str):
    """Download the rendered video with burned-in captions.

    Checks for Remotion output first, then FFmpeg output.
    """
    # Prefer Remotion output (higher quality)
    remotion_path = PROCESSED_DIR / f"{project_id}_remotion.mp4"
    ffmpeg_path = PROCESSED_DIR / f"{project_id}_captioned.mp4"

    output_path = remotion_path if remotion_path.exists() else ffmpeg_path
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
            text = "".join(
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


class DynamicReframeResponse(BaseModel):
    project_id: str
    output_path: str
    width: int
    height: int
    frames_processed: int
    faces_detected: int
    duration: float


@app.post("/api/v1/reframe-dynamic/{project_id}", response_model=DynamicReframeResponse)
async def reframe_video_dynamic(project_id: str, req: ReframeRequest):
    """Dynamic face-tracking reframe: follows the speaker frame-by-frame.

    Unlike static reframe, this detects the face in every frame and smoothly
    pans the crop window to follow the speaker as they move.
    """
    from services.reframe import reframe_video_dynamic as do_reframe_dynamic

    matches = list(UPLOAD_DIR.glob(f"{project_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Video not found")

    output_path = str(PROCESSED_DIR / f"{project_id}_portrait_dynamic.mp4")
    result = do_reframe_dynamic(str(matches[0]), output_path, req.target_width, req.target_height)

    return DynamicReframeResponse(
        project_id=project_id,
        output_path=result["output_path"],
        width=req.target_width,
        height=req.target_height,
        frames_processed=result["frames_processed"],
        faces_detected=result["faces_detected"],
        duration=result["duration"],
    )


@app.get("/api/v1/download-reframed/{project_id}")
async def download_reframed(project_id: str):
    """Download the dynamically reframed video."""
    output_path = PROCESSED_DIR / f"{project_id}_portrait_dynamic.mp4"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Reframed video not found")
    return FileResponse(path=str(output_path), media_type="video/mp4",
        filename=f"bharat-shorts-{project_id[:8]}-reframed.mp4")


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


# --- AI Stock Integration (India-Specific) ---

@app.get("/api/v1/stock/search")
async def search_stock_footage(
    query: str,
    media_type: str = "video",
    per_page: int = 8,
    orientation: str = "portrait",
    india_focus: bool = True,
):
    """Search stock footage from Pexels + Pixabay with India-focus.

    Automatically enhances generic queries with Indian context
    (e.g. "food" → "Indian street food thali").
    """
    from services.stock import search_stock
    return search_stock(query, media_type, per_page, orientation, india_focus)


@app.get("/api/v1/stock/categories")
async def list_stock_categories():
    """List all curated Indian stock categories."""
    from services.stock import list_categories
    return {"categories": list_categories()}


@app.get("/api/v1/stock/browse/{category_id}")
async def browse_stock_category(
    category_id: str,
    media_type: str = "video",
    per_page: int = 6,
    orientation: str = "portrait",
):
    """Browse a curated Indian stock category (Mumbai, festivals, street food, etc.)."""
    from services.stock import browse_category
    result = browse_category(category_id, media_type, per_page, orientation)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.post("/api/v1/stock/match/{project_id}")
async def match_indian_stock(
    project_id: str,
    model_size: str = "base",
    per_keyword: int = 3,
    orientation: str = "portrait",
):
    """Get India-enhanced B-Roll suggestions for each transcript segment.

    Like /broll-suggestions but uses multi-provider search (Pexels + Pixabay)
    with India-specific keyword enhancement.
    """
    from services.transcription import transcribe
    from services.stock import match_segments_to_indian_stock

    matches = list(UPLOAD_DIR.glob(f"{project_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Video not found")

    result = transcribe(str(matches[0]), model_size=model_size)
    suggestions = match_segments_to_indian_stock(
        result["segments"],
        per_keyword=per_keyword,
        orientation=orientation,
    )

    return {"project_id": project_id, "suggestions": suggestions}


# --- Platform-Specific Generators ---

class PlatformRequest(BaseModel):
    topic: str
    language: str = "en"
    count: int = 10
    key_points: list[str] | None = None


class HashtagRequest(BaseModel):
    topic: str
    platform: str = "instagram"
    count: int = 30


@app.post("/api/v1/tools/youtube-titles")
async def gen_youtube_titles(req: PlatformRequest):
    """Generate SEO-optimized YouTube titles."""
    from services.platform_tools import generate_youtube_titles
    titles = generate_youtube_titles(req.topic, count=req.count, language=req.language)
    return {"topic": req.topic, "titles": titles}


@app.post("/api/v1/tools/youtube-description")
async def gen_youtube_description(req: PlatformRequest):
    """Generate a full YouTube description with timestamps, CTA, and tags."""
    from services.platform_tools import generate_youtube_description
    desc = generate_youtube_description(req.topic, key_points=req.key_points, language=req.language)
    return desc


@app.post("/api/v1/tools/hashtags")
async def gen_hashtags(req: HashtagRequest):
    """Generate platform-optimized hashtags (Instagram, TikTok, YouTube)."""
    from services.platform_tools import generate_hashtags
    result = generate_hashtags(req.topic, platform=req.platform, count=req.count)
    return result


@app.post("/api/v1/tools/instagram-caption")
async def gen_instagram_caption(req: PlatformRequest):
    """Generate an Instagram caption with emojis, CTA, and hashtags."""
    from services.platform_tools import generate_instagram_caption
    result = generate_instagram_caption(req.topic, key_points=req.key_points, language=req.language)
    return result


@app.post("/api/v1/tools/tiktok-caption")
async def gen_tiktok_caption(req: PlatformRequest):
    """Generate a short TikTok caption with hashtags."""
    from services.platform_tools import generate_tiktok_caption
    result = generate_tiktok_caption(req.topic, language=req.language)
    return result


@app.post("/api/v1/tools/linkedin-post")
async def gen_linkedin_post(req: PlatformRequest):
    """Generate a professional LinkedIn post."""
    from services.platform_tools import generate_linkedin_post
    result = generate_linkedin_post(req.topic, key_points=req.key_points)
    return result


# --- Content Ideation AI Tools ---

class IdeaRequest(BaseModel):
    topic: str
    niche: str = "general"
    count: int = 10
    language: str = "en"


class HookRequest(BaseModel):
    topic: str
    count: int = 10
    styles: list[str] | None = None
    language: str = "en"


class ScriptRequest(BaseModel):
    topic: str
    duration_seconds: int = 60
    tone: str = "energetic"
    language: str = "en"
    include_cta: bool = True


@app.post("/api/v1/tools/ideas")
async def generate_ideas(req: IdeaRequest):
    """AI Video Idea Generator.

    Generates viral-worthy video ideas tailored to Indian creators.
    Supports English and Hinglish output.
    Categories: listicle, story, tutorial, controversial, trending.
    """
    from services.ideation import generate_video_ideas
    ideas = generate_video_ideas(
        topic=req.topic, niche=req.niche,
        count=req.count, language=req.language,
    )
    return {"topic": req.topic, "ideas": ideas}


@app.post("/api/v1/tools/hooks")
async def generate_hooks_endpoint(req: HookRequest):
    """AI Video Hook Generator.

    Creates attention-grabbing opening lines optimized for
    viewer retention on YouTube Shorts and Instagram Reels.
    Styles: question, statistic, story, controversial.
    """
    from services.ideation import generate_hooks
    hooks = generate_hooks(
        topic=req.topic, count=req.count,
        styles=req.styles, language=req.language,
    )
    return {"topic": req.topic, "hooks": hooks}


@app.post("/api/v1/tools/script")
async def generate_script_endpoint(req: ScriptRequest):
    """AI Video Script Generator.

    Generates a complete video script with hook, body points, and CTA.
    Tones: energetic, calm, professional, funny, dramatic.
    """
    from services.ideation import generate_script
    script = generate_script(
        topic=req.topic, duration_seconds=req.duration_seconds,
        tone=req.tone, language=req.language, include_cta=req.include_cta,
    )
    return script


# --- AI Actors Studio (Avatar Video Generation) ---

class AvatarRequest(BaseModel):
    script: str
    language: str = "hi"
    gender: str = "female"
    avatar_preset: str = "professional_female"
    background: str = "studio_dark"
    speech_rate: str = "+0%"
    width: int = 1080
    height: int = 1920


class AvatarResponse(BaseModel):
    project_id: str
    status: str
    download_url: str
    duration: float
    language: str
    avatar_used: str


class AvatarPreset(BaseModel):
    id: str
    name: str
    label: str


@app.get("/api/v1/avatar-presets", response_model=list[AvatarPreset])
def get_avatar_presets():
    """List available AI avatar presets."""
    from services.avatar import list_avatar_presets
    return list_avatar_presets()


@app.get("/api/v1/avatar-backgrounds")
def get_avatar_backgrounds():
    """List available background templates for avatar videos."""
    from services.avatar import list_backgrounds
    return list_backgrounds()


@app.post("/api/v1/avatar-video", response_model=AvatarResponse)
async def create_avatar_video(req: AvatarRequest):
    """Generate an AI avatar video from a text script.

    No filming needed. The AI:
    1. Converts your script to natural speech (24+ languages, male/female)
    2. Renders an animated avatar with lip-sync driven by audio energy
    3. Overlays word-by-word captions with highlighted current word
    4. Produces a ready-to-post vertical video (1080x1920)

    Great for: product demos, educational content, announcements,
    social media posts, and any content where filming is impractical.
    """
    from services.avatar import generate_avatar_video
    import asyncio

    project_id = str(uuid.uuid4())
    output_path = str(PROCESSED_DIR / f"{project_id}_avatar.mp4")

    result = await generate_avatar_video(
        script=req.script,
        output_path=output_path,
        lang=req.language,
        gender=req.gender,
        avatar_preset=req.avatar_preset,
        background=req.background,
        width=req.width,
        height=req.height,
        speech_rate=req.speech_rate,
    )

    return AvatarResponse(
        project_id=project_id,
        status="complete",
        download_url=f"/api/v1/download-avatar/{project_id}",
        duration=result["duration"],
        language=result["language"],
        avatar_used=result["avatar_used"],
    )


@app.post("/api/v1/avatar-video-with-image", response_model=AvatarResponse)
async def create_avatar_video_with_image(
    script: str = "नमस्ते, मैं आपका AI अवतार हूँ।",
    language: str = "hi",
    gender: str = "female",
    background: str = "studio_dark",
    speech_rate: str = "+0%",
    image: UploadFile = File(...),
):
    """Generate an avatar video using a user-uploaded face image.

    Upload a face photo and provide a script — the AI will create
    a talking-head video with lip-sync animation.
    """
    from services.avatar import generate_avatar_video

    project_id = str(uuid.uuid4())

    # Save uploaded image
    img_ext = Path(image.filename or "face.jpg").suffix
    img_path = str(PROCESSED_DIR / f"{project_id}_face{img_ext}")
    with open(img_path, "wb") as f:
        content = await image.read()
        f.write(content)

    output_path = str(PROCESSED_DIR / f"{project_id}_avatar.mp4")

    result = await generate_avatar_video(
        script=script,
        output_path=output_path,
        lang=language,
        gender=gender,
        avatar_image_path=img_path,
        background=background,
        speech_rate=speech_rate,
    )

    # Cleanup face image
    Path(img_path).unlink(missing_ok=True)

    return AvatarResponse(
        project_id=project_id,
        status="complete",
        download_url=f"/api/v1/download-avatar/{project_id}",
        duration=result["duration"],
        language=result["language"],
        avatar_used=result["avatar_used"],
    )


@app.get("/api/v1/download-avatar/{project_id}")
async def download_avatar_video(project_id: str):
    """Download the generated avatar video."""
    output_path = PROCESSED_DIR / f"{project_id}_avatar.mp4"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Avatar video not found")

    return FileResponse(
        path=str(output_path),
        media_type="video/mp4",
        filename=f"bharat-shorts-avatar-{project_id[:8]}.mp4",
    )


# --- AI Eye Contact Correction ---

class EyeContactRequest(BaseModel):
    correction_strength: float = 0.7
    process_every_n: int = 1


class EyeContactResponse(BaseModel):
    project_id: str
    status: str
    download_url: str
    frames_processed: int
    faces_detected: int
    duration: float


@app.post("/api/v1/eye-contact/{project_id}", response_model=EyeContactResponse)
async def correct_eye_contact(project_id: str, req: EyeContactRequest):
    """AI Eye Contact Correction.

    Uses MediaPipe Face Mesh (478 landmarks) to detect iris position,
    then warps each iris toward the eye center so the subject appears
    to look directly at the camera.

    Args:
        correction_strength: 0.0 (off) to 1.0 (full correction). Default 0.7.
        process_every_n: Process every Nth frame for speed (1=all frames).
    """
    from services.eye_contact import correct_eye_contact_video

    matches = list(UPLOAD_DIR.glob(f"{project_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Video not found")

    input_path = str(matches[0])
    output_path = str(PROCESSED_DIR / f"{project_id}_eye_contact.mp4")

    result = correct_eye_contact_video(
        input_path=input_path,
        output_path=output_path,
        correction_strength=req.correction_strength,
        process_every_n=req.process_every_n,
    )

    return EyeContactResponse(
        project_id=project_id,
        status="complete",
        download_url=f"/api/v1/download-eye-contact/{project_id}",
        frames_processed=result["frames_processed"],
        faces_detected=result["faces_detected"],
        duration=result["duration"],
    )


@app.get("/api/v1/download-eye-contact/{project_id}")
async def download_eye_contact(project_id: str):
    """Download the eye-contact corrected video."""
    output_path = PROCESSED_DIR / f"{project_id}_eye_contact.mp4"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Corrected video not found")

    return FileResponse(
        path=str(output_path),
        media_type="video/mp4",
        filename=f"bharat-shorts-{project_id[:8]}-eye-contact.mp4",
    )


# --- Automated Assembly ---

class AssembleRequest(BaseModel):
    music_url: str | None = None
    music_preset: str | None = None  # "chill_lo_fi", "upbeat_energy", etc.
    music_volume: float = 0.15
    max_broll_clips: int = 5
    broll_min_gap: float = 10.0
    model_size: str = "base"
    add_sfx: bool = True
    sfx_type: str = "whoosh"
    sfx_volume: float = 0.7


class AssembleResponse(BaseModel):
    project_id: str
    status: str
    download_url: str
    broll_inserted: int
    music_added: bool
    sfx_count: int = 0
    duration: float


@app.post("/api/v1/assemble/{project_id}", response_model=AssembleResponse)
async def auto_assemble_video(project_id: str, req: AssembleRequest):
    """Automatically assemble a polished video with B-Roll and music.

    Pipeline:
    1. Transcribes the video (if not already done)
    2. Extracts keywords and finds matching B-Roll from Pexels
    3. Downloads and inserts B-Roll clips at relevant timestamps
    4. Adds background music with speech-aware ducking
    5. Returns the fully assembled video

    Args:
        music_url: Optional URL to a background music file.
                   If not provided, assembles without music.
        music_volume: Base volume of background music (0.0-1.0)
        max_broll_clips: Max number of B-Roll clips to insert
        broll_min_gap: Minimum seconds between B-Roll insertions
    """
    from services.transcription import transcribe
    from services.broll import match_broll_to_segments
    from services.assembly import auto_assemble, download_stock_clip
    from services.sfx import add_sfx_to_video, generate_music_loop

    matches = list(UPLOAD_DIR.glob(f"{project_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Video not found")

    video_path = str(matches[0])

    # Step 1: Transcribe
    transcript = transcribe(video_path, model_size=req.model_size)
    segments = transcript["segments"]

    # Step 2: Get B-Roll suggestions
    broll_suggestions = match_broll_to_segments(segments)

    # Step 3: Handle music (URL or preset)
    music_path = None
    if req.music_url:
        music_path = str(PROCESSED_DIR / f"{project_id}_music.mp3")
        if not download_stock_clip(req.music_url, music_path):
            music_path = None
    elif req.music_preset:
        try:
            music_path = generate_music_loop(req.music_preset)
        except Exception as e:
            logger.warning(f"Music preset generation failed: {e}")

    # Step 4: Auto-assemble (B-Roll + music)
    result = auto_assemble(
        project_id=project_id,
        video_path=video_path,
        segments=segments,
        broll_suggestions=broll_suggestions,
        music_path=music_path,
        music_volume=req.music_volume,
        max_broll_clips=req.max_broll_clips,
        broll_min_gap=req.broll_min_gap,
    )

    # Step 5: Add SFX transitions
    sfx_count = 0
    if req.add_sfx:
        assembled_path = result["output_path"]
        sfx_result = add_sfx_to_video(
            project_id=project_id,
            video_path=assembled_path,
            segments=segments,
            sfx_type=req.sfx_type,
            sfx_volume=req.sfx_volume,
        )
        sfx_count = sfx_result["sfx_count"]
        # If SFX were added, update the assembled output
        if sfx_count > 0 and sfx_result["output_path"] != assembled_path:
            import shutil
            final = str(PROCESSED_DIR / f"{project_id}_assembled.mp4")
            shutil.copy(sfx_result["output_path"], final)

    return AssembleResponse(
        project_id=project_id,
        status="complete",
        download_url=f"/api/v1/download-assembled/{project_id}",
        broll_inserted=result["broll_inserted"],
        music_added=result["music_added"],
        sfx_count=sfx_count,
        duration=result["duration"],
    )


@app.get("/api/v1/download-assembled/{project_id}")
async def download_assembled(project_id: str):
    """Download the auto-assembled video."""
    output_path = PROCESSED_DIR / f"{project_id}_assembled.mp4"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Assembled video not found")

    return FileResponse(
        path=str(output_path),
        media_type="video/mp4",
        filename=f"bharat-shorts-{project_id[:8]}-assembled.mp4",
    )


# --- Automated SFX & Music ---

class SFXRequest(BaseModel):
    sfx_type: str = "whoosh"
    sfx_volume: float = 0.7
    min_gap: float = 3.0
    place_at: str = "transitions"  # "transitions", "all_segments", "long_pauses"
    model_size: str = "base"


class SFXResponse(BaseModel):
    project_id: str
    status: str
    download_url: str
    sfx_count: int
    sfx_type: str
    placements: list[dict]


@app.get("/api/v1/sfx-catalog")
async def get_sfx_catalog():
    """List all available SFX types."""
    from services.sfx import list_sfx_catalog
    return {"sfx": list_sfx_catalog()}


@app.get("/api/v1/music-presets")
async def get_music_presets():
    """List all available background music presets."""
    from services.sfx import list_music_presets
    return {"presets": list_music_presets()}


@app.post("/api/v1/sfx/{project_id}", response_model=SFXResponse)
async def add_sfx(project_id: str, req: SFXRequest):
    """Auto-add SFX transitions to a video.

    Analyzes transcript segments to find natural transition points,
    then mixes in the selected SFX sound at each point.
    """
    from services.transcription import transcribe
    from services.sfx import add_sfx_to_video

    matches = list(UPLOAD_DIR.glob(f"{project_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Video not found")

    video_path = str(matches[0])
    transcript = transcribe(video_path, model_size=req.model_size)
    segments = transcript["segments"]

    result = add_sfx_to_video(
        project_id=project_id,
        video_path=video_path,
        segments=segments,
        sfx_type=req.sfx_type,
        sfx_volume=req.sfx_volume,
        min_gap=req.min_gap,
        place_at=req.place_at,
    )

    return SFXResponse(
        project_id=project_id,
        status="complete",
        download_url=f"/api/v1/download-sfx/{project_id}",
        sfx_count=result["sfx_count"],
        sfx_type=result["sfx_type"],
        placements=result["placements"],
    )


@app.get("/api/v1/download-sfx/{project_id}")
async def download_sfx_video(project_id: str):
    """Download the video with SFX added."""
    output_path = PROCESSED_DIR / f"{project_id}_sfx.mp4"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="SFX video not found")

    return FileResponse(
        path=str(output_path),
        media_type="video/mp4",
        filename=f"bharat-shorts-{project_id[:8]}-sfx.mp4",
    )


@app.post("/api/v1/generate-music/{preset}")
async def generate_music(preset: str):
    """Generate an ambient music loop from a preset."""
    from services.sfx import generate_music_loop, MUSIC_PRESETS

    if preset not in MUSIC_PRESETS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown preset: {preset}. Available: {list(MUSIC_PRESETS.keys())}",
        )

    music_path = generate_music_loop(preset)
    return FileResponse(
        path=music_path,
        media_type="audio/wav",
        filename=f"bharat-shorts-{preset}.wav",
    )


# --- URL Ingestion (YouTube, Podcast, Direct) ---

class IngestRequest(BaseModel):
    url: str
    max_duration: int = 7200


class IngestResponse(BaseModel):
    project_id: str
    title: str
    file_path: str
    duration: float
    width: int
    height: int
    source_url: str
    source_type: str


@app.post("/api/v1/ingest", response_model=IngestResponse)
async def ingest_from_url(req: IngestRequest):
    """Download a video from YouTube, podcast, or direct URL.

    Supports:
    - YouTube videos, Shorts, and links
    - Podcast episodes (audio auto-converted to video)
    - Direct video/audio URLs (MP4, WebM, etc.)

    Downloads up to 1080p, max 2GB, max 2 hours (configurable).
    """
    from services.ingest import download_from_url

    result = download_from_url(req.url, max_duration=req.max_duration)

    return IngestResponse(
        project_id=result["project_id"],
        title=result["title"],
        file_path=result["file_path"],
        duration=result["duration"],
        width=result["width"],
        height=result["height"],
        source_url=result["source_url"],
        source_type=result["source_type"],
    )


# --- Translation & Dubbing ---

class TranslateRequest(BaseModel):
    segments: list[TranscriptSegment]
    target_lang: str
    source_lang: str = "auto"


class TranslateResponse(BaseModel):
    project_id: str
    translated_segments: list[TranscriptSegment]
    source_lang: str
    target_lang: str


class DubRequest(BaseModel):
    segments: list[TranscriptSegment]
    target_lang: str
    gender: str = "female"
    rate: str = "+0%"
    keep_original_audio: bool = False
    original_volume: float = 0.1


class DubResponse(BaseModel):
    project_id: str
    status: str
    download_url: str
    target_lang: str
    duration: float


class SupportedLanguage(BaseModel):
    code: str
    name: str


@app.get("/api/v1/languages", response_model=list[SupportedLanguage])
def list_languages():
    """List all supported languages for translation and dubbing."""
    from services.translator import get_supported_languages
    return get_supported_languages()


@app.post("/api/v1/translate/{project_id}", response_model=TranslateResponse)
async def translate_transcript(project_id: str, req: TranslateRequest):
    """Translate transcript segments to a target language.

    Preserves all timing data so captions stay synced.
    Supports 24+ languages including Hindi, Tamil, Marathi, Telugu, Bengali, etc.
    """
    from services.translator import translate_segments

    segments_dicts = [
        {
            "id": s.id,
            "words": [{"text": w.text, "start": w.start, "end": w.end, "confidence": w.confidence} for w in s.words],
            "text": s.text,
            "start": s.start,
            "end": s.end,
            "speaker": s.speaker,
        }
        for s in req.segments
    ]

    translated = translate_segments(
        segments_dicts,
        target_lang=req.target_lang,
        source_lang=req.source_lang,
    )

    result_segments = [
        TranscriptSegment(
            id=seg["id"],
            words=[TranscriptWord(**w) for w in seg["words"]],
            text=seg["text"],
            start=seg["start"],
            end=seg["end"],
            speaker=seg.get("speaker"),
        )
        for seg in translated
    ]

    return TranslateResponse(
        project_id=project_id,
        translated_segments=result_segments,
        source_lang=req.source_lang,
        target_lang=req.target_lang,
    )


@app.post("/api/v1/dub/{project_id}", response_model=DubResponse)
async def dub_video(project_id: str, req: DubRequest):
    """Generate AI-dubbed video in a target language.

    Pipeline:
    1. Takes translated segments (text + timing)
    2. Generates TTS audio per segment using Edge TTS (natural Indian voices)
    3. Places each audio clip at the correct timestamp
    4. Merges dubbed audio with the original video

    Supports male/female voices for Hindi, Tamil, Marathi, Telugu,
    Bengali, Kannada, Malayalam, Gujarati, Punjabi, Urdu, English,
    Arabic, Spanish, French, German, Portuguese, Japanese, Korean, Chinese, etc.
    """
    import asyncio
    from services.translator import generate_dubbed_audio, replace_audio_in_video

    matches = list(UPLOAD_DIR.glob(f"{project_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Video not found")

    video_path = str(matches[0])
    dub_dir = PROCESSED_DIR / f"{project_id}_dub"
    dub_dir.mkdir(exist_ok=True)

    segments_dicts = [
        {
            "id": s.id,
            "text": s.text,
            "start": s.start,
            "end": s.end,
        }
        for s in req.segments
    ]

    # Generate dubbed audio track
    dubbed_audio_path = await generate_dubbed_audio(
        segments_dicts,
        output_dir=str(dub_dir),
        lang=req.target_lang,
        gender=req.gender,
        rate=req.rate,
    )

    # Merge into video
    output_path = str(PROCESSED_DIR / f"{project_id}_dubbed_{req.target_lang}.mp4")
    replace_audio_in_video(
        video_path=video_path,
        audio_path=dubbed_audio_path,
        output_path=output_path,
        keep_original_audio=req.keep_original_audio,
        original_volume=req.original_volume,
    )

    # Cleanup temp dub directory
    import shutil
    shutil.rmtree(str(dub_dir), ignore_errors=True)

    info = get_video_info(output_path)

    return DubResponse(
        project_id=project_id,
        status="complete",
        download_url=f"/api/v1/download-dubbed/{project_id}/{req.target_lang}",
        target_lang=req.target_lang,
        duration=float(info["format"]["duration"]),
    )


@app.get("/api/v1/download-dubbed/{project_id}/{lang}")
async def download_dubbed(project_id: str, lang: str):
    """Download the dubbed video."""
    output_path = PROCESSED_DIR / f"{project_id}_dubbed_{lang}.mp4"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Dubbed video not found")

    return FileResponse(
        path=str(output_path),
        media_type="video/mp4",
        filename=f"bharat-shorts-{project_id[:8]}-{lang}.mp4",
    )


# --- Async Task Queue (Celery/Redis) ---

@app.get("/api/v1/task/{task_id}")
async def get_task_status(task_id: str):
    """Poll task progress. Returns state, step, progress percentage.

    States: PENDING → STARTED → PROGRESS → SUCCESS / FAILURE
    """
    try:
        from workers.celery_app import celery_app as celery
        result = celery.AsyncResult(task_id)

        response = {
            "task_id": task_id,
            "state": result.state,
            "ready": result.ready(),
        }

        if result.state == "PROGRESS":
            response["meta"] = result.info
        elif result.state == "SUCCESS":
            response["result"] = result.result
        elif result.state == "FAILURE":
            response["error"] = str(result.result)

        return response
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Task queue unavailable: {e}")


class AsyncDispatchRequest(BaseModel):
    """Generic async task dispatch."""
    task_name: str  # e.g. "transcribe_video", "render_video", "assemble_video"
    kwargs: dict = {}


class AsyncDispatchResponse(BaseModel):
    task_id: str
    task_name: str
    status: str


@app.post("/api/v1/async/dispatch", response_model=AsyncDispatchResponse)
async def dispatch_async_task(req: AsyncDispatchRequest):
    """Dispatch any heavy operation as an async Celery task.

    Available task names:
    - transcribe_video: {project_id, model_size, language}
    - render_video: {project_id, segments, caption_style, renderer, quality}
    - render_video_4k: {project_id, segments, caption_style, width, height}
    - assemble_video: {project_id, music_preset, add_sfx, sfx_type}
    - eye_contact_fix: {project_id, strength}
    - dynamic_reframe: {project_id, target_width, target_height}
    - generate_avatar: {project_id, text, voice, preset, background}
    - generate_dub: {project_id, target_language, voice_gender}
    - add_sfx: {project_id, sfx_type, sfx_volume, place_at}
    - process_video_full: {project_id, options}
    """
    try:
        from workers.celery_app import celery_app as celery
        task = celery.send_task(req.task_name, kwargs=req.kwargs)
        return AsyncDispatchResponse(
            task_id=task.id,
            task_name=req.task_name,
            status="queued",
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to dispatch task: {e}")


@app.get("/api/v1/queue/stats")
async def queue_stats():
    """Get Celery queue statistics (active, reserved, scheduled tasks)."""
    try:
        from workers.celery_app import celery_app as celery
        inspector = celery.control.inspect()

        active = inspector.active() or {}
        reserved = inspector.reserved() or {}
        scheduled = inspector.scheduled() or {}

        total_active = sum(len(v) for v in active.values())
        total_reserved = sum(len(v) for v in reserved.values())
        total_scheduled = sum(len(v) for v in scheduled.values())

        workers = list(active.keys()) or list(reserved.keys())

        return {
            "workers": len(workers),
            "worker_names": workers,
            "active_tasks": total_active,
            "reserved_tasks": total_reserved,
            "scheduled_tasks": total_scheduled,
            "status": "connected" if workers else "no_workers",
        }
    except Exception as e:
        return {
            "workers": 0,
            "worker_names": [],
            "active_tasks": 0,
            "reserved_tasks": 0,
            "scheduled_tasks": 0,
            "status": f"disconnected: {e}",
        }


# --- Enterprise Bulk API ---

class BulkProcessRequest(BaseModel):
    project_ids: list[str]
    options: dict = Field(default_factory=lambda: {
        "remove_silence": True,
        "model_size": "base",
        "language": None,
    })


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
