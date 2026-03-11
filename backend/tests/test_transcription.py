"""Quick smoke test for transcription service.

Usage:
    python tests/test_transcription.py <path_to_video>

Tests:
    1. Audio extraction via FFmpeg
    2. Faster-Whisper transcription with word timestamps
    3. SRT generation
    4. Hinglish handling (auto-detect)
"""
import sys
import json
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.transcription import transcribe, generate_srt


def main():
    if len(sys.argv) < 2:
        print("Usage: python tests/test_transcription.py <video_path>")
        print("\nRunning dry test (model loading only)...")

        # Just verify the model can load
        from services.transcription import get_model
        model = get_model("tiny")  # Use tiny for quick test
        print("Model loaded successfully!")
        return

    video_path = sys.argv[1]
    print(f"Transcribing: {video_path}")
    print("-" * 50)

    result = transcribe(video_path, model_size="base")

    print(f"Language: {result['language']} (confidence: {result['language_probability']})")
    print(f"Segments: {len(result['segments'])}")
    print()

    for seg in result["segments"]:
        word_count = len(seg["words"])
        print(f"[{seg['start']:.1f}s - {seg['end']:.1f}s] ({word_count} words)")
        print(f"  {seg['text']}")
        print()

    # Generate SRT
    srt = generate_srt(result["segments"])
    srt_path = Path(video_path).stem + ".srt"
    Path(srt_path).write_text(srt)
    print(f"SRT saved to: {srt_path}")

    # Save full JSON
    json_path = Path(video_path).stem + "_transcript.json"
    Path(json_path).write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"JSON saved to: {json_path}")


if __name__ == "__main__":
    main()
