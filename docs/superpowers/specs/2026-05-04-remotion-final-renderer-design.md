# Remotion Final Renderer Design

## Goal

Make Repo-to-Shorts generate a publishable hackathon short that looks like a designed product launch video, not a generated slide deck.

The final artifact must still prove live Kimi usage honestly. Visual polish cannot come at the cost of fake metadata, hidden fallback modes, or fragile one-off manual editing.

## Problem

The current CLI works: it ingests a repo, calls Kimi, generates narration, creates MP4 output, and records proof metadata. The weak point is taste. The Pillow renderer maps different scenes onto a small set of static templates, so even live Kimi briefs become repetitive panels, generic architecture boxes, and bottom-caption karaoke.

The upgrade needs a real motion-design layer:

- scene timing that feels native to shorts
- kinetic typography, not large static cards
- actual repo/artifact evidence in every scene
- honest Kimi proof as a visual beat
- deterministic rendering that can run from the CLI

## Research Inputs

Official Kimi guidance says to use structured object-shaped JSON output, clear role/goal/action instructions, rich context with delimiters, explicit output contracts, and provider-specific handling for thinking/JSON mode. Kimi K2.6 has a 256K context window and supports long-horizon agent workflows, but for final JSON briefs the workflow should request structured output and keep the root as an object.

Video research points to Remotion as the right rendering layer because it renders real MP4s from React components, supports programmatic input props, deterministic scene timing with `Sequence`/`Series`, animation primitives like `interpolate()` and `spring()`, and caption-heavy short-form workflows.

Good dev-product shorts follow a clear arc:

1. hook
2. pain/problem
3. product mechanism
4. concrete proof
5. result/CTA

They show product evidence. They do not rely on abstract diagrams alone.

## Product Direction

Build a Remotion final renderer driven by a JSON manifest produced by the existing Python pipeline.

Python remains the orchestrator. Kimi remains the creative director. Remotion owns the final visual system for `demo.mp4`.

The existing Pillow renderer remains as fallback and for environments without Node/npm. Metadata must truthfully record which renderer produced the MP4.

## Aesthetic Direction

Archetype: retro-futuristic editorial product short.

Differentiator: repo evidence becomes cinematic proof. Files, commands, metadata fields, generated artifacts, and Kimi proof appear as designed UI evidence inside the video, while kinetic typography carries the story.

Do not make generic dashboards, floating cards for their own sake, dark blob backgrounds, or repeated architecture slides.

## Final Video Requirements

- Format: 1080x1920, 30fps, 45-60 seconds.
- First 3 seconds must explain the product without audio.
- Each scene must have one primary visual idea.
- Every claim must connect to repo evidence, generated artifact evidence, or metadata proof.
- Captions must be readable on mobile and must not sit in a bulky repeated bottom box.
- Kimi proof must be visible: `live-api`, provider, model.
- Final CTA must be suitable for X and Hermes Discord.
- No `.env`, secrets, tokens, private keys, or generated `runs/` content in visuals.

## Scene System

The Remotion renderer will support these scene types:

- `ColdOpen`: 1.5-3s, huge kinetic hook, product clear in one glance.
- `RepoEvidence`: repo name, purpose, key files, language/framework when available.
- `PainPoint`: fast text beat about demo-making friction.
- `PipelineMap`: ingest -> Kimi brief -> render -> artifacts.
- `ArtifactStack`: repo brief, storyboard, narration, captions, MP4, metadata, submission copy.
- `LiveProof`: highlight `metadata.json` Kimi fields and render validation.
- `DemoPreview`: stylized browser/phone preview of the generated package or MP4.
- `CTAEndCard`: command, output folder, final promise.

The MVP must render at least:

1. `ColdOpen`
2. `PainPoint` or `RepoEvidence`
3. `PipelineMap`
4. `ArtifactStack`
5. `LiveProof`
6. `CTAEndCard`

## Kimi Brief Contract

Kimi should output an object-shaped JSON brief:

```json
{
  "schema_version": 1,
  "creative_direction": {
    "angle": "meta demo",
    "tone": "sharp, cinematic, builder-focused",
    "visual_style": "retro-futuristic editorial"
  },
  "storyboard": [
    {
      "type": "ColdOpen",
      "duration_seconds": 3,
      "headline": "This repo made the video you're watching.",
      "narration": "This repo made the video you're watching.",
      "evidence": ["repo_name"],
      "caption_emphasis": ["repo", "video"]
    }
  ],
  "quality_bar": {
    "avoid": ["generic architecture slide", "bottom caption box", "fake proof"],
    "must_show": ["live Kimi proof", "generated MP4", "repo evidence"]
  }
}
```

The OpenRouter adapter should keep using structured output. If OpenRouter supports strict JSON schema reliably for the selected model, add provider-specific schema mode. Otherwise keep `json_object` and validate locally.

## Python To Remotion Contract

Python writes:

`runs/<timestamp>-<repo>/render/remotion_input.json`

Required shape:

```json
{
  "schema_version": 1,
  "repo": {
    "name": "repo-to-shorts-agent",
    "description": "Turns a repo into a launch-ready technical demo video package.",
    "key_files": ["README.md", "src/repo_to_shorts/pipeline.py"]
  },
  "video": {
    "width": 1080,
    "height": 1920,
    "fps": 30,
    "duration_seconds": 45
  },
  "proof": {
    "kimi_mode": "live-api",
    "kimi_provider": "openrouter",
    "kimi_model": "moonshotai/kimi-k2.6",
    "render_validation": "pass"
  },
  "scenes": [
    {
      "type": "ColdOpen",
      "duration_seconds": 3,
      "headline": "This repo made the video you're watching.",
      "narration": "This repo made the video you're watching.",
      "evidence": ["repo-to-shorts-agent"]
    }
  ],
  "artifacts": ["demo.mp4", "metadata.json", "captions.srt", "submission_pack.md"]
}
```

Node receives only paths:

```bash
npm run render:remotion -- \
  --input /abs/path/render/remotion_input.json \
  --output /abs/path/demo.mp4
```

## Metadata Contract

If Remotion renders the MP4:

```json
"render": {
  "mode": "mp4",
  "renderer": "remotion",
  "output": "demo.mp4",
  "input": "render/remotion_input.json",
  "scene_count": 6,
  "validation": {
    "ok": true
  }
}
```

If Remotion is unavailable and Pillow succeeds:

```json
"render": {
  "mode": "mp4",
  "renderer": "pillow+ffmpeg-enhanced",
  "fallback_renderer": "remotion",
  "fallback_reason": "Remotion unavailable: npm dependencies missing",
  "output": "demo.mp4"
}
```

Never claim Remotion if Pillow produced the file.

## Taste QA Gate

The runner should produce a contact sheet or sampled frames and check:

- video is nonblank
- first frame includes product/repo identity
- Kimi proof frame exists
- no repeated generic scene title such as “Architecture in motion”
- captions stay within safe zones
- MP4 metadata validates 1080x1920 with audio
- `kimi.mode` is `live-api`

The first version can enforce the machine-checkable parts and output the contact sheet for human review.

## Implementation Scope

In scope:

- Remotion project scaffold in the repo.
- Python adapter to write the manifest and invoke Remotion.
- Remotion composition with the scene types above.
- Kimi prompt/schema update for richer storyboard/taste contract.
- Local runner uses Remotion final path when available.
- Tests for manifest, metadata, fallback, and basic Remotion invocation.
- Optional smoke command for live Remotion render.

Out of scope:

- External publishing.
- Cloud rendering.
- Paid stock/video APIs.
- Browser automation of social posts.
- Removing the Pillow renderer.

## Success Criteria

- `./scripts/run-local-final.sh` produces a valid MP4 with `kimi.mode=live-api`.
- When npm dependencies are installed, metadata records `renderer=remotion`.
- Generated contact sheet shows distinct scene types, real repo evidence, visible Kimi proof, and a clear CTA.
- If Remotion is missing, the CLI falls back honestly without breaking default artifact generation.
- Full Python tests and lint pass.
