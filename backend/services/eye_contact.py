"""
AI Eye Contact Correction Service

Uses MediaPipe Face Mesh (478 landmarks including iris) to detect gaze direction,
then shifts the iris region toward the camera center to simulate direct eye contact.

Pipeline:
1. Detect face landmarks with iris tracking per frame
2. Calculate gaze offset (iris center vs eye center)
3. Warp iris region toward center using affine transform
4. Apply correction frame-by-frame and re-encode video
"""

import subprocess
import logging
import json
import uuid
import shutil
from pathlib import Path

import cv2
import numpy as np
import mediapipe as mp

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "processed"

# MediaPipe Face Mesh landmark indices for eyes and iris
# Left eye (from viewer's perspective = subject's right eye)
LEFT_EYE_INDICES = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
# Right eye
RIGHT_EYE_INDICES = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]

# Iris landmarks (indices 468-477 when refine_landmarks=True)
LEFT_IRIS_INDICES = [468, 469, 470, 471, 472]   # center + 4 points
RIGHT_IRIS_INDICES = [473, 474, 475, 476, 477]  # center + 4 points

# Eye corner landmarks for gaze reference
LEFT_EYE_INNER = 133
LEFT_EYE_OUTER = 33
RIGHT_EYE_INNER = 362
RIGHT_EYE_OUTER = 263


def _create_landmarker():
    """Create a MediaPipe FaceLandmarker instance."""
    model_path = MODELS_DIR / "face_landmarker.task"
    if not model_path.exists():
        raise FileNotFoundError(
            f"Face landmarker model not found at {model_path}. "
            "Download from: https://storage.googleapis.com/mediapipe-models/"
            "face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
        )

    base_options = mp.tasks.BaseOptions(model_asset_path=str(model_path))
    options = mp.tasks.vision.FaceLandmarkerOptions(
        base_options=base_options,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
        num_faces=1,
    )
    return mp.tasks.vision.FaceLandmarker.create_from_options(options)


def _get_eye_center(landmarks: list, indices: list, w: int, h: int) -> tuple[float, float]:
    """Calculate the center point of an eye region from landmarks."""
    points = [(landmarks[i].x * w, landmarks[i].y * h) for i in indices]
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    return cx, cy


def _get_iris_center(landmarks: list, iris_indices: list, w: int, h: int) -> tuple[float, float]:
    """Get iris center from iris landmarks."""
    # First index is the center point
    center_idx = iris_indices[0]
    return landmarks[center_idx].x * w, landmarks[center_idx].y * h


def _get_iris_radius(landmarks: list, iris_indices: list, w: int, h: int) -> float:
    """Estimate iris radius from the 4 surrounding iris landmarks."""
    cx, cy = _get_iris_center(landmarks, iris_indices, w, h)
    radii = []
    for idx in iris_indices[1:]:
        px, py = landmarks[idx].x * w, landmarks[idx].y * h
        r = np.sqrt((px - cx) ** 2 + (py - cy) ** 2)
        radii.append(r)
    return np.mean(radii) if radii else 5.0


def _get_eye_bbox(landmarks: list, eye_indices: list, w: int, h: int, padding: float = 0.3) -> tuple:
    """Get bounding box around eye region with padding."""
    points = [(landmarks[i].x * w, landmarks[i].y * h) for i in eye_indices]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    # Add padding
    pad_x = (x_max - x_min) * padding
    pad_y = (y_max - y_min) * padding
    x_min = max(0, x_min - pad_x)
    y_min = max(0, y_min - pad_y)
    x_max = min(w, x_max + pad_x)
    y_max = min(h, y_max + pad_y)

    return int(x_min), int(y_min), int(x_max), int(y_max)


def _shift_iris(
    frame: np.ndarray,
    landmarks: list,
    eye_indices: list,
    iris_indices: list,
    correction_strength: float = 0.7,
) -> np.ndarray:
    """
    Shift the iris region toward the eye center to simulate eye contact.

    Uses seamless cloning for natural blending.
    """
    h, w = frame.shape[:2]

    # Get iris and eye centers
    iris_cx, iris_cy = _get_iris_center(landmarks, iris_indices, w, h)
    eye_cx, eye_cy = _get_eye_center(landmarks, eye_indices, w, h)
    iris_radius = _get_iris_radius(landmarks, iris_indices, w, h)

    # Calculate offset (how far iris is from eye center)
    offset_x = eye_cx - iris_cx
    offset_y = eye_cy - iris_cy

    # Apply correction strength
    shift_x = offset_x * correction_strength
    shift_y = offset_y * correction_strength

    # Skip if offset is negligible (already looking at camera)
    if abs(shift_x) < 1 and abs(shift_y) < 1:
        return frame

    # Get the eye bounding box
    x1, y1, x2, y2 = _get_eye_bbox(landmarks, eye_indices, w, h)
    if x2 <= x1 or y2 <= y1:
        return frame

    # Create a circular mask for the iris region
    radius = int(iris_radius * 1.8)  # slightly larger than iris
    mask = np.zeros((y2 - y1, x2 - x1), dtype=np.uint8)
    local_iris_cx = int(iris_cx - x1)
    local_iris_cy = int(iris_cy - y1)
    cv2.circle(mask, (local_iris_cx, local_iris_cy), radius, 255, -1)
    # Feather the edges
    mask = cv2.GaussianBlur(mask, (0, 0), radius * 0.3)

    # Extract eye region
    eye_region = frame[y1:y2, x1:x2].copy()

    # Create shifted version using affine transform
    M = np.float32([[1, 0, shift_x], [0, 1, shift_y]])
    shifted = cv2.warpAffine(eye_region, M, (x2 - x1, y2 - y1), borderMode=cv2.BORDER_REFLECT)

    # Blend shifted iris into original using the mask
    mask_3ch = cv2.merge([mask, mask, mask]).astype(np.float32) / 255.0
    eye_region_f = eye_region.astype(np.float32)
    shifted_f = shifted.astype(np.float32)

    blended = eye_region_f * (1 - mask_3ch) + shifted_f * mask_3ch
    frame[y1:y2, x1:x2] = blended.astype(np.uint8)

    return frame


def correct_eye_contact_frame(
    frame: np.ndarray,
    landmarker,
    correction_strength: float = 0.7,
) -> np.ndarray:
    """
    Correct eye contact for a single frame.

    Args:
        frame: BGR image (OpenCV format)
        landmarker: MediaPipe FaceLandmarker instance
        correction_strength: 0.0 = no correction, 1.0 = full correction

    Returns:
        Corrected frame (BGR)
    """
    # Convert BGR to RGB for MediaPipe
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    result = landmarker.detect(mp_image)

    if not result.face_landmarks:
        return frame

    landmarks = result.face_landmarks[0]

    # Check if we have iris landmarks (need at least 478 landmarks)
    if len(landmarks) < 478:
        return frame

    # Correct left eye (subject's right)
    frame = _shift_iris(
        frame, landmarks,
        LEFT_EYE_INDICES, LEFT_IRIS_INDICES,
        correction_strength,
    )

    # Correct right eye (subject's left)
    frame = _shift_iris(
        frame, landmarks,
        RIGHT_EYE_INDICES, RIGHT_IRIS_INDICES,
        correction_strength,
    )

    return frame


def correct_eye_contact_video(
    input_path: str,
    output_path: str,
    correction_strength: float = 0.7,
    process_every_n: int = 1,
) -> dict:
    """
    Process an entire video for eye contact correction.

    Args:
        input_path: Path to input video
        output_path: Path to save corrected video
        correction_strength: 0.0-1.0, how aggressively to correct gaze
        process_every_n: Process every Nth frame (1=all, 2=every other, etc.)
                         Skipped frames use the previous correction for speed.

    Returns:
        {
            "output_path": str,
            "frames_processed": int,
            "faces_detected": int,
            "duration": float,
        }
    """
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {input_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Write corrected frames to temp file (no audio)
    temp_video = output_path + ".temp.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(temp_video, fourcc, fps, (width, height))

    landmarker = _create_landmarker()

    frames_processed = 0
    faces_detected = 0
    frame_idx = 0

    logger.info(f"Processing {total_frames} frames for eye contact correction...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % process_every_n == 0:
            corrected = correct_eye_contact_frame(
                frame, landmarker, correction_strength
            )

            # Check if face was detected (frame changed)
            if not np.array_equal(frame, corrected):
                faces_detected += 1

            writer.write(corrected)
            frames_processed += 1
        else:
            writer.write(frame)

        frame_idx += 1

        if frame_idx % 100 == 0:
            logger.info(f"Eye contact: processed {frame_idx}/{total_frames} frames")

    cap.release()
    writer.release()
    landmarker.close()

    # Merge corrected video with original audio using FFmpeg
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

    # Cleanup temp file
    Path(temp_video).unlink(missing_ok=True)

    if result.returncode != 0:
        logger.error(f"FFmpeg merge failed: {result.stderr[:500]}")
        raise RuntimeError(f"Video merge failed: {result.stderr[:200]}")

    # Get output duration
    probe_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", output_path,
    ]
    probe = subprocess.run(probe_cmd, capture_output=True, text=True)
    duration = 0.0
    if probe.returncode == 0:
        duration = float(json.loads(probe.stdout).get("format", {}).get("duration", 0))

    return {
        "output_path": output_path,
        "frames_processed": frames_processed,
        "faces_detected": faces_detected,
        "duration": duration,
    }
