# Demo script

## Setup

```bash
/opt/homebrew/bin/python3.13 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
repo-shorts analyze . --audience "Nous Research Hermes Agent Creative Hackathon judges" --out runs
```

Open the generated `demo.html` in a browser.

## 60-second recording plan

### 0–5s — Hook

Narration: “A repo lands on your desk. In under a minute, Repo-to-Shorts turns it into a launch-ready short-video package.”

Visual: browser on `demo.html` hero section.

### 5–15s — Problem

Narration: “Hackathon projects often work before they are easy to understand. The missing piece is the story.”

Visual: scroll to story beats.

### 15–35s — Proof

Narration: “The agent ingests README, file tree, package metadata, git log, and diff signals. Then it creates a repo brief, storyboard, architecture SVG, narration, captions, X copy, and submission copy.”

Visual: quickly show generated folder and artifact names, then return to `demo.html`.

### 35–50s — Kimi critic/editor

Narration: “Kimi appears as a critic and script editor. If credentials are absent, the deterministic fallback still gives concrete editorial notes and documents how to enable real Kimi later.”

Visual: Kimi critic card in the demo artifact or `kimi_critique.md`.

### 50–60s — Close

Narration: “One command turns code context into a package you can screen-record and ship.”

Visual: artifact checklist and final run command.

## Capture notes

- Use a 9:16 crop if submitting as a short.
- Zoom browser to 125–150% so the cards are legible.
- Use `captions.srt` for subtitle import.
- Use `x_post.md` and `submission.md` for launch copy.
