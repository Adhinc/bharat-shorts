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


def reframe_video_dynamic(
    input_path: str,
    output_path: str,
    target_width: int = 1080,
    target_height: int = 1920,
    smoothing: float = 0.85,
    sample_interval: int = 3,
) -> dict:
    """
    Dynamic face-tracking reframe: follows the speaker frame-by-frame.

    Pipeline:
    1. Sample frames at intervals, detect face position per frame
    2. Smooth positions with exponential moving average to avoid jitter
    3. Interpolate positions for skipped frames
    4. Render using OpenCV: per-frame crop centered on smoothed face position
    5. Merge with original audio via FFmpeg

    Args:
        input_path: Source video path
        output_path: Output path
        target_width, target_height: Output dimensions (default 9:16)
        smoothing: EMA smoothing factor (0.0=no smoothing, 0.99=very smooth)
        sample_interval: Detect face every N frames (1=every frame, 3=every 3rd)

    Returns:
        {"output_path", "frames_processed", "faces_detected", "duration"}
    """
    import cv2
    import numpy as np
    import mediapipe as mp

    if not Path(input_path).is_file():
        raise FileNotFoundError(f"Input video not found: {input_path}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {input_path}")

    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Calculate crop dimensions (9:16 region from source)
    crop_h = src_h
    crop_w = int(crop_h * target_width / target_height)
    if crop_w > src_w:
        crop_w = src_w
        crop_h = int(crop_w * target_height / target_width)
    crop_w = crop_w - (crop_w % 2)
    crop_h = crop_h - (crop_h % 2)

    # --- Pass 1: Detect face positions ---
    logger.info(f"Dynamic reframe pass 1: detecting faces in {total_frames} frames...")

    # Use FaceLandmarker (tasks API)
    models_dir = Path(__file__).resolve().parent.parent / "models"
    model_path = models_dir / "face_landmarker.task"

    face_positions = {}  # frame_idx -> (cx, cy)

    if model_path.exists():
        base_options = mp.tasks.BaseOptions(model_asset_path=str(model_path))
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=base_options,
            num_faces=1,
        )
        landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)

        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % sample_interval == 0:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                result = landmarker.detect(mp_image)

                if result.face_landmarks:
                    landmarks = result.face_landmarks[0]
                    # Use nose tip (landmark 1) as face center
                    nose = landmarks[1]
                    cx = int(nose.x * src_w)
                    cy = int(nose.y * src_h)
                    face_positions[frame_idx] = (cx, cy)

            frame_idx += 1

        landmarker.close()
    else:
        # Fallback: try mp.solutions
        logger.warning("FaceLandmarker model not found, using center crop")

    cap.release()

    faces_detected = len(face_positions)
    logger.info(f"Detected faces in {faces_detected}/{total_frames} frames")

    # Default position: center
    default_x, default_y = src_w // 2, src_h // 2

    # --- Interpolate and smooth positions for all frames ---
    all_positions = []
    sorted_detected = sorted(face_positions.keys())

    for i in range(total_frames):
        if i in face_positions:
            all_positions.append(face_positions[i])
        elif sorted_detected:
            # Interpolate between nearest detected frames
            prev_idx = None
            next_idx = None
            for di in sorted_detected:
                if di <= i:
                    prev_idx = di
                if di > i and next_idx is None:
                    next_idx = di

            if prev_idx is not None and next_idx is not None:
                # Linear interpolation
                t = (i - prev_idx) / (next_idx - prev_idx)
                px, py = face_positions[prev_idx]
                nx, ny = face_positions[next_idx]
                all_positions.append((
                    int(px + (nx - px) * t),
                    int(py + (ny - py) * t),
                ))
            elif prev_idx is not None:
                all_positions.append(face_positions[prev_idx])
            elif next_idx is not None:
                all_positions.append(face_positions[next_idx])
            else:
                all_positions.append((default_x, default_y))
        else:
            all_positions.append((default_x, default_y))

    # Apply exponential moving average for smooth camera motion
    smoothed = [all_positions[0]]
    for i in range(1, len(all_positions)):
        prev_x, prev_y = smoothed[-1]
        curr_x, curr_y = all_positions[i]
        sx = smoothing * prev_x + (1 - smoothing) * curr_x
        sy = smoothing * prev_y + (1 - smoothing) * curr_y
        smoothed.append((sx, sy))

    # --- Pass 2: Render with dynamic crop ---
    logger.info("Dynamic reframe pass 2: rendering...")

    cap = cv2.VideoCapture(input_path)
    temp_video = output_path + ".temp.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(temp_video, fourcc, fps, (target_width, target_height))

    for i in range(total_frames):
        ret, frame = cap.read()
        if not ret:
            break

        cx, cy = smoothed[i] if i < len(smoothed) else (default_x, default_y)

        # Calculate crop offsets, clamped to frame bounds
        x_off = int(cx - crop_w // 2)
        y_off = int(cy - crop_h // 2)
        x_off = max(0, min(x_off, src_w - crop_w))
        y_off = max(0, min(y_off, src_h - crop_h))

        # Crop and resize
        cropped = frame[y_off:y_off + crop_h, x_off:x_off + crop_w]
        resized = cv2.resize(cropped, (target_width, target_height), interpolation=cv2.INTER_LANCZOS4)
        writer.write(resized)

    cap.release()
    writer.release()

    # Merge with original audio
    cmd = [
        "ffmpeg", "-y",
        "-i", temp_video,
        "-i", input_path,
        "-map", "0:v",
        "-map", "1:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    Path(temp_video).unlink(missing_ok=True)

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg merge failed: {result.stderr[:200]}")

    duration = _get_video_duration(output_path)

    return {
        "output_path": output_path,
        "frames_processed": total_frames,
        "faces_detected": faces_detected,
        "duration": duration,
    }


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
