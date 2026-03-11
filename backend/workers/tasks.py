"""
Celery Tasks for Bharat Shorts

Individual async tasks for every CPU-heavy operation.
Each task reports progress via self.update_state() for frontend polling.

Queue routing:
- gpu: transcription, rendering, eye contact, reframe, avatar
- default: assembly, dubbing, full pipeline
- low: SFX, stock matching
"""

from pathlib import Path
from workers.celery_app import celery_app

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "processed"
PROCESSED_DIR.mkdir(exist_ok=True)


def _find_video(project_id: str) -> str | None:
    """Find uploaded video by project ID."""
    matches = list(UPLOAD_DIR.glob(f"{project_id}.*"))
    return str(matches[0]) if matches else None


# ─── Transcription ────────────────────────────────────────────────────────

@celery_app.task(bind=True, name="transcribe_video")
def transcribe_video(
    self,
    project_id: str,
    model_size: str = "base",
    language: str | None = None,
    preprocess: bool = True,
) -> dict:
    """Transcribe video with Faster-Whisper (CPU/GPU heavy)."""
    from services.transcription import transcribe, generate_srt, generate_vtt

    video_path = _find_video(project_id)
    if not video_path:
        return {"error": "Video not found", "project_id": project_id}

    self.update_state(state="PROGRESS", meta={"step": "transcribing", "progress": 0.1})

    result = transcribe(
        video_path,
        model_size=model_size,
        language=language,
        preprocess=preprocess,
    )

    self.update_state(state="PROGRESS", meta={"step": "generating_srt", "progress": 0.9})

    # Save SRT + VTT
    srt_content = generate_srt(result["segments"])
    vtt_content = generate_vtt(result["segments"])
    Path(PROCESSED_DIR / f"{project_id}.srt").write_text(srt_content, encoding="utf-8")
    Path(PROCESSED_DIR / f"{project_id}.vtt").write_text(vtt_content, encoding="utf-8")

    return {
        "project_id": project_id,
        "status": "complete",
        "language": result["language"],
        "language_probability": result["language_probability"],
        "is_hinglish": result["is_hinglish"],
        "model_used": result["model_used"],
        "segment_count": len(result["segments"]),
        "segments": result["segments"],
    }


# ─── Render ───────────────────────────────────────────────────────────────

@celery_app.task(bind=True, name="render_video")
def render_video(
    self,
    project_id: str,
    segments: list[dict],
    caption_style: dict,
    renderer: str = "auto",
    quality: str = "high",
) -> dict:
    """Render video with captions (Remotion or FFmpeg-ASS)."""
    import subprocess
    import json

    video_path = _find_video(project_id)
    if not video_path:
        return {"error": "Video not found", "project_id": project_id}

    self.update_state(state="PROGRESS", meta={"step": "preparing", "progress": 0.1})

    # Get video info
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", video_path]
    probe = subprocess.run(cmd, capture_output=True, text=True)
    info = json.loads(probe.stdout) if probe.returncode == 0 else {}
    duration = float(info.get("format", {}).get("duration", 0))

    use_remotion = renderer in ("remotion", "auto") and quality == "high"
    rendered_with = "ffmpeg"

    if use_remotion:
        self.update_state(state="PROGRESS", meta={"step": "remotion_render", "progress": 0.2})
        try:
            from services.remotion_render import is_remotion_available, render_with_remotion
            if is_remotion_available():
                width = int(info.get("streams", [{}])[0].get("width", 1080))
                height = int(info.get("streams", [{}])[0].get("height", 1920))
                render_with_remotion(
                    project_id=project_id,
                    video_path=video_path,
                    segments=segments,
                    caption_style=caption_style,
                    duration_seconds=duration,
                    width=width,
                    height=height,
                )
                rendered_with = "remotion"
        except Exception:
            pass  # Fall through to FFmpeg

    if rendered_with == "ffmpeg":
        self.update_state(state="PROGRESS", meta={"step": "ffmpeg_render", "progress": 0.3})
        # Generate ASS and burn
        from app.main import _generate_ass, _seconds_to_ass_time

        output_path = str(PROCESSED_DIR / f"{project_id}_captioned.mp4")
        ass_path = str(PROCESSED_DIR / f"{project_id}.ass")

        # Convert segment dicts to objects for _generate_ass
        from pydantic import BaseModel

        class W(BaseModel):
            text: str; start: float; end: float; confidence: float = 0.0
        class S(BaseModel):
            id: str; words: list[W]; text: str; start: float; end: float; speaker: str | None = None

        seg_models = [S(**{**s, "words": [W(**w) for w in s.get("words", [])]}) for s in segments]
        ass_content = _generate_ass(seg_models, caption_style)
        Path(ass_path).write_text(ass_content, encoding="utf-8")

        escaped = ass_path.replace("\\", "\\\\\\\\").replace(":", "\\\\:").replace("'", "\\\\'")
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", f"ass='{escaped}'",
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac",
            output_path,
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    return {
        "project_id": project_id,
        "status": "complete",
        "renderer": rendered_with,
        "download_url": f"/api/v1/download/{project_id}",
        "duration": duration,
    }


@celery_app.task(bind=True, name="render_video_4k")
def render_video_4k(
    self,
    project_id: str,
    segments: list[dict],
    caption_style: dict,
    width: int = 3840,
    height: int = 2160,
) -> dict:
    """Render video at 4K resolution (GPU queue, high resource)."""
    self.update_state(state="PROGRESS", meta={"step": "4k_render", "progress": 0.1})

    video_path = _find_video(project_id)
    if not video_path:
        return {"error": "Video not found", "project_id": project_id}

    try:
        from services.remotion_render import is_remotion_available, render_with_remotion
        import subprocess, json

        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", video_path]
        probe = subprocess.run(cmd, capture_output=True, text=True)
        info = json.loads(probe.stdout) if probe.returncode == 0 else {}
        duration = float(info.get("format", {}).get("duration", 0))

        if is_remotion_available():
            self.update_state(state="PROGRESS", meta={"step": "rendering_4k", "progress": 0.3})
            render_with_remotion(
                project_id=project_id,
                video_path=video_path,
                segments=segments,
                caption_style=caption_style,
                duration_seconds=duration,
                width=width,
                height=height,
                crf=15,  # Higher quality for 4K
            )
            return {
                "project_id": project_id,
                "status": "complete",
                "renderer": "remotion",
                "resolution": f"{width}x{height}",
                "download_url": f"/api/v1/download/{project_id}",
            }
        else:
            return {"error": "Remotion render server not available for 4K", "project_id": project_id}
    except Exception as e:
        return {"error": str(e), "project_id": project_id}


# ─── Assembly ─────────────────────────────────────────────────────────────

@celery_app.task(bind=True, name="assemble_video")
def assemble_video(
    self,
    project_id: str,
    model_size: str = "base",
    music_preset: str | None = "chill_lo_fi",
    music_volume: float = 0.15,
    max_broll_clips: int = 5,
    add_sfx: bool = True,
    sfx_type: str = "whoosh",
) -> dict:
    """Full auto-assembly: transcribe → B-Roll → music → SFX."""
    from services.transcription import transcribe
    from services.broll import match_broll_to_segments
    from services.assembly import auto_assemble, download_stock_clip
    from services.sfx import add_sfx_to_video, generate_music_loop

    video_path = _find_video(project_id)
    if not video_path:
        return {"error": "Video not found", "project_id": project_id}

    self.update_state(state="PROGRESS", meta={"step": "transcribing", "progress": 0.1})
    transcript = transcribe(video_path, model_size=model_size)
    segments = transcript["segments"]

    self.update_state(state="PROGRESS", meta={"step": "finding_broll", "progress": 0.3})
    broll_suggestions = match_broll_to_segments(segments)

    music_path = None
    if music_preset:
        self.update_state(state="PROGRESS", meta={"step": "generating_music", "progress": 0.4})
        try:
            music_path = generate_music_loop(music_preset)
        except Exception:
            pass

    self.update_state(state="PROGRESS", meta={"step": "assembling", "progress": 0.5})
    result = auto_assemble(
        project_id=project_id,
        video_path=video_path,
        segments=segments,
        broll_suggestions=broll_suggestions,
        music_path=music_path,
        music_volume=music_volume,
        max_broll_clips=max_broll_clips,
    )

    sfx_count = 0
    if add_sfx:
        self.update_state(state="PROGRESS", meta={"step": "adding_sfx", "progress": 0.8})
        import shutil
        sfx_result = add_sfx_to_video(
            project_id=project_id,
            video_path=result["output_path"],
            segments=segments,
            sfx_type=sfx_type,
        )
        sfx_count = sfx_result["sfx_count"]
        if sfx_count > 0 and sfx_result["output_path"] != result["output_path"]:
            final = str(PROCESSED_DIR / f"{project_id}_assembled.mp4")
            shutil.copy(sfx_result["output_path"], final)

    return {
        "project_id": project_id,
        "status": "complete",
        "broll_inserted": result["broll_inserted"],
        "music_added": result["music_added"],
        "sfx_count": sfx_count,
        "duration": result["duration"],
        "download_url": f"/api/v1/download-assembled/{project_id}",
    }


# ─── Eye Contact ──────────────────────────────────────────────────────────

@celery_app.task(bind=True, name="eye_contact_fix")
def eye_contact_fix(
    self,
    project_id: str,
    strength: float = 0.7,
    skip_frames: int = 0,
) -> dict:
    """Per-frame iris correction via MediaPipe."""
    from services.eye_contact import correct_eye_contact

    video_path = _find_video(project_id)
    if not video_path:
        return {"error": "Video not found", "project_id": project_id}

    self.update_state(state="PROGRESS", meta={"step": "eye_contact_correction", "progress": 0.2})

    result = correct_eye_contact(
        project_id=project_id,
        video_path=video_path,
        strength=strength,
        skip_frames=skip_frames,
    )

    return {
        "project_id": project_id,
        "status": "complete",
        "frames_processed": result.get("frames_processed", 0),
        "download_url": f"/api/v1/download-eye-contact/{project_id}",
    }


# ─── Dynamic Reframe ─────────────────────────────────────────────────────

@celery_app.task(bind=True, name="dynamic_reframe")
def dynamic_reframe(
    self,
    project_id: str,
    target_width: int = 1080,
    target_height: int = 1920,
    smoothing: float = 0.85,
) -> dict:
    """Face-tracking reframe to portrait."""
    from services.reframe import reframe_video_dynamic

    video_path = _find_video(project_id)
    if not video_path:
        return {"error": "Video not found", "project_id": project_id}

    self.update_state(state="PROGRESS", meta={"step": "face_tracking_reframe", "progress": 0.2})

    result = reframe_video_dynamic(
        project_id=project_id,
        video_path=video_path,
        target_width=target_width,
        target_height=target_height,
        smoothing=smoothing,
    )

    return {
        "project_id": project_id,
        "status": "complete",
        "frames_processed": result.get("frames_processed", 0),
        "faces_detected": result.get("faces_detected", 0),
        "download_url": f"/api/v1/download-reframed/{project_id}",
    }


# ─── Avatar Generation ───────────────────────────────────────────────────

@celery_app.task(bind=True, name="generate_avatar")
def generate_avatar(
    self,
    project_id: str,
    text: str,
    voice: str = "en-IN-NeerjaNeural",
    preset: str = "professional_male",
    background: str = "studio_dark",
    speech_rate: str = "normal",
) -> dict:
    """Generate AI avatar video with TTS and lip-sync."""
    from services.avatar import generate_avatar_video

    self.update_state(state="PROGRESS", meta={"step": "generating_avatar", "progress": 0.1})

    result = generate_avatar_video(
        project_id=project_id,
        text=text,
        voice=voice,
        preset=preset,
        background=background,
        speech_rate=speech_rate,
    )

    return {
        "project_id": project_id,
        "status": "complete",
        "duration": result.get("duration", 0),
        "download_url": f"/api/v1/download-avatar/{project_id}",
    }


# ─── Dubbing ─────────────────────────────────────────────────────────────

@celery_app.task(bind=True, name="generate_dub")
def generate_dub(
    self,
    project_id: str,
    target_language: str,
    voice_gender: str = "female",
    keep_original: bool = True,
    original_volume: float = 0.15,
) -> dict:
    """Translate + dub video into target language."""
    from services.transcription import transcribe
    from services.translator import translate_segments, generate_dubbed_audio, replace_audio_in_video

    video_path = _find_video(project_id)
    if not video_path:
        return {"error": "Video not found", "project_id": project_id}

    self.update_state(state="PROGRESS", meta={"step": "transcribing", "progress": 0.1})
    transcript = transcribe(video_path)
    segments = transcript["segments"]

    self.update_state(state="PROGRESS", meta={"step": "translating", "progress": 0.3})
    translated = translate_segments(segments, target_language)

    self.update_state(state="PROGRESS", meta={"step": "generating_tts", "progress": 0.5})
    audio_path = generate_dubbed_audio(translated, target_language, voice_gender)

    self.update_state(state="PROGRESS", meta={"step": "mixing_audio", "progress": 0.8})
    output = replace_audio_in_video(
        video_path, audio_path, project_id,
        keep_original=keep_original,
        original_volume=original_volume,
    )

    return {
        "project_id": project_id,
        "status": "complete",
        "target_language": target_language,
        "download_url": f"/api/v1/download-dubbed/{project_id}/{target_language}",
    }


# ─── SFX ──────────────────────────────────────────────────────────────────

@celery_app.task(bind=True, name="add_sfx")
def add_sfx(
    self,
    project_id: str,
    sfx_type: str = "whoosh",
    sfx_volume: float = 0.7,
    place_at: str = "transitions",
    model_size: str = "base",
) -> dict:
    """Add SFX transitions to video."""
    from services.transcription import transcribe
    from services.sfx import add_sfx_to_video

    video_path = _find_video(project_id)
    if not video_path:
        return {"error": "Video not found", "project_id": project_id}

    self.update_state(state="PROGRESS", meta={"step": "transcribing", "progress": 0.2})
    transcript = transcribe(video_path, model_size=model_size)

    self.update_state(state="PROGRESS", meta={"step": "adding_sfx", "progress": 0.6})
    result = add_sfx_to_video(
        project_id=project_id,
        video_path=video_path,
        segments=transcript["segments"],
        sfx_type=sfx_type,
        sfx_volume=sfx_volume,
        place_at=place_at,
    )

    return {
        "project_id": project_id,
        "status": "complete",
        "sfx_count": result["sfx_count"],
        "sfx_type": result["sfx_type"],
        "download_url": f"/api/v1/download-sfx/{project_id}",
    }


# ─── Full Pipeline ────────────────────────────────────────────────────────

@celery_app.task(bind=True, name="process_video_full")
def process_video_full(self, project_id: str, options: dict) -> dict:
    """Full video processing pipeline:
    1. Remove silence
    2. Transcribe
    3. Generate captions
    4. Render final video
    """
    from services.transcription import transcribe, generate_srt
    from services.silence import remove_silence, get_video_info

    video_path = _find_video(project_id)
    if not video_path:
        return {"error": "Video not found"}

    input_path = video_path
    steps_completed = []

    if options.get("remove_silence", True):
        self.update_state(state="PROGRESS", meta={"step": "silence_removal", "progress": 0.1})
        no_silence_path = str(PROCESSED_DIR / f"{project_id}_no_silence.mp4")
        remove_silence(input_path, no_silence_path)
        input_path = no_silence_path
        steps_completed.append("silence_removal")

    self.update_state(state="PROGRESS", meta={"step": "transcription", "progress": 0.4})
    model_size = options.get("model_size", "base")
    language = options.get("language")
    result = transcribe(input_path, model_size=model_size, language=language)
    steps_completed.append("transcription")

    self.update_state(state="PROGRESS", meta={"step": "srt_generation", "progress": 0.8})
    srt_content = generate_srt(result["segments"])
    srt_path = str(PROCESSED_DIR / f"{project_id}.srt")
    Path(srt_path).write_text(srt_content, encoding="utf-8")
    steps_completed.append("srt_generation")

    info = get_video_info(input_path)

    return {
        "project_id": project_id,
        "steps_completed": steps_completed,
        "transcript": result,
        "srt_path": srt_path,
        "duration": float(info["format"]["duration"]),
        "status": "complete",
    }
