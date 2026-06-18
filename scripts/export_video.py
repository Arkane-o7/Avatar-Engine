from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from utils import load_config, resolve_tool


def frame_pattern(render_dir: Path) -> str:
    return str(render_dir / "frame_%05d.png")


def export_video(
    render_dir: Path,
    audio_wav: Path,
    output_mp4: Path,
    fps: int,
    config_path: Path,
    test_mode: bool = False,
    output_resolution: list[int] | tuple[int, int] | None = None,
) -> Path | None:
    frames = sorted(render_dir.glob("frame_*.png"))
    if not frames:
        message = f"No rendered frames found in {render_dir}"
        if test_mode:
            print(f"[export] WARNING: {message}; skipping video export.")
            return None
        raise FileNotFoundError(message)
    if not audio_wav.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_wav}")

    config = load_config(config_path)
    ffmpeg_name = str(config.get("tools", {}).get("ffmpeg", "ffmpeg"))
    ffmpeg_path = resolve_tool(ffmpeg_name)
    if not ffmpeg_path:
        message = f"FFmpeg not found at '{ffmpeg_name}'"
        if test_mode:
            print(f"[export] WARNING: {message}; skipping MP4 export in test mode.")
            return None
        raise FileNotFoundError(message)

    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(ffmpeg_path),
        "-hide_banner",
        "-loglevel",
        "warning",
        "-y",
        "-framerate",
        str(fps),
        "-i",
        frame_pattern(render_dir),
        "-i",
        str(audio_wav),
    ]
    if output_resolution is not None:
        width, height = [int(value) for value in output_resolution]
        video_filter = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease:eval=frame,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black:eval=frame,"
            "setsar=1"
        )
        command.extend(["-vf", video_filter])
    command.extend(
        [
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(output_mp4),
        ]
    )
    print(f"[export] Running FFmpeg export: {output_mp4}")
    subprocess.run(command, check=True)
    print(f"[export] Final video: {output_mp4}")
    return output_mp4


def main() -> None:
    parser = argparse.ArgumentParser(description="Combine rendered frames and audio into an MP4.")
    parser.add_argument("render_dir", type=Path)
    parser.add_argument("audio_wav", type=Path)
    parser.add_argument("output_mp4", type=Path)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--config", type=Path, default=Path("config/default.yaml"))
    parser.add_argument("--test-mode", action="store_true")
    args = parser.parse_args()
    export_video(args.render_dir, args.audio_wav, args.output_mp4, args.fps, args.config, args.test_mode)


if __name__ == "__main__":
    main()
