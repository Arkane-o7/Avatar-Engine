# News Anchor Workflow

`desk-avatar-engine` is the local rendering component for an AI-automated news channel. Upstream systems can generate a script and camera plan; this project turns that job JSON into a talking news-anchor MP4.

## Role In The Larger Pipeline

Typical channel flow:

1. Collect or write news stories.
2. Generate a short anchor script.
3. Choose camera cuts and basic gestures.
4. Write a `jobs/<job_id>.json` file.
5. Run `scripts/run_job.py`.
6. Hand `assets/output/<job_id>.mp4` to the episode compositor/editor.

This repo owns only the anchor-render stage. It does not fetch news, decide editorial content, publish videos, or call cloud TTS APIs.

## Main Commands

Always activate the project venv first:

```bash
source .venv/bin/activate
```

Fast framing/lip-sync preview:

```bash
python3 scripts/run_job.py jobs/news_anchor_preview.json --force-all
```

Final-quality anchor segment:

```bash
python3 scripts/run_job.py jobs/news_anchor_segment.json --force-all
```

Check what would be reused or regenerated:

```bash
python3 scripts/run_job.py jobs/news_anchor_segment.json --status
```

## Job JSON Contract

Required fields:

- `job_id`: output folder and manifest id.
- `script`: spoken anchor copy.
- `character`: character asset id, currently `avatar_01`.
- `face_mode`: usually `"2d"`.
- `fps`: render/export framerate.
- `resolution`: final MP4 canvas size.
- `camera_cuts`: semantic camera sequence.
- `output_path`: final MP4 path.

Common optional fields:

- `voice`: overrides TTS defaults.
- `performance_beats`: placeholder gestures and expression presets.
- `gestures`: Blender Action gestures if the template contains matching Actions.
- `render_quality`: set to `"draft"` for quick previews.
- `render_samples`: lower samples for draft mode.
- `disable_shadows`: use only for throwaway previews.
- `camera_resolution_scale`: multiplies each template camera's saved per-camera resolution.
- `use_per_camera_resolution`: defaults to `true`; keep it true for mixed portrait/landscape camera framing.

## Camera Semantics

Use semantic camera names in jobs:

- `landscape_intro`: wide opening desk or newsroom shot.
- `portrait_main`: tight anchor shot.
- `landscape_conclusion`: wide/alternate closing shot.

These map to Blender objects:

- `CAM_Landscape_Intro`
- `CAM_Portrait_Main`
- `CAM_Landscape_Conclusion`

The Blender template uses the Per-Camera Resolution addon. The runner preserves each camera's aspect ratio and then pads/scales frames into the job's final MP4 canvas, so portrait shots are centered instead of cropped.

## Preview Vs Final

Preview jobs should optimize for speed:

```json
"fps": 12,
"resolution": [960, 540],
"render_quality": "draft",
"render_samples": 4,
"disable_shadows": true,
"camera_resolution_scale": 1.0
```

Final jobs should optimize for image quality:

```json
"fps": 24,
"resolution": [1920, 1080],
"camera_resolution_scale": 2.0
```

Do not use `disable_shadows` for final news segments. It makes previews fast, but it removes depth and newsroom lighting.

## Generated Files

Each job writes only generated files under:

- `assets/temp/<job_id>/`
- `assets/renders/<job_id>/`
- `assets/output/`

Each job also writes:

```text
assets/temp/<job_id>/run_manifest.json
```

The manifest records hashes, durations, frame counts, stale status, render paths, output paths, and the Blender template mtime.

## Safety Rules

- Runtime commands must not save or overwrite `blender/avatar_template.blend`.
- Use `blender/avatar_template.blend` as the production scene.
- Keep alternate `.blend` experiments local unless intentionally promoting one to production.
- Use `--status` before reusing frames with skip flags.
- Use `--force-all` after changing script text, voice settings, mouth textures, cameras, Blender scene contents, or render quality.
