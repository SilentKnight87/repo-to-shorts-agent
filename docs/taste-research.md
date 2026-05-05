# Taste Research Notes for Repo-to-Shorts

Date: 2026-05-04
Purpose: Turn vague “make it tasteful” feedback into buildable constraints for the Repo-to-Shorts demo pipeline.

## Executive take

The useful X/search thesis is not “ask the model for better taste.” It is:

> Agents need references, constraints, and critique loops. Taste becomes a system.

For Repo-to-Shorts, that means the renderer should not only generate scenes. It should score and revise against a taste rubric:

1. Is the story clear in the first 1-2 seconds?
2. Is every scene doing a job?
3. Are captions readable and human?
4. Is motion guiding attention, or just moving because it can?
5. Does this look specific to the repo/project, or like generic AI SaaS soup?

## X signals gathered

X API bookmark access failed with `403 Forbidden`, so this pass used public X search/read via `xurl` from @Joash0x auth.

### 1. References beat vibes

Tweet: `2051362963324309563`, @tymarsha

> AI agents don’t need better taste. They need better references. Lazyweb gives Claude Code, Codex, and Cursor access to 257k+ real app screens through MCP...

Why it matters:
- Taste cannot be a prompt adjective.
- The system should pull examples/reference styles before choosing visual direction.
- For UI/demo polish, reference libraries like Lazyweb, TasteUI, DESIGN.md, and design-taste repos are more useful than “make it premium.”

Implementation implication:
- Add a `reference_pack` concept to the creative brief.
- Store reference descriptors such as `premium console`, `Linear-like restraint`, `cinematic kinetic typography`, `terminal-native launch trailer`.
- Eventually attach screenshots/examples, not just words.

### 2. Agents can build interfaces but cannot judge them unaided

Tweet: `2051315490216431704`, @0xDragoonLab

> agents build interfaces. they can't judge them. i built taste-skills... notice what's missing. rank competing solutions. trace why a decision was made. critique with precise language.

Why it matters:
- The missing feature is not generation. It is judgment.
- Repo-to-Shorts needs a self-review pass before export.

Implementation implication:
- Generate 2-3 candidate hooks/styles in preview mode.
- Score them using a rubric.
- Pick the best or ask the user to choose.

### 3. Functional is the floor

Tweet: `2051346116399043027`, @roeymiterany

> “Functional” is the floor. “Taste” is the ceiling... If the animations aren't fluid and the spacing is “default,” your app feels like a template.

Why it matters:
- Passing tests and rendering MP4 is not enough.
- The demo fails if it looks like default spacing, default typography, default cards.

Implementation implication:
- Add checks for default-looking patterns:
  - purple/blue gradient hero
  - centered generic headline
  - three-card grid
  - too many rounded cards
  - unmotivated motion
  - captions cropped or too dense

### 4. Taste beats prompt tricks

Tweet: `2050954874674647291`, @thejsnode

> AI can pour out code all day. The scarce skill is looking at the thing and knowing the login flow feels cursed, the empty state is lying, or the pricing page sounds like a hostage note.

Why it matters:
- Taste is diagnosis with precise language.
- “Looks bad” is useless. “The caption hierarchy is fighting the repo card” is useful.

Implementation implication:
- Add evaluator outputs that name the defect and remedy:
  - defect: `caption_density_high`
  - evidence: `Scene 2 has 19 words in primary caption`
  - fix: `split into 2 beats, hold each for 1.2s`

### 5. AI video is generation + direction

Tweet: `2050796103373627480`, @hi2ling

> ai video is splitting into two jobs now: generation and direction... shot list, continuity, the world... pre-prod is where taste compounds.

Why it matters:
- A good short starts before rendering.
- The creative brief should include shot list, rhythm, continuity, and world, not just script.

Implementation implication:
- Extend `video_plan.json` with:
  - `visual_world`
  - `motion_principles`
  - `shot_list`
  - `continuity_rules`
  - `negative_prompts`

### 6. Product demo moat is taste, trust, audience

Tweet: `2050407942260690994`, @PTensor89827

> The new moat is not making videos. It is having taste, trust, and an audience.

Why it matters:
- Repo-to-Shorts should not position as “it made a video.” That is commodity.
- The product promise is “it makes a credible, audience-aware launch asset.”

Implementation implication:
- The app should ask or infer audience and distribution channel.
- Judge output by whether it would build trust with that audience.

## Non-X sources worth using

### Lazyweb

Source: https://www.lazyweb.com/llms.txt

Key point: Lazyweb gives agents design context from 257k+ real app screens, user flows, and product patterns. It explicitly says to use it before designing or critiquing UI.

Repo implication:
- Future: integrate Lazyweb MCP or at least make a manual `references/` folder for screenshots/style notes.

### TasteUI

Source: https://tasteui.dev/docs

Key point: AI produces “nice but not yours” because it averages generic design. TasteUI solves this with markdown design skills that explain visual theme, color roles, typography, spacing, motion, and rationale.

Repo implication:
- Repo-to-Shorts should use `DESIGN.md`/`SKILL.md` style specs, not prompt-only design.

### Google DESIGN.md

Source: https://github.com/google-labs-code/design.md

Key point: tokens give exact values, prose explains why and how to apply them.

Repo implication:
- Add `DESIGN.md` to the repo root as a persistent visual identity for agents.

### Everything Design Taste

Source: https://github.com/Dragoon0x/everything-design-taste

Key point: taste systems use reviewers, rules, hooks, and scoring. Its `taste-audit` framing weights intentionality, craft, anti-slop, writing, and accessibility.

Repo implication:
- Add a `taste_score` or `quality_gate` after preview generation.

## Taste rubric for generated shorts

Score each 0-5.

### 1. Hook clarity, 20%

Good:
- First second makes the transformation obvious.
- Viewer knows what the repo/app does before scene 2.

Bad:
- Abstract shapes before context.
- “Introducing...” generic opener.
- Too much brand throat-clearing.

### 2. Specificity to repo, 20%

Good:
- Uses real repo name, files, commands, metrics, architecture, features.
- Captions sound like this project, not any AI app.

Bad:
- “AI-powered workflow” filler.
- Generic icons and claims.

### 3. Visual craft, 20%

Good:
- Strong hierarchy.
- Consistent palette.
- Intentional spacing.
- Motion has purpose.
- Feels cinematic but readable.

Bad:
- Default cards, default gradient, default font sizes.
- Everything moves all the time.
- Effects hide weak composition.

### 4. Caption/copy quality, 15%

Good:
- Short, punchy, human.
- 3-7 words per major beat.
- No AI-corporate filler.

Bad:
- “Seamlessly revolutionizes...” garbage.
- Long sentences as overlays.
- Voiceover repeats visible text.

### 5. Pacing/audio, 15%

Good:
- Cuts match music/voice cadence.
- Each scene earns its duration.
- Audio supports momentum without dominating.

Bad:
- Dead air.
- Rushed unreadable captions.
- Music feels unrelated.

### 6. Distribution fit, 10%

Good:
- 9:16 safe areas respected.
- Works muted.
- Final CTA is clear.
- Can be posted to X/LinkedIn without embarrassment.

Bad:
- Cropped captions.
- Tiny text.
- No ending/payoff.

## Anti-slop checks

Fail the preview if any of these are true:

- Caption is cropped or outside safe area.
- Primary caption has more than 12 words on screen.
- More than two scenes use the same layout without intentional repetition.
- Palette introduces random colors not in `DESIGN.md`.
- Output could describe any AI repo by swapping the name.
- First scene does not reveal project purpose or transformation.
- The final scene has no artifact/proof/CTA.
- Voice sounds like generic old AI narration with no music bed.

## Recommended next build steps

1. Add a `TasteProfile` / `DESIGN.md` reader to the creative pipeline.
2. Extend `video_plan.json` with visual-world fields.
3. Add a deterministic taste evaluator that scores a plan before render.
4. Add preview comparison mode: generate 2-3 concepts fast, then choose one.
5. Add a post-render QA pass using ffprobe + extracted frames:
   - duration correct
   - text safe area
   - no cropped captions
   - scene count matches plan
6. Later: integrate Lazyweb MCP or a local reference-pack folder.
