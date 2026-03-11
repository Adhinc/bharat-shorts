"""Celery tasks for async video processing."""

import uuid
from pathlib import Path
from workers.celery_app import celery_app


@celery_app.task(bind=True, name="process_video_full")
def process_video_full(self, project_id: str, options: dict) -> dict:
    """Full video processing pipeline:
    1. Remove silence
    2. Transcribe
    3. Generate captions
    4. Render final video

    Used for enterprise bulk processing.
    """
    from services.transcription import transcribe, generate_srt
    from services.silence import remove_silence, get_video_info

    upload_dir = Path("uploads")
    processed_dir = Path("processed")
    processed_dir.mkdir(exist_ok=True)

    matches = list(upload_dir.glob(f"{project_id}.*"))
    if not matches:
        return {"error": "Video not found"}

    input_path = str(matches[0])
    steps_completed = []

    # Step 1: Remove silence (optional)
    if options.get("remove_silence", True):
        self.update_state(state="PROGRESS", meta={"step": "silence_removal"})
        no_silence_path = str(processed_dir / f"{project_id}_no_silence.mp4")
        remove_silence(input_path, no_silence_path)
        input_path = no_silence_path
        steps_completed.append("silence_removal")

    # Step 2: Transcribe
    self.update_state(state="PROGRESS", meta={"step": "transcription"})
    model_size = options.get("model_size", "base")
    language = options.get("language")
    result = transcribe(input_path, model_size=model_size, language=language)
    steps_completed.append("transcription")

    # Step 3: Generate SRT
    srt_content = generate_srt(result["segments"])
    srt_path = str(processed_dir / f"{project_id}.srt")
    Path(srt_path).write_text(srt_content, encoding="utf-8")
    steps_completed.append("srt_generation")

    # Step 4: Get video info
    info = get_video_info(input_path)

    return {
        "project_id": project_id,
        "steps_completed": steps_completed,
        "transcript": result,
        "srt_path": srt_path,
        "duration": float(info["format"]["duration"]),
        "status": "complete",
    }
