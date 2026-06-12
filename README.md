# desk-avatar-engine

`desk-avatar-engine` is a local command-line MVP for generating stylized 3D desk-avatar videos. It loads a job JSON, creates local placeholder or TTS audio, generates Rhubarb-style mouth cues, drives a Blender template scene, renders PNG frames, and uses FFmpeg to export an MP4.

This is intentionally not a photorealistic MetaHuman pipeline and does not use cloud APIs.

## Current Status

- The local pipeline runs end to end from a job JSON to an MP4.
- Rhubarb, Blender, and FFmpeg can be configured through `config/default.yaml`.
- `blender/avatar_template.blend` is the production scene. Runtime scripts load it only and must not overwrite it.
- 2D face mode uses `FACE_Backdrop` and `FACE_Surface`; Rhubarb cues swap mouth PNG textures on `FACE_Surface`.
- Visual polish is still intentionally lightweight. The current focus is reliable local automation and safe iteration.

## Project Flow

Input:

```text
jobs/sample_job.json
```

Output:

```text
assets/output/<job_id>.mp4
```

Pipeline:

1. Load and validate the job JSON.
2. Generate local TTS audio, or a placeholder WAV in test mode.
3. Generate Rhubarb lip-sync cues, or fake Rhubarb-style cues when Rhubarb is missing.
4. Run Blender in background mode when Blender and `blender/avatar_template.blend` are available.
5. Animate mouth cues, expressions, gestures, and camera cuts.
6. Render PNG frames to `assets/renders/<job_id>/`.
7. Export an MP4 with FFmpeg when FFmpeg is available.

## Required Tools

Required for the full normal pipeline:

- Python 3.11+
- Blender
- FFmpeg
- Rhubarb Lip Sync
- A prepared `blender/avatar_template.blend`

Optional:

- Kokoro or another local TTS engine

The MVP can run in test mode without Kokoro, Rhubarb, Blender, or FFmpeg. Missing tools print clear warnings. If Blender is missing, the runner creates placeholder PNG frames. If FFmpeg is missing, MP4 export is skipped in test mode.

## Install

```bash
cd desk-avatar-engine
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If `python3.11` is not the command on your machine, use any Python 3.11+ interpreter.

## Configure Tools

Edit `config/default.yaml`:

```yaml
tools:
  blender: blender
  rhubarb: rhubarb
  ffmpeg: ffmpeg
```

Each value can be either a command available on `PATH` or an absolute path to the binary.

## Health Check

Run the doctor before debugging a job:

```bash
python3 scripts/doctor.py
```

It checks Python, config loading, Blender, FFmpeg, Rhubarb, the production Blender template, sample job loading, asset folders, and required mouth textures.

## Validate The Blender Template

To inspect the production template for required object names without saving it:

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b blender/avatar_template.blend --python blender/validate_template.py
```

Required objects:

- `CHAR_Avatar`
- `ARM_Avatar`
- `FACE_Surface`
- `FACE_Backdrop`
- `CAM_Portrait_Main`
- `CAM_Landscape_Intro`
- `CAM_Landscape_Conclusion`

## Run Test Mode

```bash
python3 scripts/run_job.py jobs/sample_job.json --test-mode
```

Test mode will:

- Generate a local placeholder WAV at `assets/temp/<job_id>/audio.wav`.
- Generate fake Rhubarb-style cues at `assets/temp/<job_id>/mouth_cues.json`.
- Create placeholder PNG frames if Blender or the template file is unavailable.
- Export `assets/output/<job_id>.mp4` if FFmpeg is installed.
- Skip MP4 export with a warning if FFmpeg is unavailable.

## Run Normal Mode

Set `test_mode: false` in `config/default.yaml`, install the required tools, prepare the Blender template, then run:

```bash
python3 scripts/run_job.py jobs/sample_job.json
```

You can also keep config defaults and force test mode only when needed:

```bash
python3 scripts/run_job.py jobs/sample_job.json --test-mode
```

Useful development flags:

```bash
python3 scripts/run_job.py jobs/sample_job.json --skip-render
python3 scripts/run_job.py jobs/sample_job.json --skip-export
python3 scripts/run_job.py jobs/sample_job.json --skip-tts --skip-lipsync
python3 scripts/run_job.py jobs/sample_job.json --clean
```

Skip flags reuse existing generated files under `assets/temp/<job_id>/` and `assets/renders/<job_id>/`. `--clean` removes only this job's generated temp folder, render folder, and output MP4 before running.

## Preparing `blender/avatar_template.blend`

`blender/avatar_template.blend` is the real production scene used by normal pipeline runs. The pipeline only loads this file; it should not be generated or overwritten by runtime code.

Create or copy your production Blender scene to:

```text
blender/avatar_template.blend
```

There is also a manual dummy-template utility. Do not run it unless you intentionally want to create a basic placeholder scene. It writes to `blender/avatar_template_BASIC.blend`, not the production template.

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b -P blender/create_basic_template.py -- --force
```

Without `-- --force`, the helper refuses to overwrite an existing dummy template. This creates a basic desk scene with `CHAR_Avatar`, `ARM_Avatar`, `FACE_Surface`, `CAM_Portrait_Main`, `CAM_Landscape_Intro`, `CAM_Landscape_Conclusion`, desk, and lights. It is intentionally primitive, and you can inspect or manually copy from it while building your real scene.

For the MVP, the scene should include:

- Objects named `CHAR_Avatar`, `ARM_Avatar`, `FACE_Surface`, and `FACE_Backdrop`.
- Cameras named `CAM_Portrait_Main`, `CAM_Landscape_Intro`, and `CAM_Landscape_Conclusion`.
- A 2D face surface object named `FACE_Surface` when `face_mode` is `"2d"`.
- An avatar mesh with shape keys when using `face_mode` `"3d"`.
- Shape keys matching `blender/mouth_mapping.py` and `blender/expression_presets.py`.
- An armature with common bones such as `Head`, `UpperArm.L`, `UpperArm.R`, and `Hand.R` for placeholder gestures.

The Blender driver skips missing optional objects safely and prints warnings so a rough template can be improved incrementally.

## 2D Mouth Textures

For `face_mode: "2d"`, put transparent PNG mouth drawings in:

```text
assets/characters/avatar_01/mouth_textures/
```

Required filenames:

- `mouth_X.png` and `mouth_A.png`: closed/rest
- `mouth_B.png`: M/B/P
- `mouth_C.png`: E/I
- `mouth_D.png`: A/open
- `mouth_E.png`: O
- `mouth_F.png`: U/W
- `mouth_G.png`: F/V
- `mouth_H.png`: L

The PNGs should have the same canvas size, for example 512x512, with transparent background around the mouth art. During Blender renders, Rhubarb cues in `assets/temp/<job_id>/mouth_cues.json` swap the image texture on `FACE_Surface` frame by frame. Missing cue textures fall back to `mouth_X.png` with a warning; if `mouth_X.png` is also missing, the driver uses a flat fallback material and continues.

## Generated Files

Generated files are written only under:

- `assets/temp/<job_id>/`
- `assets/renders/<job_id>/`
- `assets/output/`

These generated folders, media files, `.DS_Store`, `__pycache__`, and virtual environments should not be committed. Source files, jobs, config, character assets, mouth textures, and `blender/avatar_template.blend` are not deleted by `run_job.py`.

## Sample Jobs

- `jobs/sample_job.json`: full default sample.
- `jobs/sample_short_test.json`: short smoke test.
- `jobs/sample_portrait.json`: portrait camera sample.
- `jobs/sample_landscape_intro.json`: landscape camera sample.
