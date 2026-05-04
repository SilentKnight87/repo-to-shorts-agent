# OpenCode Task — Submission Copy & Demo Shot List

**Created:** 2026-05-04 ~02:00 (~3 hours before deadline)
**Owner:** OpenCode (Kimi K2.6 / DeepSeek)
**Coordination:** Other harnesses (Codex, Claude) are editing Python source and Remotion files — **stay out of those areas to avoid merge conflicts.**

## Scope

**Edit ONLY files under `docs/submission/`. Create the directory.**

Do not touch:
- Anything under `src/`
- Anything under `tests/`
- Anything under `remotion/` or `.worktrees/`
- `README.md`, `AGENTS.md`, `CLAUDE.md`
- `pyproject.toml`, `package.json`, `.gitignore`

If you find yourself wanting to edit those, stop and tell the user — that's a sign the brief is wrong, not that you should silently expand scope.

## Read for context (do not edit)

- `docs/HACKATHON_STRATEGY.md` — positioning, narrative, "two-front Kimi strategy"
- `README.md` — current architecture, the Hermes Agent skill section
- `.hermes/skill/SKILL.md` — the actual Hermes skill SKILL.md (load-bearing proof)
- `runs/20260504-002134-repo-to-shorts-agent/metadata.json` — live Kimi proof from a real run
- `runs/20260504-002134-repo-to-shorts-agent/submission_pack.md` — existing fallback copy
- `runs/20260504-002134-repo-to-shorts-agent/contact_sheet.jpg` — what the current rendered video looks like
- `src/repo_to_shorts/static/style.css` — VHS broadcast aesthetic tokens (informs the visual reference for the demo shot list)

## What to produce

### 1. `docs/submission/x-post-variants.md`

Exactly **5 tweet drafts**. Each ≤280 characters. Each tags `@NousResearch` and `@Kimi_Moonshot`. Vary the angle:

| # | Angle | Lead beat |
|---|---|---|
| a | Technical | "Built a real Hermes Agent skill, not Nous-branded chatbot." |
| b | Creative meta | "This video was made by the repo it's about." |
| c | Builder pain | "Your repo works, your demo doesn't. Here's the fix." |
| d | Process proof | "Hermes won't declare success until `kimi.mode=live-api` shows up in metadata.json." |
| e | Before/after | "git clone → 60s vertical short with X copy ready." |

Each tweet should assume the generated demo MP4 is attached directly, plus tags.

Format the file as:

```markdown
# X Post Variants

## Variant A — Technical
<tweet text, ≤280 chars including tags>

## Variant B — Creative Meta
<tweet text>

...etc
```

No emoji. No marketing voice. Builder-to-builder.

### 2. `docs/submission/discord-post.md`

One Discord post (~150 words) for the Nous Research `creative-hackathon-submissions` channel. Structure:

- **Lead line** (1 sentence): project name + what it does
- **Demo video link**: published X post URL after upload
- **How it works** (3 bullets):
  - Hermes Agent skill (`.hermes/skill/SKILL.md`) — judges can `hermes` and run `/repo-shorts-creative <target>`
  - Kimi K2.6 directs the storyboard via OpenRouter — visible in `metadata.json` as `kimi.mode: live-api`
  - Honest proof — Hermes validates the Kimi field before declaring success; deterministic fallback recorded transparently if the live call fails
- **Try it** (one block):
  ```
  hermes
  > /repo-shorts-creative https://github.com/<owner>/<repo>
  ```
  And the equivalent direct CLI for non-Hermes users:
  ```
  repo-shorts creative <target> --final
  ```
- **Closing**: public GitHub repo URL

Tone: builder-to-builder, honest about scope. No emoji. No marketing voice.

### 3. `docs/submission/demo-shot-list.md`

A 60-second screen recording shot list with **timestamps every 5 seconds**. Two-track structure:

- **Terminal track** (left half of screen): Hermes REPL invoking the skill, agent thinking, terminal command running, metadata.json being read, success report
- **Browser track** (right half of screen): VHS broadcast UI at `http://127.0.0.1:8765` — channel rows lighting up as the same workflow runs in parallel, final mp4 playing in the closing beat

**Hard requirements:**
- **0–3s** (hook, no audio): big white-on-black text "This video was made by the repo it's about." This is the only frame that *must* look like a title card. After that, both tracks are live.
- **3–8s**: terminal track shows `hermes` opening, user typing `/repo-shorts-creative <github-url>`. Browser track shows the VHS UI home page (lede + SKILL badge visible).
- **8–25s**: agent loop visible in terminal; channel rows lighting up in browser. Both should be moving at the same time.
- **25–45s**: terminal shows the agent inspecting `metadata.json`, calling out `kimi.mode: live-api`, `kimi.provider: openrouter`, `kimi.model: moonshotai/kimi-k2.6`. Browser shows the result page or the final MP4 playing inline.
- **45–55s**: final MP4 plays full-frame (or both tracks side-by-side with the MP4 dominant). Show the VHS UI's `kimi · live-api` status pill.
- **55–60s** (CTA): `github.com/SilentKnight87/repo-to-shorts-agent` + `@NousResearch @Kimi_Moonshot`. Big text, white-on-black again — bookend with the open.

**Format the file as a table:**

```markdown
# Demo Shot List — 60s, 9:16

## Pre-record setup
- Terminal: zsh in `<repo-root>`, font size XL
- Browser: `http://127.0.0.1:8765` open, dark theme matched to terminal
- Recording: 1080×1920 vertical, 30fps, screen capture both panes side-by-side

## Beats

| Time | Terminal track | Browser track | On-screen text |
|------|----------------|---------------|----------------|
| 0:00–0:03 | Black | Black | "This video was made by the repo it's about." |
| 0:03–0:08 | `hermes` opens, user types `/repo-shorts-creative https://github.com/...` | VHS UI home page, SKILL badge visible | none |
| 0:08–0:13 | ... | ... | ... |
... continue in 5-second increments through 0:55–1:00 ...

## Recording notes
- ...
```

Don't ad-lib new beats not in the spec above. The beats above are the design — your job is to write the table cells that execute it.

## Acceptance

Each file:
- Lives under `docs/submission/`
- Has no `<TODO>` placeholders besides the explicit URL placeholders called out above
- Uses the markdown structure shown above
- Tone is builder-to-builder, honest, no marketing voice

When you're done, report:
1. The three file paths
2. Any beats in the shot list you weren't sure about
3. Any honest concerns about scope or accuracy

If you want to deviate from the structure (e.g., 4 tweets instead of 5, different angle distribution), stop and ask first.
