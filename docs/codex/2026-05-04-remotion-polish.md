# Codex Task — Remotion Visual Polish (after wiring lands)

**Created:** 2026-05-04 ~02:10 (~2.5 hours before deadline)
**Owner:** Codex (in `.worktrees/remotion-final-renderer`)
**Trigger:** Run this AFTER you've committed the `hermes_skill.py` ↔ Remotion wiring, not before.

## Scope

Iterate on visual quality of `remotion/src/RepoShortsVideo.tsx` and the per-scene components. The plumbing is solid — now make the video stop looking AI-generated.

**Do NOT touch:**
- `src/` Python (other than the wiring already in flight)
- `docs/`, `README.md`, `AGENTS.md`
- `tests/` unless a test breaks
- `.hermes/`, `.claude/`, `.worktrees/`

## What "non-slop" looks like

The current Pillow renderer's failure mode (see `runs/20260504-002134-repo-to-shorts-agent/contact_sheet.jpg`) is: identical bokeh background on every scene, repeated static cards 01 and 02, generic "Core/Cli/Pipeline" architecture box diagram, oversized bottom caption boxes.

Anti-pattern checklist — must avoid:
- Same gradient/background on every scene
- Bottom caption box that appears on every scene at the same position
- Architecture boxes connected by lines as the centerpiece
- Bokeh, dark blob, generic abstract shapes
- Centered text on a flat color (looks like a slideshow)
- Duration drift — scenes must respect `duration_seconds` from the manifest

What to do instead:
- **Kinetic typography** — text moves, scales, breaks. `interpolate` and `spring` are your friends. Letters can enter staggered.
- **Repo evidence as cinematic proof** — file paths, code excerpts, metadata fields rendered as designed UI elements that animate in. Not floating cards; integrated panels.
- **One primary visual idea per scene type** — ColdOpen is huge text + minimal motion; PipelineMap is sequential reveals along a flow line; LiveProof is a metadata.json viewport with the kimi fields highlighting; CTAEndCard is the command + GitHub URL in monospace.
- **Vary the canvas per scene** — different layout grids, different focal points. The viewer should never feel "another scene from the same template."
- **Captions** — short, integrated into the layout (not a karaoke bar at the bottom). Use `caption_emphasis` from the manifest to size/color specific words.

## Reference

The Kimi prompt now produces a structured `storyboard` with these scene types: `ColdOpen`, `RepoEvidence`, `PainPoint`, `PipelineMap`, `ArtifactStack`, `LiveProof`, `DemoPreview`, `CTAEndCard`. Build polished components for at minimum: `ColdOpen`, `PipelineMap`, `LiveProof`, `CTAEndCard`. Stretch: `RepoEvidence` and `DemoPreview`.

Color palette is your call but stay coherent. The web UI's VHS aesthetic uses: `--bg: #0b0707`, `--ink: #f0e8d8`, `--lock: #4afa8c`, `--rec: #ff5e5e`, fonts Anton (display) + JetBrains Mono. Picking up that palette will create cross-surface consistency between the rendered MP4 and the web UI screenshot.

## Acceptance

- `npm run render:remotion` produces a 1080×1920 30fps MP4 from a real manifest (`runs/<latest>/render/remotion_input.json`).
- A contact sheet of 6-12 frames shows visually distinct scenes — no two scenes look like the same template.
- `interpolate` and `spring` are used in at least 3 scenes to drive motion.
- Captions never sit in a uniform bottom bar across scenes.
- `metadata.json` `render.renderer` reads `remotion` when this path runs.
- 117 (or current count) Python tests still pass.

## Time budget

Hard stop at T-30min before deadline (~04:30 local). If at that point any scene looks unfinished, switch its component to a clean fallback (just headline + supporting line + manifest evidence list, no clever motion). Honest minimum > broken motion.

## Reporting

When done, report:
1. Path to the rendered MP4
2. Path to the contact sheet
3. Which scene types you built vs. left as defaults
4. Any uncertainty about visual direction (we'll arbitrate fast)
