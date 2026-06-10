# AGENTS.md

This repo is a local Python + Blender automation MVP for stylized desk-avatar videos.

Guidelines for future agents:

- Keep the first pipeline local-first and command-line driven.
- Do not add cloud APIs or a web app unless the user asks for that next phase.
- External tools must fail clearly and use test-mode placeholders where practical.
- Keep Blender scene assumptions documented in `README.md` and `assets/characters/avatar_01/README.md`.
- Avoid hardcoded absolute paths; all project paths should resolve from the repo root.
- Prefer small replaceable wrappers for TTS, lip-sync, Blender rendering, and video export.
