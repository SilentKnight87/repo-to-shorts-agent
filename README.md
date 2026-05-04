# Repo-to-Shorts Agent

Turn any GitHub repo into a 60-second animated creative short. Built for the Nous Research Hermes Agent Creative Hackathon.

**The meta pitch:** The hackathon submission video will be a screen recording of this app, generating a video of itself.

## How it works

1. **Paste a GitHub URL** into the web UI
2. **Kimi 2.6 (Creative Director)** analyzes the repo and designs a creative brief: visual style, scene breakdown, narration script, pacing
3. **Enhanced renderer** animates the scenes with gradients, fade reveals, typewriter text, and component architecture diagrams
4. **TTS narration** (macOS `say`) reads the script and gets mixed into the video
5. **Output:** a 1080×1920 vertical MP4, ready to post

All of this happens in one click through the browser, or via a single command in a Hermes Agent session.

## Hermes Agent skill

Repo-to-Shorts ships as a Hermes Agent skill — `~/.hermes/skills/video/repo-shorts-creative/SKILL.md`. Inside an interactive `hermes` REPL, the agent reads the skill, decides to invoke its terminal toolset, runs the underlying CLI, and validates the live Kimi proof in `metadata.json` before declaring success.

```bash
hermes
> /repo-shorts-creative https://github.com/SilentKnight87/repo-to-shorts-agent
```

Or in natural language: *"Make a launch short for this repo: https://…"*

The skill is the boundary. Hermes Agent is the agentic operator. Repo-to-Shorts is the workflow that gets invoked. Kimi K2.6 is the model behind Hermes (configured in `~/.hermes/config.yaml`) and the creative director inside the Repo-to-Shorts pipeline. Two layers of Kimi, one Hermes loop.

### Install the skill (one time)

```bash
mkdir -p ~/.hermes/skills/video/repo-shorts-creative
cp .hermes/skill/SKILL.md ~/.hermes/skills/video/repo-shorts-creative/SKILL.md
```

(Or symlink if you'd rather edit in place.)

## Web UI (primary interface)

```bash
repo-shorts web
```

Opens `http://127.0.0.1:8765`:

- Paste any GitHub URL or local path
- Toggle **Creative short** (animated + narrated) or **Classic analysis** (artifact package)
- Click Generate
- Watch the creative brief appear, then download `demo.mp4`

For LAN demo access (e.g., record from another device):

```bash
repo-shorts web --host 0.0.0.0 --port 8765
```

## Install

```bash
/opt/homebrew/bin/python3.13 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev,render]'
```

Requires system `ffmpeg` and `ffprobe`.

## API key setup

Create `.env` in the project root:

```bash
OPENROUTER_API_KEY=sk-or-v1-...
```

If no key is present, the tool uses a deterministic fallback. It still produces a video, but the creative brief is templated rather than Kimi-designed. The metadata.json always records which mode was used.

## CLI (optional)

The web UI wraps the same engine. CLI exists for scripting:

```bash
# Creative short via CLI
repo-shorts creative https://github.com/owner/repo --out runs

# Classic artifact package
repo-shorts analyze https://github.com/owner/repo --out runs --render mp4
```

## Architecture

```
[ Hermes Agent (REPL) ]  -> reads SKILL.md, decides to invoke terminal tool
                         |
                         v
                    GitHub URL
                         |
                         v
                  [ Ingest ]  -> README, file tree, metadata, git log
                         |
                         v
        [ Creative Director ]  -> Kimi 2.6 designs brief (style, scenes, narration)
                         |
                         v
                 [ Renderer ]  -> Pillow / Remotion generates 1080×1920 @ 30fps
                         |              gradients, fades, typewriter, component reveals
                         v
              [ Compositor ]  -> ffmpeg stitches frames + TTS narration -> demo.mp4
                         |
                         v
                [ Metadata ]  -> metadata.json proves Kimi mode + creative brief
                         |
                         v
[ Hermes Agent ]  -> validates kimi.mode=live-api in metadata, returns submission_pack.md
```

Outer loop: Hermes Agent. Inner loop: the Python CLI. Hermes invokes, validates, and reports — it never fakes the proof.

## Creative brief structure

Kimi 2.6 outputs a JSON brief like:

```json
{
  "style": "dark-terminal",
  "title": "repo-to-shorts-agent: What It Builds",
  "hook": "One repo. Infinite possibilities.",
  "scenes": [
    {
      "duration_seconds": 8,
      "visual_tool": "pretext",
      "narration": "repo-to-shorts-agent — let's see what it builds.",
      "music_mood": "tension",
      "transition": "fade"
    }
  ],
  "music_mood": "electronic",
  "total_duration": 60
}
```

Styles: `dark-terminal`, `clean-academic`, `playful`, `cinematic`

Visual tools: `manim` (code viz), `pretext` (typography), `ascii` (code art), `svg` (architecture)

## Generated artifacts

Each run creates `runs/<timestamp>-<repo>/`:

- `demo.mp4` — the final 60s creative short
- `metadata.json` — proof of Kimi mode, creative brief, render details
- `video_raw.mp4` — video without audio (for remixing)
- `manim_scene_descriptor.json` — the scene script fed to the renderer

For classic analysis mode, also generates: repo brief, storyboard, architecture SVG, narration script, captions, X/Discord copy, Kimi critique.

## Kimi usage

**Creative Director** (`repo-shorts creative` / web UI creative mode):
- Kimi 2.6 analyzes repo context and designs the full creative brief
- Requires `OPENROUTER_API_KEY`
- Fallback: deterministic template when no key

**Critic/Editor** (`repo-shorts analyze`):
- Kimi reviews the generated story package and suggests improvements
- Same key requirement and fallback behavior

Both modes record honest metadata:
- `kimi.mode`: `live-api`, `deterministic-fallback`, or `api-error-fallback`
- `kimi.model`: `moonshotai/kimi-k2.6`
- `kimi.provider`: `openrouter`

## Development

```bash
.venv/bin/python -m pytest -q        # 53 tests
.venv/bin/ruff check .               # lint
repo-shorts web                      # start UI
```

## Hackathon submission

**The meta demo:** Hermes Agent invokes the `repo-shorts-creative` skill on this repository. The skill drives a Kimi-directed creative pipeline that produces a video about itself. The submission video shows Hermes building a video of the repo Hermes is building it from.

**Proof points:**
1. Open `hermes` in a terminal, type `/repo-shorts-creative https://github.com/SilentKnight87/repo-to-shorts-agent`
2. Show Hermes reading the skill, deciding to invoke `run_terminal_cmd`, and shelling out
3. (Side-by-side) open the web UI, paste the same URL — same workflow, two surfaces
4. Watch the VHS broadcast UI light up its channel rows as the pipeline runs
5. Play the generated `demo.mp4`
6. Open `metadata.json` — show `kimi.mode: live-api`, `kimi.provider: openrouter`, `kimi.model: moonshotai/kimi-k2.6`, `render.validation.ok: true`
7. Show `submission_pack.md` — the Hermes orchestration proof section cites the skill path

**What to submit:**
- Demo video (≤60s, 9:16): split-track of Hermes terminal session and VHS browser UI
- X post tagging `@NousResearch` and `@Kimi_Moonshot`
- Discord drop in the Nous Research `creative-hackathon-submissions` channel
- The repo itself (already public)
