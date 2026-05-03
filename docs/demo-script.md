# Demo script

## Setup

```bash
/opt/homebrew/bin/python3.13 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev,render]'
OPENROUTER_API_KEY="***" repo-shorts analyze . \
  --audience "Nous Research Hermes Agent Creative Hackathon judges" \
  --out runs \
  --kimi-model moonshotai/kimi-k2.6 \
  --render mp4
```

Open the generated `demo.html` in a browser. If `--render mp4` succeeds, also show `demo.mp4` and the render block in `metadata.json`.

## 60-second recording plan

### 0–5s — Hook

Narration: “A repo lands on your desk. In under a minute, Repo-to-Shorts turns it into a launch-ready short-video package.”

Visual: browser on `demo.html` hero section.

### 5–15s — Problem

Narration: “Hackathon projects often work before they are easy to understand. The missing piece is the story.”

Visual: scroll to story beats.

### 15–35s — Proof

Narration: “The agent ingests README, file tree, package metadata, git log, and diff signals. Then it creates a repo brief, storyboard, architecture SVG, narration, captions, X copy, submission copy, and an optional vertical MP4.”

Visual: quickly show generated folder, `demo.mp4`, and artifact names, then return to `demo.html`.

### 35–50s — Kimi critic/editor

Narration: “Kimi 2.6 runs through OpenRouter as the critic and script editor. The metadata records `live-api`, the model name, and the provider, so the demo shows actual Kimi usage instead of hand-wavy model perfume.”

Visual: Kimi critic card in the demo artifact or `kimi_critique.md`.

### 50–60s — Close

Narration: “One command turns code context into a package you can screen-record and ship.”

Visual: artifact checklist and final run command.

## Capture notes

- Use a 9:16 crop if screen-recording the browser artifact, or use generated `demo.mp4` directly when `--render mp4` succeeds.
- Zoom browser to 125–150% so the cards are legible.
- Use `captions.srt` for subtitle import.
- Use `x_post.md` and `submission.md` for launch copy.
