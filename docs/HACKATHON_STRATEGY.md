# Hackathon Strategy

## What we are building

Repo-to-Shorts Agent is a Hermes-powered creative workflow that turns a code repo into a launch-ready short-video package.

Input:

```text
GitHub URL or local repo
```

Output:

```text
repo brief
storyboard
architecture visual
narration
captions
X post
Discord submission copy
Kimi critic/editor notes
browser-recordable demo page
optional MP4 render
```

The simple pitch:

> Builders can make code work. Repo-to-Shorts helps them make people understand it.

## Why this fits the Hermes Creative Hackathon

The hackathon rewards creativity, usefulness, and presentation.

Repo-to-Shorts maps cleanly:

1. Creativity
   - It uses an agent to produce narrative, visuals, captions, and launch assets.
   - It is not another chatbot wrapper.
   - It turns code into media.

2. Usefulness
   - Every hackathon builder has the same problem: the repo works, but the demo is unclear.
   - This gives builders a repeatable way to turn a repo into a clear launch story.
   - It remains useful after the hackathon for demos, launches, Upwork case studies, internal engineering updates, and founder/product posts.

3. Presentation
   - The demo has an obvious before/after:
     - Before: repo full of files.
     - After: clear story, architecture visual, captions, copy, Kimi critique, and demo artifact.
   - Judges can understand the transformation in under 10 seconds.

## The two-front Kimi strategy

The intended positioning is stronger than just "we called Kimi once."

We should hit both fronts:

### Front 1: Kimi powers the Hermes harness

Hermes Agent is the harness: it coordinates tools, skills, files, terminal commands, browser capture, rendering, and artifact generation.

Kimi is the model powering that harness during the build/demo flow.

In plain English:

```text
Kimi thinks and decides.
Hermes acts.
Repo-to-Shorts is the workflow/product that comes out of that harness.
```

This matters because the hackathon is about Hermes Agent. We want the story to be:

> Hermes, powered by Kimi, orchestrates a creative production pipeline for technical demos.

Implementation/demo implications:

- Run the Hermes session or autonomous build using the Kimi provider/model when possible.
- Capture or document that Kimi is the model behind the Hermes harness.
- Include this in the submission narrative as orchestration-level Kimi usage.

Config target, subject to actual Hermes provider naming on the machine:

```bash
export KIMI_API_KEY="..."
hermes model
# choose Kimi / Moonshot provider and desired Kimi model
```

Or explicitly from CLI if supported by the local Hermes build:

```bash
hermes chat --provider kimi -m <kimi-model> -q "Run the Repo-to-Shorts golden path and generate the hackathon demo package."
```

If the exact provider slug/model differs, verify with:

```bash
hermes model
hermes config
hermes doctor
```

### Front 2: Kimi reviews the generated story inside the product

Repo-to-Shorts itself should call Kimi as a critic/script editor.

Product-level Kimi role:

```text
Hermes drafts the launch package.
Kimi reviews the package and sharpens the hook, story, narration, risk notes, and CTA.
```

Output proof:

```text
kimi_critique.md
metadata.json with kimi.mode = live-api
visible Kimi critic/editor card in demo.html
```

This gives the submission two layers of Kimi involvement:

1. Kimi as the reasoning model powering Hermes orchestration.
2. Kimi as the explicit creative editor inside the generated artifact pipeline.

That is sponsor-aligned without being gimmicky.

## Hermes skills and built-ins to leverage

The user mentioned a Hermes post with many creative skills: video, images, diagrams, and related tooling. We should inspect the exact post/thread before claiming specific official examples in the final submission.

Based on the local Hermes skill catalog, the relevant creative building blocks include:

- `architecture-diagram`: dark SVG architecture/cloud/infra diagrams.
- `manim-video`: animated explainer videos.
- `image_gen`: generated visual assets.
- `tts`: narration audio.
- `youtube-content`: summaries/transcripts if using video references later.
- `ascii-video` / `ascii-art`: stylized terminal-flavored visual artifacts if we want a hacker aesthetic.
- `claude-design` / `popular-web-designs` / `sketch`: polished HTML demo surfaces.
- `songsee` / audio tools: optional audio visualization if the demo becomes more creative.

The hackathon MVP should not use all of these. That would become a circus.

Recommended use:

P0:
- Hermes terminal/file tools to run the workflow.
- Hermes skill framing: package Repo-to-Shorts as a reusable Hermes workflow/skill.
- Kimi-powered Hermes session for orchestration if API/model access is ready.
- Product-level Kimi critic pass.

P1:
- Use Hermes creative/design skills to improve `demo.html` visual presentation.
- Optional TTS/caption generation.
- Optional MP4 render.

Avoid:
- Stuffing every creative skill into the demo.
- Making the project feel like a random skills sampler.
- Overclaiming that Hermes generated video if we only screen-recorded HTML.

## Winning demo narrative

The demo should not be framed as:

> Here is a Python script that writes markdown.

It should be framed as:

> I built a Hermes creative workflow, powered by Kimi, that turns raw code into a launch-ready technical short package.

60-second structure:

### 0-5s: Problem

Hackathon projects often work before they are easy to understand.

Visual:
- repo/file tree
- README/code

### 5-15s: Agent workflow

One command runs Repo-to-Shorts.

Visual:

```bash
repo-shorts analyze . --audience "Nous Research Hermes Agent Creative Hackathon judges" --out runs
```

If Kimi powers Hermes harness, show or mention:

```text
Hermes Agent orchestrated with Kimi as the model.
```

### 15-30s: Generated package

Show generated files:

```text
repo_brief.md
storyboard.md
architecture.svg
narration.md
captions.srt
x_post.md
submission.md
```

### 30-45s: Kimi critic/editor

Show `kimi_critique.md` and the Kimi card in `demo.html`.

Message:

```text
Kimi reviews the generated story and sharpens the hook, narration, and CTA.
```

### 45-60s: Output

Show `demo.html` or `demo.mp4`.

Close:

```text
Working repo in. Launch story out.
```

## Winning conditions

This has a real shot if the final submission proves:

1. Clear pain
   - Builders need better demos.

2. Clear transformation
   - Repo to launch package.

3. Sponsor fit
   - Hermes as the harness.
   - Kimi as both harness model and critic/editor.

4. Visible artifact
   - Judges can see the output immediately.

5. Honest claims
   - Do not claim automatic MP4 or live Kimi unless implemented and shown.

## Immediate execution path

1. Wire live Kimi API inside `repo_to_shorts.kimi`.
2. Add metadata proving live Kimi mode.
3. Add docs showing how to run Hermes with Kimi as the orchestration model.
4. Package Repo-to-Shorts as a Hermes-friendly workflow/skill.
5. Regenerate demo artifacts.
6. Screen-record polished `demo.html` unless MP4 render becomes easy.
7. Tighten X/Discord copy.
8. Submit only after maintainer approves.

## Final submission positioning

Short X version:

```text
Built Repo-to-Shorts Agent for the Hermes Creative Hackathon.

It turns a repo into a launch-ready technical short package: brief, storyboard, architecture visual, narration, captions, X/Discord copy, and Kimi critic notes.

Hermes is the creative harness. Kimi powers the reasoning and sharpens the story.

@NousResearch
```

Longer Discord version:

```text
Repo-to-Shorts Agent turns a GitHub/local repo into a launch-ready technical demo package.

The workflow uses Hermes Agent as the orchestration harness: repo ingestion, story planning, artifact generation, visual demo assembly, and submission packaging.

Kimi is used on two fronts: as the model powering the Hermes harness where available, and as an explicit critic/script-editor stage inside the product. The generated Kimi critique sharpens the hook, narration, risk notes, and final CTA.

Output includes repo brief, storyboard, architecture SVG, narration, captions, X post, Discord copy, Kimi critique, and a browser-recordable demo page.
```
