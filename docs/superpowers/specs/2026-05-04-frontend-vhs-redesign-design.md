# Frontend VHS Redesign — Design Spec

- **Date:** 2026-05-04
- **Status:** Approved (verbal, section-by-section)
- **Branch:** `frontend-vhs-redesign` (worktree: `.worktrees/frontend-vhs-redesign/`)
- **Scope:** `src/repo_to_shorts/web.py` and a new `src/repo_to_shorts/static/` directory. No backend changes (pipeline, ingest, kimi, render, hermes_skill, compositor untouched).

## Problem

The current web UI (`src/repo_to_shorts/web.py`, ~620 lines, all HTML/CSS/JS inline as f-strings) reads as a default AI-tasteful dark dashboard — radial gradient halos, glass-morphism cards, Inter sans, purple/cyan accents. It works, but it's the most-imitated AI aesthetic of the last two years and does not signal that this is a creative video production tool. The user's stated goal: "leagues and bounds better." The hackathon meta-pitch (screen-record this app generating a video of itself) means the UI must look distinctive on a recorded video, not just to a desktop user.

## Goals

1. Commit to a specific aesthetic with a point of view rather than incremental polish on the default dark-dashboard look.
2. Make every view (home, generating, success, error) feel like one cohesive piece of broadcast equipment.
3. Look striking on a 1080p screen recording (the hackathon submission video).
4. Preserve all current functionality unchanged: form fields, POST flow, progress polling, file routes, run listing, all backend behavior.
5. Keep the implementation auditable and reversible — one git revert undoes the redesign cleanly.

## Non-goals

- New features or backend changes.
- Building a JS framework or design-system component library.
- Changing the Python web server choice (stays `http.server`).
- A separate mobile experience — single responsive design only.
- Backwards-compatibility with the old visual classes — old `_page_shell` is replaced wholesale.

## Aesthetic direction (locked)

**Retro Broadcast → VHS Cassette sub-flavor → Medium effect intensity.**

VHS sub-flavor characteristics: warm degraded SMPTE color bars, label-maker tape stickers (cream sticker + brown ink, slight rotation), RGB chromatic ghost on hero headlines, EP/SP/LP tape mode toggles, occasional tracking-error and dropout animations, monospace technical chrome, scanline overlay, CRT vignette. Reads as "home recording you found in a drawer" — playful, nostalgic, character-rich. Most distinctive on a screen recording.

Medium effect intensity: scanlines + CRT vignette + subtle noise are always-on but tasteful; RGB ghost only on hero headlines; tracking-error and dropout animations fire on key beats (form submit, render complete, error) rather than constantly; reduced-motion media query disables all decorative motion.

Scope decision: option C — visual + voice + structural rewrite. Each view's layout is restructured (not just repainted), microcopy is rewritten in broadcast voice ("Roll Tape", "Eject", "Tape Archive", "Broadcast Cue Sheet"), and the page chrome is reshaped into a "control deck" metaphor.

## Section 1: Foundation

### File architecture

```
src/repo_to_shorts/
  web.py                    # gains /static/<path> route, render funcs lose <style> blob
  static/
    style.css               # ~700 lines — tokens + components + view-specific
    app.js                  # extracted form-submit/progress-poll behavior
    fonts/
      Anton-Regular.woff2
      JetBrainsMono-Regular.woff2
      JetBrainsMono-Bold.woff2
```

`web.py`'s `_page_shell` emits `<link rel=stylesheet href="/static/style.css">` and `<script src="/static/app.js" defer>`. Render functions emit body markup only — no inline styles.

### Color tokens (CSS custom properties)

| Token | Value | Use |
|---|---|---|
| `--bg` | `#0b0707` | page background (warm near-black, slight red) |
| `--panel` | `#120c0c` | raised surfaces |
| `--panel-2` | `#1a1010` | inset surfaces, inputs |
| `--ink` | `#f0e8d8` | primary text (aged-paper warm) |
| `--ink-2` | `#c9b89a` | body |
| `--ink-3` | `#8a7a64` | tertiary, captions |
| `--ink-4` | `#5a4632` | dividers, dashed borders |
| `--label-cream` | `#e8d8b6` | tape sticker fill |
| `--label-ink` | `#3a2a14` | tape sticker text |
| `--rec` | `#ff5e5e` | REC, error |
| `--live` | `#ff8c4a` | active stage, in-progress |
| `--lock` | `#4afa8c` | success, signal locked |
| `--ghost-magenta` | `#ff3a8e` | RGB ghost left |
| `--ghost-cyan` | `#38d8ff` | RGB ghost right |
| `--bar-silver` | `#bcb6a8` | SMPTE color bar 1 |
| `--bar-yellow` | `#c8b832` | SMPTE color bar 2 |
| `--bar-cyan` | `#3ab2b9` | SMPTE color bar 3 |
| `--bar-green` | `#4cb24a` | SMPTE color bar 4 |
| `--bar-magenta` | `#bf3aa8` | SMPTE color bar 5 |
| `--bar-red` | `#c8392a` | SMPTE color bar 6 |
| `--bar-blue` | `#3a48b9` | SMPTE color bar 7 |

### Typography

- **Display (h1, hero, scene labels):** Anton — locally-hosted woff2 (SIL OFL). Fallback: `"Helvetica Neue Condensed", "Arial Narrow", sans-serif`. Always `text-transform: uppercase`. `font-display: swap`. Preloaded.
- **Mono (timecodes, channel labels, technical readouts, code):** JetBrains Mono Regular + Bold — locally-hosted woff2. Fallback: `ui-monospace, SFMono-Regular, Menlo, monospace`.
- **Body sans (lede, paragraphs):** system stack — `system-ui, -apple-system, "Inter", sans-serif`. Used sparingly.
- **Type scale:** 10 / 11 / 13 / 16 / 24 / 38 / 64 / 96 px. Hero on home is 96px. Success page hero is 64px.

### Spacing & geometry

- 4px base. Scale: 4, 8, 12, 16, 24, 32, 48, 64, 96.
- **Radius: 0** by default. Single exception: `2px` on tiny chips/pills.
- **Shadows:** no soft modern shadows. Hard 2-3px offset shadows for tape labels. Inset CRT vignette via `box-shadow: inset 0 0 80px rgba(0,0,0,.55)` on main shell.

### Motion tokens

- `--motion-quick: 80ms` (hover, button press)
- `--motion-base: 200ms` (state changes, progress fill)
- `--motion-glitch: 320ms` (tracking-error burst)
- `--motion-eject: 450ms` (page transitions)
- Cursor blink: `1s steps(2) infinite`
- Color-bar shimmer: 8s slow hue-rotate, hero only
- **Scanlines: static** (real CRT scanlines don't drift; also avoids motion sickness)

### Effects library (CSS utilities)

- `.fx-scanlines` — repeating linear-gradient overlay
- `.fx-crt` — inset vignette + barely-perceptible barrel-distortion via `filter`
- `.fx-rgb-ghost` — text-shadow chromatic split (magenta + cyan)
- `.fx-tracking-error` — keyframe animation, fires on `[data-glitch]` events
- `.fx-tape-edge` — top/bottom 2px tape-damage stripes, looped via animation
- `.fx-noise` — 8KB inline SVG noise pattern, very low opacity

### Accessibility

`@media (prefers-reduced-motion: reduce)` block disables: scanlines, color-bar shimmer, glitch keyframes, dropout flashes, tape-edge dropout animation. Functional UI updates (progress fills, state changes, timecode tick) are preserved.

## Section 2: Component vocabulary

Fourteen components, each a single CSS class (or pair) with predictable markup. Every view is composed from these.

### Identity & framing

**`.slate`** — top-of-page status strip. Three columns: left = channel/state (`● REC`, `● ON AIR`, `▣ SIGNAL LOCKED`, `● SIGNAL LOST`), center = title/context, right = timecode. Mono 10px, .18em letter-spacing, dashed `--ink-4` divider below.

```html
<header class="slate">
  <span class="slate-state">● REC</span>
  <span class="slate-title">CH 02 — HERMES</span>
  <span class="slate-tc">00:00:00:00</span>
</header>
```

**`.colorbars`** — 7-stripe SMPTE strip. Modifiers: `.colorbars--banner` (12px, full-width) and `.colorbars--inline` (6px, in-card divider). Slightly desaturated palette per tokens.

**`.tape-edge`** — 2px stripe at top and bottom of main shell, with subtle dropout animation every ~8s.

### Inputs & controls

**`.tape-input`** — URL field. Black panel, dashed `--ink-4` border, mono font, blinking cursor `▌` prefix. On focus: cursor turns `--live` orange, border becomes solid `--ink-3`.

**`.btn-tape`** — chunky transport button. Sharp corners, mono uppercase, .18em letter-spacing. Modifiers: `.btn-tape--primary` (fill `--ink`, text `--bg`, leading symbol ▶ or ⏬), `.btn-tape--ghost` (transparent, 1px solid border, leading ⏏ or ⚙), `.btn-tape--rec` (fill `--rec`). Hover: 80ms lift + brightness(1.08). Active: presses inward 1px.

**`.toggle-mode`** — three-pill cluster, only one lit at a time. Lit state = `--label-cream` fill, `--label-ink` text, `transform: rotate(-1.2deg)`. Used for SP/LP/EP and DOLBY/OFF.

### Status & data

**`.status-pill`** — small inline state marker. Variants: `.is-rec` (red, blinking dot), `.is-live` (orange), `.is-lock` (green), `.is-idle` (`--ink-4`).

**`.channel-row`** — three columns: `[label] [bar] [status]`. Label mono 10px. Bar fills left→right, `--live` while running, `--lock` when done. Used 7× on generating view, also reused on home as channel-readiness readout.

```html
<div class="channel-row" data-state="live">
  <span class="ch-label">▶ FRAMES</span>
  <div class="ch-bar"><div class="ch-fill" style="width:62%"></div></div>
  <span class="ch-status">LIVE · 62%</span>
</div>
```

State on `data-state` attribute: `idle`, `stby`, `live`, `done`, `error`.

**`.vu-meter`** — 20-segment LED bar, generating view only. Greens → amber → red at the end. CSS keyframe animation (no JS required).

**`.scope-strip`** — bottom diagnostic readout: `TBC · SC-H · DROPOUT 0.0% · AGC ON · 1080×1920 · 30FPS`. Mono 9px, `--ink-4`, .18em tracking.

### Containers & viewports

**`.deck`** — primary panel container. `--panel` background, 1px `--ink-4` border, sharp corners, internal CRT vignette via inset shadow. Replaces the rounded glass cards.

**`.crt-viewport`** — video/preview frame. Aspect 9:16, slight inset radial gradient for screen curvature, 2px `--ink-4` outer border, `--rec` "● PLAY" overlay before video starts.

**`.tape-label`** — cream Brother P-touch sticker. `--label-cream` fill, `--label-ink` text, hard 2px black offset shadow, `transform: rotate(-1.2deg)`.

### Display

**`.glitch-headline`** — big VHS hero text. Anton, uppercase, `--ink`. `.fx-rgb-ghost` text-shadow. On `[data-glitch]` events, `.fx-tracking-error` fires for 320ms.

**`.kicker`** — small uppercase preamble label. Mono 11px, `--ink-3`, .18em tracking. Always paired above a headline.

## Section 3: View specs

### A. HOME (`/`)

```
┌─ tape-edge ─────────────────────────────────────────┐
│ ● REC   CH 02 — HERMES STUDIO        00:00:00:00    │  slate
│ ▓▓▓▓▓▓▓ colorbars--banner ▓▓▓▓▓▓▓                  │
│                                                     │
│   // SIGNAL IN. STORY OUT.                          │  kicker
│   REPO  →  REEL.                                    │  glitch-headline (96px)
│   Paste a repo. Kimi writes the brief.              │  lede (mono)
│   Hermes cuts the reel.                             │
│                                                     │
│ ┌─ DECK (control) ────────────────────────────────┐ │
│ │ CH · INPUT          tape-input                  │ │
│ │ AUDIENCE TARGET     tape-input                  │ │
│ │ MODEL FEED          tape-input                  │ │
│ │                                                  │ │
│ │ MODE   [SP][LP][EP]    AUDIO  [DOLBY][OFF]      │ │  toggle-mode × 2
│ │                                                  │ │
│ │ [⏏ INGEST]   [▶ ROLL TAPE]   [⚙ FALLBACKS]      │ │  btn-tape row
│ │ ──────────────────────────────────────────────── │ │
│ │ CH·KIMI    ━━━━━━━━━━     READY                 │ │  channel-row × 4
│ │ CH·HERMES  ━━━━━━━━━━     READY                 │ │
│ │ CH·TAPE    ━━━━━━━━━━     READY                 │ │
│ │ CH·OUTPUT  ━━━━━━━━━━     IDLE                  │ │
│ └──────────────────────────────────────────────────┘ │
│                                                     │
│ TAPE ARCHIVE                                        │
│  ╲ REEL · 001  · 2026-05-04 · 60s ·  [⏬ master]   │  tape-label rows
│  ╲ REEL · 002  · 2026-05-04 · 60s ·  [⏬ master]   │
│                                                     │
│ scope-strip                                         │
└─ tape-edge ─────────────────────────────────────────┘
```

**Copy rewrite:**
- Generate → `▶ ROLL TAPE`
- Latest runs → `TAPE ARCHIVE`
- Target repo → `CH · INPUT`
- Audience → `AUDIENCE TARGET`
- Kimi model → `MODEL FEED`
- Three checkboxes → `SP / LP / EP` tape-mode toggle (SP=fast, LP=preview+audio, EP=full master) and `DOLBY / OFF` audio toggle. The classic-MP4 toggle moves under a `[⚙ FALLBACKS]` ghost button (de-emphasized).

**Mapping SP/LP/EP to backend POST fields** (preserves backend contract):
| Tape mode | `creative_mode` | `preview` | `skip_audio` |
|---|---|---|---|
| SP (fast silent preview — default) | on | on | on |
| LP (preview with narration) | on | on | off |
| EP (full master) | on | off | off |

The toggle is a JS-managed UI; on submit, JS writes the three boolean values to hidden inputs that match the existing form field names. No backend change.

### B. GENERATING (in-place takeover, same URL)

When form submits, the control deck is replaced (in-place, no navigation) by the broadcasting deck.

```
│ ● ON AIR   BROADCASTING — REEL.001     00:00:34:12  │  slate (red, pulsing; tc ticks via JS)
│ ▓▓▓▓▓▓▓ colorbars--banner ▓▓▓▓▓▓▓                  │
│                                                     │
│   // NOW BROADCASTING                                │
│   RENDERING FRAMES…                                  │  glitch-headline (64px)
│                                                     │
│ ┌─ DECK ──────────────────────────────────────────┐ │
│ │ ▣ INGEST       ████████████████████   DONE      │ │
│ │ ▣ KIMI BRIEF   ████████████████████   DONE      │ │  channel-row × 7
│ │ ▶ FRAMES       ███████████░░░░░░░░░   LIVE 62%  │ │
│ │ ○ NARRATION    ░░░░░░░░░░░░░░░░░░░░   STBY      │ │
│ │ ○ COMPOSE      ░░░░░░░░░░░░░░░░░░░░   STBY      │ │
│ │ ○ MASTER       ░░░░░░░░░░░░░░░░░░░░   STBY      │ │
│ │ ○ PROOF        ░░░░░░░░░░░░░░░░░░░░   STBY      │ │
│ │                                                  │ │
│ │  ▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌░░░░░  vu-meter              │ │
│ └──────────────────────────────────────────────────┘ │
│                                                     │
│ TBC · SC-H · DROPOUT 0.0% · AGC ON · ETA ~12s       │  scope-strip (live)
```

**On submit:** `.fx-tracking-error` fires once on the headline (320ms chromatic burst). Timecode counter starts ticking via JS (`mm:ss:ff` format, 30fps frames). On `percent === 100`: dropout flash, then existing redirect-to-success behavior.

### C. SUCCESS (`/generate` POST renders)

Two-column layout (60/40):

```
│ ▣ SIGNAL LOCKED   REEL.001 — MASTER   00:01:00:00   │  slate (green)
│ ▓▓▓▓▓▓▓ colorbars--banner ▓▓▓▓▓▓▓                  │
│                                                     │
│   // BROADCAST COMPLETE                             │
│   {{ creative_brief.title }}                        │  glitch-headline (64px)
│   {{ creative_brief.hook }}                         │  lede
│                                                     │
│ ┌─ MASTER VIEWER ─────┐ ┌─ BROADCAST CUE SHEET ───┐ │
│ │   crt-viewport      │ │ 01  PRETEXT             │ │
│ │   <video controls>  │ │     "..."               │ │  scene rows
│ │                     │ │ 02  MANIM               │ │  (channel-row variant)
│ │ TAPE: REEL.001…MP4  │ │     "..."               │ │
│ │ KIMI: LIVE-API      │ │ ...                     │ │
│ │ MASTER: 1080×1920   │ └─────────────────────────┘ │
│ │                     │                              │
│ │ [⏬ MASTER] [⏏ NEW]  │  ARTIFACTS                  │
│ └─────────────────────┘   tape-label tiles           │
```

**Copy rewrite:** Generation complete → `BROADCAST COMPLETE`. Download → `⏬ MASTER`. New run → `⏏ NEW REEL`. Run → `TAPE`. Creative brief → `BROADCAST CUE SHEET`. Artifact gallery → `ARTIFACTS` (each as a tape-label tile, slight rotate).

### D. ERROR (`/generate` 4xx/5xx)

```
│ ● SIGNAL LOST   CH 02 — TRACKING ERROR  --:--:--:-- │  slate (red, blinking)
│ ▓ ▓▓▓ ▓▓ broken-colorbars (extra dropouts) ▓▓ ▓ ▓▓ │
│                                                     │
│   // TAPE ATE THE REEL.                             │
│   TRACKING ERROR.                                   │  glitch-headline (heavy ghost)
│                                                     │
│ ┌─ ERROR LOG ─────────────────────────────────────┐ │
│ │ ! {{ exception_message }}                       │ │  mono, --rec border-left
│ └──────────────────────────────────────────────────┘ │
│                                                     │
│ [⏏ EJECT TAPE]                                       │  back to home
```

**Rotating headline:** randomly picks from `["TRACKING ERROR.", "TAPE ATE THE REEL.", "SIGNAL LOST.", "DROPOUT.", "BAD HEAD."]` per page render — adds character without being silly.

## Section 4: Implementation plan

Six phases, designed for parallel execution by subagents working from this spec.

### Phase 0 — Plumbing
1. `mkdir -p src/repo_to_shorts/static/fonts/`
2. Add `/static/<path>` route to `web.py do_GET`. Copy traversal protection from `resolve_run_file`.
3. Headers: `Content-Type` from `mimetypes.guess_type`, `Cache-Control: public, max-age=3600` for static assets.
4. Bundle `Anton-Regular.woff2`, `JetBrainsMono-Regular.woff2`, `JetBrainsMono-Bold.woff2` (download from Google Fonts repo, all SIL OFL).
5. Strip inline `<style>` and `<script>` from `_page_shell`. Replace with:
   ```html
   <link rel="preload" as="font" type="font/woff2" href="/static/fonts/Anton-Regular.woff2" crossorigin>
   <link rel="stylesheet" href="/static/style.css">
   <script src="/static/app.js" defer></script>
   ```

### Phase 1 — CSS foundation
1. `static/style.css` token layer: `:root { --bg: #0b0707; ... }` with all tokens from Section 1.
2. `@font-face` declarations for Anton + JetBrains Mono.
3. Reset + base `body` (font, color, bg, applies `.fx-scanlines` `.fx-crt` `.fx-noise`).
4. `@media (prefers-reduced-motion: reduce)` block disabling decorative motion.

### Phase 2 — Components
Build all 14 components per Section 2. Order: identity (`.slate`, `.colorbars`, `.tape-edge`) → inputs (`.tape-input`, `.btn-tape`, `.toggle-mode`) → status (`.status-pill`, `.channel-row`, `.vu-meter`, `.scope-strip`) → containers (`.deck`, `.crt-viewport`, `.tape-label`) → display (`.glitch-headline`, `.kicker`).

### Phase 3 — Effects
1. `.fx-tracking-error` keyframes (chromatic burst + 2-3px Y-shift, 320ms).
2. Cursor blink, color-bar shimmer (8s hue-rotate).
3. Tape-edge dropout flash (~8s interval, plus on-demand class for one-shot).

### Phase 4 — Views
Rewrite `render_home_page`, `render_success_page`, `render_error_page` and the in-form generating-state markup using the component vocabulary. No inline styles in render output.

### Phase 5 — JS rewire
1. Move `static/app.js` out of inline; preserve existing behavior first.
2. Add SP/LP/EP toggle handler that writes to hidden inputs (`creative_mode`, `preview`, `skip_audio`).
3. Fire `.fx-tracking-error` on submit (replaces "Generating…" button text swap).
4. Update progress-poll: instead of class-swapping `.progress-stage`, set `data-state` on `.channel-row`.
5. Timecode ticker (mm:ss:ff format, 30fps) running during generating state.
6. On `percent >= 100`: fire dropout flash, then redirect (existing form re-submit behavior).
7. Rotating error headline picker.
8. Respect `prefers-reduced-motion`.

### Phase 6 — Tests
1. `test_web_static_serves_css` — `GET /static/style.css` → 200, content-type `text/css`.
2. `test_web_static_serves_js` — `GET /static/app.js` → 200, content-type `application/javascript`.
3. `test_web_static_serves_fonts` — `GET /static/fonts/Anton-Regular.woff2` → 200.
4. `test_web_static_traversal_blocked` — `GET /static/../web.py` → 404.
5. `test_web_home_uses_new_components` — `GET /` body contains `class="slate"`, `class="channel-row"`, `class="btn-tape"`, `class="glitch-headline"`.
6. `test_web_error_renders_with_new_class` — POST `/generate` empty target → response contains `glitch-headline` and one of the rotating error headlines.

Existing 53 pytest tests run unchanged.

## Acceptance criteria

- [ ] All four views render with new VHS aesthetic.
- [ ] All existing form fields submit successfully; backend pipeline produces identical output.
- [ ] Progress polling drives the channel rows correctly (`stby` → `live` → `done`).
- [ ] Submit fires the glitch animation; render-complete fires the dropout flash.
- [ ] Tape-mode toggle (SP/LP/EP) correctly maps to the three backend booleans.
- [ ] Existing 53 pytest tests pass unchanged.
- [ ] New 6 web tests pass.
- [ ] `ruff check .` passes.
- [ ] Reduced-motion mode disables all decorative animations.
- [ ] Site renders correctly on a 1080p screen recording (manual check via QuickTime).
- [ ] One git revert restores the prior design (no orphan files left behind).

## Risks

1. **Font loading flash** — Anton fallback to system condensed during first paint. Mitigated by `<link rel=preload>` + `font-display: swap`. Acceptable: 50ms swap.
2. **Color bars on screen recording** — saturated rainbow stripes can shimmer/moiré in lossy codecs. Desaturated SMPTE palette already mitigates; validated via the screen-record test.
3. **SP/LP/EP semantic change** — three checkboxes → one tri-state is a real product change. Toggle is purely cosmetic JS; backend POST fields unchanged. Reversible without redoing CSS.
4. **DOM ID changes during JS migration** — existing `app.js` reads `#progress-detail`, `#progress-bar-fill`, `#progress-stages`. New markup uses `.channel-row[data-state]`. Both updated in one commit.

## Out of scope (explicit)

- Backend changes of any kind.
- Changes to `cli.py`, `pipeline.py`, `hermes_skill.py`, `creative_director.py`, `kimi.py`, `compositor.py`, `manim_render.py`, `progress.py`, `render.py`, `ingest.py`.
- Adding a build step (no Tailwind, PostCSS, esbuild, etc.).
- Adding any new dependencies to `pyproject.toml`.
- New JS framework or component library.
- Changes to file output (videos, metadata.json, artifact filenames).
