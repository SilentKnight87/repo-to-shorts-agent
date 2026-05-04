# Repo-to-Shorts Agent Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement plans task-by-task.

**Goal:** Track the actual implementation plan for Repo-to-Shorts without pretending old milestones are still open.

**Architecture:** Keep the CLI pipeline as the canonical engine. Layer optional interfaces, renderers, and final-mile submission flows on top of `run_analysis(...)` instead of forking logic.

**Tech Stack:** Python 3.13, Typer, Jinja2, Pillow, ffmpeg/ffprobe, OpenRouter Kimi 2.6, pytest, Ruff, optional future stdlib local web server.

---

## Current shipped system

Input:

```text
local repo path or public GitHub URL
```

Output:

```text
runs/<timestamp>-<repo>/metadata.json
runs/<timestamp>-<repo>/repo_brief.md
runs/<timestamp>-<repo>/storyboard.md
runs/<timestamp>-<repo>/architecture.svg
runs/<timestamp>-<repo>/narration.md
runs/<timestamp>-<repo>/captions.srt
runs/<timestamp>-<repo>/x_post.md
runs/<timestamp>-<repo>/submission.md
runs/<timestamp>-<repo>/kimi_critique.md
runs/<timestamp>-<repo>/demo.html
runs/<timestamp>-<repo>/recording_instructions.md
runs/<timestamp>-<repo>/demo.mp4, if --render mp4 succeeds
```

Current command:

```bash
OPENROUTER_API_KEY="***" .venv/bin/repo-shorts analyze . \
  --audience "Nous Research Hermes Agent Creative Hackathon judges" \
  --out runs \
  --kimi-model moonshotai/kimi-k2.6 \
  --render mp4
```

## Completed milestone plans

1. `docs/plans/2026-05-01-live-kimi-render-plan.md`
   - live OpenRouter/Kimi critic adapter
   - structured Kimi metadata
   - honest fallback behavior

2. `docs/plans/2026-05-02-creative-mp4-renderer-plan.md`
   - optional `--render mp4`
   - Pillow scene cards
   - ffmpeg MP4 render
   - render metadata

## Next active plan

3. `docs/plans/2026-05-03-local-web-ui-plan.md`
   - local browser form
   - Generate button
   - latest runs list
   - artifact links
   - local-only safe defaults

## Current vs target

| Capability | Current | Target next |
| --- | --- | --- |
| CLI generation | Built | keep stable |
| Live Kimi | Built | show fresh `live-api` proof in final run |
| MP4 render | Built | expose checkbox in web UI |
| Static viewing | Works via ad hoc server | fold into local web command |
| Browser form | Not built | build minimal local form |
| Job status | Not built | synchronous success/error page first |
| Submission posting | Not built | manual, after maintainer approval |

## Scope rules

- One golden path beats a generic platform.
- CLI remains canonical.
- Web UI wraps `run_analysis(...)`, it does not duplicate generation logic.
- Use static/server-rendered HTML first. No React swamp.
- API keys come from environment variables only.
- If web UI slows down final submission, fall back to CLI demo plus generated MP4.
- Demo must show the agent working, not just the final artifact.

## Verification commands

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/repo-shorts analyze . --audience "hackathon judges" --out runs --render mp4
```

## Final-mile order

1. Review the web UI plan.
2. Implement only the minimal local UI if approved.
3. Generate fresh live Kimi + MP4 golden run.
4. Record demo showing input, generation, metadata proof, Kimi critique, and output.
5. Tighten X/Discord copy.
6. Submit only after maintainer approval.
