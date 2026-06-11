# desk-avatar-engine

`desk-avatar-engine` is a local command-line MVP for generating stylized 3D desk-avatar videos. It loads a job JSON, creates local placeholder or TTS audio, generates Rhubarb-style mouth cues, drives a Blender template scene, renders PNG frames, and uses FFmpeg to export an MP4.

This is intentionally not a photorealistic MetaHuman pipeline and does not use cloud APIs.

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

## Run Test Mode

```bash
python scripts/run_job.py jobs/sample_job.json --test-mode
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
python scripts/run_job.py jobs/sample_job.json
```

You can also keep config defaults and force test mode only when needed:

```bash
python scripts/run_job.py jobs/sample_job.json --test-mode
```

## Preparing `blender/avatar_template.blend`

Create or copy a Blender scene to:

```text
blender/avatar_template.blend
```

To generate a simple local placeholder template, run Blender directly:

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b -P blender/create_basic_template.py
```

This creates a basic desk scene with `CHAR_Avatar`, `ARM_Avatar`, `FACE_Surface`, the required cameras, desk, and lights. It is intentionally primitive, but it is enough for the normal Blender stage to render while you replace the assets incrementally.

For the MVP, the scene should include:

- Cameras named `CAM_Front_Medium`, `CAM_Front_Close`, and `CAM_Side_ThreeQuarter`.
- A 2D face surface object named `FACE_Surface` when `face_mode` is `"2d"`.
- An avatar mesh with shape keys when using `face_mode` `"3d"`.
- Shape keys matching `blender/mouth_mapping.py` and `blender/expression_presets.py`.
- An armature with common bones such as `Head`, `UpperArm.L`, `UpperArm.R`, and `Hand.R` for placeholder gestures.

The Blender driver skips missing optional objects safely and prints warnings so a rough template can be improved incrementally.
