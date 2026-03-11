"""
Auto-reframe service for Bharat Shorts.

Converts landscape (16:9) videos to portrait (9:16) for YouTube Shorts,
Instagram Reels, etc. MVP uses center-crop; face-tracking via MediaPipe
will be added in a future phase.
"""

import json
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_video_dimensions(input_path: str) -> tuple[int, int]:
    """Probe video width and height using FFprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        input_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFprobe failed: {result.stderr}")

    probe = json.loads(result.stdout)
    streams = probe.get("streams", [])
    if not streams:
        raise RuntimeError(f"No video stream found in {input_path}")

    return int(streams[0]["width"]), int(streams[0]["height"])


def _get_video_duration(input_path: str) -> float:
    """Probe video duration in seconds using FFprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        input_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFprobe failed: {result.stderr}")

    probe = json.loads(result.stdout)
    duration = probe.get("format", {}).get("duration")
    if duration is None:
        raise RuntimeError(f"Could not determine duration for {input_path}")

    return float(duration)


def detect_face_position(input_path: str, sample_frames: int = 5) -> tuple[int, int]:
    """
    Detect the primary face position in a video.

    Uses MediaPipe if available, otherwise falls back to center crop.

    Returns:
        (x, y) pixel coordinates of the face center.
    """
    src_w, src_h = _get_video_dimensions(input_path)

    try:
        import cv2
        import mediapipe as mp
        import numpy as np
    except ImportError:
        logger.warning("MediaPipe/OpenCV not installed, using center crop fallback")
        return (src_w // 2, src_h // 2)

    mp_face_detection = mp.solutions.face_detection
    cap = cv2.VideoCapture(input_path)

    # Sample frames evenly across the video
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        total_frames = sample_frames
    step = max(1, total_frames // sample_frames)

    face_centers = []

    with mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) as face_detection:
        for i in range(sample_frames):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i * step)
            success, image = cap.read()
            if not success:
                break

            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = face_detection.process(image_rgb)

            if results.detections:
                detection = results.detections[0]
                bbox = detection.location_data.relative_bounding_box
                center_x = int((bbox.xmin + bbox.width / 2) * src_w)
                center_y = int((bbox.ymin + bbox.height / 2) * src_h)
                face_centers.append((center_x, center_y))

    cap.release()

    if face_centers:
        avg_x = int(np.median([c[0] for c in face_centers]))
        avg_y = int(np.median([c[1] for c in face_centers]))
        logger.info(f"Detected face at ({avg_x}, {avg_y})")
        return (avg_x, avg_y)

    logger.warning("No face detected, falling back to center crop")
    return (src_w // 2, src_h // 2)


def reframe_video(
    input_path: str,
    output_path: str,
    target_width: int = 1080,
    target_height: int = 1920,
) -> str:
    """
    Convert a landscape (16:9) video to portrait (9:16) via AI-powered face-centric crop.

    The source video is cropped to a 9:16 region centered on the detected face,
    then scaled to the exact target dimensions.
    """
    if not Path(input_path).is_file():
        raise FileNotFoundError(f"Input video not found: {input_path}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    src_w, src_h = _get_video_dimensions(input_path)
    logger.info("Source dimensions: %dx%d", src_w, src_h)

    # Detect face position
    face_x, face_y = detect_face_position(input_path)

    # Calculate the largest 9:16 crop that fits inside the source frame.
    crop_h = src_h
    crop_w = int(crop_h * target_width / target_height)

    if crop_w > src_w:
        crop_w = src_w
        crop_h = int(crop_w * target_height / target_width)

    # Ensure even dimensions
    crop_w = crop_w - (crop_w % 2)
    crop_h = crop_h - (crop_h % 2)

    # Center the crop window around the face_x, but clamp to frame boundaries
    x_offset = int(face_x - crop_w // 2)
    y_offset = int(face_y - crop_h // 2)

    # Clamp offsets so we don't crop outside the frame
    x_offset = max(0, min(x_offset, src_w - crop_w))
    y_offset = max(0, min(y_offset, src_h - crop_h))

    logger.info(
        "Face-centric crop: %dx%d at offset (%d, %d) -> scale to %dx%d",
        crop_w, crop_h, x_offset, y_offset, target_width, target_height,
    )

    # Build the FFmpeg filter
    vf = (
        f"crop={crop_w}:{crop_h}:{x_offset}:{y_offset},"
        f"scale={target_width}:{target_height}:flags=lanczos"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_path,
    ]

    logger.info("Running FFmpeg reframe: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg reframe failed: {result.stderr}")

    logger.info("Reframed video written to %s", output_path)
    return output_path


def auto_zoom(
    input_path: str,
    output_path: str,
    zoom_times: list[float],
    zoom_factor: float = 1.3,
    zoom_duration: float = 0.5,
) -> str:
    """
    Apply punch-in zoom effects at specific timestamps.

    Each zoom is a smooth scale-up from 1.0x to `zoom_factor` and back,
    lasting `zoom_duration` seconds, centered on the frame.

    Args:
        input_path:     Path to the source video.
        output_path:    Where to write the zoomed result.
        zoom_times:     List of timestamps (seconds) where zoom occurs.
        zoom_factor:    Maximum zoom multiplier (default 1.3 = 130%).
        zoom_duration:  How long each zoom lasts in seconds (default 0.5).

    Returns:
        The output_path on success.

    Raises:
        FileNotFoundError: If input_path does not exist.
        ValueError:        If zoom_times is empty.
        RuntimeError:      If FFmpeg fails.
    """
    if not Path(input_path).is_file():
        raise FileNotFoundError(f"Input video not found: {input_path}")

    if not zoom_times:
        raise ValueError("zoom_times must contain at least one timestamp")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    src_w, src_h = _get_video_dimensions(input_path)
    duration = _get_video_duration(input_path)

    # Clamp zoom times to video duration
    zoom_times = sorted(t for t in zoom_times if 0 <= t <= duration)
    if not zoom_times:
        raise ValueError("No valid zoom timestamps within video duration")

    # Build a zoompan-style filter using crop + scale expressions.
    # For each zoom point we create a smooth triangle envelope:
    #   zoom(t) = 1 + (factor-1) * triangle((t - start) / duration)
    # where triangle peaks at 0.5 and returns to 0 at 0 and 1.
    #
    # FFmpeg's expression syntax lets us build this with between() and
    # arithmetic on time (t).

    zoom_exprs = []
    for t in zoom_times:
        half = zoom_duration / 2
        start = t
        end = t + zoom_duration
        # Triangle: rises linearly to peak at midpoint, falls back
        # between(t,start,end) gates the expression
        peak = zoom_factor - 1.0
        expr = (
            f"{peak}*between(t,{start:.3f},{end:.3f})"
            f"*(1-abs(2*(t-{start:.3f})/{zoom_duration:.3f}-1))"
        )
        zoom_exprs.append(expr)

    # Total zoom multiplier expression (base 1 + sum of all zoom bumps)
    z_expr = "1+" + "+".join(zoom_exprs)

    # Use the zoompan filter: zoom expression, keep size, 25fps default
    # zoompan works on each frame: z=zoom level, d=1 means one output
    # frame per input frame.
    # We output at the original resolution; caller can chain with reframe.
    vf = (
        f"zoompan=z='{z_expr}'"
        f":x='iw/2-(iw/zoom/2)'"
        f":y='ih/2-(ih/zoom/2)'"
        f":d=1"
        f":s={src_w}x{src_h}"
        f":fps=30"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_path,
    ]

    logger.info("Running FFmpeg auto-zoom: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg auto-zoom failed: {result.stderr}")

    logger.info("Zoomed video written to %s", output_path)
    return output_path
