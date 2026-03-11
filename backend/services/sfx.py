"""
Automated SFX & Music Service for Bharat Shorts

Features:
- Synthesize transition SFX via FFmpeg (whoosh, swoosh, pop, ding, bass drop, rise)
- Auto-place SFX at segment boundaries / scene transitions
- Generate ambient background music loops via FFmpeg tone synthesis
- Bundled SFX library (generated on first use, cached in assets/sfx/)
- Mix SFX track into video with proper timing via adelay
"""

import subprocess
import json
import uuid
import shutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
SFX_DIR = ASSETS_DIR / "sfx"
MUSIC_DIR = ASSETS_DIR / "music"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "processed"

SFX_DIR.mkdir(parents=True, exist_ok=True)
MUSIC_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)

# ─── SFX Definitions (synthesized via FFmpeg lavfi) ───────────────────────

SFX_CATALOG = {
    "whoosh": {
        "name": "Whoosh",
        "description": "Fast air sweep transition",
        "duration": 0.4,
        "filter": (
            "anoisesrc=d=0.4:c=pink:r=44100:a=0.3,"
            "highpass=f=800,"
            "lowpass=f=6000,"
            "afade=t=in:ss=0:d=0.1,"
            "afade=t=out:st=0.2:d=0.2,"
            "asetrate=44100*1.5,aresample=44100,"
            "atempo=1.3"
        ),
    },
    "swoosh": {
        "name": "Swoosh",
        "description": "Smooth sweep transition",
        "duration": 0.5,
        "filter": (
            "sine=f=300:d=0.5,"
            "aeval='val(0)*exp(-3*t)',"
            "highpass=f=200,"
            "afade=t=in:ss=0:d=0.05,"
            "afade=t=out:st=0.3:d=0.2"
        ),
    },
    "pop": {
        "name": "Pop",
        "description": "Quick pop/click sound",
        "duration": 0.15,
        "filter": (
            "sine=f=800:d=0.15,"
            "aeval='val(0)*exp(-20*t)',"
            "afade=t=out:st=0.05:d=0.1"
        ),
    },
    "ding": {
        "name": "Ding",
        "description": "Bright notification ding",
        "duration": 0.6,
        "filter": (
            "sine=f=1200:d=0.6,"
            "aeval='val(0)*exp(-5*t)',"
            "afade=t=out:st=0.3:d=0.3"
        ),
    },
    "bass_drop": {
        "name": "Bass Drop",
        "description": "Deep bass impact",
        "duration": 0.5,
        "filter": (
            "sine=f=60:d=0.5,"
            "aeval='val(0)*exp(-4*t)*1.5',"
            "lowpass=f=150,"
            "afade=t=out:st=0.2:d=0.3"
        ),
    },
    "rise": {
        "name": "Rise",
        "description": "Building tension riser",
        "duration": 1.0,
        "filter": (
            "anoisesrc=d=1.0:c=white:r=44100:a=0.2,"
            "highpass=f=2000,"
            "afade=t=in:ss=0:d=0.8,"
            "afade=t=out:st=0.8:d=0.2,"
            "atempo=0.8"
        ),
    },
    "click": {
        "name": "Click",
        "description": "Subtle UI click",
        "duration": 0.08,
        "filter": (
            "sine=f=2000:d=0.08,"
            "aeval='val(0)*exp(-40*t)',"
            "afade=t=out:st=0.02:d=0.06"
        ),
    },
    "reveal": {
        "name": "Reveal",
        "description": "Shimmer reveal sound",
        "duration": 0.8,
        "filter": (
            "sine=f=600:d=0.8,"
            "aeval='val(0)*sin(2*PI*8*t)*exp(-3*t)',"
            "afade=t=in:ss=0:d=0.1,"
            "afade=t=out:st=0.5:d=0.3"
        ),
    },
}

# ─── Background Music Presets (synthesized ambient loops) ─────────────────

MUSIC_PRESETS = {
    "chill_lo_fi": {
        "name": "Chill Lo-Fi",
        "description": "Soft lo-fi ambient background",
        "duration": 30.0,
        "filter": (
            "sine=f=220:d=30,"
            "aeval='0.15*val(0)*(1+0.3*sin(2*PI*0.5*t))',"
            "lowpass=f=3000,"
            "afade=t=in:ss=0:d=2,"
            "afade=t=out:st=28:d=2"
        ),
    },
    "upbeat_energy": {
        "name": "Upbeat Energy",
        "description": "Energetic background pulse",
        "duration": 30.0,
        "filter": (
            "sine=f=330:d=30,"
            "aeval='0.12*val(0)*(1+0.5*sin(2*PI*2*t))*(1+0.3*sin(2*PI*0.25*t))',"
            "highpass=f=100,lowpass=f=5000,"
            "afade=t=in:ss=0:d=1,"
            "afade=t=out:st=28:d=2"
        ),
    },
    "cinematic_pad": {
        "name": "Cinematic Pad",
        "description": "Deep cinematic atmosphere",
        "duration": 30.0,
        "filter": (
            "sine=f=110:d=30,"
            "aeval='0.1*val(0)*(1+0.2*sin(2*PI*0.1*t))',"
            "lowpass=f=2000,"
            "afade=t=in:ss=0:d=3,"
            "afade=t=out:st=27:d=3"
        ),
    },
    "news_intro": {
        "name": "News Intro",
        "description": "Professional news-style background",
        "duration": 30.0,
        "filter": (
            "sine=f=440:d=30,"
            "aeval='0.08*val(0)*(1+0.4*sin(2*PI*1*t))*(0.7+0.3*sin(2*PI*0.2*t))',"
            "highpass=f=200,lowpass=f=4000,"
            "afade=t=in:ss=0:d=1,"
            "afade=t=out:st=28:d=2"
        ),
    },
    "bollywood_vibe": {
        "name": "Bollywood Vibe",
        "description": "Indian-inspired rhythmic background",
        "duration": 30.0,
        "filter": (
            "sine=f=261:d=30,"
            "aeval='0.12*val(0)*(1+0.6*sin(2*PI*3*t))*(1+0.3*sin(2*PI*0.5*t))',"
            "highpass=f=100,lowpass=f=6000,"
            "afade=t=in:ss=0:d=1,"
            "afade=t=out:st=28:d=2"
        ),
    },
}


# ─── SFX Generation ──────────────────────────────────────────────────────

def generate_sfx(sfx_type: str) -> str:
    """Generate an SFX audio file. Returns path to WAV file (cached)."""
    if sfx_type not in SFX_CATALOG:
        raise ValueError(f"Unknown SFX type: {sfx_type}. Available: {list(SFX_CATALOG.keys())}")

    cached_path = SFX_DIR / f"{sfx_type}.wav"
    if cached_path.exists():
        return str(cached_path)

    sfx = SFX_CATALOG[sfx_type]
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", sfx["filter"],
        "-ar", "44100", "-ac", "1",
        str(cached_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"SFX generation failed for {sfx_type}: {result.stderr[:300]}")

    logger.info(f"Generated SFX: {sfx_type} → {cached_path}")
    return str(cached_path)


def generate_all_sfx() -> dict[str, str]:
    """Generate all SFX files. Returns {type: path} map."""
    paths = {}
    for sfx_type in SFX_CATALOG:
        try:
            paths[sfx_type] = generate_sfx(sfx_type)
        except Exception as e:
            logger.warning(f"Failed to generate SFX {sfx_type}: {e}")
    return paths


def generate_music_loop(preset: str) -> str:
    """Generate an ambient music loop. Returns path to WAV file (cached)."""
    if preset not in MUSIC_PRESETS:
        raise ValueError(f"Unknown music preset: {preset}. Available: {list(MUSIC_PRESETS.keys())}")

    cached_path = MUSIC_DIR / f"{preset}.wav"
    if cached_path.exists():
        return str(cached_path)

    music = MUSIC_PRESETS[preset]
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", music["filter"],
        "-ar", "44100", "-ac", "2",
        str(cached_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Music generation failed for {preset}: {result.stderr[:300]}")

    logger.info(f"Generated music loop: {preset} → {cached_path}")
    return str(cached_path)


# ─── Auto SFX Placement ──────────────────────────────────────────────────

def auto_place_sfx(
    segments: list[dict],
    sfx_type: str = "whoosh",
    min_gap: float = 3.0,
    place_at: str = "transitions",
) -> list[dict]:
    """
    Auto-detect where to place SFX in a video based on transcript segments.

    Args:
        segments: Transcript segments with start/end times
        sfx_type: Which SFX to use
        min_gap: Minimum seconds between SFX placements
        place_at: Placement strategy:
            - "transitions": At gaps between segments (scene changes)
            - "all_segments": At the start of every segment
            - "long_pauses": Only at pauses > 1 second

    Returns:
        List of {"time": float, "sfx_type": str, "sfx_path": str}
    """
    if not segments:
        return []

    sfx_path = generate_sfx(sfx_type)
    sfx_duration = SFX_CATALOG[sfx_type]["duration"]
    placements = []
    last_placement = -min_gap

    sorted_segments = sorted(segments, key=lambda s: s["start"])

    for i in range(len(sorted_segments)):
        seg = sorted_segments[i]

        if place_at == "transitions" and i > 0:
            prev_end = sorted_segments[i - 1]["end"]
            gap = seg["start"] - prev_end
            if gap > 0.3:  # meaningful gap between segments
                place_time = prev_end + (gap / 2) - (sfx_duration / 2)
                place_time = max(place_time, prev_end)
                if place_time - last_placement >= min_gap:
                    placements.append({
                        "time": round(place_time, 3),
                        "sfx_type": sfx_type,
                        "sfx_path": sfx_path,
                    })
                    last_placement = place_time

        elif place_at == "all_segments":
            place_time = max(0, seg["start"] - sfx_duration)
            if place_time - last_placement >= min_gap:
                placements.append({
                    "time": round(place_time, 3),
                    "sfx_type": sfx_type,
                    "sfx_path": sfx_path,
                })
                last_placement = place_time

        elif place_at == "long_pauses" and i > 0:
            prev_end = sorted_segments[i - 1]["end"]
            gap = seg["start"] - prev_end
            if gap > 1.0:
                place_time = prev_end + (gap / 2) - (sfx_duration / 2)
                if place_time - last_placement >= min_gap:
                    placements.append({
                        "time": round(place_time, 3),
                        "sfx_type": sfx_type,
                        "sfx_path": sfx_path,
                    })
                    last_placement = place_time

    return placements


# ─── SFX Mixing into Video ───────────────────────────────────────────────

def _get_duration(file_path: str) -> float:
    """Get media file duration via ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", file_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        data = json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0))
    return 0.0


def mix_sfx_into_video(
    video_path: str,
    sfx_placements: list[dict],
    output_path: str,
    sfx_volume: float = 0.7,
) -> str:
    """
    Mix SFX sounds into a video at specified timestamps.

    Uses FFmpeg adelay to position each SFX at the correct time,
    then amix to combine all SFX with the original audio.
    """
    if not sfx_placements:
        shutil.copy(video_path, output_path)
        return output_path

    # Collect unique SFX files
    inputs = ["-i", video_path]
    filter_parts = []
    sfx_labels = []

    for i, placement in enumerate(sfx_placements):
        sfx_path = placement["sfx_path"]
        delay_ms = int(placement["time"] * 1000)

        inputs.extend(["-i", sfx_path])
        input_idx = i + 1

        # Delay the SFX to its placement time and set volume
        filter_parts.append(
            f"[{input_idx}:a]adelay={delay_ms}|{delay_ms},"
            f"volume={sfx_volume}[sfx_{i}]"
        )
        sfx_labels.append(f"[sfx_{i}]")

    # Mix all SFX together
    if len(sfx_labels) > 1:
        filter_parts.append(
            f"{''.join(sfx_labels)}amix=inputs={len(sfx_labels)}:"
            f"duration=longest:dropout_transition=0[all_sfx]"
        )
        mix_label = "all_sfx"
    else:
        mix_label = "sfx_0"

    # Mix SFX track with original audio
    filter_parts.append(f"[0:a]acopy[orig]")
    filter_parts.append(
        f"[orig][{mix_label}]amix=inputs=2:duration=first:"
        f"dropout_transition=2[final]"
    )

    filter_complex = ";\n".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[final]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        logger.error(f"SFX mixing failed: {result.stderr[:500]}")
        shutil.copy(video_path, output_path)

    return output_path


# ─── Full SFX Pipeline ───────────────────────────────────────────────────

def add_sfx_to_video(
    project_id: str,
    video_path: str,
    segments: list[dict],
    sfx_type: str = "whoosh",
    sfx_volume: float = 0.7,
    min_gap: float = 3.0,
    place_at: str = "transitions",
) -> dict:
    """
    Full SFX pipeline: auto-detect placements and mix into video.

    Returns:
        {
            "output_path": "/path/to/video_with_sfx.mp4",
            "sfx_count": 5,
            "sfx_type": "whoosh",
            "placements": [...],
        }
    """
    # Auto-detect SFX placements
    placements = auto_place_sfx(
        segments, sfx_type=sfx_type, min_gap=min_gap, place_at=place_at
    )

    if not placements:
        return {
            "output_path": video_path,
            "sfx_count": 0,
            "sfx_type": sfx_type,
            "placements": [],
        }

    output_path = str(PROCESSED_DIR / f"{project_id}_sfx.mp4")

    mix_sfx_into_video(
        video_path=video_path,
        sfx_placements=placements,
        output_path=output_path,
        sfx_volume=sfx_volume,
    )

    return {
        "output_path": output_path,
        "sfx_count": len(placements),
        "sfx_type": sfx_type,
        "placements": [{"time": p["time"], "sfx_type": p["sfx_type"]} for p in placements],
    }


def list_sfx_catalog() -> list[dict]:
    """List all available SFX types."""
    return [
        {
            "id": sfx_id,
            "name": sfx["name"],
            "description": sfx["description"],
            "duration": sfx["duration"],
        }
        for sfx_id, sfx in SFX_CATALOG.items()
    ]


def list_music_presets() -> list[dict]:
    """List all available music presets."""
    return [
        {
            "id": preset_id,
            "name": preset["name"],
            "description": preset["description"],
            "duration": preset["duration"],
        }
        for preset_id, preset in MUSIC_PRESETS.items()
    ]
