from __future__ import annotations

from typing import Any

GESTURES = {
    "seated_idle",
    "hands_on_desk",
    "explain_small",
    "nod_yes",
    "point_camera",
}


def find_armature(bpy_module: Any) -> Any | None:
    for obj in bpy_module.context.scene.objects:
        if getattr(obj, "type", "") == "ARMATURE":
            return obj
    print("[blender:gesture] WARNING: No armature found; skipping gestures.")
    return None


def pose_bone(armature: Any, *names: str) -> Any | None:
    for name in names:
        bone = armature.pose.bones.get(name)
        if bone is not None:
            return bone
    print(f"[blender:gesture] WARNING: Missing expected bone from {names}; skipping that motion.")
    return None


def key_bone_rotation(bone: Any, frame: int, rotation: tuple[float, float, float]) -> None:
    bone.rotation_mode = "XYZ"
    bone.rotation_euler = rotation
    bone.keyframe_insert(data_path="rotation_euler", frame=frame)


def apply_placeholder_gesture(bpy_module: Any, gesture_name: str, start_frame: int, end_frame: int) -> None:
    if gesture_name not in GESTURES:
        print(f"[blender:gesture] WARNING: Unknown gesture '{gesture_name}', skipping.")
        return

    armature = find_armature(bpy_module)
    if armature is None:
        return

    # TODO: Replace these procedural rotations with loaded Blender Actions.
    mid_frame = max(start_frame + 1, (start_frame + end_frame) // 2)
    head = pose_bone(armature, "Head", "head", "DEF-head")
    left_arm = pose_bone(armature, "UpperArm.L", "upper_arm.L", "DEF-upper_arm.L")
    right_arm = pose_bone(armature, "UpperArm.R", "upper_arm.R", "DEF-upper_arm.R")
    right_hand = pose_bone(armature, "Hand.R", "hand.R", "DEF-hand.R")

    if gesture_name == "seated_idle":
        if head:
            key_bone_rotation(head, start_frame, (0.0, 0.0, 0.0))
            key_bone_rotation(head, end_frame, (0.03, 0.0, 0.0))
    elif gesture_name == "hands_on_desk":
        for bone in (left_arm, right_arm):
            if bone:
                key_bone_rotation(bone, start_frame, (0.35, 0.0, 0.0))
                key_bone_rotation(bone, end_frame, (0.35, 0.0, 0.0))
    elif gesture_name == "explain_small":
        if right_arm:
            key_bone_rotation(right_arm, start_frame, (0.25, 0.0, -0.15))
            key_bone_rotation(right_arm, mid_frame, (0.55, 0.1, -0.35))
            key_bone_rotation(right_arm, end_frame, (0.25, 0.0, -0.15))
    elif gesture_name == "nod_yes":
        if head:
            key_bone_rotation(head, start_frame, (0.0, 0.0, 0.0))
            key_bone_rotation(head, mid_frame, (0.18, 0.0, 0.0))
            key_bone_rotation(head, end_frame, (0.0, 0.0, 0.0))
    elif gesture_name == "point_camera":
        if right_arm:
            key_bone_rotation(right_arm, start_frame, (0.2, -0.25, -0.25))
            key_bone_rotation(right_arm, mid_frame, (0.85, -0.45, -0.15))
            key_bone_rotation(right_arm, end_frame, (0.2, -0.25, -0.25))
        if right_hand:
            key_bone_rotation(right_hand, mid_frame, (0.0, 0.0, -0.2))

    print(f"[blender:gesture] Applied placeholder gesture '{gesture_name}'.")
