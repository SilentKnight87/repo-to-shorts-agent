# Creative Rendering Engine — Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Replace Pillow text-card "slop" rendering with Kimi 2.6 creative direction + Manim animation + Pretext typography + ffmpeg composition, producing hackathon-winning creative shorts from any GitHub URL.

**Architecture:** Kimi 2.6 (via OpenRouter) acts as creative director: it analyzes the repo, decides visual style + scene breakdown + tool selection per scene, then orchestrates Manim (code animation), Pretext (typography/kinetic text), Architecture-diagram (SVG structure), and ASCII-video (stylistic segments). ffmpeg composes final video with TTS narration and background music. Everything wrapped as a Hermes Agent skill.

**Tech Stack:** Python 3.13, OpenRouter Kimi 2.6, Manim CE, Pretext (HTML/CSS), ffmpeg, macOS `say` (TTS), existing `repo_to_shorts` ingest/pipeline.

---

## Current vs Target

| Area | Current (slop) | Target |
|------|-------|--------|
| Creative direction | Hardcoded 5-scene template | Kimi 2.6 decides visual style, pacing, tool per scene |
| Visuals | Pillow text cards (static slides) | Manim animated code viz + Pretext kinetic typography |
| Narration | AI describing its own pipeline | Creative storytelling about the repo's purpose |
| Voice | None | macOS `say` TTS, upgrade path to ElevenLabs |
| Music | None | Background score (royalty-free or generated) |
| Kimi critic | Deterministic fallback only | Live OpenRouter Kimi 2.6 creative director + QC pass |
| Output format | Vertical slideshow | Produced creative short with scene transitions |
| Agent integration | Typer CLI only | Hermes Agent skill wrapping the full pipeline |

## Non-Negotiables

- Kimi 2.6 MUST be the creative director — it decides, not hardcoded templates
- Do not rewrite `ingest.py` or core `pipeline.py` — extend, don't break
- API keys from environment only (OPENROUTER_API_KEY already set)
- Every scene must have a creative rationale in metadata (why this style, why this tool)
- Golden path must work without credentials (deterministic fallback with Manim only)
- Live path uses OpenRouter Kimi 2.6 for creative direction

---

## Architecture

```
GitHub URL or local path
        │
        ▼
┌───────────────────┐
│  ingest.py         │  (unchanged — repo snapshotting)
│  pipeline.py       │  (unchanged — artifact generation)
└───────┬───────────┘
        │ repo analysis (brief, structure, key files)
        ▼
┌───────────────────┐
│  CREATIVE DIRECTOR │  ★ NEW — kimi_creative_director.py
│  (Kimi 2.6)        │
│                    │  Input: repo analysis
│  Decides:          │  Output: creative_brief.json
│  - Visual style    │    - style: "dark-terminal" | "clean-academic" | "playful"
│  - Scene breakdown │    - scenes[] with: duration, visual_tool, narration_text,
│  - Tool per scene  │      music_mood, transition
│  - Music mood      │
│  - Pacing          │
└───────┬───────────┘
        │ creative_brief.json
        ▼
┌───────────────────┐
│  RENDER ENGINES    │  ★ NEW — replaces render.py
│                    │
│  ┌───────────────┐ │
│  │ manim_render  │ │  Animated code viz, architecture reveals
│  └───────────────┘ │
│  ┌───────────────┐ │
│  │ pretext_render│ │  Kinetic typography, title sequences
│  └───────────────┘ │
│  ┌───────────────┐ │
│  │ ascii_render  │ │  Stylistic code-to-ASCII sequences
│  └───────────────┘ │
│  ┌───────────────┐ │
│  │ svg_render    │ │  Architecture-diagram (existing + enhanced)
│  └───────────────┘ │
└───────┬───────────┘
        │ per-scene video clips
        ▼
┌───────────────────┐
│  COMPOSITOR        │  ★ NEW — compositor.py
│                    │
│  - TTS narration   │  macOS `say` → .aiff → ffmpeg
│  - Background music│  Royalty-free or generated
│  - Scene stitching │  ffmpeg concat + crossfade
│  - Captions        │  Burn SRT subtitles
│  - Audio mixing    │  Voice + music ducking
└───────┬───────────┘
        │ final demo.mp4
        ▼
┌───────────────────┐
│  KIMI QC PASS      │  (optional, live mode)
│  - Watch final     │
│  - Flag issues     │
│  - Suggest fixes   │
└───────────────────┘
```

---

## File Plan

**Create:**
- `src/repo_to_shorts/creative_director.py` — Kimi 2.6 creative direction
- `src/repo_to_shorts/manim_render.py` — Manim scene generation + rendering
- `src/repo_to_shorts/pretext_render.py` — Pretext kinetic typography scenes
- `src/repo_to_shorts/ascii_render.py` — ASCII-video stylized segments
- `src/repo_to_shorts/compositor.py` — ffmpeg composition + TTS + music
- `src/repo_to_shorts/hermes_skill.py` — Hermes Agent skill wrapper
- `tests/test_creative_director.py`
- `tests/test_manim_render.py`
- `tests/test_compositor.py`

**Modify:**
- `src/repo_to_shorts/render.py` — deprecated, replaced by new engines
- `src/repo_to_shorts/cli.py` — add `creative` subcommand
- `src/repo_to_shorts/pipeline.py` — route to creative director when `--creative` flag
- `README.md` — document creative mode
- `AGENTS.md` — update architecture

**Preserve (unchanged):**
- `src/repo_to_shorts/ingest.py`
- `src/repo_to_shorts/kimi.py` (use for API calls)
- `tests/test_pipeline.py`, `tests/test_kimi.py`

---

## Task 1: Creative Director Module

**Objective:** Kimi 2.6 analyzes repo context and outputs a structured creative brief (JSON) dictating visual style, scene breakdown, and tool selection per scene.

**Files:**
- Create: `src/repo_to_shorts/creative_director.py`
- Test: `tests/test_creative_director.py`

**Step 1: Write failing test**

Test that `direct_scene()` returns a valid `CreativeBrief` with required fields:
- `style`: one of `["dark-terminal", "clean-academic", "playful", "cinematic"]`
- `scenes`: list of dicts with `{duration_seconds, visual_tool, narration, music_mood, transition}`
- `title`: creative title for the short
- `hook`: opening hook line

Mock the OpenRouter API call. Test deterministic fallback when no key.

**Step 2: Implement creative director**

```python
# src/repo_to_shorts/creative_director.py

from dataclasses import dataclass, field
from pathlib import Path
import json
from .kimi import _call_openrouter_api, _get_api_key

@dataclass
class CreativeBrief:
    style: str
    title: str
    hook: str
    scenes: list = field(default_factory=list)
    music_mood: str = "ambient"
    total_duration: int = 60

def direct(repo_analysis: dict, model: str = "moonshotai/kimi-k2.6") -> CreativeBrief:
    """Kimi 2.6 creative director: analyze repo → output creative brief."""
    api_key = _get_api_key()
    if not api_key:
        return _deterministic_fallback(repo_analysis)
    
    prompt = _build_director_prompt(repo_analysis)
    response = _call_openrouter_api(api_key, model, prompt, json_mode=True)
    
    if response.get("mode") == "api-error-fallback":
        return _deterministic_fallback(repo_analysis)
    
    return _parse_brief(response["content"])

def _build_director_prompt(analysis: dict) -> str:
    """Build the creative director prompt from repo analysis."""
    return f"""You are a creative director for technical demo videos. 
Given this repo analysis, create a creative brief for a 60-second short video.

REPO: {analysis.get('repo_name')}
DESCRIPTION: {analysis.get('description', '')}
LANGUAGE: {analysis.get('primary_language', '')}
KEY_FILES: {analysis.get('key_files', [])}
PURPOSE: {analysis.get('purpose', '')}

Output valid JSON:
{{
  "style": "dark-terminal|clean-academic|playful|cinematic",
  "title": "creative video title",
  "hook": "opening hook line (5-8 words, punchy)",
  "scenes": [
    {{
      "duration_seconds": 10,
      "visual_tool": "manim|pretext|ascii|svg",
      "narration": "narration text for this scene",
      "music_mood": "tension|reveal|energy|calm",
      "transition": "cut|fade|slide-left|zoom"
    }}
  ],
  "music_mood": "ambient|electronic|orchestral|minimal",
  "total_duration": 60
}}

Rules:
- 4-6 scenes, total ~60 seconds
- Hook scene first (5-8s, punchy)
- Vary visual_tool across scenes — don't use the same tool twice in a row
- Narration should tell a STORY about what this code ENABLES, not list files
- Style should match the repo's vibe (framework→clean-academic, game→playful, infra→dark-terminal, crypto→cinematic)
"""

def _deterministic_fallback(analysis: dict) -> CreativeBrief:
    """Fallback when no API key — still decent, not slop."""
    return CreativeBrief(
        style="dark-terminal",
        title=f"{analysis.get('repo_name', 'This Repo')}: What It Builds",
        hook="One repo. Infinite possibilities.",
        scenes=[
            {"duration_seconds": 8, "visual_tool": "pretext", 
             "narration": f"{analysis.get('repo_name')} — let's see what it builds.",
             "music_mood": "tension", "transition": "fade"},
            {"duration_seconds": 15, "visual_tool": "svg",
             "narration": "Here's the architecture. Clean. Focused. Purpose-built.",
             "music_mood": "reveal", "transition": "cut"},
            {"duration_seconds": 20, "visual_tool": "manim",
             "narration": "Watch how the pieces connect. Each component has one job, and it does it well.",
             "music_mood": "energy", "transition": "slide-left"},
            {"duration_seconds": 12, "visual_tool": "ascii",
             "narration": "Under the hood: every line of code serves the mission.",
             "music_mood": "energy", "transition": "fade"},
            {"duration_seconds": 5, "visual_tool": "pretext",
             "narration": f"repo-to-shorts: from code to creative short. Generated by Hermes Agent.",
             "music_mood": "calm", "transition": "fade"},
        ],
        music_mood="electronic",
        total_duration=60
    )
```

**Step 3: Verify**

```bash
.venv/bin/python -m pytest tests/test_creative_director.py -q
```

Expected: pass.

---

## Task 2: Manim Rendering Engine

**Objective:** Generate animated code visualization scenes using Manim CE. Each scene is a self-contained `.py` file that renders to MP4.

**Files:**
- Create: `src/repo_to_shorts/manim_render.py`
- Test: `tests/test_manim_render.py`

**Step 1: Install Manim dependencies**

```bash
.venv/bin/pip install manim
# Manim requires LaTeX for equations — install MacTeX if needed:
# brew install --cask mactex
# For MVP, use Text() only (no MathTex) to skip LaTeX requirement
```

**Step 2: Write failing test**

Test that `generate_manim_script()` produces valid Python Manim code:
- File starts with `from manim import *`
- Contains at least one `class.*Scene`
- Has `self.play()` calls
- Has `self.wait()` calls

Test that `render_scene()` calls `manim` CLI and produces `.mp4` (mock the subprocess).

**Step 3: Implement Manim generator**

```python
# src/repo_to_shorts/manim_render.py

def generate_manim_script(scene: dict, repo_analysis: dict, output_dir: Path) -> Path:
    """Generate a self-contained Manim scene script from a creative brief scene."""
    
    style = scene.get("style", "dark-terminal")
    narration = scene.get("narration", "")
    
    # Map creative brief style → Manim color palette
    palettes = {
        "dark-terminal": ("#0A0A0A", "#00F5FF", "#FF00FF", "#39FF14"),
        "clean-academic": ("#1C1C1C", "#58C4DD", "#83C167", "#FFFF00"),
        "playful": ("#2D2B55", "#FF6B6B", "#FFD93D", "#6BCB77"),
        "cinematic": ("#0D0D0D", "#FF4500", "#FFD700", "#FFFFFF"),
    }
    bg, primary, secondary, accent = palettes.get(style, palettes["dark-terminal"])
    
    script = f'''"""Auto-generated Manim scene — {scene.get("visual_tool", "code-viz")}"""
from manim import *

BG = "{bg}"
PRIMARY = "{primary}"
SECONDARY = "{secondary}"
ACCENT = "{accent}"
MONO = "Menlo"

class RepoScene(Scene):
    def construct(self):
        self.camera.background_color = BG
        
        # Title reveal
        title = Text("{repo_analysis.get('repo_name', 'This Repo')}", 
                      font_size=48, color=PRIMARY, weight=BOLD, font=MONO)
        self.play(Write(title), run_time=1.5)
        self.wait(1.0)
        self.play(title.animate.scale(0.6).to_edge(UP), run_time=1.0)
        
        # Architecture reveal — animated boxes for key components
        components = {json.dumps(repo_analysis.get("key_files", [])[:5])}
        boxes = []
        for i, comp in enumerate(components):
            box = Rectangle(height=0.8, width=2.5, color=SECONDARY, fill_opacity=0.1)
            label = Text(comp[:20], font_size=16, color=PRIMARY, font=MONO)
            group = VGroup(box, label)
            group.move_to([-4 + (i % 3) * 4, 1.5 - (i // 3) * 1.5, 0])
            boxes.append(group)
            self.play(Create(box), Write(label), run_time=0.8)
            self.wait(0.2)
        
        self.wait(1.5)
        
        # Clean exit
        self.play(FadeOut(Group(*self.mobjects)), run_time=1.0)
'''
    
    script_path = output_dir / "manim_scene.py"
    script_path.write_text(script)
    return script_path

def render_scene(script_path: Path, output_dir: Path, quality: str = "ql") -> Path:
    """Render a Manim scene to MP4."""
    import subprocess
    cmd = ["manim", f"-{quality}", str(script_path), "RepoScene", "-o", str(output_dir / "scene")]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_dir / "scene.mp4"
```

**Step 4: Verify**

```bash
.venv/bin/python -m pytest tests/test_manim_render.py -q
# Manual smoke test:
.venv/bin/python -c "from repo_to_shorts.manim_render import generate_manim_script; print(generate_manim_script({}, {'repo_name':'test'}, Path('/tmp')).read_text())"
```

Expected: pass.

---

## Task 3: Pretext Typography Renderer

**Objective:** Generate kinetic typography title sequences and text-driven scenes using Pretext (DOM-free text layout engine).

**Files:**
- Create: `src/repo_to_shorts/pretext_render.py`
- Test: `tests/test_pretext_render.py` (or extend `test_manim_render.py`)

**Step 1: Write failing test**

Test that `generate_pretext_html()` produces valid HTML with:
- `<script>` tag loading Pretext
- Text content from narration
- Dark background styling
- Viewport dimensions for 9:16 vertical video

**Step 2: Implement**

```python
def generate_pretext_html(scene: dict, output_dir: Path) -> Path:
    """Generate a Pretext kinetic typography HTML page."""
    narration = scene.get("narration", "")
    style = scene.get("style", "dark-terminal")
    
    colors = {
        "dark-terminal": ("#0A0A0A", "#00F5FF"),
        "cinematic": ("#0D0D0D", "#FF4500"),
    }
    bg, fg = colors.get(style, ("#0A0A0A", "#FFFFFF"))
    
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body {{ margin:0; background:{bg}; overflow:hidden; width:1080px; height:1920px; }}
  #output {{ width:1080px; height:1920px; }}
</style></head><body>
<script type="module">
  import pretext from 'https://esm.sh/@chenglou/pretext';
  const p = pretext({{ fontSize: 72, color: '{fg}', fontWeight: 'bold' }});
  p.render("{narration}", document.getElementById('output'));
</script>
<div id="output"></div>
</body></html>"""
    
    html_path = output_dir / "pretext_scene.html"
    html_path.write_text(html)
    return html_path
```

Pitfall: Pretext needs a browser to render. For MVP, use a headless screenshot via `screencapture` or record via browser recording. For automated pipeline, capture via puppeteer or fallback to simpler text animation via Manim.

**Step 3: Verify**

Expected: HTML file renders correctly in browser. For pipeline, prefer Manim text animation as the reliable path; Pretext is the "creative spice" for title sequences only.

---

## Task 4: ASCII-Video Renderer

**Objective:** Generate stylized ASCII-art video segments for code-to-ASCII reveals.

**Files:**
- Create: `src/repo_to_shorts/ascii_render.py`

**Step 1: Implement ASCII scene generator**

Load the `ascii-video` skill for exact commands. For the pipeline:

```python
def generate_ascii_scene(text_content: str, output_dir: Path, duration: int = 10) -> Path:
    """Convert text/code snippet to ASCII art video segment."""
    # Write text to temp file
    text_path = output_dir / "scene_text.txt"
    text_path.write_text(text_content)
    
    # Use pyfiglet for title treatment, then ffmpeg for scrolling effect
    import subprocess
    # Generate ASCII art frame
    subprocess.run([
        "python3", "-c", f"""
import pyfiglet
art = pyfiglet.figlet_format(open('{text_path}').read()[:100], width=80)
open('{output_dir}/ascii_frame.txt', 'w').write(art)
"""
    ])
    
    # Convert to video with scrolling
    subprocess.run([
        "ffmpeg", "-f", "lavfi", 
        "-i", f"color=c=#0A0A0A:s=1080x1920:d={duration},drawtext=fontfile=/System/Library/Fonts/Menlo.ttc:textfile={output_dir}/ascii_frame.txt:fontcolor=#00F5FF:fontsize=24:x=(w-text_w)/2:y=h-mod(t*h/30,h):line_spacing=8",
        "-c:v", "libx264", "-preset", "fast",
        str(output_dir / "ascii_scene.mp4")
    ])
    
    return output_dir / "ascii_scene.mp4"
```

---

## Task 5: ffmpeg Compositor + TTS + Music

**Objective:** Stitch rendered scenes, add TTS narration, mix background music, burn captions.

**Files:**
- Create: `src/repo_to_shorts/compositor.py`
- Test: `tests/test_compositor.py`

**Step 1: Write failing test**

Test that `compose()` accepts a list of scene MP4 paths + narration texts + music path, and calls ffmpeg with correct concat/filter flags. Mock subprocess calls.

**Step 2: Implement compositor**

```python
def compose(scenes: list[dict], output_path: Path, music_path: Path = None) -> Path:
    """Compose scenes into final video with TTS narration, music, captions."""
    
    # 1. Generate TTS audio for each scene's narration
    for i, scene in enumerate(scenes):
        narration = scene.get("narration", "")
        if narration:
            tts_path = output_path.parent / f"narration_{i:02d}.aiff"
            subprocess.run(["say", "-o", str(tts_path), narration], check=True)
            # Convert to proper audio format
            wav_path = output_path.parent / f"narration_{i:02d}.wav"
            subprocess.run(["ffmpeg", "-i", str(tts_path), "-acodec", "pcm_s16le", 
                          str(wav_path)], check=True, capture_output=True)
            scene["audio_path"] = wav_path
    
    # 2. Build ffmpeg filter complex for scene stitching + audio mixing
    # ... (see full implementation in compositor.py)
    
    return output_path
```

**Step 3: Add background music support**

For MVP: download royalty-free track, loop/trim to match video duration.
Upgrade path: Suno AI generation via `songwriting-and-ai-music` skill.

```bash
# Download royalty-free ambient track (example)
curl -L "https://pixabay.com/music/..." -o runs/music/bg_track.mp3
```

**Step 4: Verify**

```bash
.venv/bin/python -m pytest tests/test_compositor.py -q
```

---

## Task 6: Hermes Agent Skill Wrapper

**Objective:** Wrap the entire pipeline as a Hermes Agent skill so the workflow is demonstrably "powered by Hermes Agent."

**Files:**
- Create: `src/repo_to_shorts/hermes_skill.py`
- Create: `skills/creative-short-generator/SKILL.md`

**Step 1: Write the Hermes skill manifest**

```markdown
---
name: creative-short-generator
description: "Generate a creative short video from any GitHub repo. Kimi 2.6 directs; Manim animates; Hermes orchestrates."
version: 1.0.0
---

# Creative Short Generator

Powered by Hermes Agent + Kimi 2.6.

## Usage

From Hermes CLI or chat:
  "Generate a creative short for https://github.com/user/repo"

The agent will:
1. Ingest the repo
2. Use Kimi 2.6 as creative director to design the short
3. Render scenes using Manim, Pretext, ASCII-video
4. Compose final video with narration + music
5. Deliver demo.mp4 + full artifact package
```

**Step 2: Implement skill entrypoint**

```python
def run_creative_pipeline(target: str, audience: str = "technical builders") -> dict:
    """Full creative pipeline, invoked by Hermes Agent skill."""
    # 1. Ingest (existing)
    analysis = ingest_target(target)
    
    # 2. Creative direction (new — Kimi 2.6)
    brief = direct(analysis)
    
    # 3. Render each scene with assigned tool
    scene_paths = []
    for scene in brief.scenes:
        tool = scene["visual_tool"]
        if tool == "manim":
            script = generate_manim_script(scene, analysis, out_dir)
            path = render_scene(script, out_dir)
        elif tool == "pretext":
            path = generate_pretext_html(scene, out_dir)
        elif tool == "ascii":
            path = generate_ascii_scene(scene.get("text", ""), out_dir)
        elif tool == "svg":
            path = render_architecture_svg(analysis, out_dir)
        scene_paths.append({"path": path, **scene})
    
    # 4. Compose
    final = compose(scene_paths, out_dir / "demo.mp4")
    
    # 5. Metadata
    write_metadata(out_dir, brief, final)
    
    return {"output": str(final), "brief": brief}
```

---

## Task 7: CLI Integration

**Objective:** Add `repo-shorts creative` subcommand that invokes the full creative pipeline.

**Files:**
- Modify: `src/repo_to_shorts/cli.py`

```python
@app.command()
def creative(
    target: str = typer.Argument(..., help="GitHub URL or local path"),
    audience: str = typer.Option("technical builders", help="Target audience"),
    out: str = typer.Option("runs", help="Output directory"),
    kimi_model: str = typer.Option("moonshotai/kimi-k2.6", help="Kimi model for creative direction"),
    render_mp4: bool = typer.Option(True, help="Generate final MP4"),
) -> None:
    """Generate a creative short video with Kimi 2.6 creative direction."""
    from .hermes_skill import run_creative_pipeline
    result = run_creative_pipeline(target, audience)
    print(f"✅ Creative short generated: {result['output']}")
```

---

## Task 8: Docs + Golden Run + Demo Recording

**Objective:** Update all docs, generate a fresh golden run with live Kimi, and produce the submission package.

**Files:**
- Modify: `README.md`, `AGENTS.md`, `docs/PRD.md`
- Generate: `runs/FINAL/demo.mp4`, `runs/FINAL/metadata.json`

**Acceptance Checklist:**
- [ ] `repo-shorts creative https://github.com/user/repo` produces demo.mp4
- [ ] metadata.json shows `kimi.mode: "live-api"`, `model: "moonshotai/kimi-k2.6"`
- [ ] Creative brief is included in metadata (proves Kimi directed)
- [ ] At least 3 different visual tools used across scenes
- [ ] TTS narration is synced with visuals
- [ ] Video is 9:16 vertical, 60s, with transitions
- [ ] All tests pass, ruff clean
- [ ] Submission copy (X post + Discord) ready for approval
- [ ] Demo recording shows: input URL → generation → output playing

---

## Execution Order

1. Task 1 (creative director) — unblocks everything
2. Task 2 (Manim renderer) — primary visual engine
3. Task 5 (compositor) — so we can test end-to-end early
4. Task 3 + 4 (Pretext + ASCII) — creative spice
5. Task 6 + 7 (Hermes skill + CLI) — agent integration
6. Task 8 (docs + golden run + demo)

Parallel where possible: Tasks 1+2 can start simultaneously. Task 3+4 after 2. Task 5 can start after 2 (test with placeholder scenes).

---

## Fallback Strategy

If Manim setup (MacTeX) blocks: fall back to enhanced Pillow + ffmpeg with better visual design (gradients, animations via ffmpeg drawtext/fade filters) + Pretext for typography. Not ideal, but ships.

If OpenRouter Kimi 2.6 unavailable: deterministic fallback creative brief (already implemented in `_deterministic_fallback()`). Less creative but functional.

---

## Estimated Time

| Task | Est. | Depends on |
|------|------|-----------|
| Creative director | 30 min | Nothing |
| Manim renderer | 45 min | Manim install |
| Pretext renderer | 20 min | Nothing |
| ASCII renderer | 15 min | Nothing |
| Compositor | 45 min | Manim, ffmpeg |
| Hermes skill | 20 min | All renderers |
| CLI integration | 10 min | Hermes skill |
| Docs + golden run + demo | 30 min | Everything |
| **Total** | **~3.5 hrs** | |

---

## Final-Mile Operating Plan

1. Generate golden run: `OPENROUTER_API_KEY="***" repo-shorts creative . --render-mp4`
2. Verify metadata.json shows `kimi.mode: "live-api"`
3. Screen-record the full flow: `repo-shorts creative <url>` → output playing
4. Post submission copy (draft, await maintainer approval)
5. Upload to hackathon submission platform
6. Post on X/Discord (maintainer approves first)
