# Hermes Creative Agency Design

- **Date:** 2026-05-04
- **Status:** Proposed direction
- **Scope:** Research-backed design plan for post-hackathon polish. No implementation in this document.
- **Chosen direction:** Option B, Hermes Creative Agency.

## Goal

Turn Repo-to-Shorts from a working hackathon MVP into a taste-driven creative production workflow.

The product should feel less like "one prompt creates a video" and more like a small creative team that understands the repository, chooses a visual and audio treatment, produces the short, critiques it, and only then declares it ready.

The output target is still practical:

- local repo or GitHub URL in
- audience prompt in
- repo-informed short-video package out
- honest Kimi/OpenRouter proof in metadata
- browser workflow works end to end
- final video is polished enough to publish, not merely valid enough to render

## Current State

The current codebase has the right foundation:

- `src/repo_to_shorts/web.py` exposes the local website and `/generate` flow.
- `src/repo_to_shorts/hermes_skill.py` is the creative pipeline coordinator.
- `src/repo_to_shorts/creative_director.py` asks Kimi for creative direction.
- `src/repo_to_shorts/remotion_render.py` and the Remotion app provide the best current final-render path.
- `src/repo_to_shorts/render.py` remains the lower-dependency Pillow/ffmpeg renderer.
- `metadata.json` records Kimi and render proof.

Validation from the current review:

- `pytest -q` passed with 136 tests.
- `ruff check .` passed.
- A real local website `/generate` smoke run completed without API keys.
- The smoke run produced artifacts, but preview mode yielded a 13 second no-audio MP4 and `validation.ok=false`.
- The success page still presented the run as complete even when preview validation failed.

That means the project works mechanically, but the post-hackathon polish target is not simply "make tests pass." The gaps are workflow truthfulness, final-video taste, audio direction, and QA.

## README And Product Truth Review

The README should be treated as aspirational until implementation catches up.

Claims that need tightening or backing:

- "Turn any GitHub repo into a 60-second animated creative short" should distinguish preview mode from final mode.
- "All of this runs from one browser click" is only true when local dependencies and optional credentials are configured.
- The contact sheet / visual QA language should map to actual generated files and gates.
- The website should not call a validation-failed preview a completed broadcast.

Recommendation: split public language into three modes:

1. **Deterministic package mode:** always works without keys, produces written/HTML/SVG artifacts.
2. **Preview video mode:** fast MP4 smoke path, allowed to be short and no-audio, clearly labeled preview.
3. **Final video mode:** 45-60s, audio policy enforced, taste QA enforced, validation must pass before success language.

## Research Inputs

### Creative Excellence Patterns

The first version of this plan researched available tools and local Hermes skills more deeply than it researched how excellent creative-agent workflows are built. This addendum closes that gap.

The strongest public pattern is not "give one model every tool and hope." Anthropic's agent guidance separates predictable workflows from more autonomous agents, and recommends simple, composable patterns before adding complexity. Two patterns map directly to Repo-to-Shorts:

- **Orchestrator-workers:** Kimi acts as director, decomposes the creative job, and delegates to specialist roles.
- **Evaluator-optimizer:** the renderer creates a draft, a critic grades it against explicit criteria, and the system performs a bounded revision loop.

The `12-factor-agents` project makes the same practical point from a production angle: strong agent products are mostly deterministic software with LLM calls inserted at the points where language, judgment, or adaptation create leverage. That supports this plan's spine: deterministic evidence, manifests, rendering, and validation, with Kimi making creative direction decisions through structured contracts.

Short-form video references point to a similar rule: quality is not just visual polish. TikTok's creator guidance emphasizes vertical format, captions/context, creative effects/sounds, watch time, and learning from analytics. YouTube Shorts documentation emphasizes vertical uploads, previewing, text-to-speech, effects, and engaged-view measurement. For Repo-to-Shorts, that means taste QA should score:

- first 1-3 seconds: does the viewer understand the product and why to care?
- vertical composition: does every scene read on mobile?
- captions: are they readable, timed, and not hidden by platform UI?
- sound: does voice/music/sfx support retention instead of masking the message?
- watchability: is there a visual or semantic reason to keep watching through every beat?

Motion-design references also matter. Material Design frames motion as a way to show structure, guide focus, indicate hierarchy, and add polish. Apple HIG warns against gratuitous motion and treats animation as support for feedback, state, and instruction. The QA harness should therefore reject animation that is merely decorative. Motion must reveal architecture, focus attention, prove a claim, or make a transition understandable.

For image/video generation, the ComfyUI research direction is especially relevant. Recent papers such as ComfyGen, ComfyGI, ComfyGPT, and ComfySearch all converge on the same point: high-quality generative output comes from prompt-adaptive workflows, workflow optimization, self-optimizing multi-agent systems, and validation-guided construction. This argues against a single fixed ComfyUI workflow for every repo. Repo-to-Shorts should use Kimi to select a small workflow family from the repo's creative brief, then use QA to decide whether generated assets are good enough for the final cut.

Evaluation research and tooling point to a final constraint: LLM-as-judge is useful, but it cannot be the only gate. Good creative QA should combine deterministic checks, trajectory/tool-call checks, small replayable eval sets, and LLM/vision critic review. A taste critic can grade visual hierarchy and narrative fit; code should still enforce duration, resolution, audio stream, caption bounds, artifact presence, and proof metadata.

### Practical Takeaways For This Product

The plan should treat "taste" as an operational system:

1. **Reference bank:** maintain examples of excellent and rejected outputs, with notes explaining why.
2. **Taste rubric:** make Kimi write the rubric before rendering, then grade against it after rendering.
3. **Agent traces:** record every role decision, tool choice, asset request, and critique result in production manifests.
4. **Bounded iteration:** allow one draft/revise cycle by default; more loops require explicit final-mode budget.
5. **Prompt-adaptive tool routing:** choose Pretext, p5.js, Manim, ComfyUI, ASCII, or plain Remotion based on repo identity and scene purpose.
6. **Human-calibrated eval set:** collect 20-50 known repos/runs over time with expected quality notes, then replay them before changing creative prompts or adapters.
7. **No vibe-only success:** a final run is publishable only when deterministic validation and taste QA both pass.

### Hermes Skills

Hermes skills are the right abstraction for repeatable creative procedures, not for hiding all runtime complexity inside a single prompt. The local Hermes skill inventory includes:

- `creative/comfyui`: image, video, audio, and 3D generation through ComfyUI with lifecycle, REST/WebSocket execution, workflow parameter injection, dependency checks, and example workflows including AnimateDiff and Wan T2V.
- `creative/manim-video`: programmatic technical explainers, algorithm visualization, architecture diagrams, and educational animation with a strong first-render quality bar.
- `creative/p5js`: browser-based generative art, kinetic typography, shaders, WebGL, audio-reactive visuals, and frame/video export.
- `creative/pretext`: DOM-free text measurement/layout for kinetic typography and text-as-geometry visuals.
- `creative/architecture-diagram`: repo and system structure visualization.
- `creative/ascii-video` and `creative/ascii-art`: terminal/retro treatments when the repo's identity supports it.
- `creative/songwriting-and-ai-music`: music ideation and prompt craft.
- `creative/popular-web-designs`, `creative/design-md`, `creative/claude-design`: design-language references and visual direction.

Official Hermes docs frame skills as procedural memory and capability bundles that can wrap CLIs/APIs. That matches this product: Kimi should decide what kind of creative work is needed, then the pipeline should call narrow tools with structured contracts.

### Rendering And Video Tooling

Remotion is the strongest final assembly layer because it creates real MP4s with React, parameterized data, deterministic timing, captions, and local/server rendering. It should remain the final editor.

ComfyUI is useful for controlled accent assets, not as the main editor. Its API supports queued prompt execution, `/prompt`, `/history/{prompt_id}`, `/view`, `/queue`, and `/ws` progress. This makes it viable for 2-5 second generated inserts or poster frames, but those outputs must be bounded by QA and fallbacks.

Manim is strong for technical explainers and architecture scenes where clarity matters more than cinematic novelty. It should produce small clips or transparent overlays for specific scene types, not own the full short.

p5.js and Pretext are strong for repo-native visual identity: code-as-text, typography motion, generative backgrounds, flow fields, package graphs, and title treatments. They can produce deterministic frame sequences or HTML captures that Remotion assembles.

Runway, Luma, and Veo-style APIs are plausible future adapters for high-cinematic accent clips. They carry cost, latency, model drift, and reproducibility risk, so they should be an optional "cinema lab" lane after the deterministic spine is solid.

ElevenLabs and similar voice/sound APIs are useful for narration, sound effects, and possibly music, but the product needs an audio policy before adding more providers.

## Product Direction

Build a **Hermes Creative Agency** workflow.

Kimi 2.6 remains the creative director, but the pipeline stops treating Kimi as the only creative worker. Instead, it produces a structured production brief and delegates narrow work to specialist lanes:

```text
Repo ingest
  -> Evidence curator
  -> Kimi creative director
  -> Visual designer
  -> Sound designer
  -> Editor / renderer
  -> Taste QA critic
  -> One revision pass
  -> Final package
```

The critical design choice: keep a deterministic edit spine. Remotion owns timing, composition, captions, audio ducking, and final MP4 assembly. Generative skills contribute assets and scene ideas through contracts.

## Agency Roles

### Evidence Curator

Input: ingested repo snapshot.

Output: safe, visualizable repo evidence.

Responsibilities:

- identify product purpose, key files, architecture, install/run path, and proof artifacts
- select evidence that can appear on screen without secrets
- write an evidence manifest with file paths, snippets, commands, and redaction status
- feed only curated evidence to creative roles

This role reduces hallucinated product claims and keeps the video grounded in the repo.

### Kimi Creative Director

Input: repo analysis, audience, evidence manifest, available skill inventory.

Output: production brief.

Responsibilities:

- choose the core angle and audience promise
- choose visual language based on repo type
- decide voiceover vs music-forward vs hybrid
- assign scene treatments to tools
- define what would count as "slop" for this repo
- define the QA rubric before rendering

Kimi should output object-shaped JSON and never be asked to produce the final video directly.

### Visual Designer

Input: production brief and evidence manifest.

Output: scene asset plan plus generated deterministic assets.

Responsibilities:

- choose scene templates from Remotion, Manim, p5.js, Pretext, architecture diagram, or ComfyUI accent lanes
- generate or request assets through narrow adapters
- produce stills/contact sheets before final video render
- keep every scene tied to repo evidence or product narrative

### Sound Designer

Input: production brief, narration script, scene timings.

Output: audio plan and audio assets.

Responsibilities:

- decide voiceover, music, sound effects, or silence
- choose voice tone and pacing
- generate or select music bed when useful
- enforce ducking rules so music never overwhelms voiceover
- produce audio metadata: provider, model, duration, loudness, failure mode

MVP audio policy:

- voiceover-first for repo explainers
- music bed optional and quiet under narration
- music-only only when the visual story is self-explanatory
- no final success if audio is required but missing

### Editor / Renderer

Input: scene plan, assets, audio plan.

Output: MP4 plus render metadata.

Responsibilities:

- assemble the final short in Remotion
- keep 1080x1920, 30fps, 45-60s for final mode
- align captions, cuts, voice beats, and motion cues
- enforce safe area and mobile readability
- record exact renderer, input manifest, assets used, and validation result

### Taste QA Critic

Input: contact sheets, frame samples, metadata, audio stats, ffprobe output, maybe a vision-model review.

Output: pass/fail with concrete revision instructions.

Responsibilities:

- reject generic slide decks
- reject unreadable captions or crowded scenes
- reject mismatched style, random palettes, or repeated layouts
- reject fake proof, missing metadata, or unsupported claims
- reject final outputs outside duration/audio requirements
- allow one bounded revision pass before final failure

This should be a real harness, not a vibes-only postscript.

## Scene Strategy

The creative director should choose from a scene vocabulary, not invent arbitrary video grammar each run.

Core scene types:

- `ColdOpen`: product understood in the first 3 seconds without audio.
- `RepoIdentity`: repo name, purpose, language/framework, key entrypoint.
- `Problem`: why this repo matters or what pain it solves.
- `Mechanism`: architecture or workflow reveal.
- `Proof`: live Kimi metadata, generated artifacts, tests, commands, or screenshots.
- `VisualSignature`: repo-specific aesthetic moment, often p5.js/Pretext/Manim/ComfyUI.
- `Result`: what the viewer gets.
- `CTA`: command, output folder, or publish-ready package.

Tool routing:

| Scene need | Preferred tool |
|---|---|
| final edit, captions, layout, timing | Remotion |
| architecture / algorithm / system mechanism | Manim or architecture-diagram |
| kinetic typography / source-code motion | Pretext or Remotion |
| generative visual identity / data-driven texture | p5.js |
| cinematic accent shot / poster / mood clip | ComfyUI, later Runway/Luma/Veo |
| terminal / retro repo identity | ASCII video/art |
| narration/music/sfx | audio adapter plus sound designer policy |

## Workflow Contract

Add a new intermediate package under each run:

```text
runs/<timestamp>-<repo>/
  production/
    evidence_manifest.json
    creative_brief.json
    scene_plan.json
    asset_manifest.json
    audio_plan.json
    qa_report.json
    contact_sheet.jpg
```

### `creative_brief.json`

```json
{
  "schema_version": 1,
  "angle": "repo-native launch short",
  "audience": "technical judges",
  "tone": "sharp, cinematic, builder-focused",
  "visual_language": {
    "palette": ["#0b0707", "#f0e8d8", "#ff8c4a", "#38d8ff"],
    "motion": "fast editorial cuts with readable proof beats",
    "avoid": ["generic dashboard cards", "random gradients", "unverified claims"]
  },
  "audio_direction": {
    "mode": "voiceover_with_ducked_music",
    "voice": "calm technical narrator",
    "music": "low-volume repo-themed pulse"
  },
  "scene_assignments": [
    {
      "scene_id": "cold_open",
      "tool": "remotion",
      "purpose": "explain product instantly",
      "evidence": ["repo.name", "repo.summary"]
    }
  ],
  "qa_rubric": {
    "must_pass": [
      "first 3 seconds explain product without audio",
      "captions readable on mobile",
      "Kimi proof visible and honest",
      "final duration 45-60 seconds",
      "music does not mask voiceover"
    ]
  }
}
```

### `qa_report.json`

```json
{
  "schema_version": 1,
  "overall": "fail",
  "score": 0.68,
  "blocking_issues": [
    {
      "category": "duration",
      "evidence": "ffprobe duration 13.0s",
      "fix": "render final mode, not preview mode"
    }
  ],
  "taste_issues": [
    {
      "category": "visual_repetition",
      "evidence": "4 of 6 sampled frames use the same centered card layout",
      "fix": "replace one proof scene with kinetic source-code treatment"
    }
  ],
  "allowed_to_publish": false
}
```

## Taste QA Harness

The QA harness should combine deterministic checks and critic review.

Deterministic checks:

- ffprobe duration, resolution, fps, audio stream presence
- caption file exists and timestamps fit duration
- `metadata.json` Kimi mode/provider/model present
- final mode duration is 45-60 seconds
- audio loudness/ducking meets threshold when voiceover and music coexist
- no obvious secret patterns in rendered text inputs
- run manifest includes expected artifacts

Visual checks:

- sample frames at scene boundaries
- generate contact sheet
- OCR or layout probes for caption readability if practical
- image histogram/blank-frame detection
- repeated-layout detection using frame similarity

Critic review:

- feed the creative brief, contact sheet, metadata, and frame notes into Kimi or another critic model
- require structured output with pass/fail and concrete fixes
- allow exactly one revision pass by default
- never let critic text override deterministic failures

The critic rubric should have concrete categories:

| Category | Pass condition | Failure examples |
|---|---|---|
| Hook | product and payoff are legible in 1-3 seconds | starts with abstract context, logo-only intro, or slow preamble |
| Evidence | claims map to repo/artifact/proof fields | generic "AI magic" claims, no visible repo evidence |
| Visual hierarchy | one primary idea per scene | crowded cards, random decorative layers, unreadable code |
| Motion | movement reveals structure or guides focus | constant ambient motion, transitions with no meaning |
| Rhythm | cuts match narration/music beats | long dead holds, rushed proof, no beat contrast |
| Audio | voice/music/sfx support the story | music masks voice, no sonic cue on key transitions |
| Captions | readable on mobile and safe from platform UI | tiny text, bottom UI collision, no emphasis words |
| Originality | repo-specific visual identity | same template/palette for every repo |
| Craft | feels intentionally edited | repeated layout, blank frames, rough timing |
| Truth | metadata and mode are honest | fake live proof, hidden validation failure |

For agent QA, evaluate both output and trajectory:

- did Kimi choose tools that match the scene purpose?
- did any specialist ignore the production brief?
- did the renderer use all required proof/evidence beats?
- did the critic catch known blockers?
- did the revision actually address the critic's findings?

This turns "knowing good creative" into a recorded decision process that can improve over time.

## Reference Bank

Create a repo-local reference bank before adding more creative adapters:

```text
docs/creative-reference-bank/
  README.md
  excellent/
    remotion-code-proof.md
    manim-architecture-reveal.md
    pretext-kinetic-source.md
    p5-generative-identity.md
  rejected/
    generic-slide-deck.md
    unreadable-captions.md
    fake-proof.md
    overgenerated-cinematic-noise.md
```

Each reference note should include:

- why it is excellent or rejected
- which QA rubric categories it touches
- visual/audio traits worth copying or avoiding
- a local or external source link when available
- a small still/contact-sheet image if rights and storage constraints allow

This gives future Kimi/Hermes runs a taste memory that is more concrete than adjectives like "beautiful" or "cinematic."

## Website Fixes Needed Before Big Creative Work

The website should be made truthful before adding more generative power.

Required changes:

1. Label preview runs as preview/draft, not broadcast complete.
2. Show validation status prominently when `validation.ok=false`.
3. Wire the SP/LP/EP and DOLBY/OFF toggles correctly; the current markup/JS selector contract appears mismatched.
4. Expose final mode as a deliberate control with dependency warnings.
5. Keep API keys in environment variables only.
6. Make generated run pages link to production manifests, metadata, QA report, MP4, and submission pack.

## Implementation Phases

### Phase 0: Creative reference sweep

Deliverables:

- collect 15-30 public examples from X, GitHub, YouTube, Remotion examples, ComfyUI workflows, design galleries, and short-form launch videos
- classify each example as excellent, useful-but-flawed, or rejected
- extract the specific traits worth copying or avoiding
- seed `docs/creative-reference-bank/`
- convert the findings into 8-12 concrete QA checks before writing creative-adapter code

This phase should be time-boxed. The goal is not infinite taste research; it is to give Kimi, Hermes, and the QA critic concrete examples before implementation starts.

Current acquisition routes:

- **X API via Mac Mini `xurl`:** `/opt/homebrew/bin/xurl` is installed and authenticated for `@Joash0x`; profile and home timeline reads work. Recent search, bookmarks, and user-tweet timeline reads currently return authorization errors, so the app/token needs search/bookmark/timeline access fixed before relying on API search.
- **Known-account X reads:** even without search, known public accounts can be profiled and manually sampled through URLs or browser fallback. Useful starting accounts include `@v0`, `@ComfyUI`, `@Remotion`, `@RunwayML`, `@LumaLabsAI`, `@elevenlabsio`, and agent/eval builders.
- **Grok/xAI:** the Mac Mini has an `XAI_API_KEY` available in Hermes environment. Use it only through scripts/agents that do not print secrets. Grok can help summarize/cluster examples, but source links and raw examples should still be captured because model summaries are not evidence.
- **Browser fallback:** if API search remains blocked, use browser-based public search/extraction for targeted queries and save URLs/screenshots/notes into the reference bank.
- **Hermes oneshot:** Hermes can be invoked over SSH, but do not give it broad social autonomy. Use read-only prompts with explicit constraints and have it write a local markdown report, not post, like, follow, DM, or mutate account state.

### Phase 1: Truthful demo and QA surface

Deliverables:

- web UI distinguishes preview/final states
- validation failure is visible in success/error pages
- toggle markup and JS contract fixed
- README language split by deterministic/preview/final modes
- smoke test covers web `/generate` preview semantics

This phase addresses the current "demo not fully working" concern before adding more tools.

### Phase 2: Production manifests

Deliverables:

- `evidence_manifest.json`
- `creative_brief.json`
- `scene_plan.json`
- `asset_manifest.json`
- `audio_plan.json`
- `qa_report.json`
- tests for schema validation and no-secret evidence selection

This makes the workflow inspectable and gives Kimi/Hermes handoff points.

### Phase 3: Taste QA harness

Deliverables:

- contact sheet generation
- deterministic QA checks
- structured critic pass
- one revision loop
- final mode refuses publish language unless QA passes
- output/trajectory scoring for role handoffs and tool choices
- a seed reference bank of excellent/rejected creative examples

This creates the "slop/good" evaluator the product currently lacks.

### Phase 4: Creative specialist adapters

Deliver adapters in this order:

1. Pretext/Remotion kinetic typography for repo/source-code scenes.
2. Manim or architecture-diagram for mechanism scenes.
3. p5.js for generative identity/background scenes.
4. ComfyUI for optional poster/accent clips.
5. External video APIs only after local QA proves the spine works.

Each adapter must write assets into `production/assets/` and record inputs, outputs, seeds, provider/tool versions, and fallbacks.

### Phase 5: Audio direction

Deliverables:

- audio policy engine
- voiceover/music mode selection in `creative_brief.json`
- loudness and ducking validation
- provider-neutral audio asset manifest
- final-mode failure when required audio is missing

The sound designer role should land after QA exists, because audio polish without QA will just create harder-to-debug output.

## Non-Goals

- External posting to X, Discord, YouTube, or any social platform.
- Fully autonomous public publishing.
- Hiding paid-provider failures behind fake success.
- Replacing Remotion with a stochastic video generator.
- Letting generated video models decide factual repo proof.
- Claiming "any repo" final-mode support until dependency and QA paths are robust.

## Open Decisions

- Which critic model should grade visual taste: Kimi only, a vision-capable model, or both?
- Should final mode require voiceover by default, or allow music-only for specific repo categories?
- Should ComfyUI run locally, through Comfy Cloud, or behind a user-provided endpoint?
- What is the minimum acceptable final-mode runtime on a typical laptop?
- Should the website expose all creative controls or keep an opinionated "Roll Tape" path with advanced options hidden?

## Sources

- Hermes Agent docs: https://hermes-agent.nousresearch.com/docs/
- Hermes skill authoring docs: https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills
- Hermes skills catalog: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/reference/skills-catalog.md
- Anthropic Building Effective Agents: https://www.anthropic.com/engineering/building-effective-agents
- HumanLayer 12-Factor Agents: https://github.com/humanlayer/12-factor-agents
- YouTube Shorts Help: https://support.google.com/youtube/answer/10059070
- TikTok Creator Tips: https://newsroom.tiktok.com/5-tips-for-tiktok-creators
- Material Design Motion: https://m1.material.io/motion/material-motion.html
- Apple Human Interface Guidelines, Motion: https://developer.apple.com/design/human-interface-guidelines/motion
- ComfyGen, Prompt-Adaptive Workflows: https://arxiv.org/abs/2410.01731
- ComfyGI, Automatic Improvement of Image Generation Workflows: https://arxiv.org/abs/2411.14193
- ComfyGPT, Self-Optimizing Multi-Agent ComfyUI Workflow Generation: https://arxiv.org/abs/2503.17671
- ComfySearch, Validation-Guided ComfyUI Workflow Construction: https://arxiv.org/abs/2601.04060
- OpenAI Evals guide: https://platform.openai.com/docs/guides/evals
- Braintrust evaluation docs: https://www.braintrust.dev/docs/evaluate
- LangSmith complex agent evaluation: https://docs.langchain.com/langsmith/evaluate-complex-agent
- Local Hermes ComfyUI skill: `/Users/peterbrown/.hermes/skills/creative/comfyui/SKILL.md`
- Local Hermes Manim skill: `/Users/peterbrown/.hermes/skills/creative/manim-video/SKILL.md`
- Local Hermes p5.js skill: `/Users/peterbrown/.hermes/skills/creative/p5js/SKILL.md`
- Local Hermes Pretext skill: `/Users/peterbrown/.hermes/skills/creative/pretext/SKILL.md`
- Remotion docs: https://www.remotion.dev/
- ComfyUI server routes: https://docs.comfy.org/development/comfyui-server/comms_routes
- Manim docs: https://docs.manim.community/en/stable/tutorials/quickstart.html
- Runway API docs: https://docs.dev.runwayml.com/api
- Luma Dream Machine API docs: https://docs.lumalabs.ai/docs/video-generation
- ElevenLabs API docs: https://elevenlabs.io/api/
