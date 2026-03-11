"""
Magic Clips — heuristic-based highlight extraction for Bharat Shorts.

Scans a transcript (list of segments with text / start / end) and proposes
viral-worthy clips scored by energy, hook potential, and emotional intensity.
No external LLM required; everything runs locally with pure Python.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Sequence

# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------

MIN_CLIP_DURATION: float = 30.0   # seconds
MAX_CLIP_DURATION: float = 60.0   # seconds
SEGMENT_SCORE_THRESHOLD: float = 0.3  # min normalised score to consider

# ---------------------------------------------------------------------------
# Keyword / pattern banks
# ---------------------------------------------------------------------------

# High-energy words that signal excitement or authority
ENERGY_WORDS: set[str] = {
    "amazing", "incredible", "unbelievable", "insane", "crazy", "mind-blowing",
    "shocking", "absolutely", "literally", "seriously", "honestly", "exactly",
    "powerful", "massive", "huge", "game-changer", "breaking", "explosive",
    "secret", "hack", "trick", "ultimate", "best", "worst", "never", "always",
    "impossible", "legendary", "epic", "viral", "fastest", "biggest",
    # Hinglish / Hindi-English common intensifiers
    "bahut", "ekdum", "zabardast", "kamaal", "dhamaal", "pagal", "toofan",
    "solid", "mast", "jhakkas", "fatafat", "seedha",
}

# Emotional intensity keywords
EMOTION_KEYWORDS: dict[str, float] = {
    # Surprise / shock
    "surprise": 0.8, "shocked": 0.9, "wait": 0.6, "what": 0.5,
    "oh my god": 1.0, "omg": 0.9, "wow": 0.7, "whoa": 0.7, "damn": 0.6,
    # Urgency
    "urgent": 0.7, "hurry": 0.6, "now": 0.4, "immediately": 0.7,
    "breaking": 0.8, "alert": 0.7, "warning": 0.7,
    # Motivation / inspiration
    "believe": 0.5, "dream": 0.5, "success": 0.6, "hustle": 0.6,
    "grind": 0.5, "winner": 0.6, "champion": 0.6, "inspire": 0.7,
    # Conflict / controversy
    "wrong": 0.5, "lie": 0.7, "truth": 0.6, "exposed": 0.9,
    "scam": 0.8, "fraud": 0.8, "fight": 0.6, "debate": 0.5,
    # Humour
    "funny": 0.5, "hilarious": 0.7, "lol": 0.4, "comedy": 0.5,
}

# Regex patterns that indicate a strong "hook"
HOOK_PATTERNS: list[tuple[re.Pattern[str], float, str]] = [
    # Questions
    (re.compile(r"\?"), 0.6, "question"),
    # Exclamations
    (re.compile(r"!{1,}"), 0.5, "exclamation"),
    # Numbers / statistics  (e.g. "10x", "500%", "3 million", "$100")
    (re.compile(r"\b\d+[\.,]?\d*\s*(%|x|million|billion|crore|lakh|thousand|k\b)", re.I), 0.8, "statistic"),
    (re.compile(r"[$₹€£]\s*\d+", re.I), 0.7, "money_reference"),
    # List / ranking hooks ("number one", "#1", "top 5")
    (re.compile(r"\b(number\s*\d|#\d|top\s*\d|first|second|third)\b", re.I), 0.6, "ranking"),
    # Surprising / contrarian openers
    (re.compile(r"\b(but here'?s the thing|nobody tells you|the truth is|stop doing|you'?re wrong)\b", re.I), 0.9, "contrarian_hook"),
    # Call-to-action / engagement
    (re.compile(r"\b(subscribe|like|comment|share|follow|watch till the end)\b", re.I), 0.3, "cta"),
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TranscriptSegment:
    """A single transcript segment (mirrors the dict from transcription service)."""
    text: str
    start: float
    end: float
    id: str = ""
    words: list[dict] = field(default_factory=list)
    speaker: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> TranscriptSegment:
        return cls(
            text=d.get("text", ""),
            start=d.get("start", 0.0),
            end=d.get("end", 0.0),
            id=d.get("id", ""),
            words=d.get("words", []),
            speaker=d.get("speaker"),
        )


@dataclass
class ScoredSegment:
    """A segment with its computed virality score and contributing reasons."""
    segment: TranscriptSegment
    score: float
    reasons: list[str]


@dataclass
class ProposedClip:
    """A clip proposed by the Magic Clips engine."""
    id: str
    title: str
    start_time: float
    end_time: float
    score: float
    reason: str
    segment_count: int

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "start_time": round(self.start_time, 3),
            "end_time": round(self.end_time, 3),
            "duration": round(self.end_time - self.start_time, 3),
            "score": round(self.score, 3),
            "reason": self.reason,
            "segment_count": self.segment_count,
        }


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _score_energy(text: str) -> tuple[float, list[str]]:
    """Score segment text for high-energy words. Returns (score, reasons)."""
    words_lower = set(re.findall(r"[a-zA-Z\u0900-\u097F]+", text.lower()))
    matches = words_lower & ENERGY_WORDS
    if not matches:
        return 0.0, []
    # More matches = higher score, capped at 1.0
    score = min(len(matches) * 0.25, 1.0)
    return score, [f"energy_words:{','.join(sorted(matches))}"]


def _score_hooks(text: str) -> tuple[float, list[str]]:
    """Score segment text for hook patterns. Returns (score, reasons)."""
    total = 0.0
    reasons: list[str] = []
    for pattern, weight, label in HOOK_PATTERNS:
        if pattern.search(text):
            total += weight
            reasons.append(f"hook:{label}")
    return min(total, 1.0), reasons


def _score_emotion(text: str) -> tuple[float, list[str]]:
    """Score segment text for emotional intensity. Returns (score, reasons)."""
    text_lower = text.lower()
    total = 0.0
    reasons: list[str] = []
    for keyword, weight in EMOTION_KEYWORDS.items():
        if keyword in text_lower:
            total += weight
            reasons.append(f"emotion:{keyword}")
    return min(total, 1.0), reasons


def _score_brevity(segment: TranscriptSegment) -> tuple[float, list[str]]:
    """Bonus for punchier segments (shorter is often more viral)."""
    duration = segment.end - segment.start
    word_count = len(segment.text.split())
    # Short, punchy segments (< 10 words or < 5 s) get a bonus
    if word_count <= 8 or duration <= 4.0:
        return 0.3, ["brevity:punchy"]
    if word_count <= 15 or duration <= 8.0:
        return 0.15, ["brevity:concise"]
    return 0.0, []


def score_segment(segment: TranscriptSegment) -> ScoredSegment:
    """Compute a normalised virality score (0-1) for a single segment."""
    weights = {"energy": 0.25, "hooks": 0.30, "emotion": 0.25, "brevity": 0.20}

    energy_score, energy_reasons = _score_energy(segment.text)
    hook_score, hook_reasons = _score_hooks(segment.text)
    emotion_score, emotion_reasons = _score_emotion(segment.text)
    brevity_score, brevity_reasons = _score_brevity(segment)

    weighted = (
        energy_score * weights["energy"]
        + hook_score * weights["hooks"]
        + emotion_score * weights["emotion"]
        + brevity_score * weights["brevity"]
    )

    all_reasons = energy_reasons + hook_reasons + emotion_reasons + brevity_reasons
    return ScoredSegment(segment=segment, score=min(weighted, 1.0), reasons=all_reasons)


# ---------------------------------------------------------------------------
# Clip grouping
# ---------------------------------------------------------------------------

def _group_into_clips(
    scored: list[ScoredSegment],
    min_duration: float = MIN_CLIP_DURATION,
    max_duration: float = MAX_CLIP_DURATION,
    gap_tolerance: float = 2.0,
) -> list[list[ScoredSegment]]:
    """
    Group consecutive high-scoring segments into clip candidates.

    Segments are merged if they are within *gap_tolerance* seconds of each
    other. Groups shorter than *min_duration* get expanded by pulling in
    neighbouring segments; groups longer than *max_duration* get split.
    """
    if not scored:
        return []

    # Sort by start time
    scored_sorted = sorted(scored, key=lambda s: s.segment.start)

    groups: list[list[ScoredSegment]] = []
    current_group: list[ScoredSegment] = [scored_sorted[0]]

    for ss in scored_sorted[1:]:
        prev_end = current_group[-1].segment.end
        curr_start = ss.segment.start

        if curr_start - prev_end <= gap_tolerance:
            current_group.append(ss)
        else:
            groups.append(current_group)
            current_group = [ss]

    groups.append(current_group)

    # Split groups that exceed max_duration
    final_groups: list[list[ScoredSegment]] = []
    for group in groups:
        start = group[0].segment.start
        current_sub: list[ScoredSegment] = []
        for ss in group:
            if ss.segment.end - start > max_duration and current_sub:
                final_groups.append(current_sub)
                current_sub = [ss]
                start = ss.segment.start
            else:
                current_sub.append(ss)
        if current_sub:
            final_groups.append(current_sub)

    return final_groups


def _generate_title(reasons: list[str], text_preview: str) -> str:
    """Auto-generate a short clip title from reasons and text."""
    # Pick the first ~6 words of the clip text as a fallback title
    preview_words = text_preview.split()[:6]
    fallback = " ".join(preview_words)
    if len(preview_words) == 6:
        fallback += "..."

    # Try to create a descriptive title from reasons
    if any("contrarian_hook" in r for r in reasons):
        return f"Hot Take: {fallback}"
    if any("statistic" in r for r in reasons) or any("money_reference" in r for r in reasons):
        return f"By the Numbers: {fallback}"
    if any("emotion:shocked" in r or "emotion:surprise" in r for r in reasons):
        return f"Shocking Moment: {fallback}"
    if any("question" in r for r in reasons):
        return f"Big Question: {fallback}"
    return fallback


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_highlights(
    segments: list[dict],
    *,
    min_clip_duration: float = MIN_CLIP_DURATION,
    max_clip_duration: float = MAX_CLIP_DURATION,
    score_threshold: float = SEGMENT_SCORE_THRESHOLD,
    max_clips: int = 10,
) -> list[dict]:
    """
    Analyse transcript segments and return proposed viral clips.

    Args:
        segments: List of dicts with keys ``text``, ``start``, ``end``
            (as returned by ``transcription.transcribe``).
        min_clip_duration: Minimum clip length in seconds.
        max_clip_duration: Maximum clip length in seconds.
        score_threshold: Minimum normalised score for a segment to be
            considered highlight-worthy.
        max_clips: Maximum number of clips to return.

    Returns:
        List of clip dicts, each containing ``id``, ``title``,
        ``start_time``, ``end_time``, ``score``, ``reason``,
        ``segment_count``, and ``duration``.
    """
    parsed: list[TranscriptSegment] = [TranscriptSegment.from_dict(s) for s in segments]

    # Score every segment
    scored_all: list[ScoredSegment] = [score_segment(seg) for seg in parsed]

    # Filter to high-scoring segments
    high_scoring = [s for s in scored_all if s.score >= score_threshold]

    if not high_scoring:
        return []

    # Group into clips
    groups = _group_into_clips(
        high_scoring,
        min_duration=min_clip_duration,
        max_duration=max_clip_duration,
    )

    # Build ProposedClip objects
    clips: list[ProposedClip] = []
    for group in groups:
        start_time = group[0].segment.start
        end_time = group[-1].segment.end
        avg_score = sum(s.score for s in group) / len(group)
        all_reasons = []
        for s in group:
            all_reasons.extend(s.reasons)
        # Deduplicate reasons while preserving order
        seen: set[str] = set()
        unique_reasons: list[str] = []
        for r in all_reasons:
            if r not in seen:
                seen.add(r)
                unique_reasons.append(r)

        text_preview = group[0].segment.text
        title = _generate_title(unique_reasons, text_preview)

        clips.append(ProposedClip(
            id=str(uuid.uuid4()),
            title=title,
            start_time=start_time,
            end_time=end_time,
            score=avg_score,
            reason="; ".join(unique_reasons),
            segment_count=len(group),
        ))

    # Sort by score descending, take top N
    clips.sort(key=lambda c: c.score, reverse=True)
    clips = clips[:max_clips]

    return [c.to_dict() for c in clips]


def score_transcript(segments: list[dict]) -> list[dict]:
    """
    Score every segment without grouping — useful for visualising a
    heatmap in the frontend timeline.

    Returns a list of dicts with ``start``, ``end``, ``score``,
    ``reasons`` for each segment.
    """
    parsed = [TranscriptSegment.from_dict(s) for s in segments]
    results: list[dict] = []
    for seg in parsed:
        ss = score_segment(seg)
        results.append({
            "start": round(ss.segment.start, 3),
            "end": round(ss.segment.end, 3),
            "text": ss.segment.text,
            "score": round(ss.score, 3),
            "reasons": ss.reasons,
        })
    return results
