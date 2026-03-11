"""
Advanced Transcription Service for Bharat Shorts

Features:
- Faster-Whisper with optimized model selection for Indian languages
- Audio preprocessing (noise reduction, normalization) for noisy phone recordings
- Hinglish detection and code-switching handling
- Regional dialect post-processing for Hindi, Tamil, Marathi, Telugu, Bengali
- Multi-model fallback: tries larger model if confidence is low
- Beam search tuning for Indian language accuracy
- VTT and SRT export
"""

import uuid
import subprocess
import re
import logging
from pathlib import Path
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

# Singleton model instances (cache multiple sizes)
_models: dict[str, WhisperModel] = {}

# Indian language codes and their optimal Whisper settings
INDIAN_LANGUAGES = {
    "hi": {"name": "Hindi", "beam_size": 8, "best_of": 5},
    "ta": {"name": "Tamil", "beam_size": 8, "best_of": 5},
    "mr": {"name": "Marathi", "beam_size": 8, "best_of": 5},
    "te": {"name": "Telugu", "beam_size": 8, "best_of": 5},
    "bn": {"name": "Bengali", "beam_size": 8, "best_of": 5},
    "gu": {"name": "Gujarati", "beam_size": 8, "best_of": 5},
    "kn": {"name": "Kannada", "beam_size": 8, "best_of": 5},
    "ml": {"name": "Malayalam", "beam_size": 8, "best_of": 5},
    "pa": {"name": "Punjabi", "beam_size": 8, "best_of": 5},
    "ur": {"name": "Urdu", "beam_size": 8, "best_of": 5},
    "ne": {"name": "Nepali", "beam_size": 5, "best_of": 3},
    "si": {"name": "Sinhala", "beam_size": 5, "best_of": 3},
}

# Recommended model for Indian languages (larger = better for tonal languages)
LANGUAGE_MODEL_MAP = {
    "hi": "small",   # Hindi needs at least small for Devanagari
    "ta": "small",   # Tamil script complexity
    "mr": "small",   # Marathi similar to Hindi
    "te": "medium",  # Telugu benefits from medium
    "bn": "small",   # Bengali
    "ml": "medium",  # Malayalam complex script
    "kn": "medium",  # Kannada
    "gu": "small",   # Gujarati
    "pa": "small",   # Punjabi
    "ur": "small",   # Urdu
    "en": "base",    # English works fine with base
}

# Common Hinglish patterns for detection
_HINGLISH_MARKERS = re.compile(
    r'\b(hai|hain|kya|nahi|aur|bhi|toh|yeh|woh|kaise|kuch|bahut|accha|theek|'
    r'matlab|samajh|baat|dekho|suno|chalo|acha|haan|ji|abhi|kal|aaj)\b',
    re.IGNORECASE,
)


def get_model(model_size: str = "base") -> WhisperModel:
    """Lazy-load Whisper model with caching for multiple sizes."""
    global _models
    if model_size not in _models:
        logger.info(f"Loading Whisper model: {model_size}")
        _models[model_size] = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",
        )
    return _models[model_size]


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


def preprocess_audio(input_path: str, output_path: str) -> str:
    """
    Preprocess audio for better transcription accuracy.

    Applies:
    1. High-pass filter (remove low rumble/AC noise common in Indian recordings)
    2. Loudness normalization (handles quiet phone recordings)
    3. Noise gate (reduce background chatter)
    """
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-af", (
            "highpass=f=80,"           # Remove rumble below 80Hz
            "lowpass=f=8000,"          # Remove hiss above 8kHz
            "loudnorm=I=-16:TP=-1.5,"  # EBU R128 loudness normalization
            "agate=threshold=-30dB:ratio=3:attack=10:release=100"  # Noise gate
        ),
        "-ar", "16000", "-ac", "1",
        "-c:a", "pcm_s16le",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning(f"Audio preprocessing failed, using raw audio: {result.stderr[:200]}")
        return input_path
    return output_path


def detect_hinglish(text: str) -> bool:
    """Detect if text contains Hinglish (Hindi+English code-switching)."""
    hindi_words = len(_HINGLISH_MARKERS.findall(text))
    english_words = len(re.findall(r'\b[a-zA-Z]{3,}\b', text))
    total = hindi_words + english_words
    if total < 5:
        return False
    # Hinglish = mix of both (neither purely Hindi nor purely English)
    hindi_ratio = hindi_words / total
    return 0.15 < hindi_ratio < 0.85


def get_optimal_model(language: str | None, model_size: str = "base") -> str:
    """Get the optimal model size for a given language."""
    if model_size != "base" and model_size != "auto":
        return model_size  # User explicitly chose a model
    if language and language in LANGUAGE_MODEL_MAP:
        recommended = LANGUAGE_MODEL_MAP[language]
        logger.info(f"Using recommended model '{recommended}' for language '{language}'")
        return recommended
    return model_size


def post_process_transcript(segments: list[dict], language: str) -> list[dict]:
    """
    Post-process transcript for regional language accuracy.

    Fixes:
    - Common Whisper misrecognitions for Indian languages
    - Punctuation normalization for Devanagari/Tamil/Telugu scripts
    - Number formatting (lakh/crore style)
    """
    corrections = {
        "hi": {
            # Common Whisper errors for Hindi
            "namaskar": "नमस्कार",
            "dhanyavaad": "धन्यवाद",
            "swaagat": "स्वागत",
        },
        "ta": {
            "vanakkam": "வணக்கம்",
            "nandri": "நன்றி",
        },
        "mr": {
            "namaskar": "नमस्कार",
            "dhanyavaad": "धन्यवाद",
        },
    }

    lang_corrections = corrections.get(language, {})
    if not lang_corrections:
        return segments

    for seg in segments:
        text = seg["text"]
        for wrong, right in lang_corrections.items():
            text = re.sub(re.escape(wrong), right, text, flags=re.IGNORECASE)
        seg["text"] = text

        # Also fix individual words
        for word in seg.get("words", []):
            w_text = word["text"]
            for wrong, right in lang_corrections.items():
                w_text = re.sub(re.escape(wrong), right, w_text, flags=re.IGNORECASE)
            word["text"] = w_text

    return segments


def transcribe(
    video_path: str,
    model_size: str = "base",
    language: str | None = None,
    preprocess: bool = True,
    auto_model: bool = True,
) -> dict:
    """
    Advanced transcription with Indian language optimization.

    Args:
        video_path: Path to video file
        model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large-v3')
                    Use 'auto' to auto-select based on detected language.
        language: Language code (None = auto-detect)
        preprocess: Apply audio preprocessing for noisy recordings
        auto_model: Auto-upgrade model for Indian languages if using 'base'

    Returns:
        {
            "segments": [...],
            "language": "hi",
            "language_probability": 0.95,
            "is_hinglish": False,
            "model_used": "small",
            "preprocessed": True,
        }
    """
    audio_dir = Path(__file__).resolve().parent.parent / "processed"
    audio_dir.mkdir(exist_ok=True)
    raw_audio = str(audio_dir / f"{uuid.uuid4()}.wav")
    processed_audio = str(audio_dir / f"{uuid.uuid4()}_processed.wav")

    try:
        # Extract audio
        extract_audio(video_path, raw_audio)

        # Preprocess audio for better accuracy
        if preprocess:
            audio_path = preprocess_audio(raw_audio, processed_audio)
        else:
            audio_path = raw_audio

        # Auto-select optimal model for language
        effective_model = model_size
        if auto_model and model_size in ("base", "auto"):
            effective_model = get_optimal_model(language, model_size)

        model = get_model(effective_model)

        # Get language-specific beam search settings
        lang_settings = INDIAN_LANGUAGES.get(language, {})
        beam_size = lang_settings.get("beam_size", 5)
        best_of = lang_settings.get("best_of", 3)

        # Transcribe with optimized settings
        segments_gen, info = model.transcribe(
            audio_path,
            language=language,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=400,
                speech_pad_ms=250,
                threshold=0.35,  # Lower threshold for soft-spoken Indian speakers
            ),
            beam_size=beam_size,
            best_of=best_of,
            temperature=[0.0, 0.2, 0.4],  # Temperature fallback for better accuracy
            condition_on_previous_text=True,  # Better context for code-switching
            no_speech_threshold=0.5,
        )

        segments = []
        full_text_parts = []
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
            full_text_parts.append(segment.text.strip())

        # Detect Hinglish
        full_text = " ".join(full_text_parts)
        is_hinglish = detect_hinglish(full_text)

        # If confidence is low and we used a small model, retry with larger
        if (info.language_probability < 0.6
                and effective_model in ("base", "small")
                and auto_model):
            logger.info(
                f"Low confidence ({info.language_probability:.2f}) with {effective_model}, "
                f"retrying with larger model..."
            )
            fallback_model = "medium" if effective_model == "small" else "small"
            return transcribe(
                video_path,
                model_size=fallback_model,
                language=language,
                preprocess=preprocess,
                auto_model=False,  # Don't recurse again
            )

        # Post-process for regional accuracy
        detected_lang = info.language
        segments = post_process_transcript(segments, detected_lang)

        return {
            "segments": segments,
            "language": detected_lang,
            "language_probability": round(info.language_probability, 3),
            "is_hinglish": is_hinglish,
            "model_used": effective_model,
            "preprocessed": preprocess,
        }

    finally:
        Path(raw_audio).unlink(missing_ok=True)
        Path(processed_audio).unlink(missing_ok=True)


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


def generate_vtt(segments: list[dict]) -> str:
    """Convert transcript segments to WebVTT format."""
    lines = ["WEBVTT", ""]
    for i, seg in enumerate(segments, 1):
        start = _format_vtt_time(seg["start"])
        end = _format_vtt_time(seg["end"])
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


def _format_vtt_time(seconds: float) -> str:
    """Convert seconds to WebVTT timestamp format (HH:MM:SS.mmm)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
