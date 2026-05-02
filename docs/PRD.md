# Repo-to-Shorts Agent PRD

## One-line product

Repo-to-Shorts Agent turns a GitHub repo or local repo into a finished, submission-ready technical short: repo analysis, narrative, visuals, Kimi critic/editor pass, captions, launch copy, and optionally an MP4 render.

## Hackathon goal

Ship a credible Nous Hermes Creative Hackathon demo that proves Hermes can orchestrate a useful creative workflow for technical builders: turning working code into a clear launch story.

## Strategic positioning

Repo-to-Shorts should be positioned as a Hermes creative workflow, not merely a standalone Python script.

Hermes is the harness:
- coordinates repo analysis, file operations, terminal commands, browser/demo artifacts, and creative skills
- provides the agentic execution layer
- makes the workflow reusable as a builder tool

Kimi should be used on two fronts:

1. **Kimi powers the Hermes harness** where possible. The intended demo posture is: Kimi reasons, Hermes acts. In other words, Hermes Agent runs the creative production workflow with Kimi as the model behind the harness.
2. **Kimi reviews the generated package inside the product.** Repo-to-Shorts calls Kimi as a critic/script editor to sharpen hook, narration, risk notes, and CTA.

This two-front strategy is stronger than a token API call because it makes Kimi both the orchestration brain and the visible editorial collaborator.

See `docs/HACKATHON_STRATEGY.md` for the submission narrative and demo framing.

## Current truth

The current repo is an MVP scaffold that generates a browser-recordable short-video package. It does not yet call the live Kimi model and does not yet render an MP4 automatically.

Current shipped path:

```text
repo target
  -> deterministic repo snapshot
  -> deterministic story package
  -> deterministic Kimi fallback / placeholder
  -> Markdown + SVG + SRT + HTML artifacts
  -> user manually screen-records demo.html
```

Target path:

```text
repo target
  -> repo snapshot
  -> story package
  -> live Kimi critic/editor rewrite
  -> visual scenes + captions + narration
  -> browser demo + rendered MP4
  -> X/Discord submission package
```

## Users

Primary user:
- A technical builder who has a working repo but needs a sharp demo video and submission copy quickly.

Hackathon judge view:
- The demo should be understandable in 10 seconds.
- It should show useful creative automation, not just static docs.
- It should prove the Kimi stage if entering the Kimi track.

## Non-goals for hackathon MVP

- Full video editing suite.
- Multi-track timeline editor.
- Social posting automation.
- Perfect voiceover/TTS.
- General-purpose repo intelligence platform.
- Public publishing without user approval.

## Product requirements

### P0, must ship for credible submission

0. Hermes harness positioning

Must document and demonstrate Repo-to-Shorts as a Hermes workflow:
- Hermes orchestrates the run, file generation, and creative artifact assembly.
- Kimi can power the Hermes harness as the selected model/provider.
- Repo-to-Shorts can be invoked cleanly from a Hermes session.
- The final submission explains: Kimi reasons, Hermes acts, Repo-to-Shorts packages the output.

Current status: documented in `docs/HACKATHON_STRATEGY.md`; not yet packaged as a dedicated Hermes skill/workflow.

1. CLI golden path

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

2. Repo ingestion

Must collect:
- README text.
- File tree summary.
- package metadata from `pyproject.toml` or `package.json`.
- recent git log if available.
- git diff/stat if available.

Current status: implemented.

3. Artifact package

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

4. Browser-recordable demo page

Must show:
- Clear hero/hook.
- Story beats.
- Architecture pipeline.
- Kimi critic/editor card.
- Artifact checklist.
- Recording flow.

Current status: implemented and visually checked.

5. Real Kimi critic/editor stage

Must:
- Use `KIMI_API_KEY` when available.
- Call Moonshot/Kimi OpenAI-compatible chat completions.
- Send repo brief + storyboard + audience.
- Ask Kimi to return a sharper hook, critique, revised narration, and final CTA.
- Write actual model output to `kimi_critique.md`.
- Record `mode: live-api` and model name in `metadata.json`.
- Fall back deterministically if no key or API failure.

Current status: not implemented. Placeholder only.

6. Honest Kimi proof for demo

Must show one of:
- `metadata.json` with `kimi.mode = live-api` and model name.
- `kimi_critique.md` containing live model output.
- Terminal command with `KIMI_API_KEY` set and successful run.

Current status: not implemented because live API is not wired.

### P1, should ship if time allows

7. MP4 render

Should generate:
- `demo.mp4`

Acceptable implementation:
- Use generated HTML scenes or simple image cards.
- Render deterministic 60-second MP4 via MoviePy or ffmpeg.
- Include captions or caption-like text overlays.
- Use generated `narration.md` as script, not necessarily audio.

Current status: not implemented. `pyproject.toml` has optional `render = ["moviepy>=1.0"]`, but no rendering code exists.

8. Better story from Kimi

Should allow Kimi to revise:
- hook
- story beats
- narration
- X post
- Discord submission copy

Current status: not implemented.

9. Demo command in README

README should clearly separate:
- current deterministic package generation
- optional live Kimi mode
- optional MP4 render mode

Current status: partially documented, but should be updated once features land.

### P2, nice-to-have

10. TTS voiceover

Generate audio narration with a local or configured TTS provider.

11. Multiple visual themes

Allow `--theme dark-terminal`, `--theme clean-launch`, etc.

12. Input diff mode

Allow:

```bash
repo-shorts analyze . --diff HEAD~1..HEAD
```

13. Direct social draft export

Generate thread variants, Discord post, and LinkedIn post.

## CLI requirements

Target commands:

```bash
repo-shorts analyze . --audience "hackathon judges" --out runs
```

```bash
repo-shorts analyze . \
  --audience "hackathon judges" \
  --out runs \
  --kimi-model "kimi-k2-0905-preview"
```

```bash
repo-shorts render runs/<run-dir> --format mp4
```

If render is folded into analyze:

```bash
repo-shorts analyze . --render mp4 --out runs
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
scenes/
frames/
narration.mp3
```

## Metadata contract

Current:

```json
{
  "target": ".",
  "source_type": "local",
  "repo_name": "repo-to-shorts-agent",
  "audience": "...",
  "created_at": "...",
  "artifacts": [...],
  "kimi": {"mode": "deterministic-fallback"}
}
```

Target:

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
    "model": "kimi-k2-0905-preview",
    "fallback_reason": null
  },
  "render": {
    "mode": "mp4",
    "file": "demo.mp4",
    "duration_seconds": 60
  }
}
```

Fallback example:

```json
"kimi": {
  "mode": "deterministic-fallback",
  "model": null,
  "fallback_reason": "KIMI_API_KEY not set"
}
```

## Acceptance criteria

### Current MVP acceptance

Passes when:

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/repo-shorts analyze . --audience "Nous Research Hermes Agent Creative Hackathon judges" --out runs
```

Expected:
- Tests pass.
- Ruff passes.
- New run directory exists.
- All 11 core artifacts exist.
- `demo.html` opens and is visually screen-recordable.

Current status: passes.

### Live Kimi acceptance

Passes when:

```bash
KIMI_API_KEY=... .venv/bin/repo-shorts analyze . --audience "Nous Research Hermes Agent Creative Hackathon judges" --out runs
```

Expected:
- `kimi_critique.md` contains model-generated critique, not placeholder text.
- `metadata.json` has `kimi.mode = live-api`.
- If API fails, run still succeeds with deterministic fallback and `fallback_reason`.
- Tests cover both live-call mocked path and fallback path.

Current status: not passing because not implemented.

### MP4 acceptance

Passes when:

```bash
.venv/bin/repo-shorts analyze . --audience "Nous Research Hermes Agent Creative Hackathon judges" --out runs --render mp4
```

Expected:
- `demo.mp4` exists.
- Duration is roughly 45-75 seconds.
- File opens locally.
- Visuals show hero, story beats, architecture, Kimi critique, artifact checklist.
- Tests cover render command without requiring external network.

Current status: not implemented.

## What is needed from the operator

### Required

1. Kimi/Moonshot API key

Needed for real Kimi track proof.

Environment variable:

```bash
export KIMI_API_KEY="..."
```

If you do not have one, use the Nous/Kimi hackathon instructions to get access or credits. Without this, we can still submit main track, but Kimi track eligibility is weak.

2. GitHub auth refresh

Local repo is ahead by one commit. Push failed because `gh` token is invalid.

Run:

```bash
gh auth login -h github.com
cd /Users/aiserver/projects/repo-to-shorts-agent
git push origin main
```

3. Final submission decision

Need explicit approval before posting publicly:
- X post under `@Joash0x`.
- Discord submission in `creative-hackathon-submissions`.

### Useful but optional

4. Preferred sample input repo

Default sample is this project itself. Better demo may use:
- Hermes Agent repo
- Repo-to-Shorts repo
- Another small personal agent repo

5. Voice preference

Options:
- The operator records voiceover manually.
- Use generated captions only.
- Add TTS later.

6. Visual preference

Options:
- Dark terminal/agent aesthetic.
- Clean Linear-style product launch aesthetic.
- Hacker demo card style.

## Risks

1. Overclaiming

Do not claim live Kimi or automatic MP4 until implemented. Judges will smell bullshit. They have noses.

2. Kimi API uncertainty

Model name/base URL may differ from docs/account. Implement adapter with configurable model and graceful fallback.

3. Video rendering yak-shave

If MP4 rendering gets slow, use the polished `demo.html` screen recording path. A submitted video matters more than elegant renderer internals.

4. Auth friction

GitHub token is currently invalid locally. Fix before relying on remote repo state.

## Recommended next implementation order

1. Wire live Kimi adapter with tests.
2. Update metadata and README to honestly show Kimi modes.
3. Add optional MP4 render command if time remains.
4. Run golden path.
5. Record submission video.
6. Tighten X/Discord copy.
7. Submit after approval.
