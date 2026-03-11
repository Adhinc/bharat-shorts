"""
Remotion Render Service for Bharat Shorts

Calls the Node.js Remotion render server for high-fidelity
caption rendering with complex animations (bounce, glow, shake, emoji-pop).

Falls back to FFmpeg-ASS rendering if the Remotion server is unavailable.
"""

import json
import logging
from urllib import request, error
from pathlib import Path

logger = logging.getLogger(__name__)

RENDER_SERVER_URL = "http://localhost:3100"
BACKEND_URL = "http://localhost:8000"


def is_remotion_available() -> bool:
    """Check if the Remotion render server is running."""
    try:
        req = request.Request(f"{RENDER_SERVER_URL}/health", method="GET")
        with request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            return data.get("status") == "ok"
    except Exception:
        return False


def render_with_remotion(
    project_id: str,
    video_path: str,
    segments: list[dict],
    caption_style: dict,
    duration_seconds: float,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    crf: int = 18,
) -> dict:
    """
    Render video with captions using the Remotion server.

    Args:
        project_id: Video project UUID
        video_path: Absolute path to the source video
        segments: Transcript segments with word-level timing
        caption_style: Caption style configuration
        duration_seconds: Video duration in seconds
        width: Output width
        height: Output height
        fps: Frames per second
        crf: Constant rate factor (lower = better quality, 18 is visually lossless)

    Returns:
        {"status": "complete", "output_path": "...", "download_url": "...", "renderer": "remotion"}

    Raises:
        RuntimeError: If the Remotion render server fails
    """
    # Build the video URL that Remotion can fetch from
    video_url = f"{BACKEND_URL}/api/v1/video/{project_id}"

    payload = {
        "project_id": project_id,
        "video_url": video_url,
        "segments": segments,
        "caption_style": caption_style,
        "duration_seconds": duration_seconds,
        "width": width,
        "height": height,
        "fps": fps,
        "crf": crf,
    }

    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{RENDER_SERVER_URL}/render",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    logger.info(f"Sending render request to Remotion server for project {project_id}")

    try:
        with request.urlopen(req, timeout=600) as resp:
            result = json.loads(resp.read())
            result["renderer"] = "remotion"
            logger.info(f"Remotion render complete for {project_id}")
            return result
    except error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Remotion render failed ({e.code}): {err_body}")
    except error.URLError as e:
        raise RuntimeError(f"Cannot reach Remotion server: {e.reason}")


def get_remotion_output_path(project_id: str) -> Path:
    """Get the path where Remotion saves rendered output."""
    return Path(__file__).resolve().parent.parent / "processed" / f"{project_id}_remotion.mp4"
