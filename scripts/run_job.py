from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from export_video import export_video
from generate_lipsync import generate_lipsync, wav_duration_seconds
from generate_tts import generate_tts
from utils import create_placeholder_frames, load_config, load_json, resolve_project_path, resolve_tool


REQUIRED_JOB_FIELDS = {
    "job_id",
    "script",
    "character",
    "face_mode",
    "fps",
    "resolution",
    "voice",
    "camera_cuts",
    "performance_beats",
    "output_path",
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def validate_job(job: dict[str, Any], job_path: Path, root: Path) -> None:
    missing = sorted(REQUIRED_JOB_FIELDS - set(job))
    if missing:
        raise ValueError(f"Job file {job_path} is missing required field(s): {', '.join(missing)}")
    if not isinstance(job["resolution"], list) or len(job["resolution"]) != 2:
        raise ValueError("Job field 'resolution' must be a two-item list like [1920, 1080].")
    character_dir = root / "assets" / "characters" / str(job["character"])
    if not character_dir.exists():
        raise FileNotFoundError(f"Character folder not found: {character_dir}")


def create_job_folders(root: Path, job_id: str) -> tuple[Path, Path, Path]:
    temp_dir = root / "assets" / "temp" / job_id
    render_dir = root / "assets" / "renders" / job_id
    output_dir = root / "assets" / "output"
    for folder in (temp_dir, render_dir, output_dir):
        folder.mkdir(parents=True, exist_ok=True)
    return temp_dir, render_dir, output_dir


def ensure_inside(path: Path, allowed_parent: Path) -> None:
    resolved_path = path.resolve()
    resolved_parent = allowed_parent.resolve()
    if resolved_path != resolved_parent and resolved_parent not in resolved_path.parents:
        raise ValueError(f"Refusing to clean path outside generated folder: {path}")


def clean_generated_outputs(root: Path, temp_dir: Path, render_dir: Path, output_path: Path) -> None:
    generated_roots = {
        "temp": root / "assets" / "temp",
        "renders": root / "assets" / "renders",
        "output": root / "assets" / "output",
    }

    for folder, allowed_parent in ((temp_dir, generated_roots["temp"]), (render_dir, generated_roots["renders"])):
        ensure_inside(folder, allowed_parent)
        if folder.exists():
            print(f"[clean] Removing generated folder: {folder}")
            shutil.rmtree(folder)
        folder.mkdir(parents=True, exist_ok=True)

    ensure_inside(output_path, generated_roots["output"])
    if output_path.exists():
        print(f"[clean] Removing generated output file: {output_path}")
        output_path.unlink()


def run_blender(
    root: Path,
    job_path: Path,
    job: dict[str, Any],
    config: dict[str, Any],
    render_dir: Path,
    mouth_path: Path,
    test_mode: bool,
) -> None:
    blender_name = str(config.get("tools", {}).get("blender", "blender"))
    blender_path = resolve_tool(blender_name)
    template_path = root / "blender" / "avatar_template.blend"

    if not blender_path:
        message = f"Blender not found at '{blender_name}'"
        if test_mode:
            print(f"[blender] WARNING: {message}; creating placeholder PNG frames.")
            make_placeholder_render(job, render_dir, config, mouth_path)
            return
        raise FileNotFoundError(message)

    if not template_path.exists():
        message = f"Template blend file not found: {template_path}"
        if test_mode:
            print(f"[blender] WARNING: {message}; creating placeholder PNG frames.")
            make_placeholder_render(job, render_dir, config, mouth_path)
            return
        raise FileNotFoundError(message)

    driver_path = root / "blender" / "blender_driver.py"
    command = [
        str(blender_path),
        "-b",
        str(template_path),
        "--python",
        str(driver_path),
        "--",
        str(job_path),
    ]
    print(f"[blender] Running Blender in background mode: {blender_path}")
    subprocess.run(command, check=True)


def make_placeholder_render(job: dict[str, Any], render_dir: Path, config: dict[str, Any], mouth_path: Path) -> None:
    render_config = config.get("render", {})
    fps = int(job.get("fps", render_config.get("fps", 30)))
    resolution = [int(value) for value in job.get("resolution", render_config.get("resolution", [1920, 1080]))]
    frame_count = int(render_config.get("placeholder_frame_count", fps * 3))
    if mouth_path.exists():
        mouth_data = load_json(mouth_path)
        duration = float(mouth_data.get("metadata", {}).get("duration", 0.0))
        if duration > 0:
            frame_count = max(frame_count, int(duration * fps))
    create_placeholder_frames(render_dir, frame_count, resolution)
    print(f"[blender] Wrote {frame_count} placeholder frames to: {render_dir}")


def run_pipeline(
    job_path: Path,
    config_path: Path,
    test_mode: bool = False,
    skip_tts: bool = False,
    skip_lipsync: bool = False,
    skip_render: bool = False,
    skip_export: bool = False,
    keep_temp: bool = False,
    clean: bool = False,
) -> Path | None:
    root = project_root()
    job_path = job_path if job_path.is_absolute() else root / job_path
    config_path = config_path if config_path.is_absolute() else root / config_path

    print(f"[job] Loading config: {config_path}")
    config = load_config(config_path)
    test_mode = test_mode or bool(config.get("test_mode", False))

    print(f"[job] Loading job: {job_path}")
    job = load_json(job_path)
    validate_job(job, job_path, root)

    job_id = str(job["job_id"])
    temp_dir, render_dir, _ = create_job_folders(root, job_id)
    output_path = resolve_project_path(root, str(job["output_path"]))
    audio_path = temp_dir / "audio.wav"
    mouth_path = temp_dir / "mouth_cues.json"

    if clean:
        clean_generated_outputs(root, temp_dir, render_dir, output_path)

    print(f"[job] Starting '{job_id}'")
    print(f"[job] Test mode: {'on' if test_mode else 'off'}")
    print(
        "[job] Skips: "
        f"tts={'on' if skip_tts else 'off'}, "
        f"lipsync={'on' if skip_lipsync else 'off'}, "
        f"render={'on' if skip_render else 'off'}, "
        f"export={'on' if skip_export else 'off'}"
    )
    if keep_temp:
        print("[job] Keep temp: on")
    print(f"[job] Temp: {temp_dir}")
    print(f"[job] Renders: {render_dir}")
    print(f"[job] Output: {output_path}")

    if skip_tts:
        if not audio_path.exists():
            raise FileNotFoundError(f"--skip-tts requested but audio file is missing: {audio_path}")
        print(f"[tts] Skipping TTS; using existing audio: {audio_path}")
    else:
        generate_tts(job_path, audio_path, test_mode=test_mode)

    if skip_lipsync:
        if not mouth_path.exists():
            raise FileNotFoundError(f"--skip-lipsync requested but mouth cue file is missing: {mouth_path}")
        print(f"[lipsync] Skipping lip sync; using existing cues: {mouth_path}")
    else:
        generate_lipsync(audio_path, mouth_path, config_path=config_path, test_mode=test_mode)

    if skip_render:
        frames = sorted(render_dir.glob("frame_*.png"))
        if frames:
            print(f"[blender] Skipping render; using {len(frames)} existing frame(s): {render_dir}")
        else:
            print(f"[blender] WARNING: --skip-render requested but no frames exist in: {render_dir}")
    else:
        run_blender(root, job_path, job, config, render_dir, mouth_path, test_mode=test_mode)

    fps = int(job.get("fps", 30))
    try:
        duration = wav_duration_seconds(audio_path)
        print(f"[job] Audio duration: {duration:.2f}s at {fps} fps")
    except Exception as exc:
        print(f"[job] WARNING: Could not read audio duration: {exc}")

    if skip_export:
        print("[export] Skipping MP4 export.")
        print("[job] Done: export skipped by request.")
        return None

    exported = export_video(
        render_dir=render_dir,
        audio_wav=audio_path,
        output_mp4=output_path,
        fps=fps,
        config_path=config_path,
        test_mode=test_mode,
    )
    if exported:
        print(f"[job] Done: {exported}")
    else:
        print("[job] Done with warnings: MP4 export was skipped.")
    return exported


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a desk-avatar video generation job.")
    parser.add_argument("job_json", nargs="?", type=Path, default=Path("jobs/sample_job.json"))
    parser.add_argument("--config", type=Path, default=Path("config/default.yaml"))
    parser.add_argument("--test-mode", action="store_true")
    parser.add_argument("--skip-tts", action="store_true", help="Reuse assets/temp/<job_id>/audio.wav.")
    parser.add_argument("--skip-lipsync", action="store_true", help="Reuse assets/temp/<job_id>/mouth_cues.json.")
    parser.add_argument("--skip-render", action="store_true", help="Reuse existing assets/renders/<job_id>/frame_*.png.")
    parser.add_argument("--skip-export", action="store_true", help="Run generation steps but do not create an MP4.")
    parser.add_argument("--keep-temp", action="store_true", help="Explicitly keep generated temp files. This is the default.")
    parser.add_argument("--clean", action="store_true", help="Clean only this job's temp, render frames, and MP4 before running.")
    args = parser.parse_args()

    try:
        run_pipeline(
            args.job_json,
            args.config,
            test_mode=args.test_mode,
            skip_tts=args.skip_tts,
            skip_lipsync=args.skip_lipsync,
            skip_render=args.skip_render,
            skip_export=args.skip_export,
            keep_temp=args.keep_temp,
            clean=args.clean,
        )
    except subprocess.CalledProcessError as exc:
        print(f"[error] External command failed with exit code {exc.returncode}: {exc.cmd}", file=sys.stderr)
        raise SystemExit(exc.returncode)
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
