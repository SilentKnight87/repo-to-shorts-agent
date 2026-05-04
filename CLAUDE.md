# CLAUDE.md — Repo-to-Shorts Agent

Guidance for Claude Code sessions working on this repo. Keep this file current. If something here contradicts the code, fix the file.

## What this is

Hackathon submission for the Nous Research Hermes Agent Creative Hackathon (Kimi Track). The project takes a GitHub repo or local directory and produces a 45-60 second 9:16 launch video plus submission copy.

The submission angle: **a real Hermes Agent skill, not Nous-branded chatbot wrapping**. The skill at `.hermes/skill/SKILL.md` is the load-bearing integration. Hermes invokes the underlying CLI; Kimi K2.6 directs the storyboard. Two layers of Kimi (Hermes's underlying model + the in-pipeline creative director), one Hermes loop.

## Read before editing

- `AGENTS.md` — the canonical architecture description, file map, hackathon priorities
- `README.md` — public-facing description; keep it honest with what the code does
- `.hermes/skill/SKILL.md` — the Hermes Agent skill (verification rules matter; don't fabricate Kimi proof)
- `docs/HACKATHON_STRATEGY.md` — positioning and judging strategy
- `docs/superpowers/specs/2026-05-04-remotion-final-renderer-design.md` — current rendering architecture (Pillow + Remotion fallback chain)

## Pipeline shape

Three surfaces, one engine:

1. **Hermes REPL** → `/repo-shorts-creative <target>` — the hackathon-correct path
2. **CLI** → `repo-shorts creative <target> --final` — what the skill shells out to
3. **Web UI** at `127.0.0.1:8765` → same `run_creative_pipeline()` call

Engine path:
```
ingest → Kimi creative director → render (Remotion if available, else Pillow) → TTS + music → validate → write metadata + submission_pack
```

`metadata.json` is the proof artifact. Never fake `kimi.mode=live-api`.

## Parallel-session conventions

When multiple agents work this repo simultaneously (Claude + Codex + OpenCode), claim file ownership explicitly. The 2026-05-04 hackathon push had Codex and OpenCode independently rewrite `creative_director.py` because both followed the same design spec — duplicated work, near-conflict on merge. Avoid this.

**Convention:**
- Briefs to delegated agents must list `do not touch` files explicitly
- Use `docs/codex/<date>-<topic>.md` and `docs/opencode/<date>-<topic>.md` for stable hand-off specs (don't copy-paste each turn)
- Worktrees are great for parallel work but require rebasing onto main before merge — don't accumulate stale branches

## Time-pressure conventions

This repo got built to ship under hackathon clock. When deadline is hours away:
- Prefer correctness over completeness — a working subset beats a half-done full feature
- Smoke-test live golden runs before T-30min, never at T-5min
- Keep the fallback floor obvious — most recent successful `runs/<timestamp>/` is the worst-case submission
- Test suite is the contract; if `pytest -q` fails, stop

## Don't

- Commit secrets. Period. `.env` is gitignored; `runs/` is gitignored.
- Claim live Kimi when the call fell back. The metadata records the truth — don't override it.
- Add backwards-compat shims for hypothetical migrations the project will never do.
- Add features beyond the brief. The hackathon is in hours, not days.
- Refactor adjacent code while fixing a bug. Stay focused.

## Do

- Run `.venv/bin/python -m pytest -q` before declaring work done.
- Update `metadata.json`'s `render.renderer` honestly when changing rendering paths.
- Keep the skill's procedure in sync between `.hermes/skill/SKILL.md` and `~/.hermes/skills/video/repo-shorts-creative/SKILL.md`.
- Cite file paths with line numbers when discussing code.

## Hackathon priority order

1. Live Kimi proof in `metadata.json`
2. Hermes Agent skill integration intact
3. Pipeline reliability (5+ scenes, 45-60s, validated MP4)
4. Web UI legibility — SKILL badge in hero must stay
5. Submission copy honest and concise
