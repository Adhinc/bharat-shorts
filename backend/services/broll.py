"""
B-Roll service — keyword extraction, Pexels stock footage search,
transcript-to-B-roll matching, and audio ducking helpers for Bharat Shorts.
"""

from __future__ import annotations

import os
import re
import urllib.parse
from dataclasses import dataclass
from typing import Any, Sequence

import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PEXELS_API_KEY: str = os.getenv("PEXELS_API_KEY", "YOUR_PEXELS_API_KEY_HERE")
PEXELS_VIDEO_SEARCH_URL: str = "https://api.pexels.com/videos/search"
PEXELS_PER_PAGE: int = 5

# Common stop-words to strip when extracting keywords
_STOP_WORDS: set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "must",
    "i", "me", "my", "we", "our", "you", "your", "he", "she", "it",
    "they", "them", "their", "this", "that", "these", "those",
    "and", "but", "or", "nor", "not", "so", "if", "then", "than",
    "too", "very", "just", "about", "above", "after", "again", "all",
    "also", "am", "any", "because", "before", "between", "both",
    "by", "each", "few", "for", "from", "get", "got", "here", "him",
    "his", "how", "in", "into", "its", "let", "like", "make", "many",
    "more", "most", "much", "no", "of", "off", "on", "one", "only",
    "other", "own", "per", "put", "said", "same", "see", "seem",
    "since", "some", "still", "such", "take", "tell", "to", "up",
    "us", "use", "way", "what", "when", "where", "which", "while",
    "who", "whom", "why", "with", "yet",
    # Hinglish fillers
    "hai", "hain", "ka", "ki", "ke", "ko", "mein", "se", "par",
    "toh", "bhi", "aur", "yeh", "ye", "woh", "wo", "kya", "nahi",
    "na", "ek", "jo",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BRollSuggestion:
    """A single B-roll suggestion tied to a transcript window."""
    keyword: str
    start_time: float
    end_time: float
    videos: list[dict]

    def to_dict(self) -> dict:
        return {
            "keyword": self.keyword,
            "start_time": round(self.start_time, 3),
            "end_time": round(self.end_time, 3),
            "videos": self.videos,
        }


@dataclass
class AudioDuckCommand:
    """FFmpeg filter description for ducking music under speech."""
    speech_start: float
    speech_end: float
    duck_db: float  # how many dB to lower the music
    fade_ms: float  # fade duration in milliseconds

    def to_dict(self) -> dict:
        return {
            "speech_start": round(self.speech_start, 3),
            "speech_end": round(self.speech_end, 3),
            "duck_db": self.duck_db,
            "fade_ms": self.fade_ms,
        }


# ---------------------------------------------------------------------------
# Keyword extraction
# ---------------------------------------------------------------------------

def extract_keywords(text: str, max_keywords: int = 5) -> list[str]:
    """
    Extract meaningful keywords from transcript text.

    Uses a lightweight approach: tokenise, remove stop-words & short tokens,
    then rank by simple frequency.  No NLP model required.

    Args:
        text: Raw transcript text (can be multi-sentence).
        max_keywords: Maximum number of keywords to return.

    Returns:
        List of keywords sorted by descending frequency.
    """
    # Tokenise: keep only alpha words (ASCII + Devanagari range)
    tokens = re.findall(r"[a-zA-Z\u0900-\u097F]{3,}", text.lower())
    # Remove stop-words
    filtered = [t for t in tokens if t not in _STOP_WORDS]

    # Frequency count
    freq: dict[str, int] = {}
    for t in filtered:
        freq[t] = freq.get(t, 0) + 1

    # Sort by frequency descending, then alphabetical for stability
    ranked = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
    return [word for word, _ in ranked[:max_keywords]]


# ---------------------------------------------------------------------------
# Pexels API integration
# ---------------------------------------------------------------------------

def search_pexels_videos(
    query: str,
    *,
    per_page: int = PEXELS_PER_PAGE,
    orientation: str = "portrait",
    api_key: str | None = None,
) -> list[dict]:
    """
    Search the Pexels Video API for stock footage matching *query*.

    Args:
        query: Search term (e.g. ``"city skyline"``).
        per_page: Number of results to fetch (max 80).
        orientation: ``"portrait"`` | ``"landscape"`` | ``"square"``.
        api_key: Override the default / env-var API key.

    Returns:
        List of dicts, each containing ``id``, ``url``, ``image``
        (thumbnail), ``duration``, and ``video_files`` (list of
        rendition dicts with ``link``, ``width``, ``height``,
        ``quality``).
    """
    key = api_key or PEXELS_API_KEY
    headers = {"Authorization": key}
    params: dict[str, Any] = {
        "query": query,
        "per_page": min(per_page, 80),
        "orientation": orientation,
    }

    try:
        resp = httpx.get(
            PEXELS_VIDEO_SEARCH_URL,
            headers=headers,
            params=params,
            timeout=15.0,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        # Gracefully degrade — return empty list instead of crashing pipeline
        return [{"error": str(exc)}]

    data = resp.json()
    results: list[dict] = []
    for video in data.get("videos", []):
        video_files = []
        for vf in video.get("video_files", []):
            video_files.append({
                "link": vf.get("link"),
                "width": vf.get("width"),
                "height": vf.get("height"),
                "quality": vf.get("quality"),
            })
        results.append({
            "id": video.get("id"),
            "url": video.get("url"),
            "image": video.get("image"),  # thumbnail
            "duration": video.get("duration"),
            "video_files": video_files,
        })

    return results


# ---------------------------------------------------------------------------
# Transcript → B-roll matching
# ---------------------------------------------------------------------------

def match_broll_to_segments(
    segments: list[dict],
    *,
    keywords_per_segment: int = 2,
    search_per_keyword: int = 3,
    orientation: str = "portrait",
    api_key: str | None = None,
) -> list[dict]:
    """
    For each transcript segment, extract keywords and find matching
    Pexels stock footage.

    Args:
        segments: List of segment dicts (``text``, ``start``, ``end``).
        keywords_per_segment: How many keywords to extract per segment.
        search_per_keyword: How many Pexels results per keyword.
        orientation: Video orientation for Pexels search.
        api_key: Optional Pexels API key override.

    Returns:
        List of :class:`BRollSuggestion` dicts.
    """
    suggestions: list[dict] = []
    seen_keywords: set[str] = set()

    for seg in segments:
        text: str = seg.get("text", "")
        start: float = seg.get("start", 0.0)
        end: float = seg.get("end", 0.0)

        keywords = extract_keywords(text, max_keywords=keywords_per_segment)

        for kw in keywords:
            if kw in seen_keywords:
                continue
            seen_keywords.add(kw)

            videos = search_pexels_videos(
                kw,
                per_page=search_per_keyword,
                orientation=orientation,
                api_key=api_key,
            )

            suggestion = BRollSuggestion(
                keyword=kw,
                start_time=start,
                end_time=end,
                videos=videos,
            )
            suggestions.append(suggestion.to_dict())

    return suggestions


# ---------------------------------------------------------------------------
# Audio ducking helpers
# ---------------------------------------------------------------------------

def compute_duck_regions(
    segments: list[dict],
    *,
    duck_db: float = -14.0,
    fade_ms: float = 200.0,
    padding_ms: float = 100.0,
) -> list[dict]:
    """
    Given transcript segments (speech regions), compute the time ranges
    where background music should be ducked.

    Args:
        segments: Transcript segments with ``start`` / ``end`` times.
        duck_db: Decibel reduction during speech (negative value).
        fade_ms: Fade in/out duration in milliseconds.
        padding_ms: Extra padding before and after each speech region.

    Returns:
        List of :class:`AudioDuckCommand` dicts.
    """
    pad_sec = padding_ms / 1000.0
    regions: list[dict] = []

    for seg in segments:
        start = max(0.0, seg.get("start", 0.0) - pad_sec)
        end = seg.get("end", 0.0) + pad_sec
        cmd = AudioDuckCommand(
            speech_start=start,
            speech_end=end,
            duck_db=duck_db,
            fade_ms=fade_ms,
        )
        regions.append(cmd.to_dict())

    # Merge overlapping regions
    if not regions:
        return []

    regions.sort(key=lambda r: r["speech_start"])
    merged: list[dict] = [regions[0]]
    for region in regions[1:]:
        prev = merged[-1]
        if region["speech_start"] <= prev["speech_end"]:
            prev["speech_end"] = max(prev["speech_end"], region["speech_end"])
        else:
            merged.append(region)

    return merged


def generate_duck_ffmpeg_filter(
    regions: list[dict],
    *,
    music_volume: float = 1.0,
    duck_db: float = -14.0,
    fade_ms: float = 200.0,
) -> str:
    """
    Generate an FFmpeg ``-filter_complex`` string that ducks the music
    track during speech regions.

    Expects a two-input setup:
      - ``[0:a]`` = speech / main audio
      - ``[1:a]`` = background music

    The output pads are ``[speech]`` and ``[ducked_music]``.  You can
    then ``amix`` them together.

    Args:
        regions: List of duck-region dicts from :func:`compute_duck_regions`.
        music_volume: Base music volume (0.0 – 1.0) before ducking.
        duck_db: dB reduction during speech regions.
        fade_ms: Fade duration in ms.

    Returns:
        FFmpeg filter_complex string ready for ``-filter_complex``.

    Example usage::

        ffmpeg -i main.mp4 -i music.mp3 \\
            -filter_complex "<output of this function>" \\
            -map "[speech]" -map "[ducked_music]" out.mp4
    """
    if not regions:
        # No speech regions — just pass music through at base volume
        return (
            f"[0:a]acopy[speech];"
            f"[1:a]volume={music_volume}[ducked_music]"
        )

    fade_sec = fade_ms / 1000.0

    # Build a volume expression that lowers music during speech
    # Use the 'volume' filter with an enable expression per region
    # We chain multiple volume filters, one per duck region
    parts: list[str] = []
    input_label = "[1:a]"

    # Set base volume first
    base_label = "[music_base]"
    parts.append(f"{input_label}volume={music_volume}{base_label}")

    prev_label = base_label
    for i, region in enumerate(regions):
        start = region["speech_start"]
        end = region["speech_end"]
        out_label = f"[duck_{i}]"

        # Use enable expression to activate only during this region
        # Volume in dB: 10^(duck_db/20) gives the linear multiplier
        duck_linear = round(10 ** (duck_db / 20), 4)

        parts.append(
            f"{prev_label}volume=volume={duck_linear}:enable='between(t,{start:.3f},{end:.3f})'{out_label}"
        )
        prev_label = out_label

    # Rename final label
    final_music_label = prev_label
    # Copy speech through
    parts.append(f"[0:a]acopy[speech]")

    # Build full filter, renaming the last duck label to [ducked_music]
    filter_str = ";\n".join(parts)
    # Replace last output label with [ducked_music]
    filter_str = filter_str.rsplit(prev_label, 1)
    filter_str = f"{prev_label}".join(filter_str[:-1]) + "[ducked_music]" + filter_str[-1] if len(filter_str) > 1 else parts[-1]

    # Simpler, cleaner rebuild:
    lines: list[str] = []
    lines.append(f"[1:a]volume={music_volume}[music_base]")

    prev = "music_base"
    for i, region in enumerate(regions):
        start = region["speech_start"]
        end = region["speech_end"]
        duck_linear = round(10 ** (duck_db / 20), 4)
        out = f"duck_{i}" if i < len(regions) - 1 else "ducked_music"
        lines.append(
            f"[{prev}]volume=volume={duck_linear}:"
            f"enable='between(t,{start:.3f},{end:.3f})'[{out}]"
        )
        prev = out

    lines.append("[0:a]acopy[speech]")
    return ";\n".join(lines)


def generate_full_mix_command(
    input_video: str,
    music_file: str,
    output_file: str,
    regions: list[dict],
    *,
    music_volume: float = 0.3,
    duck_db: float = -14.0,
    fade_ms: float = 200.0,
) -> list[str]:
    """
    Build a complete FFmpeg command list that mixes speech + ducked music.

    Args:
        input_video: Path to the main video file.
        music_file: Path to the background music file.
        output_file: Desired output path.
        regions: Duck regions from :func:`compute_duck_regions`.
        music_volume: Base volume of background music.
        duck_db: Ducking level in dB.
        fade_ms: Fade time in ms.

    Returns:
        List of strings suitable for ``subprocess.run()``.
    """
    filter_complex = generate_duck_ffmpeg_filter(
        regions,
        music_volume=music_volume,
        duck_db=duck_db,
        fade_ms=fade_ms,
    )

    # Combine ducked music + speech via amix
    full_filter = (
        f"{filter_complex};\n"
        f"[speech][ducked_music]amix=inputs=2:duration=first:dropout_transition=2[final_audio]"
    )

    return [
        "ffmpeg", "-y",
        "-i", input_video,
        "-i", music_file,
        "-filter_complex", full_filter,
        "-map", "0:v",
        "-map", "[final_audio]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        output_file,
    ]
