# Repo-to-Shorts Agent

Turn a GitHub repo or local repo into a launch-ready technical short-video package.

Built for the Nous Research Hermes Agent Creative Hackathon as a polished MVP golden path: paste a repo target, get a repo brief, story arc, storyboard, architecture diagram, narration, captions, launch copy, Discord submission copy, Kimi critic notes, and a browser-presentable demo artifact.

> Repo remains private. The tool does not publish or submit anything externally.

## Kimi + Hermes strategy

Repo-to-Shorts is intended to be a Hermes creative workflow, not just a standalone Python script.

The submission strategy is two-front Kimi usage:

1. Kimi powers the Hermes harness where possible: Kimi reasons, Hermes acts.
2. Repo-to-Shorts calls Kimi as a critic/script editor inside the generated artifact pipeline.

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

# Optional MP4 renderer support
.venv/bin/python -m pip install -e '.[render]'
```

## CLI

```bash
repo-shorts analyze <target> --audience "hackathon judges" --out runs
```

Examples:

```bash
# Local repository
repo-shorts analyze . --audience "Nous Research hackathon judges" --out runs

# GitHub repository, cloned shallowly to a temporary directory
repo-shorts analyze https://github.com/SilentKnight87/repo-to-shorts-agent.git \
  --audience "technical founders" \
  --out runs
```

Options:

- `--audience`, `-a`: audience to tailor the short-video package for.
- `--out`, `-o`: output directory for timestamped run folders. Default: `runs`.
- `--force`: allow overwriting an existing timestamped run directory if one collides.
- `--kimi-model`: OpenRouter/Moonshot Kimi model name. Default: `moonshotai/kimi-k2.6`.
- `--render`: optional renderer. Use `none` for artifact-only output or `mp4` for a 9:16 `demo.mp4` built with Pillow + ffmpeg.

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

## Optional MP4 export

The default run remains lightweight and browser-first. Add `--render mp4` when you want a generated vertical video file:

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
  -> deterministic story package
  -> Kimi critic/script-editor adapter or fallback
  -> Markdown/SVG/SRT/HTML launch artifacts
  -> optional Pillow + ffmpeg MP4 export
```

The MVP deliberately favors one reliable, deterministic golden path over a generic media platform. It is safe to run without model credentials.

## Kimi critic stage

Kimi is an explicit critic/script-editor stage in `repo_to_shorts.kimi`.

Default live mode uses OpenRouter with Kimi 2.6:

```bash
export OPENROUTER_API_KEY="[REDACTED]"
repo-shorts analyze . \
  --audience "Nous Research Hermes Agent Creative Hackathon judges" \
  --out runs \
  --kimi-model moonshotai/kimi-k2.6 \
  --render mp4
```

If `OPENROUTER_API_KEY`/`KIMI_API_KEY` is absent, the tool writes a deterministic fallback critique and records that honestly in `metadata.json`. If the API call fails, it still writes the package and records `api-error-fallback` rather than pretending the run was live.

## Development

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
repo-shorts analyze . --audience "hackathon judges" --out runs --force
repo-shorts analyze . --audience "hackathon judges" --out runs --render mp4 --force
```

## Hackathon demo angle

Most technical projects die in the gap between “it works” and “people understand why it matters.” Repo-to-Shorts Agent closes that gap by turning code context into a ready-to-record launch package.
