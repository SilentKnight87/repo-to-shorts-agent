# AGENTS.md — Repo-to-Shorts Agent

This repo is a hackathon MVP for the Nous Research Hermes Agent Creative Hackathon / Kimi Track.

## Product

Repo-to-Shorts turns a local Git repo or GitHub URL into a launch-ready short-video package:

- repo brief
- storyboard
- architecture SVG
- narration script
- captions SRT
- X post copy
- Discord submission copy
- Kimi critic/editor pass
- browser-recordable `demo.html`
- optional 9:16 `demo.mp4`
- recording instructions

This is not a full video editor and does not currently publish anything externally.

## Core architecture

```text
src/repo_to_shorts/cli.py
  -> pipeline.run_analysis()
  -> ingest.ingest_target()
  -> pipeline.build_story()
  -> kimi.critique_story()
  -> render Markdown/SVG/SRT/HTML artifacts into runs/<timestamp>-<repo>/
  -> optional render.render_video() for --render mp4
```

Key files:

- `src/repo_to_shorts/cli.py`: Typer CLI entrypoint.
- `src/repo_to_shorts/ingest.py`: local/GitHub repo snapshotting.
- `src/repo_to_shorts/pipeline.py`: artifact generation pipeline.
- `src/repo_to_shorts/kimi.py`: OpenRouter/Kimi critic adapter with deterministic fallback.
- `src/repo_to_shorts/render.py`: optional Pillow + ffmpeg vertical MP4 renderer.
- `tests/test_pipeline.py`: pipeline/CLI/integration coverage.
- `tests/test_kimi.py`: Kimi adapter tests, mocked network only.
- `tests/test_render.py`: renderer tests, with no real ffmpeg dependency except explicit smoke/golden runs.
- `docs/HACKATHON_STRATEGY.md`: positioning and judging strategy.
- `docs/PRD.md`: product requirements.
- `docs/demo-script.md`: recording plan.
- `docs/submission-copy.md`: X/Discord copy.
- `docs/plans/2026-05-03-local-web-ui-plan.md`: next planned feature, a minimal local browser UI around the existing CLI engine.

## Environment and secrets

Never commit API keys, tokens, `.env`, run outputs, or credentials.

`.gitignore` intentionally excludes:

```text
.env
.env.*
runs/
.venv/
```

Live Kimi via OpenRouter uses environment variables only:

```bash
export OPENROUTER_API_KEY="[REDACTED]"
repo-shorts analyze . \
  --audience "Nous Research Hermes Agent Creative Hackathon judges" \
  --out runs \
  --kimi-model moonshotai/kimi-k2.6
```

Do not paste real keys into docs, tests, fixtures, commits, issue comments, or PR descriptions.

Before committing, scan for secrets:

```bash
git diff --cached
rg -n "sk-or-v1|OPENROUTER_API_KEY=.*sk|KIMI_API_KEY=.*sk|[A-Za-z0-9_\-]{40,}" . --glob '!runs/**' --glob '!.venv/**'
```

If a real key ever lands in git history, stop and rotate the key. Do not just delete the line and pretend the dragon went back in the cave.

## Development setup

```bash
/opt/homebrew/bin/python3.13 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pip install -e '.[render]'  # optional MP4 support
```

Run checks:

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
```

Generate a deterministic no-key run:

```bash
.venv/bin/repo-shorts analyze . \
  --audience "Nous Research Hermes Agent Creative Hackathon judges" \
  --out runs
```

Generate a live Kimi run, key provided via environment only:

```bash
OPENROUTER_API_KEY="***" .venv/bin/repo-shorts analyze . \
  --audience "Nous Research Hermes Agent Creative Hackathon judges" \
  --out runs \
  --kimi-model moonshotai/kimi-k2.6 \
  --render mp4
```

Generate an optional MP4 run, requires Pillow plus `ffmpeg`/`ffprobe`:

```bash
.venv/bin/repo-shorts analyze . \
  --audience "Nous Research Hermes Agent Creative Hackathon judges" \
  --out runs \
  --render mp4
```

## Kimi behavior

`critique_story()` must remain honest and reliable:

- no key: `mode=deterministic-fallback`
- API error: `mode=api-error-fallback`
- live success: `mode=live-api`, `provider=openrouter`, `model=moonshotai/kimi-k2.6`

`metadata.json` is the proof artifact for the demo. Do not fake live model usage.

Network calls must not run in tests. Use monkeypatch/mocks around `_call_openrouter_api()` or `urllib.request.urlopen`.

## Render behavior

`--render mp4` is optional. It must never break the default artifact-only path.

- Keep renderer dependencies optional under the `render` extra.
- Require `ffmpeg` and `ffprobe` for real MP4 generation.
- Record render status in `metadata.json` under `render`.
- Add `demo.mp4` to the artifact manifest only when MP4 rendering is requested.
- Prefer simple, deterministic Pillow scene cards over fragile creative dependencies.

## Planned web UI behavior

The web UI is not implemented yet. When added, it should wrap `pipeline.run_analysis(...)`; it must not fork the generation logic.

Safe defaults:
- default host: `127.0.0.1`
- explicit LAN demo: `--host 0.0.0.0`
- API keys stay in environment variables only
- no database
- no external publishing

See `docs/plans/2026-05-03-local-web-ui-plan.md` before building.

## Coding rules

- Keep the golden path reliable without credentials.
- Do not add external posting, browser automation, or public submission behavior without explicit approval from the operator.
- Prefer small, tested changes over big rewrites.
- Add tests before behavior changes.
- Keep generated `runs/` out of git.
- Keep docs truthful. If the code only creates a package, do not claim it renders finished media. If `--render mp4` works, describe it as optional generated MP4, not a full video editor.

## Commit checklist

Before commit:

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
git status --short
```

Then inspect the staged diff:

```bash
git diff --cached
```

Recommended commit message style:

```text
feat: add live openrouter kimi critic
docs: update hackathon demo script
polish: improve demo artifact checklist
```

## Hackathon priority order

1. Preserve live Kimi proof in generated artifacts.
2. Review and follow the local web UI plan before implementation.
3. Keep the demo browser-recordable and legible.
4. Make X/Discord copy concise and honest.
5. Keep optional MP4 rendering honest and stable.

Presentation beats clever machinery. Shipping beats architecture fan fiction.
