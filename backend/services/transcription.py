import uuid
import subprocess
from pathlib import Path
from faster_whisper import WhisperModel

# Singleton model instance
_model: WhisperModel | None = None
_model_size: str | None = None


def get_model(model_size: str = "base") -> WhisperModel:
    """Lazy-load Whisper model. Reloads if model_size changes."""
    global _model, _model_size
    if _model is None or _model_size != model_size:
        _model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",
        )
        _model_size = model_size
    return _model


def extract_audio(video_path: str, audio_path: str) -> str:
    """Extract audio from video using FFmpeg."""
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1",
        audio_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Audio extraction failed: {result.stderr}")
    return audio_path


def transcribe(video_path: str, model_size: str = "base", language: str | None = None) -> dict:
    """
    Transcribe video with word-level timestamps.

    Returns:
        {
            "segments": [...],
            "language": "hi",
            "language_probability": 0.95
        }
    """
    # Extract audio to temp WAV
    audio_dir = Path(__file__).resolve().parent.parent / "processed"
    audio_dir.mkdir(exist_ok=True)
    audio_path = str(audio_dir / f"{uuid.uuid4()}.wav")

    try:
        extract_audio(video_path, audio_path)

        model = get_model(model_size)

        # Transcribe with word timestamps for caption sync
        segments_gen, info = model.transcribe(
            audio_path,
            language=language,  # None = auto-detect (handles Hinglish)
            word_timestamps=True,
            vad_filter=True,  # Voice Activity Detection to skip silence
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=200,
            ),
        )

        segments = []
        for segment in segments_gen:
            words = []
            if segment.words:
                for word in segment.words:
                    words.append({
                        "text": word.word.strip(),
                        "start": round(word.start, 3),
                        "end": round(word.end, 3),
                        "confidence": round(word.probability, 3),
                    })

            segments.append({
                "id": str(uuid.uuid4()),
                "words": words,
                "text": segment.text.strip(),
                "start": round(segment.start, 3),
                "end": round(segment.end, 3),
                "speaker": None,
            })

        return {
            "segments": segments,
            "language": info.language,
            "language_probability": round(info.language_probability, 3),
        }

    finally:
        # Clean up temp audio file
        Path(audio_path).unlink(missing_ok=True)


def generate_srt(segments: list[dict]) -> str:
    """Convert transcript segments to SRT format."""
    lines = []
    for i, seg in enumerate(segments, 1):
        start = _format_srt_time(seg["start"])
        end = _format_srt_time(seg["end"])
        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        lines.append(seg["text"])
        lines.append("")
    return "\n".join(lines)


def _format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
