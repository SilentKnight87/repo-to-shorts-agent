# Submission Checklist

**Deadline:** 2026-05-04 05:00 local
**Generated:** ~02:15 local
**Floor (worst-case submission):** `runs/20260504-002134-repo-to-shorts-agent/` — already valid, live-Kimi, 60s, validated. If everything else fails, this ships.

Read top-to-bottom. Each step has a time budget and a decision gate. Don't skip; don't re-order. When you hit a `STOP IF` line and the condition is true, jump to the abort section.

---

## Phase 1 — Settle code (target: T+0:30, by 02:45)

### 1.1 — Codex unblock (~5 min)

Tell Codex:

```
git checkout -- src/repo_to_shorts/creative_director.py tests/test_creative_director.py
git fetch
git rebase origin/main
.venv/bin/python -m pytest -q
```

- [ ] Codex's worktree no longer shows `M creative_director.py` or `M test_creative_director.py`
- [ ] Codex's branch rebased on `main` cleanly (no conflicts after the discards above)
- [ ] `pytest` shows 117 passing in the worktree

**STOP IF** rebase has unresolved conflicts → switch Codex to read-only mode, ship from `main` only.

### 1.2 — OpenCode start (~0 min)

Tell OpenCode:

```
Read and execute docs/opencode/2026-05-04-submission-copy-task.md
```

- [ ] OpenCode acknowledges and begins
- [ ] `docs/submission/` directory appears within 5 min of starting

### 1.3 — Codex visual polish (~25 min)

Tell Codex (after 1.1 succeeds):

```
Read and execute docs/codex/2026-05-04-remotion-polish.md
```

- [ ] Codex begins iterating on `RepoShortsVideo.tsx`
- [ ] At T+0:30 (02:45), check Codex's `git log` — at least 1 polish commit landed

**STOP IF** at T+0:30 Codex hasn't shipped a polish commit → accept current Pillow path, skip Phase 2.2 below.

---

## Phase 2 — Live golden run (target: T+1:00, by 03:15)

### 2.1 — Test the Hermes skill end-to-end (~10 min)

In a fresh terminal (NOT in this Claude session):

```bash
hermes
```

Then in the REPL:

```
/repo-shorts-creative .
```

Or natural language: *"Make a launch short for this repo: . Run final mode."*

- [ ] Hermes acknowledges the skill exists
- [ ] Hermes calls `run_terminal_cmd` with the CLI command from `SKILL.md`
- [ ] CLI starts running, ingest → kimi_brief → render visible in stdout
- [ ] When done, Hermes reads `metadata.json` and reports `kimi.mode: live-api`

**STOP IF** Hermes can't find the skill → check `~/.hermes/skills/video/repo-shorts-creative/SKILL.md` exists. Restart `hermes` REPL.

**STOP IF** Hermes invokes the CLI but fails → run the underlying CLI directly and skip the Hermes invocation in the demo (keep the skill installed for proof but record from the CLI).

### 2.2 — Direct CLI live golden run (~12 min, parallel to 2.1)

In another terminal:

```bash
cd /Users/operator/Documents/Code/repo-to-shorts-agent
.venv/bin/repo-shorts creative . \
  --audience "Nous Research Hermes Agent Creative Hackathon judges" \
  --kimi-model moonshotai/kimi-k2.6 \
  --tts-provider xai \
  --fallback-tts-provider openai \
  --out runs \
  --final
```

This is the load-bearing test. Must produce a fresh run dir with:

- [ ] `runs/<new-timestamp>-repo-to-shorts-agent/demo.mp4` exists, > 1 MB
- [ ] `metadata.json` contains:
  - `kimi.mode: "live-api"`
  - `kimi.provider: "openrouter"`
  - `kimi.model: "moonshotai/kimi-k2.6"`
  - `render.validation.ok: true`
  - `render.scene_count: >= 5`
  - `creative_brief.total_duration: 45-60`
- [ ] `submission_pack.md` references the Hermes skill (already templated)
- [ ] Open `demo.mp4` and confirm it plays end-to-end without obvious glitches

**STOP IF** Kimi returns invalid JSON → check OpenCode's prompt diff didn't break parsing. Roll back to pre-08b05ed creative_director.py if needed (`git show 08b05ed^:src/repo_to_shorts/creative_director.py > /tmp/cd.py && cp /tmp/cd.py src/repo_to_shorts/creative_director.py`).

**STOP IF** any check fails → ship the existing fallback run at `runs/20260504-002134/`. It's already valid.

### 2.3 — Renderer mode check (~2 min)

If Codex finished Remotion polish:

- [ ] In Codex's worktree, `npm install` completed and `node_modules/` exists
- [ ] Run the same CLI command above from inside the worktree (so it uses Remotion)
- [ ] `metadata.json` shows `render.renderer: "remotion"` (NOT `pillow+ffmpeg-enhanced`)
- [ ] Visually compare: Remotion video should look distinctly better than Pillow

**STOP IF** Remotion produces a worse-looking video than Pillow → ship Pillow. Honest fallback. The architecture supports it; metadata records the truth.

---

## Phase 3 — Recording (target: T+1:45, by 04:00)

### 3.1 — Pre-record setup (~5 min)

- [ ] Terminal: zsh in `/Users/operator/Documents/Code/repo-to-shorts-agent`, font size XL (so it's readable in a 1080×1920 capture)
- [ ] Browser: `http://127.0.0.1:8765` open with a fresh load (`.venv/bin/repo-shorts web` running in another terminal)
- [ ] Confirm SKILL badge is visible in the hero
- [ ] Screen recorder set to 1080×1920, 30fps
- [ ] Quit other apps that might surface notifications

### 3.2 — Record (~20 min including retakes)

Use OpenCode's shot list at `docs/submission/demo-shot-list.md` as the script.

Two-track structure recommended (or split-screen via QuickTime + Photo Booth or screen capture software):

- [ ] **Take 1** — full 60s, no errors. If something glitches, retake.
- [ ] If take 1 succeeded, edit only if necessary (trim cold-open lead-in, fix audio levels)
- [ ] Final video is ≤60 seconds, 9:16, plays cleanly

**STOP IF** can't get a clean recording by T+2:00 → use the generated `demo.mp4` from the live golden run as the submission video itself (the meta angle still works: "this video was made by the repo it's about" is intrinsically true).

### 3.3 — Save & verify (~3 min)

- [ ] Recording saved as `runs/submission/repo-to-shorts-submission.mp4`
- [ ] Plays from start to end without freezing
- [ ] Audio is clear (no clipping, narration audible)
- [ ] Resolution/aspect right (X allows 9:16)

---

## Phase 4 — Copy review (target: T+2:15, by 04:30)

### 4.1 — Open OpenCode's drafts

- [ ] `docs/submission/x-post-variants.md` exists with 5 tweets
- [ ] `docs/submission/discord-post.md` exists with one Discord post
- [ ] `docs/submission/demo-shot-list.md` exists (already used in Phase 3)

### 4.2 — Pick & finalize X tweet (~5 min)

- [ ] Read all 5 variants — pick the one that lands hardest given the actual recording you just made
- [ ] Substitute `<DEMO VIDEO URL>` with… nothing yet (you'll paste it after upload)
- [ ] Verify ≤280 chars including tags
- [ ] Tags `@NousResearch` and `@Kimi_Moonshot` are both present

### 4.3 — Finalize Discord post (~3 min)

- [ ] Substitute `<X POST URL HERE>` and `<GITHUB URL>` placeholders
- [ ] Verify it mentions the Hermes skill path (`.hermes/skill/SKILL.md`) and the live-Kimi proof claim
- [ ] No marketing voice, no emoji

---

## Phase 5 — Submit (target: T+2:30, by 04:45)

### 5.1 — Upload video to X (~5 min)

- [ ] Compose tweet on x.com
- [ ] Attach `runs/submission/repo-to-shorts-submission.mp4`
- [ ] Paste the chosen tweet text from variants file
- [ ] Tag `@NousResearch` and `@Kimi_Moonshot`
- [ ] Post

### 5.2 — Drop in Nous Discord (~3 min)

- [ ] Open Nous Research Discord, navigate to `creative-hackathon-submissions` channel
- [ ] Paste the Discord post from `discord-post.md`
- [ ] Replace `<X POST URL HERE>` with the X post URL from 5.1
- [ ] Replace `<GITHUB URL>` with `https://github.com/SilentKnight87/repo-to-shorts-agent`
- [ ] Post

### 5.3 — Verify submission (~2 min)

- [ ] X post is live and the video plays in the embed
- [ ] Discord post is live in the right channel
- [ ] Both posts cross-reference each other correctly

---

## Phase 6 — Buffer (T+2:45 → T+3:00 → 05:00)

If you finished early:
- Take a screenshot of `metadata.json` showing live-Kimi proof, post as a reply to your X tweet (extra credibility)
- Pin the X post to your profile

If you finished late but before deadline:
- Submit anything that's ready and acknowledge gaps in the Discord post

If you missed the deadline:
- Don't lie. Either accept it or reach out to Nous directly. Honest > strategic.

---

## Abort path: ship the floor

If at any `STOP IF` you decide to fall back to the existing run:

- [ ] Source the fallback: `runs/20260504-002134-repo-to-shorts-agent/demo.mp4`
- [ ] Skip Phase 2 entirely
- [ ] Phase 3 records the fallback video being played in the web UI (or just attach the MP4 directly)
- [ ] Phases 4-5 proceed normally
- [ ] In Discord post, you can still claim live-Kimi proof — `metadata.json` for the fallback run shows `kimi.mode: live-api`

The floor is real. The floor is enough. Don't burn the deadline chasing diminishing returns.

---

## Decision log (fill as you go)

| Time | Decision | Rationale |
|------|----------|-----------|
|      |          |           |
|      |          |           |
