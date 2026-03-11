"""Silence removal service - extracted from main.py for modularity."""

import subprocess
import json
from pathlib import Path


def get_video_info(file_path: str) -> dict:
    """Extract video metadata using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", file_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    return json.loads(result.stdout)


def remove_silence(
    input_path: str,
    output_path: str,
    threshold_db: float = -30,
    min_silence_ms: int = 500,
) -> float:
    """Remove silent segments from video using FFmpeg silencedetect.

    Returns new duration in seconds.
    """
    # Detect silence
    detect_cmd = [
        "ffmpeg", "-i", input_path,
        "-af", f"silencedetect=noise={threshold_db}dB:d={min_silence_ms / 1000}",
        "-f", "null", "-",
    ]
    result = subprocess.run(detect_cmd, capture_output=True, text=True)
    stderr = result.stderr

    # Parse silence intervals
    silence_starts: list[float] = []
    silence_ends: list[float] = []
    for line in stderr.split("\n"):
        if "silence_start:" in line:
            val = line.split("silence_start:")[1].strip().split()[0]
            silence_starts.append(float(val))
        if "silence_end:" in line:
            val = line.split("silence_end:")[1].strip().split()[0]
            silence_ends.append(float(val))

    if not silence_starts:
        import shutil
        shutil.copy(input_path, output_path)
        info = get_video_info(output_path)
        return float(info["format"]["duration"])

    # Build non-silent segments
    info = get_video_info(input_path)
    total_duration = float(info["format"]["duration"])

    segments: list[tuple[float, float]] = []
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
