from __future__ import annotations

import sys

import bpy  # type: ignore


REQUIRED_OBJECTS = (
    "CHAR_Avatar",
    "ARM_Avatar",
    "FACE_Surface",
    "FACE_Backdrop",
    "CAM_Portrait_Main",
    "CAM_Landscape_Intro",
    "CAM_Landscape_Conclusion",
)


def main() -> None:
    missing = [name for name in REQUIRED_OBJECTS if bpy.data.objects.get(name) is None]
    print("[template] Required objects:")
    for name in REQUIRED_OBJECTS:
        status = "OK" if name not in missing else "MISSING"
        print(f"[template] {status}: {name}")

    if missing:
        print(f"[template] FAIL: Missing {len(missing)} required object(s): {', '.join(missing)}")
        raise SystemExit(1)

    print("[template] PASS: Blender template contains all required objects.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        print(f"[template] ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
