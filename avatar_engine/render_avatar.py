"""CLI entrypoint: python -m avatar_engine.render_avatar

Usage examples
--------------
# TalkingHead renderer (explicit):
python -m avatar_engine.render_avatar --job jobs/talkinghead_ep01.json --renderer talkinghead

# Blender renderer (explicit):
python -m avatar_engine.render_avatar --job jobs/sample_job.json --renderer blender

# Use renderer from job JSON or AVATAR_ENGINE_RENDERER env var:
python -m avatar_engine.render_avatar --job jobs/talkinghead_ep01.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Allow imports from scripts/ and the repo root when run directly
_here = Path(__file__).resolve()
_repo_root = _here.parents[1]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from avatar_engine.renderer_base import AvatarJob
from avatar_engine.renderer_factory import (
    allow_renderer_fallback,
    get_renderer,
    resolve_renderer_name,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m avatar_engine.render_avatar",
        description="Render a talking-avatar clip using the TalkingHead or Blender renderer.",
    )
    parser.add_argument(
        "--job", required=True, help="Path to the avatar job JSON file."
    )
    parser.add_argument(
        "--renderer",
        choices=["talkinghead", "rocketbox", "blender"],
        default=None,
        help="Override the renderer (default: from job or AVATAR_ENGINE_RENDERER env var).",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to config YAML (default: config/default.yaml).",
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Run in test mode (relaxed file checks for CI).",
    )

    args = parser.parse_args(argv)

    job_path = Path(args.job)
    if not job_path.is_absolute():
        job_path = _repo_root / job_path
    if not job_path.exists():
        print(f"[render_avatar] ERROR: Job file not found: {job_path}", file=sys.stderr)
        return 1

    config_path = (
        Path(args.config) if args.config else _repo_root / "config" / "default.yaml"
    )

    with job_path.open("r", encoding="utf-8") as fh:
        raw_job = json.load(fh)

    job = AvatarJob(raw=raw_job, job_path=job_path)

    # Determine which renderer to use (may raise ValueError for unknown names)
    try:
        resolved_renderer = resolve_renderer_name(job, override=args.renderer)
    except ValueError as exc:
        print(f"[render_avatar] ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"[render_avatar] Job:      {job_path}")
    print(f"[render_avatar] Renderer: {resolved_renderer}")
    print(f"[render_avatar] Episode:  {job.episode_id}  Story: {job.story_id}")

    renderer = get_renderer(job, override=args.renderer, config_path=config_path)

    result = renderer.render(job)

    # Print summary
    if result.status == "pass":
        print(f"[render_avatar] DONE  — output: {result.output_path}")
        print(
            f"[render_avatar] Wall time: {result.wall_time_seconds:.1f}s  "
            f"Realtime factor: {result.realtime_factor:.2f}x"
        )
        if result.warnings:
            for w in result.warnings:
                print(f"[render_avatar] WARNING: {w}")
        return 0
    else:
        print(f"[render_avatar] FAILED — {result.error}", file=sys.stderr)

        if allow_renderer_fallback() and resolved_renderer != "blender":
            print(
                "[render_avatar] AVATAR_ENGINE_ALLOW_RENDERER_FALLBACK=1 is set; "
                "retrying with blender renderer.",
                file=sys.stderr,
            )
            from avatar_engine.renderer_factory import get_renderer as _get

            blender_renderer = _get(job, override="blender", config_path=config_path)
            fallback_result = blender_renderer.render(job)
            if fallback_result.status == "pass":
                print(
                    f"[render_avatar] Blender fallback succeeded: {fallback_result.output_path}"
                )
                return 0
            print(
                f"[render_avatar] Blender fallback also failed: {fallback_result.error}",
                file=sys.stderr,
            )

        return 1


if __name__ == "__main__":
    sys.exit(main())
