# Repo-to-Shorts Polish Upgrade Plan

## Current State Assessment

### What's working
- Web UI loads, form submits, result page renders
- Loading state shows immediately on click (button disabled, spinner visible)
- Creative pipeline runs end-to-end: ingest → Kimi brief → render → TTS → compose
- Tests pass (56 passed), ruff clean
- Server runs on LAN for MacBook testing

### What's broken / ugly
1. **No progress tracking**: Browser sees "Generating…" for 2-5 minutes with no stage breakdown
2. **TTS is macOS `say`**: Sounds like a 2005 GPS robot. Unacceptable for a demo video.
3. **Visuals are Pillow slop**: Static frames with Arial font, basic gradients, no motion, no transitions. Looks like a cheap Canva template.
4. **No scene motion**: Each scene is a static PNG held for N seconds. No text animations, no camera moves, no particle effects.
5. **Captions are basic**: ffmpeg drawtext with Menlo font, black box. Not TikTok/Instagram style.
6. **No background music**: Silent video except for robotic voice.

---

## Upgrade Targets

### 1. Progress Bar (P0 — user asked)
**Problem**: 2-5 minute synchronous POST with no stage visibility.
**Solution**: Lightweight in-memory progress tracker + polling endpoint.
**Stages to track**:
- `ingest` — cloning / reading repo
- `analyze` — building repo analysis struct
- `kimi_brief` — calling creative director
- `render_frames` — generating scene frames
- `tts` — generating voice narration
- `compose` — mixing audio + video
- `finalize` — writing metadata, packaging

**Implementation**:
- Add `_progress_store: dict[str, list[dict]]` in web.py (session_id → stages)
- Each pipeline stage calls `_report_progress(session_id, stage, status, detail)`
- New endpoint: `GET /progress?session=<id>` returns JSON
- Frontend polls `/progress` every 2s while loading panel is visible
- Display stage names with checkmarks / active indicators

### 2. TTS Upgrade (P0 — biggest audio quality win)
**Problem**: `say` command is robotic garbage.
**Solution**: Use `edge-tts` (already installed) for neural voices.
**Voice**: `en-US-AriaNeural` or `en-US-GuyNeural` — both are high-quality neural TTS.
**Fallback**: If edge-tts fails, fall back to `say`.

**Implementation**:
- Replace `generate_tts()` in `compositor.py`
- Use `edge-tts` CLI or Python API
- Cache TTS per scene to avoid re-generation
- Add `--voice` option to CLI/web UI

### 3. Visual Frame Upgrade (P1 — biggest visual quality win)
**Problem**: Static frames with Arial font, no motion, no camera.
**Solution**: Keep Pillow but dramatically improve design + add ffmpeg-based motion.

**Frame design improvements**:
- Download Inter font or use SF Pro / system fonts
- Cinematic gradient backgrounds (not flat colors)
- Glow effects behind text
- Subtle animated grain/noise texture overlay
- Code snippet insets with syntax highlighting
- Component cards that "float" with shadow

**Motion improvements (via ffmpeg filters)**:
- `zoompan` for slow camera push on each scene
- `fade` transitions between scenes
- `gblur` for depth-of-field blur on background
- `colorchannelmixer` for color grading
- Subtle `vignette` effect

### 4. Karaoke Captions (P1)
**Problem**: Static captions with black box. Boring.
**Solution**: Word-by-word highlight captions like TikTok/Instagram Reels.
**Implementation**:
- Parse narration into words
- Generate SRT with per-word timestamps
- Use ffmpeg `drawtext` with `enable='between(t,start,end)'` per word
- Highlight active word in accent color, dim others

### 5. Background Music (P2)
**Problem**: Silent video feels empty.
**Solution**: Generate ambient electronic music with `audiocraft` or use a royalty-free loop.
**Alternative**: Use `heartmula` skill for generated music (but requires GPU/setup).
**Simpler**: Use a pre-generated ambient loop or generate with AudioCraft MusicGen.

### 6. Scene Design Principles (P1)
Apply lessons from loaded skills:
- `manim-video`: Use opacity layering, breathing room, cohesive palette
- `pretext`: Better typography, real fonts, kinetic text
- `claude-design`: Dark premium aesthetic, considered palette
- `popular-web-designs`: Linear/Stripe/Vercel design language

Each scene should have:
- A dominant color from a cohesive palette
- A clear hierarchy: title > body > footer
- Motion: text fade-in, scale, or slide
- A visual element that ties to the repo (file tree snippet, architecture SVG, code highlight)

---

## Implementation Order

1. **Progress bar** (fastest win, user explicitly asked)
2. **TTS upgrade** (edge-tts, dramatic audio improvement)
3. **Visual frame redesign** (better fonts, gradients, effects)
4. **Karaoke captions** (word-by-word highlight)
5. **Background music** (ambient loop)
6. **Scene motion** (ffmpeg zoompan, transitions)

---

## Risks

- **edge-tts requires network**: May fail offline. Fallback to `say` needed.
- **Font availability**: Inter may not be installed. Need to download or use SF Pro.
- **ffmpeg filter complexity**: Complex filtergraphs can break. Test incrementally.
- **Time**: Each improvement adds risk. Ship incrementally, test each change.

---

## Success Criteria

- [ ] User clicks Generate, sees 7-stage progress bar updating in real-time
- [ ] Generated video has neural TTS voice (not robotic)
- [ ] Video frames look cinematic, not like a template
- [ ] Captions highlight word-by-word
- [ ] Background music plays subtly under narration
- [ ] All tests pass, ruff clean
- [ ] Server restarts successfully on LAN
