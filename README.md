# Repo-to-Shorts Agent

Turn a GitHub repo or local repo into a launch-ready technical short-video package.

Built for the Nous Research Hermes Agent Creative Hackathon as a polished MVP golden path: pass a repo target, get a repo brief, story arc, storyboard, architecture diagram, narration, captions, launch copy, Discord submission copy, Kimi critic notes, a browser-presentable demo artifact, and an optional creative short video.

**NEW:** `repo-shorts creative` generates a 60-second animated creative short with Kimi 2.6 creative direction, animated visuals, and TTS narration. `repo-shorts web` launches a local browser UI.

> Repo remains private. The tool does not publish or submit anything externally.

## Kimi + Hermes strategy

Repo-to-Shorts is a Hermes Agent creative workflow, not just a standalone Python script.

The submission strategy is two-front Kimi usage:

1. **Kimi 2.6 Creative Director** (`repo-shorts creative`): Kimi analyzes the repo and designs a creative brief (visual style, scene breakdown, narration, pacing) for a 60-second short.
2. **Kimi Critic/Editor** (`repo-shorts analyze`): Kimi critiques the generated story package and suggests improvements.

Both paths use OpenRouter with `moonshotai/kimi-k2.6`. Both have honest deterministic fallbacks when no API key is present.

See:

```text
docs/HACKATHON_STRATEGY.md
docs/PRD.md
```

## Install

Use Python 3.13 from Homebrew on the hackathon machine:

```bash
/opt/homebrew/bin/python3.13 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'

# Optional MP4 renderer support (Pillow + ffmpeg)
.venv/bin/python -m pip install -e '.[render]'
```

Requires system `ffmpeg` and `ffprobe` for video generation.

## Quick start

### Creative short (new)

Generate a 60-second animated creative short with Kimi 2.6 creative direction:

```bash
repo-shorts creative . --audience "hackathon judges" --out runs
```

With live Kimi via OpenRouter:

```bash
export OPENROUTER_API_KEY="***"
repo-shorts creative . \
  --audience "Nous Research Hermes Agent Creative Hackathon judges" \
  --out runs \
  --kimi-model moonshotai/kimi-k2.6
```

### Classic analysis

Generate the full artifact package (brief, storyboard, narration, etc.):

```bash
repo-shorts analyze <target> --audience "hackathon judges" --out runs --render mp4
```

### Local web UI

Launch a browser form at `http://127.0.0.1:8765`:

```bash
repo-shorts web
```

For LAN demo access:

```bash
repo-shorts web --host 0.0.0.0 --port 8765
```

## Generated artifacts

Each run writes a folder like `runs/20260501-012345-repo-to-shorts-agent/` containing:

- `metadata.json` — run target, source type, audience, Kimi mode, artifact manifest.
- `repo_brief.md` — README signal, package metadata, file tree summary, git log/diff when available.
- `storyboard.md` — 60-second story arc with visuals.
- `architecture.svg` — deterministic architecture diagram.
- `narration.md` — voiceover script.
- `captions.srt` — subtitle file for the golden-path short.
- `x_post.md` — X-ready launch copy.
- `submission.md` — Discord/hackathon submission copy.
- `kimi_critique.md` — Kimi critic/script-editor pass or deterministic fallback.
- `demo.html` — browser-presentable artifact designed for screen recording.
- `demo.mp4` — optional 9:16 video export when run with `--render mp4`.
- `recording_instructions.md` — practical capture checklist.

## Creative mode

The `repo-shorts creative` command generates a produced 60-second creative short:

1. **Ingest** the repo (same as `analyze`)
2. **Kimi 2.6 Creative Director** designs a creative brief with style, scene breakdown, narration, and pacing
3. **Enhanced renderer** animates each scene with gradients, fades, typewriter effects, and component reveals
4. **TTS narration** is generated via macOS `say` and merged into the final video
5. **Metadata** proves Kimi directed the brief

Output:
- `demo.mp4` — 1080×1920 vertical, 60s, h264 + aac
- `metadata.json` — includes `creative_brief` and `kimi.mode` proof

Renderer: `pillow+ffmpeg-enhanced` (animated frames, not static slides)

```bash
repo-shorts creative . \
  --audience "Nous Research Hermes Agent Creative Hackathon judges" \
  --out runs \
  --kimi-model moonshotai/kimi-k2.6 \
  --music bg_track.mp3
```

## Optional classic MP4 export

The `repo-shorts analyze --render mp4` path creates a simpler vertical slideshow:

```bash
repo-shorts analyze . \
  --audience "Nous Research Hermes Agent Creative Hackathon judges" \
  --out runs \
  --kimi-model moonshotai/kimi-k2.6 \
  --render mp4
```

Requirements:

- Python extra: `pip install -e '.[render]'`
- System binaries: `ffmpeg` and `ffprobe`

The renderer creates Pillow scene cards, stitches them with ffmpeg, and writes render proof into `metadata.json`:

```json
"render": {
  "mode": "mp4",
  "status": "success",
  "renderer": "pillow+ffmpeg",
  "output": "demo.mp4",
  "scene_count": 5,
  "error": null
}
```

## How it works

```text
local repo or GitHub URL
  -> ingest README, file tree, package metadata, git log/diff
  -> deterministic story package OR Kimi creative brief
  -> enhanced animation renderer (Pillow + ffmpeg)
  -> TTS narration + optional music
  -> final demo.mp4 with metadata proof
```

The MVP deliberately favors one reliable, deterministic golden path over a generic media platform. It is safe to run without model credentials.

## Kimi usage

### Creative Director (`repo-shorts creative`)

Kimi 2.6 analyzes the repo and outputs a structured creative brief:
- `style`: dark-terminal, clean-academic, playful, or cinematic
- `scenes`: 4-6 scenes with duration, visual tool, narration, music mood, transition
- `hook`: punchy opening line

### Critic/Editor (`repo-shorts analyze`)

Kimi critiques the generated story package and suggests improvements.

Default live mode uses OpenRouter with Kimi 2.6:

```bash
export OPENROUTER_API_KEY="***"
repo-shorts analyze . \
  --audience "Nous Research Hermes Agent Creative Hackathon judges" \
  --out runs \
  --kimi-model moonshotai/kimi-k2.6 \
  --render mp4
```

If `OPENROUTER_API_KEY`/`KIMI_API_KEY` is absent, the tool writes a deterministic fallback and records that honestly in `metadata.json`. If the API call fails, it records `api-error-fallback` rather than pretending the run was live.

## Development

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
repo-shorts creative . --out runs --force
repo-shorts analyze . --out runs --render mp4 --force
```

## Hackathon demo angle

Most technical projects die in the gap between "it works" and "people understand why it matters." Repo-to-Shorts Agent closes that gap by turning code context into a ready-to-record launch package.

The creative mode goes further: instead of static slides, it produces an animated, narrated short with creative direction from Kimi 2.6 — proving that agentic AI can orchestrate the entire creative workflow from repo analysis to final video.
