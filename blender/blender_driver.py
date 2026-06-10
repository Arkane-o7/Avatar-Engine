from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import bpy  # type: ignore

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from camera_cuts import add_camera_cuts, seconds_to_frames  # noqa: E402
from expression_presets import apply_expression_preset  # noqa: E402
from gesture_loader import apply_placeholder_gesture  # noqa: E402
from mouth_mapping import MOUTH_CUE_INDEX, SHAPE_KEY_MOUTH_MAP, shape_key_for_cue  # noqa: E402


def parse_blender_args() -> Path:
    if "--" not in sys.argv:
        raise SystemExit("Usage in Blender: blender -b template.blend --python blender_driver.py -- jobs/sample_job.json")
    args = sys.argv[sys.argv.index("--") + 1 :]
    if not args:
        raise SystemExit("Missing job JSON path after '--'.")
    path = Path(args[0]).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def find_avatar_mesh() -> Any | None:
    preferred_names = ("Avatar", "Avatar_Mesh", "Head", "Face")
    for name in preferred_names:
        obj = bpy.data.objects.get(name)
        if obj and getattr(obj, "type", "") == "MESH":
            return obj
    for obj in bpy.context.scene.objects:
        if getattr(obj, "type", "") == "MESH" and getattr(getattr(obj, "data", None), "shape_keys", None):
            return obj
    print("[blender] WARNING: No avatar mesh with shape keys found.")
    return None


def add_audio_to_timeline(audio_path: Path) -> None:
    if not audio_path.exists():
        print(f"[blender] WARNING: Audio file missing: {audio_path}")
        return
    scene = bpy.context.scene
    if scene.sequence_editor is None:
        scene.sequence_editor_create()
    try:
        scene.sequence_editor.sequences.new_sound("dialogue", str(audio_path), channel=1, frame_start=1)
        print(f"[blender] Added audio to timeline: {audio_path}")
    except Exception as exc:
        print(f"[blender] WARNING: Could not add audio to timeline: {exc}")


def reset_mouth_shape_keys(mesh_object: Any, frame: int) -> None:
    shape_keys = getattr(getattr(mesh_object, "data", None), "shape_keys", None)
    key_blocks = getattr(shape_keys, "key_blocks", None)
    if key_blocks is None:
        return
    for key_name in SHAPE_KEY_MOUTH_MAP.values():
        key = key_blocks.get(key_name)
        if key is not None:
            key.value = 0.0
            key.keyframe_insert("value", frame=frame)


def apply_3d_mouth_animation(mesh_object: Any, mouth_cues: list[dict], fps: int) -> None:
    shape_keys = getattr(getattr(mesh_object, "data", None), "shape_keys", None)
    key_blocks = getattr(shape_keys, "key_blocks", None)
    if key_blocks is None:
        print(f"[blender] WARNING: Object '{mesh_object.name}' has no shape keys for mouth animation.")
        return

    for cue in mouth_cues:
        frame = seconds_to_frames(float(cue.get("start", 0.0)), fps)
        cue_value = str(cue.get("value", "X")).upper()
        reset_mouth_shape_keys(mesh_object, frame)
        key_name = shape_key_for_cue(cue_value)
        key = key_blocks.get(key_name)
        if key is None:
            print(f"[blender] WARNING: Missing mouth shape key '{key_name}', skipping.")
            continue
        key.value = 1.0
        key.keyframe_insert("value", frame=frame)
    print("[blender] Applied 3D mouth animation.")


def apply_2d_mouth_animation(mouth_cues: list[dict], fps: int) -> None:
    face_surface = bpy.data.objects.get("FACE_Surface")
    if face_surface is None:
        print("[blender] WARNING: FACE_Surface missing; cannot keyframe 2D mouth cues.")
        return

    for cue in mouth_cues:
        frame = seconds_to_frames(float(cue.get("start", 0.0)), fps)
        cue_value = str(cue.get("value", "X")).upper()
        face_surface["mouth_cue"] = MOUTH_CUE_INDEX.get(cue_value, MOUTH_CUE_INDEX["X"])
        face_surface.keyframe_insert(data_path='["mouth_cue"]', frame=frame)
    print("[blender] Applied 2D placeholder mouth cue animation on FACE_Surface.mouth_cue.")


def apply_performance_beats(job: dict[str, Any], fps: int) -> None:
    avatar_mesh = find_avatar_mesh()
    for beat in job.get("performance_beats", []):
        start_frame = seconds_to_frames(float(beat.get("start", 0.0)), fps)
        end_frame = seconds_to_frames(float(beat.get("end", beat.get("start", 0.0))), fps)
        expression = str(beat.get("expression", "calm"))
        gesture = str(beat.get("gesture", "seated_idle"))
        if avatar_mesh is not None:
            apply_expression_preset(avatar_mesh, expression, start_frame)
        apply_placeholder_gesture(bpy, gesture, start_frame, end_frame)


def configure_render(job: dict[str, Any], mouth_metadata: dict[str, Any]) -> None:
    scene = bpy.context.scene
    fps = int(job.get("fps", 30))
    resolution = job.get("resolution", [1920, 1080])
    duration = float(mouth_metadata.get("duration", 5.0))

    scene.render.fps = fps
    scene.render.resolution_x = int(resolution[0])
    scene.render.resolution_y = int(resolution[1])
    scene.frame_start = 1
    scene.frame_end = max(1, int(duration * fps))
    scene.render.image_settings.file_format = "PNG"
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    print(f"[blender] Render configured: {fps} fps, {resolution[0]}x{resolution[1]}, frames 1-{scene.frame_end}.")


def main() -> None:
    job_path = parse_blender_args()
    job = load_json(job_path)
    job_id = str(job["job_id"])
    temp_dir = PROJECT_ROOT / "assets" / "temp" / job_id
    render_dir = PROJECT_ROOT / "assets" / "renders" / job_id
    mouth_path = temp_dir / "mouth_cues.json"
    audio_path = temp_dir / "audio.wav"

    mouth_data = load_json(mouth_path)
    mouth_cues = mouth_data.get("mouthCues", [])
    configure_render(job, mouth_data.get("metadata", {}))
    add_audio_to_timeline(audio_path)

    face_mode = str(job.get("face_mode", "2d")).lower()
    if face_mode == "3d":
        avatar_mesh = find_avatar_mesh()
        if avatar_mesh is not None:
            apply_3d_mouth_animation(avatar_mesh, mouth_cues, int(job.get("fps", 30)))
    else:
        apply_2d_mouth_animation(mouth_cues, int(job.get("fps", 30)))

    apply_performance_beats(job, int(job.get("fps", 30)))
    add_camera_cuts(bpy, bpy.context.scene, job.get("camera_cuts", []), int(job.get("fps", 30)))

    render_dir.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.render.filepath = str(render_dir / "frame_#####")
    print(f"[blender] Rendering PNG frames to: {render_dir}")
    bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
