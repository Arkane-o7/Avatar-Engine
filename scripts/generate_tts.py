from __future__ import annotations

import argparse
import math
import struct
import wave
from pathlib import Path

from utils import load_json


def generate_with_kokoro(job: dict, output_wav: Path) -> bool:
    """Placeholder integration point for Kokoro or another local TTS engine."""
    try:
        import kokoro  # type: ignore  # noqa: F401
    except ImportError:
        return False

    print("[tts] Kokoro is importable, but the MVP wrapper has no voice pipeline wired yet.")
    print("[tts] Falling back to a local placeholder WAV.")
    return False


def estimate_duration_seconds(script: str) -> float:
    words = max(1, len(script.split()))
    return max(2.0, min(30.0, words / 2.6))


def generate_placeholder_wav(output_wav: Path, duration_seconds: float, sample_rate: int) -> None:
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    amplitude = 1200
    beep_frequency = 440.0
    total_samples = int(duration_seconds * sample_rate)

    with wave.open(str(output_wav), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for index in range(total_samples):
            second = index / sample_rate
            in_beep = int(second * 2) % 2 == 0 and second < duration_seconds - 0.25
            sample = 0
            if in_beep:
                sample = int(amplitude * math.sin(2 * math.pi * beep_frequency * second))
            wav.writeframesraw(struct.pack("<h", sample))


def generate_tts(job_json_path: Path, output_wav: Path, test_mode: bool = False) -> Path:
    job = load_json(job_json_path)
    voice = job.get("voice", {})
    sample_rate = int(voice.get("sample_rate", 24000))
    script = str(job.get("script", ""))

    print(f"[tts] Generating audio for job: {job.get('job_id', '<unknown>')}")
    if not test_mode and generate_with_kokoro(job, output_wav):
        print(f"[tts] Wrote Kokoro audio: {output_wav}")
        return output_wav

    if test_mode:
        print("[tts] Test mode enabled; using placeholder beep WAV.")
    else:
        print("[tts] WARNING: Kokoro is unavailable or not configured; using placeholder WAV.")

    generate_placeholder_wav(output_wav, estimate_duration_seconds(script), sample_rate)
    print(f"[tts] Wrote placeholder audio: {output_wav}")
    return output_wav


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate local TTS audio for a desk-avatar job.")
    parser.add_argument("job_json", type=Path)
    parser.add_argument("output_wav", type=Path)
    parser.add_argument("--test-mode", action="store_true")
    args = parser.parse_args()
    generate_tts(args.job_json, args.output_wav, args.test_mode)


if __name__ == "__main__":
    main()
