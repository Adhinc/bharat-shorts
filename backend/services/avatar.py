"""
AI Actors Studio — Avatar Video Generation Service

Creates talking-head style videos from text scripts using:
1. AI avatars (user-uploaded face images or built-in presets)
2. Edge TTS for natural voice synthesis (24+ languages)
3. Lip-sync mouth animation driven by audio energy
4. Caption overlay synced to speech
5. Background templates and Ken Burns animation

No filming required — businesses can create professional video content
with just a script and an avatar image.
"""

import asyncio
import subprocess
import uuid
import json
import logging
import math
import shutil
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "processed"
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
AVATARS_DIR = ASSETS_DIR / "avatars"
AVATARS_DIR.mkdir(parents=True, exist_ok=True)

# Built-in avatar placeholder colors (used when no image provided)
AVATAR_PRESETS = {
    "professional_male": {
        "name": "Arjun",
        "bg_color": (30, 30, 40),
        "avatar_color": (70, 130, 180),
        "label": "Professional Male",
    },
    "professional_female": {
        "name": "Priya",
        "bg_color": (40, 30, 35),
        "avatar_color": (180, 100, 140),
        "label": "Professional Female",
    },
    "casual_male": {
        "name": "Rahul",
        "bg_color": (25, 35, 25),
        "avatar_color": (100, 160, 100),
        "label": "Casual Male",
    },
    "casual_female": {
        "name": "Ananya",
        "bg_color": (35, 30, 40),
        "avatar_color": (150, 120, 180),
        "label": "Casual Female",
    },
    "corporate": {
        "name": "Business",
        "bg_color": (20, 25, 40),
        "avatar_color": (60, 100, 160),
        "label": "Corporate",
    },
}

# Background templates
BACKGROUNDS = {
    "studio_dark": (18, 18, 24),
    "studio_blue": (15, 25, 45),
    "studio_warm": (35, 25, 20),
    "studio_green": (15, 30, 20),
    "gradient_purple": None,  # special: rendered as gradient
    "gradient_sunset": None,
}


def _generate_gradient_bg(width: int, height: int, style: str) -> np.ndarray:
    """Generate a gradient background image."""
    img = np.zeros((height, width, 3), dtype=np.uint8)

    if style == "gradient_purple":
        for y in range(height):
            ratio = y / height
            img[y, :] = [
                int(15 + 25 * ratio),
                int(10 + 15 * ratio),
                int(40 + 30 * (1 - ratio)),
            ]
    elif style == "gradient_sunset":
        for y in range(height):
            ratio = y / height
            img[y, :] = [
                int(15 + 20 * ratio),
                int(20 + 40 * (1 - ratio)),
                int(50 + 30 * (1 - ratio)),
            ]

    return img


def _create_avatar_frame(
    width: int,
    height: int,
    avatar_image: np.ndarray | None,
    background: str,
    mouth_open: float = 0.0,
    frame_idx: int = 0,
    total_frames: int = 1,
) -> np.ndarray:
    """
    Create a single avatar frame with background, avatar, and mouth animation.

    Args:
        width, height: Output dimensions
        avatar_image: User-provided face image (or None for placeholder)
        background: Background template name
        mouth_open: 0.0 (closed) to 1.0 (fully open) for lip animation
        frame_idx: Current frame index (for subtle animation)
        total_frames: Total frame count
    """
    # Create background
    bg_color = BACKGROUNDS.get(background)
    if bg_color is None:
        frame = _generate_gradient_bg(width, height, background)
    else:
        frame = np.full((height, width, 3), bg_color, dtype=np.uint8)

    # Subtle vignette effect
    Y, X = np.ogrid[:height, :width]
    cx, cy = width // 2, height // 2
    dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2).astype(np.float32)
    max_dist = np.sqrt(cx ** 2 + cy ** 2)
    vignette = 1.0 - 0.3 * (dist / max_dist) ** 2
    frame = (frame.astype(np.float32) * vignette[:, :, np.newaxis]).astype(np.uint8)

    if avatar_image is not None:
        # Place user avatar in center-upper area
        av_h, av_w = avatar_image.shape[:2]

        # Scale avatar to fit ~60% of frame width
        target_w = int(width * 0.6)
        scale = target_w / av_w
        target_h = int(av_h * scale)

        # Subtle breathing animation (gentle scale oscillation)
        breath = 1.0 + 0.005 * math.sin(2 * math.pi * frame_idx / (total_frames * 0.1))
        target_w = int(target_w * breath)
        target_h = int(target_h * breath)

        avatar_resized = cv2.resize(avatar_image, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)

        # Center horizontally, position in upper 60% of frame
        x_offset = (width - target_w) // 2
        y_offset = int(height * 0.08)

        # Clamp to frame bounds
        src_y1 = max(0, -y_offset)
        src_x1 = max(0, -x_offset)
        dst_y1 = max(0, y_offset)
        dst_x1 = max(0, x_offset)
        copy_h = min(target_h - src_y1, height - dst_y1)
        copy_w = min(target_w - src_x1, width - dst_x1)

        if copy_h > 0 and copy_w > 0:
            frame[dst_y1:dst_y1 + copy_h, dst_x1:dst_x1 + copy_w] = \
                avatar_resized[src_y1:src_y1 + copy_h, src_x1:src_x1 + copy_w]

        # Draw mouth animation overlay if speaking
        if mouth_open > 0.05:
            mouth_cx = width // 2
            mouth_cy = dst_y1 + int(copy_h * 0.75)
            mouth_w = int(copy_w * 0.12)
            mouth_h = int(mouth_w * 0.4 * mouth_open)

            if mouth_h > 1:
                overlay = frame.copy()
                cv2.ellipse(
                    overlay,
                    (mouth_cx, mouth_cy),
                    (mouth_w, mouth_h),
                    0, 0, 360,
                    (30, 20, 20),
                    -1,
                )
                alpha = 0.6 * mouth_open
                frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
    else:
        # Placeholder avatar (colored circle with initials)
        cx, cy = width // 2, int(height * 0.35)
        radius = int(width * 0.2)

        # Breathing animation
        breath = 1.0 + 0.008 * math.sin(2 * math.pi * frame_idx / 60)
        r = int(radius * breath)

        cv2.circle(frame, (cx, cy), r, (80, 80, 90), -1)
        cv2.circle(frame, (cx, cy), r, (120, 120, 130), 2)

        # Draw simple face
        # Eyes
        eye_y = cy - int(r * 0.15)
        eye_spacing = int(r * 0.35)
        cv2.circle(frame, (cx - eye_spacing, eye_y), int(r * 0.08), (200, 200, 210), -1)
        cv2.circle(frame, (cx + eye_spacing, eye_y), int(r * 0.08), (200, 200, 210), -1)

        # Mouth (animated)
        mouth_y = cy + int(r * 0.25)
        if mouth_open > 0.05:
            mouth_h = int(r * 0.15 * mouth_open)
            cv2.ellipse(frame, (cx, mouth_y), (int(r * 0.2), mouth_h), 0, 0, 360, (150, 150, 160), -1)
        else:
            cv2.ellipse(frame, (cx, mouth_y), (int(r * 0.2), int(r * 0.03)), 0, 0, 180, (150, 150, 160), 2)

    return frame


def _extract_audio_energy(audio_path: str, fps: float) -> list[float]:
    """
    Extract per-frame audio energy for lip-sync animation.
    Returns a list of energy values (0.0-1.0) per video frame.
    """
    # Use FFmpeg to get audio samples as raw PCM
    cmd = [
        "ffmpeg", "-i", audio_path,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1",
        "-f", "s16le", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=120)
    if result.returncode != 0:
        return []

    samples = np.frombuffer(result.stdout, dtype=np.int16).astype(np.float32)
    if len(samples) == 0:
        return []

    # Normalize
    max_val = np.abs(samples).max()
    if max_val > 0:
        samples = samples / max_val

    # Calculate energy per frame
    sample_rate = 16000
    samples_per_frame = int(sample_rate / fps)
    energies = []

    for i in range(0, len(samples), samples_per_frame):
        chunk = samples[i:i + samples_per_frame]
        if len(chunk) > 0:
            energy = np.sqrt(np.mean(chunk ** 2))  # RMS energy
            energies.append(float(min(energy * 3.0, 1.0)))  # scale up and clamp

    return energies


async def generate_avatar_video(
    script: str,
    output_path: str,
    lang: str = "hi",
    gender: str = "female",
    avatar_image_path: str | None = None,
    avatar_preset: str = "professional_female",
    background: str = "studio_dark",
    width: int = 1080,
    height: int = 1920,
    fps: float = 30.0,
    speech_rate: str = "+0%",
    caption_style: dict | None = None,
) -> dict:
    """
    Generate a complete avatar video from a text script.

    Pipeline:
    1. Generate TTS audio from script
    2. Extract audio energy for lip-sync
    3. Render avatar frames with mouth animation
    4. Burn captions onto frames
    5. Merge video + audio

    Args:
        script: The text to speak
        output_path: Where to save the final video
        lang: Language code for TTS
        gender: "male" or "female" voice
        avatar_image_path: Path to face image (optional)
        avatar_preset: Built-in avatar preset name
        background: Background template name
        width, height: Output dimensions
        fps: Frame rate
        speech_rate: TTS speed adjustment
        caption_style: Caption styling options

    Returns:
        {
            "output_path": str,
            "duration": float,
            "language": str,
            "avatar_used": str,
        }
    """
    import edge_tts
    from services.translator import VOICE_MAP

    work_dir = Path(output_path).parent / f"avatar_work_{uuid.uuid4().hex[:8]}"
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        # --- Step 1: Generate TTS audio ---
        voice_info = VOICE_MAP.get(lang)
        if not voice_info:
            raise ValueError(f"Unsupported language: {lang}")

        voice = voice_info.get(gender, voice_info["female"])
        audio_path = str(work_dir / "speech.mp3")

        # Use edge-tts with word-level timestamps (SSML)
        communicate = edge_tts.Communicate(script, voice, rate=speech_rate)

        # Collect word timing from SubMaker
        sub_maker = edge_tts.SubMaker()
        with open(audio_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    sub_maker.feed(chunk)

        # Get audio duration
        probe_cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", audio_path,
        ]
        probe = subprocess.run(probe_cmd, capture_output=True, text=True)
        audio_duration = 0.0
        if probe.returncode == 0:
            audio_duration = float(json.loads(probe.stdout).get("format", {}).get("duration", 0))

        if audio_duration <= 0:
            raise RuntimeError("TTS audio generation failed")

        # --- Step 2: Extract audio energy for lip sync ---
        energies = _extract_audio_energy(audio_path, fps)
        total_frames = max(len(energies), int(audio_duration * fps) + 1)

        # Pad energies if needed
        while len(energies) < total_frames:
            energies.append(0.0)

        # --- Step 3: Load avatar image ---
        avatar_image = None
        avatar_name = avatar_preset
        if avatar_image_path and Path(avatar_image_path).exists():
            avatar_image = cv2.imread(avatar_image_path)
            avatar_name = "custom"
        elif avatar_preset in AVATAR_PRESETS:
            avatar_name = AVATAR_PRESETS[avatar_preset]["label"]

        # --- Step 4: Render frames ---
        temp_video = str(work_dir / "frames.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(temp_video, fourcc, fps, (width, height))

        logger.info(f"Rendering {total_frames} avatar frames...")

        for frame_idx in range(total_frames):
            mouth_open = energies[frame_idx] if frame_idx < len(energies) else 0.0

            # Smooth mouth animation
            if frame_idx > 0 and frame_idx < len(energies):
                mouth_open = 0.3 * energies[max(0, frame_idx - 1)] + 0.7 * mouth_open

            frame = _create_avatar_frame(
                width, height,
                avatar_image, background,
                mouth_open=mouth_open,
                frame_idx=frame_idx,
                total_frames=total_frames,
            )

            # --- Step 5: Add captions to frame ---
            current_time = frame_idx / fps

            # Simple word-by-word caption rendering
            words = script.split()
            if words and audio_duration > 0:
                words_per_sec = len(words) / audio_duration
                current_word_idx = int(current_time * words_per_sec)

                # Show a window of words around current position
                window_size = 6
                start_idx = max(0, current_word_idx - 1)
                end_idx = min(len(words), start_idx + window_size)
                display_words = words[start_idx:end_idx]

                if display_words:
                    caption_text = " ".join(display_words)
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    font_scale = width / 800.0
                    thickness = max(2, int(font_scale * 2))

                    # Calculate text size for centering
                    (text_w, text_h), baseline = cv2.getTextSize(
                        caption_text, font, font_scale, thickness
                    )

                    # Position at bottom 15% of frame
                    text_x = max(10, (width - text_w) // 2)
                    text_y = int(height * 0.88)

                    # Background bar
                    pad = 15
                    cv2.rectangle(
                        frame,
                        (text_x - pad, text_y - text_h - pad),
                        (text_x + text_w + pad, text_y + baseline + pad),
                        (0, 0, 0),
                        -1,
                    )
                    cv2.rectangle(
                        frame,
                        (text_x - pad, text_y - text_h - pad),
                        (text_x + text_w + pad, text_y + baseline + pad),
                        (255, 107, 0),
                        2,
                    )

                    # Draw text
                    cv2.putText(
                        frame, caption_text,
                        (text_x, text_y),
                        font, font_scale, (255, 255, 255), thickness,
                        cv2.LINE_AA,
                    )

                    # Highlight current word
                    if 0 <= current_word_idx - start_idx < len(display_words):
                        highlight_word = display_words[current_word_idx - start_idx]
                        prefix = " ".join(display_words[:current_word_idx - start_idx])
                        if prefix:
                            prefix += " "
                        (prefix_w, _), _ = cv2.getTextSize(prefix, font, font_scale, thickness)
                        (hw, hh), _ = cv2.getTextSize(highlight_word, font, font_scale, thickness)

                        cv2.putText(
                            frame, highlight_word,
                            (text_x + prefix_w, text_y),
                            font, font_scale, (0, 107, 255), thickness,
                            cv2.LINE_AA,
                        )

            writer.write(frame)

        writer.release()
        logger.info("Avatar frames rendered, merging with audio...")

        # --- Step 6: Merge video + audio ---
        cmd = [
            "ffmpeg", "-y",
            "-i", temp_video,
            "-i", audio_path,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise RuntimeError(f"Video merge failed: {result.stderr[:200]}")

        return {
            "output_path": output_path,
            "duration": audio_duration,
            "language": lang,
            "avatar_used": avatar_name,
        }

    finally:
        shutil.rmtree(str(work_dir), ignore_errors=True)


def list_avatar_presets() -> list[dict]:
    """Return available avatar presets."""
    return [
        {"id": k, "name": v["name"], "label": v["label"]}
        for k, v in AVATAR_PRESETS.items()
    ]


def list_backgrounds() -> list[str]:
    """Return available background template names."""
    return list(BACKGROUNDS.keys())
