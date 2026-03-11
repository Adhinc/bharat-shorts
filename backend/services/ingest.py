"""
URL Ingestion Service

Downloads videos from YouTube, podcasts, and direct URLs using yt-dlp.
Supports:
- YouTube videos & Shorts
- YouTube playlists (first N videos)
- Podcast RSS feed episodes (audio)
- Direct video/audio URLs (MP4, WebM, MP3, etc.)
"""

import uuid
import logging
import subprocess
import json
from pathlib import Path

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


def download_from_url(
    url: str,
    max_duration: int = 7200,
    format_preference: str = "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
) -> dict:
    """
    Download a video/audio from a URL using yt-dlp.

    Args:
        url: YouTube URL, podcast URL, or direct media URL
        max_duration: Max video duration in seconds (default 2 hours)
        format_preference: yt-dlp format string

    Returns:
        {
            "project_id": "uuid",
            "file_path": "/path/to/file.mp4",
            "title": "Video Title",
            "duration": 123.4,
            "width": 1920,
            "height": 1080,
            "source_url": "https://...",
            "source_type": "youtube" | "podcast" | "direct"
        }
    """
    project_id = str(uuid.uuid4())
    output_path = str(UPLOAD_DIR / f"{project_id}.%(ext)s")

    # Determine source type
    source_type = _detect_source_type(url)

    # Build yt-dlp command
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--merge-output-format", "mp4",
        "-f", format_preference,
        "--max-filesize", "2G",
        "-o", output_path,
        "--write-info-json",
        "--no-write-thumbnail",
        "--no-write-comments",
        url,
    ]

    # For podcasts/audio-only, prefer audio format
    if source_type == "podcast":
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "-x",
            "--audio-format", "mp3",
            "-o", output_path,
            "--write-info-json",
            url,
        ]

    logger.info(f"Downloading from {url} (type: {source_type})")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    if result.returncode != 0:
        logger.error(f"yt-dlp failed: {result.stderr[:500]}")
        raise RuntimeError(f"Download failed: {result.stderr[:200]}")

    # Find the downloaded file
    downloaded = list(UPLOAD_DIR.glob(f"{project_id}.*"))
    # Filter out .json info files
    media_files = [f for f in downloaded if f.suffix not in (".json",)]

    if not media_files:
        raise RuntimeError("Download completed but no media file found")

    file_path = media_files[0]

    # Read metadata from info json
    info_json = UPLOAD_DIR / f"{project_id}.info.json"
    title = "Untitled"
    duration = 0.0
    width = 0
    height = 0

    if info_json.exists():
        try:
            with open(info_json) as f:
                info = json.load(f)
            title = info.get("title", "Untitled")
            duration = float(info.get("duration", 0) or 0)
            width = int(info.get("width", 0) or 0)
            height = int(info.get("height", 0) or 0)
            info_json.unlink()  # cleanup
        except Exception as e:
            logger.warning(f"Could not parse info json: {e}")

    # If we didn't get dimensions from yt-dlp metadata, use ffprobe
    if not width or not height or not duration:
        probe = _ffprobe(str(file_path))
        if probe:
            duration = duration or float(probe.get("format", {}).get("duration", 0))
            for stream in probe.get("streams", []):
                if stream.get("codec_type") == "video":
                    width = width or int(stream.get("width", 0))
                    height = height or int(stream.get("height", 0))
                    break

    # For audio-only files (podcasts), convert to video with black background
    if source_type == "podcast" and file_path.suffix in (".mp3", ".m4a", ".wav", ".ogg"):
        video_path = UPLOAD_DIR / f"{project_id}.mp4"
        _audio_to_video(str(file_path), str(video_path), duration)
        file_path.unlink()  # remove audio-only file
        file_path = video_path
        width = 1080
        height = 1920

    # Enforce max duration
    if duration > max_duration:
        raise RuntimeError(
            f"Video too long ({duration:.0f}s). Max allowed: {max_duration}s"
        )

    return {
        "project_id": project_id,
        "file_path": str(file_path),
        "title": title,
        "duration": duration,
        "width": width,
        "height": height,
        "source_url": url,
        "source_type": source_type,
    }


def _detect_source_type(url: str) -> str:
    """Detect the type of URL."""
    url_lower = url.lower()

    youtube_patterns = [
        "youtube.com", "youtu.be", "youtube-nocookie.com",
        "youtube.com/shorts", "youtube.com/watch",
    ]
    if any(p in url_lower for p in youtube_patterns):
        return "youtube"

    podcast_patterns = [
        ".rss", "/feed", "anchor.fm", "spotify.com/episode",
        "podcasts.apple.com", "podbean.com", "buzzsprout.com",
        "soundcloud.com", ".mp3",
    ]
    if any(p in url_lower for p in podcast_patterns):
        return "podcast"

    return "direct"


def _ffprobe(file_path: str) -> dict | None:
    """Extract media metadata using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", file_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception:
        pass
    return None


def _audio_to_video(audio_path: str, video_path: str, duration: float) -> None:
    """Convert audio-only file to video with a dark background for the editor."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=0x111111:s=1080x1920:d={duration}:r=1",
        "-i", audio_path,
        "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"Audio-to-video conversion failed: {result.stderr[:200]}")
