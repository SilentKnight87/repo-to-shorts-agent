# Repo-to-Shorts Agent PRD

## One-line product

Repo-to-Shorts Agent turns a GitHub repo or local repo into a submission-ready technical short package: repo analysis, narrative, visuals, Kimi critic/editor pass, captions, launch copy, browser demo, and optional MP4 render.

## Hackathon goal

Ship a credible Nous Hermes Creative Hackathon demo that proves Hermes can orchestrate a useful creative workflow for technical builders: turning working code into a clear launch story.

Official source:
- X announcement: `https://x.com/NousResearch/status/2045225469088326039`
- Readable mirror: `https://en.rattibha.com/thread/2045225469088326039`

Contest framing: Hermes Agent pushed into creative domains including video, image, audio, 3D, long-form writing, creative software, interactive media, and more. Judging criteria are creativity, usefulness, and presentation. Kimi Track requires proof of Kimi model usage in the submission video.

## Strategic positioning

Repo-to-Shorts should be positioned as a Hermes creative workflow, not merely a standalone Python script.

Hermes is the harness:
- coordinates repo analysis, file operations, terminal commands, browser/demo artifacts, rendering, and creative packaging
- provides the agentic execution layer
- makes the workflow reusable as a builder tool

Kimi is used on two fronts:

1. **Kimi powers the Hermes harness where possible.** The intended demo posture is: Kimi reasons, Hermes acts.
2. **Kimi reviews the generated package inside the product.** Repo-to-Shorts calls Kimi as a critic/script editor to sharpen hook, narration, risk notes, and CTA.

This two-front strategy is stronger than a token model call because Kimi is both the orchestration brain and the visible editorial collaborator.

See `docs/HACKATHON_STRATEGY.md` for submission narrative and demo framing.

## Current truth, May 3

The repo is currently a CLI-first MVP with static output serving. It is not yet an interactive website.

Current shipped path:

```text
repo target, local path or GitHub URL
  -> repo snapshot
  -> deterministic story package
  -> Kimi critic/script-editor, live via OpenRouter when key is present, honest fallback otherwise
  -> Markdown + SVG + SRT + HTML launch artifacts
  -> optional Pillow + ffmpeg vertical MP4
  -> static file server can show generated runs
```

Current non-existent path:

```text
browser form
  -> paste GitHub URL
  -> click Generate
  -> wait for job status
  -> view latest demo.html/demo.mp4 links
```

That web UI is the next planned feature. Until it is built, the product is tested through the CLI and viewed through generated artifacts.

## Current capability table

| Area | Status | Evidence |
| --- | --- | --- |
| CLI golden path | Built | `repo-shorts analyze <target> --out runs` |
| Local repo ingest | Built | `src/repo_to_shorts/ingest.py` |
| Public GitHub URL ingest | Built | shallow clone path in ingest flow |
| Artifact package | Built | `metadata.json`, markdown, SVG, SRT, HTML outputs |
| Browser-recordable `demo.html` | Built | generated every run |
| Live Kimi critic/editor | Built | OpenRouter/Kimi adapter in `src/repo_to_shorts/kimi.py` |
| Honest Kimi fallback | Built | `deterministic-fallback` and `api-error-fallback` metadata modes |
| Optional MP4 render | Built | `--render mp4`, Pillow + ffmpeg, `demo.mp4` |
| Static run viewing | Available ad hoc | local static server over generated `runs/` |
| Interactive web UI | Not built | planned in `docs/plans/2026-05-03-local-web-ui-plan.md` |
| Public posting/submission | Not built by design | requires maintainer approval |

## Users

Primary user:
- A technical builder who has a working repo but needs a sharp demo video and submission copy quickly.

Hackathon judge view:
- The demo should be understandable in 10 seconds.
- It should show useful creative automation, not just static docs.
- It should prove the Kimi stage if entering the Kimi track.

Operator view:
- The local web UI should make the demo feel like a product, not a pile of CLI artifacts.
- The CLI remains the stable engine. The web UI should be a thin wrapper, not a rewrite.

## Non-goals for hackathon MVP

- Full video editing suite.
- Multi-track timeline editor.
- Social posting automation.
- Perfect voiceover/TTS.
- General-purpose repo intelligence platform.
- Hosted SaaS deployment.
- Public publishing without explicit user approval.
- Complex auth. Local-only is enough.

## Product requirements

### P0, already shipped

1. Hermes harness positioning

Must document and demonstrate Repo-to-Shorts as a Hermes workflow:
- Hermes orchestrates the run, file generation, and creative artifact assembly.
- Kimi can power the Hermes harness as the selected model/provider.
- Repo-to-Shorts can be invoked cleanly from a Hermes session.
- The final submission explains: Kimi reasons, Hermes acts, Repo-to-Shorts packages the output.

Current status: documented in `docs/HACKATHON_STRATEGY.md`; not yet packaged as a dedicated Hermes skill/workflow.

2. CLI golden path

Command:

```bash
repo-shorts analyze <repo-or-github-url> \
  --audience "Nous Research Hermes Agent Creative Hackathon judges" \
  --out runs
```

Expected:
- Creates one timestamped run directory.
- Never posts externally.
- Works with no optional credentials.
- Works with local repo targets.
- Works with public GitHub URL targets via shallow clone.

Current status: implemented.

3. Repo ingestion

Must collect:
- README text.
- File tree summary.
- package metadata from `pyproject.toml` or `package.json`.
- recent git log if available.
- git diff/stat if available.

Current status: implemented.

4. Artifact package

Must generate:
- `metadata.json`
- `repo_brief.md`
- `storyboard.md`
- `architecture.svg`
- `narration.md`
- `captions.srt`
- `x_post.md`
- `submission.md`
- `kimi_critique.md`
- `demo.html`
- `recording_instructions.md`

Current status: implemented.

5. Browser-recordable demo page

Must show:
- Clear hero/hook.
- Story beats.
- Architecture pipeline.
- Kimi critic/editor card.
- Artifact checklist.
- Recording flow.

Current status: implemented.

6. Real Kimi critic/editor stage

Must:
- Use `OPENROUTER_API_KEY` or `KIMI_API_KEY` when available.
- Default to OpenRouter model `moonshotai/kimi-k2.6`.
- Send repo brief + storyboard + audience.
- Ask Kimi to return a sharper hook, critique, revised narration, and final CTA.
- Write actual model output to `kimi_critique.md`.
- Record `mode: live-api`, provider, and model name in `metadata.json`.
- Fall back deterministically if no key or API failure.

Current status: implemented.

7. Honest Kimi proof for demo

Must show:
- `metadata.json` with `kimi.mode = live-api`, provider, and model name.
- `kimi_critique.md` containing live model output.
- Terminal command with API key supplied via environment.

Current status: implemented, but final submission still needs a fresh golden run with live credentials.

8. MP4 render

Must generate:
- `demo.mp4` when `--render mp4` is requested.
- render status/proof in `metadata.json`.
- default artifact-only path must still work without render dependencies.

Current status: implemented with Pillow + ffmpeg.

### P0.5, next planned feature

9. Minimal local web UI

Goal: make the product testable and demoable from a browser without pretending it is a hosted SaaS.

Must provide:
- local server command, likely `repo-shorts web`
- page at `/`
- target input for GitHub URL or local path
- audience input
- optional MP4 checkbox
- Kimi model input defaulting to `moonshotai/kimi-k2.6`
- Generate button
- latest runs list
- links to `demo.html`, `demo.mp4`, `metadata.json`, and `kimi_critique.md`
- clear status messages for running/success/failure

Must not:
- publish externally
- store API keys
- expose server publicly by default unless explicitly bound to LAN for local demo
- rewrite the CLI pipeline
- add a database
- require a front-end framework

Current status: planned, not implemented. Detailed plan: `docs/plans/2026-05-03-local-web-ui-plan.md`.

### P1, should ship if time allows

10. Better final-mile submission package

Should include:
- final golden run checklist
- exact recording sequence
- final X copy
- final Discord copy
- proof checklist for Kimi Track

Current status: partially documented in `docs/demo-script.md` and `docs/submission-copy.md`; should be tightened after the web UI decision.

11. TTS voiceover

Generate audio narration with a local or configured TTS provider.

Current status: not implemented.

12. Multiple visual themes

Allow `--theme dark-terminal`, `--theme clean-launch`, etc.

Current status: not implemented.

## CLI requirements

Current commands:

```bash
repo-shorts analyze . --audience "hackathon judges" --out runs
```

```bash
OPENROUTER_API_KEY="***" repo-shorts analyze . \
  --audience "hackathon judges" \
  --out runs \
  --kimi-model moonshotai/kimi-k2.6 \
  --render mp4
```

Planned web command:

```bash
repo-shorts web --host 127.0.0.1 --port 8765
```

Optional LAN demo mode, only when LAN access is desired:

```bash
repo-shorts web --host 0.0.0.0 --port 8765
```

## Output directory contract

Every run directory should contain:

```text
metadata.json
repo_brief.md
storyboard.md
architecture.svg
narration.md
captions.srt
x_post.md
submission.md
kimi_critique.md
demo.html
recording_instructions.md
```

If MP4 render is enabled, also:

```text
demo.mp4
```

Optional future files:

```text
narration.mp3
video_plan.json
```

## Metadata contract

Current successful live + MP4 example:

```json
{
  "target": ".",
  "source_type": "local",
  "repo_name": "repo-to-shorts-agent",
  "audience": "...",
  "created_at": "...",
  "artifacts": [...],
  "kimi": {
    "mode": "live-api",
    "model": "moonshotai/kimi-k2.6",
    "provider": "openrouter",
    "fallback_reason": null
  },
  "render": {
    "mode": "mp4",
    "status": "success",
    "renderer": "pillow+ffmpeg",
    "output": "demo.mp4",
    "scene_count": 5,
    "error": null
  }
}
```

Fallback example:

```json
"kimi": {
  "mode": "deterministic-fallback",
  "model": "moonshotai/kimi-k2.6",
  "provider": "openrouter",
  "fallback_reason": "OPENROUTER_API_KEY/KIMI_API_KEY not set"
}
```

## Acceptance criteria

### Current CLI MVP acceptance

Passes when:

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/repo-shorts analyze . \
  --audience "Nous Research Hermes Agent Creative Hackathon judges" \
  --out runs \
  --render mp4
```

Expected:
- Tests pass.
- Ruff passes.
- New run directory exists.
- Core artifacts exist.
- `demo.html` opens.
- `demo.mp4` exists when render succeeds.
- `metadata.json` records render status honestly.

Current status: passes.

### Live Kimi acceptance

Passes when:

```bash
OPENROUTER_API_KEY="***" .venv/bin/repo-shorts analyze . \
  --audience "Nous Research Hermes Agent Creative Hackathon judges" \
  --out runs \
  --kimi-model moonshotai/kimi-k2.6 \
  --render mp4
```

Expected:
- `kimi_critique.md` contains model-generated critique.
- `metadata.json` has `kimi.mode = live-api`.
- `metadata.json` has `kimi.provider = openrouter`.
- `metadata.json` has `kimi.model = moonshotai/kimi-k2.6`.
- If API fails, run still succeeds with `api-error-fallback` and `fallback_reason`.
- Tests cover mocked live-call path and fallback path.

Current status: implemented; final submission needs a fresh golden run.

### Minimal web UI acceptance

Passes when:

```bash
.venv/bin/repo-shorts web --host 127.0.0.1 --port 8765
```

Expected:
- `/` loads a local page.
- User can enter a GitHub URL or local path and audience.
- User can request MP4 render.
- Submit triggers the existing `run_analysis(...)` pipeline.
- Success page shows links to generated `demo.html`, `demo.mp4` if present, `metadata.json`, and `kimi_critique.md`.
- Latest runs list appears on the page.
- Server serves generated artifacts under `/runs/...`.
- No API keys are shown or stored.
- Tests cover form rendering, successful generate flow with monkeypatched pipeline, validation/failure path, and artifact links.

Current status: not implemented.

## What is needed from the operator

### Required for final Kimi Track proof

1. Live OpenRouter/Kimi key available in environment during the golden run.

Environment variable:

```bash
export OPENROUTER_API_KEY="***"
```

No key should be committed, logged into docs, or shown in the video.

2. Final submission decision

Need explicit approval before posting publicly:
- X post under `@Joash0x`.
- Discord submission in `creative-hackathon-submissions`.

### Useful but optional

3. Preferred sample input repo

Default sample is this project itself. Better demo may use:
- Repo-to-Shorts repo
- Hermes Agent repo
- another small personal agent repo

4. Voice preference

Options:
- The operator records voiceover manually.
- Use generated captions only.
- Add TTS later.

## Risks

1. Moving blind

Building features without a current plan makes the project feel random. Fix: keep PRD and implementation plans current before implementation.

2. Overclaiming

Do not claim interactive web UI until implemented. Do not claim live Kimi unless `metadata.json` shows `live-api` from a fresh run.

3. Local networking friction

LAN demo requires binding to `0.0.0.0` and may need macOS firewall permissions. Default should remain `127.0.0.1` for safety.

4. Video rendering yak-shave

If MP4 rendering gets slow or brittle, use `demo.html` and generated copy. A submitted video matters more than elegant renderer internals.

## Recommended next order

1. Review and approve `docs/plans/2026-05-03-local-web-ui-plan.md`.
2. Build minimal local web UI using existing pipeline, not a rewrite.
3. Run tests/lint.
4. Generate a fresh live Kimi + MP4 golden run.
5. Record final demo showing web UI, metadata proof, Kimi critique, and output artifacts.
6. Tighten X/Discord copy.
7. Submit only after maintainer approval.
