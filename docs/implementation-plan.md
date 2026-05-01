# Repo-to-Shorts Agent Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build one polished end-to-end workflow that turns a repo into a launch-ready technical short video package.

**Architecture:** Start with a CLI-first pipeline. Each stage writes markdown/JSON artifacts to `runs/<slug>/`, making the demo visible and debuggable. Rendering can be simple HTML/frames + screen recording if MP4 rendering gets spicy.

**Tech Stack:** Python, Typer, Jinja2, Mermaid/SVG or Excalidraw-style diagrams, ffmpeg/moviepy optional, Kimi/LLM call optional via provider adapter.

---

## Winning Demo Path

Input: a small repo URL or local path.

Output:

- `runs/<slug>/repo_brief.md`
- `runs/<slug>/storyboard.md`
- `runs/<slug>/architecture.svg`
- `runs/<slug>/narration.md`
- `runs/<slug>/x_post.md`
- `runs/<slug>/video_plan.md`
- optional `runs/<slug>/demo.mp4`

## Tasks

### Task 1: Create CLI skeleton

**Objective:** Provide `repo-shorts analyze <path-or-url>` that creates a run folder.

**Files:**
- Create: `pyproject.toml`
- Create: `src/repo_to_shorts/__init__.py`
- Create: `src/repo_to_shorts/cli.py`

**Verification:**

```bash
python -m repo_to_shorts.cli analyze .
```

Expected: run folder exists with metadata.

### Task 2: Repo ingestion

**Objective:** Read README, file tree, package metadata, and recent git diff/log when local.

**Files:**
- Create: `src/repo_to_shorts/ingest.py`
- Test: `tests/test_ingest.py`

**Verification:**

```bash
pytest tests/test_ingest.py -v
```

Expected: extracts README and top-level file map.

### Task 3: Story generator

**Objective:** Convert repo facts into problem/audience/architecture/outcome narrative.

**Files:**
- Create: `src/repo_to_shorts/story.py`
- Create: `templates/story_prompt.md`

**Verification:**

Run CLI and inspect `storyboard.md`.

### Task 4: Visual asset generator

**Objective:** Produce architecture SVG and 5-7 slide/card frames.

**Files:**
- Create: `src/repo_to_shorts/visuals.py`
- Create: `templates/architecture.svg.j2`
- Create: `templates/frame.html.j2`

**Verification:**

Open generated SVG/HTML locally.

### Task 5: Kimi critic pass

**Objective:** Add a visible critic/editor stage using Kimi, or a provider adapter that can be wired to Kimi.

**Files:**
- Create: `src/repo_to_shorts/critic.py`
- Create: `templates/critic_prompt.md`

**Verification:**

`runs/<slug>/kimi_critique.md` shows recommendations and applied changes.

### Task 6: Render/export

**Objective:** Produce either MP4 or browser-presentable HTML with recording instructions.

**Files:**
- Create: `src/repo_to_shorts/render.py`

**Verification:**

Final artifact exists at `runs/<slug>/demo.html` or `demo.mp4`.

### Task 7: Submission package

**Objective:** Generate final X post, Discord submission blurb, and 60-90 sec demo script.

**Files:**
- Create: `templates/x_post.md`
- Create: `templates/submission.md`

**Verification:**

All copy is saved under `runs/<slug>/submission/`.

## Scope Rules

- One golden path beats a generic tool.
- Use static templates when LLM integration slows down.
- If MP4 rendering blocks, ship HTML + screen recording.
- Demo must show the agent working, not just the final artifact.
