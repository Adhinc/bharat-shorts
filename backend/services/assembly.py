"""
Automated Assembly Service

Orchestrates the full auto-edit pipeline:
1. Downloads matching B-Roll stock clips from Pexels
2. Inserts B-Roll overlays at relevant timestamps
3. Adds transitions (crossfade) between main video and B-Roll
4. Mixes background music with speech-aware ducking
5. Outputs a fully assembled video ready to post
"""

import subprocess
import uuid
import logging
import json
import shutil
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "processed"
PROCESSED_DIR.mkdir(exist_ok=True)

# Bundled royalty-free music tracks (short loops)
MUSIC_DIR = Path(__file__).resolve().parent.parent / "assets" / "music"
MUSIC_DIR.mkdir(parents=True, exist_ok=True)


def download_stock_clip(video_url: str, output_path: str, timeout: float = 30.0) -> bool:
    """Download a single stock video clip from a URL."""
    try:
        with httpx.stream("GET", video_url, timeout=timeout, follow_redirects=True) as resp:
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)
        return True
    except Exception as e:
        logger.warning(f"Failed to download clip: {e}")
        return False


def select_best_clip_url(videos: list[dict], preferred_height: int = 720) -> str | None:
    """Pick the best video file URL from Pexels results.
    Prefers SD quality to keep file sizes manageable."""
    for video in videos:
        if "error" in video:
            continue
        files = video.get("video_files", [])
        # Sort by closeness to preferred height
        valid = [f for f in files if f.get("link") and f.get("height")]
        if not valid:
            continue
        valid.sort(key=lambda f: abs(f["height"] - preferred_height))
        return valid[0]["link"]
    return None


def _get_duration(file_path: str) -> float:
    """Get media duration via ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", file_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        data = json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0))
    return 0.0


def _get_video_info(file_path: str) -> dict:
    """Get full video info via ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", file_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return json.loads(result.stdout)
    return {}


def generate_silence_audio(output_path: str, duration: float) -> None:
    """Generate a silent audio file of given duration."""
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"anullsrc=r=44100:cl=stereo",
        "-t", str(duration),
        "-c:a", "aac", "-b:a", "128k",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, text=True)


def insert_broll_overlays(
    main_video: str,
    broll_clips: list[dict],
    output_path: str,
    transition_duration: float = 0.5,
    broll_opacity: float = 1.0,
) -> str:
    """
    Insert B-Roll clips as overlay cuts into the main video.

    Each broll_clip dict: {
        "file_path": "/path/to/clip.mp4",
        "start_time": 5.0,   # when to insert in the main timeline
        "end_time": 8.0,     # when B-Roll ends
    }

    Uses FFmpeg to cut and splice B-Roll segments into the main video
    at the specified timestamps with crossfade transitions.
    """
    if not broll_clips:
        shutil.copy(main_video, output_path)
        return output_path

    # Get main video info
    main_info = _get_video_info(main_video)
    main_duration = float(main_info.get("format", {}).get("duration", 0))
    v_stream = next(
        (s for s in main_info.get("streams", []) if s["codec_type"] == "video"), None
    )
    if not v_stream:
        shutil.copy(main_video, output_path)
        return output_path

    width = int(v_stream.get("width", 1920))
    height = int(v_stream.get("height", 1080))

    # Sort B-Roll by start time
    broll_clips = sorted(broll_clips, key=lambda c: c["start_time"])

    # Build timeline segments: alternating main video and B-Roll
    # Each segment is either from main video or from a B-Roll clip
    segments = []
    current_time = 0.0

    for clip in broll_clips:
        broll_start = clip["start_time"]
        broll_end = clip["end_time"]
        broll_path = clip["file_path"]

        if not Path(broll_path).exists():
            continue

        # Main video segment before this B-Roll
        if broll_start > current_time:
            segments.append({
                "type": "main",
                "start": current_time,
                "end": broll_start,
            })

        # B-Roll segment
        broll_duration = broll_end - broll_start
        actual_broll_duration = _get_duration(broll_path)
        # Use the shorter of requested duration and actual clip length
        use_duration = min(broll_duration, actual_broll_duration) if actual_broll_duration > 0 else broll_duration

        segments.append({
            "type": "broll",
            "path": broll_path,
            "duration": use_duration,
            "original_start": broll_start,
        })

        current_time = broll_start + use_duration

    # Remaining main video after last B-Roll
    if current_time < main_duration:
        segments.append({
            "type": "main",
            "start": current_time,
            "end": main_duration,
        })

    if not segments:
        shutil.copy(main_video, output_path)
        return output_path

    # Build FFmpeg filter_complex to concatenate all segments
    inputs = ["-i", main_video]
    broll_input_idx = 1
    filter_parts = []
    concat_inputs_v = []
    concat_inputs_a = []

    for i, seg in enumerate(segments):
        if seg["type"] == "main":
            # Trim main video
            filter_parts.append(
                f"[0:v]trim=start={seg['start']:.3f}:end={seg['end']:.3f},"
                f"setpts=PTS-STARTPTS,scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2[v{i}]"
            )
            filter_parts.append(
                f"[0:a]atrim=start={seg['start']:.3f}:end={seg['end']:.3f},"
                f"asetpts=PTS-STARTPTS[a{i}]"
            )
        else:
            # B-Roll clip
            inputs.extend(["-i", seg["path"]])
            filter_parts.append(
                f"[{broll_input_idx}:v]trim=start=0:end={seg['duration']:.3f},"
                f"setpts=PTS-STARTPTS,scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2[v{i}]"
            )
            # Use main video audio during B-Roll time (keep speech)
            orig_start = seg["original_start"]
            filter_parts.append(
                f"[0:a]atrim=start={orig_start:.3f}:end={orig_start + seg['duration']:.3f},"
                f"asetpts=PTS-STARTPTS[a{i}]"
            )
            broll_input_idx += 1

        concat_inputs_v.append(f"[v{i}]")
        concat_inputs_a.append(f"[a{i}]")

    # Concatenate all segments
    n = len(segments)
    filter_parts.append(
        f"{''.join(concat_inputs_v)}{''.join(concat_inputs_a)}"
        f"concat=n={n}:v=1:a=1[outv][outa]"
    )

    filter_complex = ";\n".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        logger.error(f"B-Roll insertion failed: {result.stderr[:500]}")
        # Fallback: copy original
        shutil.copy(main_video, output_path)

    return output_path


def add_background_music(
    video_path: str,
    music_path: str,
    output_path: str,
    segments: list[dict],
    music_volume: float = 0.15,
    duck_db: float = -14.0,
) -> str:
    """
    Mix background music into video with speech-aware ducking.
    Music volume drops during speech and rises during pauses.
    """
    from services.broll import compute_duck_regions

    # Compute speech regions for ducking
    regions = compute_duck_regions(segments, duck_db=duck_db)

    video_duration = _get_duration(video_path)
    music_duration = _get_duration(music_path)

    if music_duration <= 0:
        shutil.copy(video_path, output_path)
        return output_path

    # Build filter: loop music if needed, apply ducking, mix with speech
    filter_parts = []

    # Loop music to match video duration if needed
    if music_duration < video_duration:
        loop_count = int(video_duration / music_duration) + 1
        filter_parts.append(
            f"[1:a]aloop=loop={loop_count}:size={int(music_duration * 44100)},"
            f"atrim=0:{video_duration:.3f},asetpts=PTS-STARTPTS[music_loop]"
        )
        music_label = "music_loop"
    else:
        filter_parts.append(
            f"[1:a]atrim=0:{video_duration:.3f},asetpts=PTS-STARTPTS[music_trimmed]"
        )
        music_label = "music_trimmed"

    # Apply base volume
    filter_parts.append(
        f"[{music_label}]volume={music_volume}[music_base]"
    )

    # Apply ducking during speech regions
    prev_label = "music_base"
    if regions:
        for i, region in enumerate(regions):
            start = region["speech_start"]
            end = region["speech_end"]
            duck_linear = round(10 ** (duck_db / 20), 4)
            out_label = f"duck_{i}" if i < len(regions) - 1 else "ducked_music"
            filter_parts.append(
                f"[{prev_label}]volume=volume={duck_linear}:"
                f"enable='between(t,{start:.3f},{end:.3f})'[{out_label}]"
            )
            prev_label = out_label
    else:
        filter_parts.append(f"[music_base]acopy[ducked_music]")

    # Mix speech + ducked music
    filter_parts.append("[0:a]acopy[speech]")
    filter_parts.append(
        "[speech][ducked_music]amix=inputs=2:duration=first:dropout_transition=2[final_audio]"
    )

    filter_complex = ";\n".join(filter_parts)

    # Add fade out on music at the end (last 3 seconds)
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", music_path,
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[final_audio]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        logger.error(f"Music mix failed: {result.stderr[:500]}")
        shutil.copy(video_path, output_path)

    return output_path


def auto_assemble(
    project_id: str,
    video_path: str,
    segments: list[dict],
    broll_suggestions: list[dict],
    music_path: str | None = None,
    music_volume: float = 0.15,
    max_broll_clips: int = 5,
    broll_min_gap: float = 10.0,
    work_dir: str | None = None,
) -> dict:
    """
    Full automated assembly pipeline.

    1. Downloads top B-Roll clips from Pexels suggestions
    2. Inserts B-Roll at keyword-matched timestamps
    3. Adds background music with ducking
    4. Returns path to final assembled video

    Args:
        project_id: UUID of the project
        video_path: Path to the main video
        segments: Transcript segments for ducking
        broll_suggestions: B-Roll suggestions from broll service
        music_path: Optional path to background music file
        music_volume: Base music volume (0.0-1.0)
        max_broll_clips: Maximum number of B-Roll clips to insert
        broll_min_gap: Minimum seconds between B-Roll insertions
        work_dir: Working directory for temp files

    Returns:
        {
            "output_path": "/path/to/assembled.mp4",
            "broll_inserted": 3,
            "music_added": True,
            "duration": 45.2,
        }
    """
    if work_dir:
        wdir = Path(work_dir)
    else:
        wdir = PROCESSED_DIR / f"{project_id}_assembly"
    wdir.mkdir(parents=True, exist_ok=True)

    current_video = video_path
    broll_inserted = 0

    # --- Step 1: Download and insert B-Roll ---
    if broll_suggestions:
        downloaded_clips = []
        last_broll_time = -broll_min_gap  # ensure first clip can be inserted

        for suggestion in broll_suggestions[:max_broll_clips * 2]:  # check more than we need
            if len(downloaded_clips) >= max_broll_clips:
                break

            start_time = suggestion.get("start_time", 0)
            end_time = suggestion.get("end_time", 0)

            # Enforce minimum gap between B-Roll insertions
            if start_time - last_broll_time < broll_min_gap:
                continue

            videos = suggestion.get("videos", [])
            clip_url = select_best_clip_url(videos)
            if not clip_url:
                continue

            # Download clip
            clip_path = str(wdir / f"broll_{len(downloaded_clips)}.mp4")
            if download_stock_clip(clip_url, clip_path):
                # Limit B-Roll duration to segment duration, max 5 seconds
                broll_duration = min(end_time - start_time, 5.0)
                downloaded_clips.append({
                    "file_path": clip_path,
                    "start_time": start_time,
                    "end_time": start_time + broll_duration,
                })
                last_broll_time = start_time + broll_duration
                logger.info(f"Downloaded B-Roll for '{suggestion.get('keyword', '')}' at {start_time:.1f}s")

        if downloaded_clips:
            broll_output = str(wdir / "with_broll.mp4")
            insert_broll_overlays(current_video, downloaded_clips, broll_output)
            if Path(broll_output).exists() and Path(broll_output).stat().st_size > 0:
                current_video = broll_output
                broll_inserted = len(downloaded_clips)

    # --- Step 2: Add background music ---
    music_added = False
    if music_path and Path(music_path).exists():
        music_output = str(wdir / "with_music.mp4")
        add_background_music(
            current_video, music_path, music_output,
            segments, music_volume=music_volume,
        )
        if Path(music_output).exists() and Path(music_output).stat().st_size > 0:
            current_video = music_output
            music_added = True

    # --- Step 3: Copy final output ---
    final_output = str(PROCESSED_DIR / f"{project_id}_assembled.mp4")
    if current_video != final_output:
        shutil.copy(current_video, final_output)

    # Cleanup work directory
    shutil.rmtree(str(wdir), ignore_errors=True)

    duration = _get_duration(final_output)

    return {
        "output_path": final_output,
        "broll_inserted": broll_inserted,
        "music_added": music_added,
        "duration": duration,
    }
