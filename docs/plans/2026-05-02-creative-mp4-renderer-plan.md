# Creative MP4 Renderer Implementation Plan

> Historical status, May 3: this plan has been executed for the MVP path. The shipped renderer uses Pillow scene cards plus ffmpeg/ffprobe behind `--render mp4`, records render metadata, and keeps default artifact generation safe. Current truth lives in `docs/PRD.md` and `README.md`.

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Evolve Repo-to-Shorts Agent from a launch-asset generator into a creative Hermes/Kimi-directed workflow that emits a real, postable MP4 video.

**Architecture:** Keep the existing reliable artifact pipeline intact, then add a constrained creative director layer and an optional MP4 renderer. The shippable MVP should use generated HTML/canvas or Pillow frames plus ffmpeg, not GPU-heavy video generation, so the hackathon demo is reliable on this machine.

**Tech Stack:** Python 3.13, Typer, Jinja2, Pillow or browser/Playwright rendering, ffmpeg, OpenRouter Kimi 2.6, optional macOS `say`/Hermes TTS, optional future ComfyUI/Manim/ASCII-video modes.

---

## Vision

Repo-to-Shorts should not merely summarize a repo. It should act like a creative production agent:

1. Read a GitHub/local repo.
2. Extract what matters: problem, product, architecture, proof, demo flow, story risk.
3. Ask Kimi to act as critic/editor/creative director.
4. Choose a visual treatment based on repo type.
5. Generate timed scenes, narration/captions, and motion direction.
6. Render a real MP4.
7. Package the MP4 plus submission copy and X copy.

This is meta in the good way: use Repo-to-Shorts to create the hackathon short for Repo-to-Shorts itself.

## Current vs Target Capability

| Area | Current | Target |
| --- | --- | --- |
| Repo understanding | Local/GitHub ingest, file tree, README, metadata, git signals | Same, plus creative scoring/style routing |
| Kimi | Live OpenRouter Kimi critic/editor proof | Kimi critic plus constrained creative director JSON |
| Output | Markdown/SVG/SRT/HTML artifacts | Same plus `video_plan.json`, `video.html`, `demo.mp4` |
| Video | Browser-recordable `demo.html` only | Real 9:16 H.264/AAC MP4 |
| Creative style | One generic demo page | Template chosen by repo type: voiceover explainer, caption-only neon, terminal/ASCII, architecture/product spotlight |
| External tools | Kimi + local files | ffmpeg required, optional TTS/Playwright/ComfyUI/Manim later |
| Claim safety | Honest package generator | Honest MP4 generator, not full video editor or auto-publisher |

## Recommended MVP Path

Ship the non-GPU path first:

```text
existing run_analysis()
  -> generate existing artifacts
  -> build_video_plan()
  -> render timed vertical scenes
  -> ffmpeg encodes demo.mp4
  -> metadata records render proof
```

Do **not** make Manim or ComfyUI required for MVP. They are excellent stretch modes but can become install/GPU sinkholes. The current machine has ffmpeg and browser tooling; ComfyUI is not installed and local hardware is marginal for heavy video generation.

## Creative Director Contract

Create a constrained JSON plan instead of letting the model invent arbitrary rendering code.

Suggested shape:

```json
{
  "format": "voiceover_explainer",
  "aspect": "9:16",
  "duration_sec": 60,
  "visual_style": "neon_terminal_cards",
  "motion_style": "screen_zoom_pan",
  "audio_mode": "voiceover",
  "caption_mode": "burned_in",
  "scenes": [
    {
      "start": 0,
      "end": 5,
      "type": "hook",
      "headline": "Every repo has a demo trapped inside it.",
      "visual": "repo_card_fan",
      "caption": "Paste a repo. Get the short."
    }
  ]
}
```

Style routing rules for MVP:

- CLI/devtool repo -> `terminal_neon_cards` or `ascii_terminal`.
- Frontend/app repo -> `browser_product_spotlight`.
- Architecture/platform repo -> `systems_diagram_motion`.
- ML/data/math repo -> `manim_like_explainer` using HTML/Pillow, not Manim dependency.
- If voiceover unavailable -> `caption_only_musicless` with burned-in captions.
- If Kimi live mode succeeds -> show a visible Kimi editor/critic beat.

## Task 1: Add render dependency and runtime checks

**Objective:** Prepare the repo for optional MP4 rendering without breaking the default install.

**Files:**
- Modify: `pyproject.toml`
- Create: `src/repo_to_shorts/render.py`
- Test: `tests/test_render.py`

**Steps:**
1. Replace optional render dependency with Pillow:
   ```toml
   [project.optional-dependencies]
   render = ["pillow>=10.0"]
   ```
2. In `render.py`, add:
   - `ffmpeg_available() -> bool`
   - clear `RuntimeError` if ffmpeg missing
   - clear `RuntimeError` if Pillow missing
3. Add unit tests for ffmpeg missing path.
4. Run:
   ```bash
   .venv/bin/python -m pip install -e '.[dev,render]'
   .venv/bin/python -m pytest tests/test_render.py -q
   ```

## Task 2: Define video scene and render result models

**Objective:** Create typed internal structures for video rendering.

**Files:**
- Modify: `src/repo_to_shorts/render.py`
- Test: `tests/test_render.py`

**Implementation sketch:**

```python
@dataclass(frozen=True)
class VideoScene:
    title: str
    body: str
    footer: str = ""
    accent: str = "#8b5cf6"

@dataclass(frozen=True)
class RenderConfig:
    width: int = 1080
    height: int = 1920
    fps: int = 30
    seconds_per_scene: int = 10
    output_name: str = "demo.mp4"

@dataclass(frozen=True)
class RenderResult:
    output_path: Path
    mode: str
    renderer: str
    scene_count: int
```

Tests:
- constructing defaults works
- config defaults to 1080x1920
- output name is `demo.mp4`

## Task 3: Build video scenes from existing story package

**Objective:** Convert the existing repo story/Kimi critique into a 5-scene video plan.

**Files:**
- Modify: `src/repo_to_shorts/render.py`
- Test: `tests/test_render.py`

**Scene structure:**
1. Hook
2. Problem/promise
3. Repo ingest/proof
4. Kimi critic/editor
5. Launch package/CTA

**Test assertions:**
- returns 5 scenes
- repo name appears
- Kimi scene exists
- CTA scene exists
- text is bounded/truncated, not unbounded wall-of-text

## Task 4: Render vertical PNG scene cards

**Objective:** Create visually decent 9:16 frames using Pillow.

**Files:**
- Modify: `src/repo_to_shorts/render.py`
- Test: `tests/test_render.py`

**Design requirements:**
- 1080x1920
- dark/neon style
- large readable title
- wrapped body text
- footer/caption lower third
- no remote fonts required
- safe fallback to system fonts

**Verification:**
- render one PNG into temp dir
- assert file exists
- assert image size is 1080x1920

## Task 5: Stitch frames into MP4 with ffmpeg

**Objective:** Emit a real `demo.mp4` from rendered scene images.

**Files:**
- Modify: `src/repo_to_shorts/render.py`
- Test: `tests/test_render.py`

**ffmpeg command shape:**

```bash
ffmpeg -y \
  -f concat -safe 0 -i frames.txt \
  -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=44100 \
  -shortest \
  -vf "fps=30,format=yuv420p" \
  -c:v libx264 \
  -c:a aac \
  -movflags +faststart \
  demo.mp4
```

**Tests:**
- mock `subprocess.run`
- assert command includes ffmpeg/libx264/yuv420p/aac
- fake-create output file
- assert `RenderResult` points to `demo.mp4`

## Task 6: Wire renderer into pipeline behind explicit option

**Objective:** Add optional MP4 generation without changing the current default behavior.

**Files:**
- Modify: `src/repo_to_shorts/pipeline.py`
- Test: `tests/test_pipeline.py`

**API shape:**

```python
def run_analysis(..., render: str = "none") -> Path:
```

Valid values:
- `none`
- `mp4`

Metadata addition:

```json
"render": {
  "mode": "mp4",
  "renderer": "pillow+ffmpeg",
  "output": "demo.mp4",
  "scene_count": 5
}
```

Tests:
- default run has `render.mode == "none"`
- `render="mp4"` adds `demo.mp4` to manifest
- invalid render mode raises `ValueError`

## Task 7: Add CLI flag

**Objective:** Let users request MP4 export from the command line.

**Files:**
- Modify: `src/repo_to_shorts/cli.py`
- Test: CLI smoke test in `tests/test_pipeline.py` or new `tests/test_cli.py`

**CLI shape:**

```bash
repo-shorts analyze . \
  --audience "Nous Research Hermes Agent Creative Hackathon judges" \
  --out runs \
  --render mp4
```

CLI should print MP4 path if present.

## Task 8: Update docs and claims

**Objective:** Make the README and submission copy honest after MP4 support lands.

**Files:**
- Modify: `README.md`
- Modify: `docs/demo-script.md`
- Modify: `docs/submission-copy.md`
- Modify: `AGENTS.md`

Claims to use:
- “optional MP4 export”
- “vertical short-video render”
- “Kimi critic/editor plus creative direction”
- “does not auto-post or auto-submit”

Claims to avoid:
- “full video editor”
- “guaranteed cinematic AI video for any repo”
- “ComfyUI/Manim powered” unless actually implemented
- “finished voiceover” unless TTS is actually added

## Task 9: Generate final meta-demo with Repo-to-Shorts itself

**Objective:** Use the tool to create the hackathon video for the tool.

**Command:**

```bash
cd /Users/aiserver/projects/repo-to-shorts-agent
.venv/bin/repo-shorts analyze . \
  --audience "Nous Research Hermes Agent Creative Hackathon judges" \
  --out runs \
  --kimi-model moonshotai/kimi-k2.6 \
  --render mp4
```

**Verification:**

```bash
ffprobe -v error \
  -select_streams v:0 \
  -show_entries stream=codec_name,width,height,duration \
  -of default=noprint_wrappers=1 \
  runs/<latest>/demo.mp4
```

Expected:
- codec `h264`
- width `1080`
- height `1920`
- duration around 50-60 seconds

## Stretch Modes After MVP

### Stretch A: Browser/Playwright renderer

Generate `video.html`, then capture deterministic frames via Playwright. This unlocks more creative CSS/canvas motion.

Best after MVP because Playwright is available via Hermes, but adding it to the package is more surface area.

### Stretch B: macOS/Hermes TTS

Add `--voiceover` mode:
- local fallback: `say`
- higher quality: Hermes `text_to_speech` outside package, or provider-specific future integration

### Stretch C: ASCII/terminal style

Use repo file names and code tokens as moving glyph texture for CLI/devtool repos.

### Stretch D: ComfyUI asset mode

Optional hero still generation only, not required video generation. ComfyUI is not currently installed/running locally and heavy video generation is risky on M4 16GB.

### Stretch E: Manim-style explainer

Prefer HTML/Pillow imitation first. Real Manim is not installed and may add LaTeX/render friction.

## Acceptance Criteria

- `repo-shorts analyze . --render mp4` creates `demo.mp4`.
- Default `repo-shorts analyze .` still works without Pillow/render extras.
- Tests pass.
- Ruff passes.
- Metadata honestly records render mode and output.
- Generated MP4 is 9:16, H.264, social-upload compatible.
- Submission copy no longer implies manual screen recording is the only path.

## Verification Commands

```bash
cd /Users/aiserver/projects/repo-to-shorts-agent
.venv/bin/python -m pip install -e '.[dev,render]'
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/repo-shorts analyze . \
  --audience "Nous Research Hermes Agent Creative Hackathon judges" \
  --out runs \
  --render mp4
ffprobe -v error -show_format -show_streams runs/<latest>/demo.mp4 | head -80
```
