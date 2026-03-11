"""
AI Video Translator & Dubbing Service

Provides:
1. Text translation across 48+ languages (Google Translate via deep-translator)
2. AI voice dubbing with natural-sounding Indian language voices (Edge TTS)
3. FFmpeg audio replacement to merge dubbed audio back into video
"""

import asyncio
import subprocess
import uuid
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Supported Indian languages with Edge TTS voice mappings
VOICE_MAP = {
    # Indian languages
    "hi": {"name": "Hindi", "female": "hi-IN-SwaraNeural", "male": "hi-IN-MadhurNeural"},
    "ta": {"name": "Tamil", "female": "ta-IN-PallaviNeural", "male": "ta-IN-ValluvarNeural"},
    "mr": {"name": "Marathi", "female": "mr-IN-AarohiNeural", "male": "mr-IN-ManoharNeural"},
    "te": {"name": "Telugu", "female": "te-IN-ShrutiNeural", "male": "te-IN-MohanNeural"},
    "bn": {"name": "Bengali", "female": "bn-IN-TanishaaNeural", "male": "bn-IN-BashkarNeural"},
    "kn": {"name": "Kannada", "female": "kn-IN-SapnaNeural", "male": "kn-IN-GaganNeural"},
    "ml": {"name": "Malayalam", "female": "ml-IN-SobhanaNeural", "male": "ml-IN-MidhunNeural"},
    "gu": {"name": "Gujarati", "female": "gu-IN-DhwaniNeural", "male": "gu-IN-NiranjanNeural"},
    "pa": {"name": "Punjabi", "female": "pa-IN-GurpreetNeural", "male": "pa-IN-GurpreetNeural"},
    "ur": {"name": "Urdu", "female": "ur-PK-UzmaNeural", "male": "ur-PK-AsadNeural"},
    # Global languages
    "en": {"name": "English", "female": "en-IN-NeerjaNeural", "male": "en-IN-PrabhatNeural"},
    "ar": {"name": "Arabic", "female": "ar-SA-ZariyahNeural", "male": "ar-SA-HamedNeural"},
    "es": {"name": "Spanish", "female": "es-ES-ElviraNeural", "male": "es-ES-AlvaroNeural"},
    "fr": {"name": "French", "female": "fr-FR-DeniseNeural", "male": "fr-FR-HenriNeural"},
    "de": {"name": "German", "female": "de-DE-KatjaNeural", "male": "de-DE-ConradNeural"},
    "pt": {"name": "Portuguese", "female": "pt-BR-FranciscaNeural", "male": "pt-BR-AntonioNeural"},
    "ja": {"name": "Japanese", "female": "ja-JP-NanamiNeural", "male": "ja-JP-KeitaNeural"},
    "ko": {"name": "Korean", "female": "ko-KR-SunHiNeural", "male": "ko-KR-InJoonNeural"},
    "zh": {"name": "Chinese", "female": "zh-CN-XiaoxiaoNeural", "male": "zh-CN-YunxiNeural"},
    "id": {"name": "Indonesian", "female": "id-ID-GadisNeural", "male": "id-ID-ArdiNeural"},
    "th": {"name": "Thai", "female": "th-TH-PremwadeeNeural", "male": "th-TH-NiwatNeural"},
    "vi": {"name": "Vietnamese", "female": "vi-VN-HoaiMyNeural", "male": "vi-VN-NamMinhNeural"},
    "ru": {"name": "Russian", "female": "ru-RU-SvetlanaNeural", "male": "ru-RU-DmitryNeural"},
    "tr": {"name": "Turkish", "female": "tr-TR-EmelNeural", "male": "tr-TR-AhmetNeural"},
}

# Language code mapping for deep-translator (Google Translate codes)
TRANSLATE_LANG_MAP = {
    "hi": "hindi",
    "ta": "tamil",
    "mr": "marathi",
    "te": "telugu",
    "bn": "bengali",
    "kn": "kannada",
    "ml": "malayalam",
    "gu": "gujarati",
    "pa": "punjabi",
    "ur": "urdu",
    "en": "english",
    "ar": "arabic",
    "es": "spanish",
    "fr": "french",
    "de": "german",
    "pt": "portuguese",
    "ja": "japanese",
    "ko": "korean",
    "zh-CN": "chinese (simplified)",
    "zh": "chinese (simplified)",
    "id": "indonesian",
    "th": "thai",
    "vi": "vietnamese",
    "ru": "russian",
    "tr": "turkish",
}


def get_supported_languages() -> list[dict]:
    """Return list of supported languages with codes and names."""
    return [
        {"code": code, "name": info["name"]}
        for code, info in VOICE_MAP.items()
    ]


def translate_text(text: str, target_lang: str, source_lang: str = "auto") -> str:
    """Translate a single text string to the target language."""
    from deep_translator import GoogleTranslator

    target = TRANSLATE_LANG_MAP.get(target_lang, target_lang)
    src = "auto" if source_lang == "auto" else TRANSLATE_LANG_MAP.get(source_lang, source_lang)

    translator = GoogleTranslator(source=src, target=target)
    return translator.translate(text)


def translate_segments(
    segments: list[dict],
    target_lang: str,
    source_lang: str = "auto",
) -> list[dict]:
    """
    Translate all transcript segments to the target language.
    Preserves timing information, only changes text.
    """
    from deep_translator import GoogleTranslator

    target = TRANSLATE_LANG_MAP.get(target_lang, target_lang)
    src = "auto" if source_lang == "auto" else TRANSLATE_LANG_MAP.get(source_lang, source_lang)

    translator = GoogleTranslator(source=src, target=target)

    translated_segments = []
    for seg in segments:
        translated_text = translator.translate(seg["text"])

        # Translate individual words and preserve timing
        translated_words = []
        if seg.get("words"):
            # Batch translate words for efficiency
            word_texts = [w["text"] for w in seg["words"]]
            joined = " | ".join(word_texts)
            translated_joined = translator.translate(joined)
            translated_word_texts = [t.strip() for t in translated_joined.split("|")]

            # Map back to original timing (best effort — word count may differ)
            original_words = seg["words"]
            if len(translated_word_texts) == len(original_words):
                for i, w in enumerate(original_words):
                    translated_words.append({
                        "text": translated_word_texts[i],
                        "start": w["start"],
                        "end": w["end"],
                        "confidence": w["confidence"],
                    })
            else:
                # Word count mismatch: distribute timing evenly
                total_start = seg["start"]
                total_end = seg["end"]
                # Split translated text into words
                t_words = translated_text.split()
                if not t_words:
                    t_words = [translated_text]
                duration_per_word = (total_end - total_start) / len(t_words)
                for i, tw in enumerate(t_words):
                    translated_words.append({
                        "text": tw,
                        "start": round(total_start + i * duration_per_word, 3),
                        "end": round(total_start + (i + 1) * duration_per_word, 3),
                        "confidence": 0.9,
                    })
        else:
            # No word-level data, create from translated text
            t_words = translated_text.split()
            if t_words:
                duration_per_word = (seg["end"] - seg["start"]) / len(t_words)
                for i, tw in enumerate(t_words):
                    translated_words.append({
                        "text": tw,
                        "start": round(seg["start"] + i * duration_per_word, 3),
                        "end": round(seg["start"] + (i + 1) * duration_per_word, 3),
                        "confidence": 0.9,
                    })

        translated_segments.append({
            "id": seg["id"],
            "words": translated_words,
            "text": translated_text,
            "start": seg["start"],
            "end": seg["end"],
            "speaker": seg.get("speaker"),
        })

    return translated_segments


async def generate_tts_audio(
    text: str,
    output_path: str,
    lang: str = "hi",
    gender: str = "female",
    rate: str = "+0%",
) -> str:
    """Generate TTS audio for a single text using Edge TTS."""
    import edge_tts

    voice_info = VOICE_MAP.get(lang)
    if not voice_info:
        raise ValueError(f"Unsupported language: {lang}. Supported: {list(VOICE_MAP.keys())}")

    voice = voice_info.get(gender, voice_info["female"])

    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)
    return output_path


async def generate_dubbed_audio(
    segments: list[dict],
    output_dir: str,
    lang: str = "hi",
    gender: str = "female",
    rate: str = "+0%",
) -> str:
    """
    Generate a complete dubbed audio track from translated segments.
    Creates individual TTS clips per segment, then concatenates with
    silence padding to match original timing.
    """
    import edge_tts

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    voice_info = VOICE_MAP.get(lang)
    if not voice_info:
        raise ValueError(f"Unsupported language: {lang}")

    voice = voice_info.get(gender, voice_info["female"])

    # Generate TTS for each segment
    segment_files = []
    for i, seg in enumerate(segments):
        seg_path = str(output_dir / f"seg_{i:04d}.mp3")
        try:
            communicate = edge_tts.Communicate(seg["text"], voice, rate=rate)
            await communicate.save(seg_path)
            segment_files.append({
                "path": seg_path,
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
            })
        except Exception as e:
            logger.warning(f"TTS failed for segment {i}: {e}")
            continue

    if not segment_files:
        raise RuntimeError("No TTS segments were generated")

    # Find total duration needed (last segment end time)
    total_duration = max(s["end"] for s in segment_files)

    # Build FFmpeg filter to place each segment at correct timestamp
    # Using adelay to position each clip at the right time
    final_output = str(output_dir / "dubbed_audio.mp3")

    # Create a silent base track
    silent_path = str(output_dir / "silence.wav")
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"anullsrc=r=44100:cl=mono",
        "-t", str(total_duration + 1),
        "-c:a", "pcm_s16le",
        silent_path,
    ], capture_output=True)

    # Build FFmpeg command to overlay each segment at correct time
    inputs = ["-i", silent_path]
    filter_parts = []

    for i, sf in enumerate(segment_files):
        inputs.extend(["-i", sf["path"]])
        delay_ms = int(sf["start"] * 1000)
        filter_parts.append(f"[{i + 1}:a]adelay={delay_ms}|{delay_ms}[d{i}]")

    # Mix all delayed segments with the silent base
    if filter_parts:
        mix_inputs = "[0:a]" + "".join(f"[d{i}]" for i in range(len(segment_files)))
        filter_parts.append(
            f"{mix_inputs}amix=inputs={len(segment_files) + 1}:normalize=0[out]"
        )

        filter_complex = ";".join(filter_parts)
        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-c:a", "libmp3lame", "-q:a", "2",
            final_output,
        ]
    else:
        # Fallback: just use silence
        cmd = ["cp", silent_path, final_output]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"FFmpeg mix failed: {result.stderr[:500]}")
        raise RuntimeError(f"Audio mixing failed: {result.stderr[:200]}")

    # Cleanup individual segment files
    for sf in segment_files:
        Path(sf["path"]).unlink(missing_ok=True)
    Path(silent_path).unlink(missing_ok=True)

    return final_output


def replace_audio_in_video(
    video_path: str,
    audio_path: str,
    output_path: str,
    keep_original_audio: bool = False,
    original_volume: float = 0.1,
) -> str:
    """
    Replace or mix dubbed audio into the original video.

    Args:
        video_path: Path to original video
        audio_path: Path to dubbed audio
        output_path: Path to save dubbed video
        keep_original_audio: If True, mix original audio at low volume
        original_volume: Volume of original audio when mixing (0.0 to 1.0)
    """
    if keep_original_audio:
        # Mix: dubbed audio at full volume + original at low volume
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-filter_complex",
            f"[0:a]volume={original_volume}[orig];[1:a]volume=1.0[dub];[orig][dub]amix=inputs=2:normalize=0[out]",
            "-map", "0:v",
            "-map", "[out]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_path,
        ]
    else:
        # Replace original audio entirely
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-map", "0:v",
            "-map", "1:a",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_path,
        ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Audio replacement failed: {result.stderr[:200]}")

    return output_path
