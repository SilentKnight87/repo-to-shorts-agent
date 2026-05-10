from __future__ import annotations

import html
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from jinja2 import Template

from repo_to_shorts.heygen_render import render_heygen_preview_video, render_heygen_video
from repo_to_shorts.hyperframes_render import render_hyperframes_video
from repo_to_shorts.ingest import RepoSnapshot, ingest_target
from repo_to_shorts.kimi import critique_story
from repo_to_shorts.render import build_video_scenes

ARTIFACTS = (
    "metadata.json",
    "repo_brief.md",
    "storyboard.md",
    "architecture.svg",
    "narration.md",
    "captions.srt",
    "x_post.md",
    "submission.md",
    "kimi_critique.md",
    "demo.html",
    "recording_instructions.md",
)


@dataclass(frozen=True)
class StoryPackage:
    hook: str
    promise: str
    beats: list[str]
    cta: str


def run_analysis(
    target: str,
    audience: str,
    out_dir: Path | str = Path("runs"),
    force: bool = False,
    kimi_model: str | None = None,
    render: str = "none",
) -> Path:
    if render not in {"none", "mp4", "hyperframes", "heygen-preview", "heygen"}:
        raise ValueError("render must be one of: none, mp4, hyperframes, heygen-preview, heygen")
    snapshot = ingest_target(target)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = Path(out_dir) / f"{timestamp}-{_slug(snapshot.name)}"
    if run_dir.exists() and not force:
        raise FileExistsError(f"Run directory already exists: {run_dir}. Use --force to overwrite.")
    run_dir.mkdir(parents=True, exist_ok=True)

    package = build_story(snapshot, audience)
    repo_brief = render_repo_brief(snapshot, audience, package)
    storyboard = render_storyboard(snapshot, audience, package)
    kimi = critique_story(snapshot, audience, storyboard, model=kimi_model)

    files = {
        "repo_brief.md": repo_brief,
        "storyboard.md": storyboard,
        "architecture.svg": render_architecture_svg(snapshot),
        "narration.md": render_narration(snapshot, package),
        "captions.srt": render_captions(package),
        "x_post.md": render_x_post(snapshot, package),
        "submission.md": render_submission(snapshot, package),
        "kimi_critique.md": kimi.text,
        "demo.html": render_demo_html(snapshot, audience, package, repo_brief, storyboard, kimi.text),
        "recording_instructions.md": render_recording_instructions(run_dir),
    }
    for name, content in files.items():
        (run_dir / name).write_text(content, encoding="utf-8")

    artifacts = list(ARTIFACTS)
    render_metadata = {"mode": "none", "status": "skipped", "renderer": None, "output": None, "scene_count": 0, "error": None}
    if render in {"mp4", "hyperframes", "heygen-preview", "heygen"}:
        scenes = build_video_scenes(snapshot, audience, package, kimi.text)
        renderer_name = "hyperframes"
        artifact_prefix = "hyperframes"
        renderer = render_hyperframes_video
        if render == "heygen-preview":
            renderer_name = "heygen-preview"
            artifact_prefix = "heygen-preview"
            renderer = render_heygen_preview_video
        elif render == "heygen":
            renderer_name = "heygen"
            artifact_prefix = "heygen"
            renderer = render_heygen_video
        try:
            result = renderer(run_dir, scenes, package)
        except Exception as exc:  # noqa: BLE001 - optional renderer should not break core artifacts.
            render_metadata = {
                "mode": "mp4",
                "status": "failed",
                "renderer": renderer_name,
                "output": None,
                "scene_count": len(scenes),
                "error": str(exc),
            }
        else:
            artifacts.append(result.output_path.name)
            artifacts.append(f"{artifact_prefix}/index.html" if render != "heygen" else "heygen/request.json")
            render_metadata = {
                "mode": result.mode,
                "status": "success" if result.error is None else "failed",
                "renderer": result.renderer,
                "output": result.output_path.name,
                "scene_count": result.scene_count,
                "error": result.error,
            }

    metadata = {
        "target": target,
        "source_type": snapshot.source_type,
        "repo_name": snapshot.name,
        "audience": audience,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "artifacts": artifacts,
        "kimi": {
            "mode": kimi.mode,
            "model": kimi.model,
            "provider": kimi.provider,
            "fallback_reason": kimi.fallback_reason,
        },
        "render": render_metadata,
    }
    (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return run_dir


def build_story(snapshot: RepoSnapshot, audience: str) -> StoryPackage:
    description = snapshot.package_metadata.get("description") or _first_readme_sentence(snapshot.readme)
    return StoryPackage(
        hook=f"A repo lands on your desk. In under a minute, {snapshot.name} becomes a launch-ready short.",
        promise=f"For {audience}, this turns source code context into a crisp story, visual plan, captions, and submission copy.",
        beats=[
            f"Ingest `{snapshot.name}`: README, file tree, package metadata, git log, and diff signals.",
            f"Extract the why: {description}",
            "Shape a three-act technical short: problem, proof, launch.",
            "Render deterministic assets so the golden path works without model credentials.",
            "Run a Kimi critic/script-editor pass, with fallback when no API key is present.",
        ],
        cta="Open demo.html, screen-record the package, and ship the hackathon submission.",
    )


def render_repo_brief(snapshot: RepoSnapshot, audience: str, package: StoryPackage) -> str:
    metadata = "\n".join(f"- **{k}**: {v}" for k, v in snapshot.package_metadata.items()) or "- No package metadata found."
    tree = "\n".join(f"- `{entry}`" for entry in snapshot.file_tree[:40])
    return f"""# {snapshot.name} repo brief

## Audience
{audience}

## One-line promise
{package.promise}

## README signal
{snapshot.readme[:1600]}

## Package metadata
{metadata}

## File tree summary
{tree}

## Recent git log
```text
{snapshot.git_log}
```

## Current git diff/stat
```text
{snapshot.git_diff}
```
"""


def render_storyboard(snapshot: RepoSnapshot, audience: str, package: StoryPackage) -> str:
    rows = [
        ("0-5s", "Hook", package.hook, "Repo card appears; source files fan into a vertical frame."),
        ("5-15s", "Problem", f"{audience} need a story, not another wall of code.", "README and tree highlights pulse."),
        ("15-35s", "Proof", package.beats[0] + " " + package.beats[3], "Pipeline boxes animate left to right."),
        ("35-50s", "Editor", package.beats[4], "Kimi critic card marks sharper hook and CTA."),
        ("50-60s", "Launch", package.cta, "Artifact checklist fills green."),
    ]
    table = "\n".join(f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows)
    return f"""# Storyboard for {snapshot.name}

| Time | Beat | Narration | Visual |
| --- | --- | --- | --- |
{table}
"""


def render_architecture_svg(snapshot: RepoSnapshot) -> str:
    labels = ["Repo", "Ingest", "Story", "Kimi critic", "Artifacts", "Demo HTML"]
    boxes = []
    arrows = []
    for i, label in enumerate(labels):
        x = 30 + i * 150
        boxes.append(f'<rect x="{x}" y="70" width="120" height="64" rx="14" fill="#111827" stroke="#8b5cf6" stroke-width="3"/>')
        boxes.append(f'<text x="{x + 60}" y="108" text-anchor="middle" fill="#f9fafb" font-size="15" font-family="Inter, Arial">{html.escape(label)}</text>')
        if i < len(labels) - 1:
            arrows.append(f'<path d="M{x + 120} 102 L{x + 146} 102" stroke="#22d3ee" stroke-width="4" marker-end="url(#arrow)"/>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="940" height="220" viewBox="0 0 940 220" role="img" aria-label="Repo-to-shorts architecture for {html.escape(snapshot.name)}">
<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#22d3ee"/></marker></defs>
<rect width="940" height="220" fill="#030712"/>
<text x="470" y="38" text-anchor="middle" fill="#f9fafb" font-size="24" font-family="Inter, Arial">Repo-to-Shorts Agent MVP</text>
{''.join(boxes)}
{''.join(arrows)}
</svg>
'''


def render_narration(snapshot: RepoSnapshot, package: StoryPackage) -> str:
    lines = ["# Narration script", "", package.hook, package.promise, *package.beats, package.cta]
    return "\n\n".join(lines) + "\n"


def render_captions(package: StoryPackage) -> str:
    captions = [package.hook, package.promise, package.beats[0], package.beats[4], package.cta]
    blocks = []
    start = 0
    for idx, caption in enumerate(captions, start=1):
        end = start + 10
        blocks.append(f"{idx}\n00:00:{start:02d},000 --> 00:00:{end:02d},000\n{caption}\n")
        start = end
    return "\n".join(blocks)


def render_x_post(snapshot: RepoSnapshot, package: StoryPackage) -> str:
    return f"""Built a Repo-to-Shorts Agent for the Hermes Creative Hackathon.

Paste `{snapshot.name}` → get repo brief, story arc, storyboard, SVG architecture, narration, captions, X/Discord copy, Kimi critic pass, and a browser demo artifact.

{package.cta}
"""


def render_submission(snapshot: RepoSnapshot, package: StoryPackage) -> str:
    return f"""# Discord submission copy

Project: Repo-to-Shorts Agent

What it does: {package.promise}

Why it matters: it closes the gap between working code and a clear launch narrative.

Demo path: run `repo-shorts analyze <repo>`, open `demo.html`, and screen-record the generated short-video package.

Kimi role: critic/script-editor stage with deterministic fallback when credentials are absent.
"""


def render_demo_html(snapshot: RepoSnapshot, audience: str, package: StoryPackage, brief: str, storyboard: str, kimi: str) -> str:
    beat_cards = "".join(f"<li>{html.escape(beat)}</li>" for beat in package.beats)
    scene_rows = [
        ("00", "Hook", package.hook),
        ("05", "Audience pain", f"{audience} need a story, not another wall of code."),
        ("15", "Repo proof", package.beats[0]),
        ("35", "Kimi edit", package.beats[4]),
        ("50", "Launch package", package.cta),
    ]
    scenes = "".join(
        f'<article class="scene"><span>{html.escape(time)}s</span><strong>{html.escape(title)}</strong><p>{html.escape(copy)}</p></article>'
        for time, title, copy in scene_rows
    )
    proof_line = _trim(_first_non_heading_line(brief), 180)
    storyboard_line = _trim(_first_non_heading_line(storyboard), 180)
    return Template("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ name }} — Repo-to-Shorts Demo</title>
<style>
:root { color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif; --bg:#030712; --panel:rgba(17,24,39,.82); --line:rgba(255,255,255,.12); --cyan:#22d3ee; --violet:#8b5cf6; --green:#34d399; }
* { box-sizing: border-box; }
body { margin: 0; background: radial-gradient(circle at top left, #312e81, var(--bg) 45%); color: #f9fafb; }
.deck { width: min(1180px, 94vw); margin: 0 auto; padding: 36px 0 52px; }
.hero { display: grid; grid-template-columns: minmax(0, 1fr) minmax(320px, 390px); gap: 24px; align-items: stretch; border: 1px solid #7c3aed; border-radius: 28px; padding: 28px; background: var(--panel); box-shadow: 0 30px 90px rgba(0,0,0,.45); }
h1 { font-size: clamp(42px, 7vw, 82px); line-height: .9; letter-spacing: -.06em; margin: 0 0 18px; }
h2 { margin: 0 0 14px; }
.kicker { color: var(--cyan); font-weight: 800; letter-spacing: .16em; text-transform: uppercase; font-size: 12px; }
.promise { font-size: clamp(19px, 2.4vw, 25px); color: #ddd6fe; max-width: 760px; line-height: 1.35; }
.badges { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 22px; }
.badge { display: inline-block; padding: 8px 12px; border-radius: 999px; background: #065f46; color: #bbf7d0; font-weight: 700; }
.phone { width: min(100%, 360px); aspect-ratio: 9 / 16; justify-self: center; border-radius: 42px; padding: 12px; background: linear-gradient(145deg, rgba(255,255,255,.20), rgba(255,255,255,.04)); border: 1px solid rgba(255,255,255,.20); box-shadow: 0 24px 80px rgba(0,0,0,.50); }
.screen { height: 100%; overflow: hidden; border-radius: 32px; padding: 18px; display: flex; flex-direction: column; justify-content: space-between; background: radial-gradient(circle at 50% 0%, rgba(34,211,238,.28), transparent 34%), linear-gradient(180deg, #111827, #020617 74%); border: 1px solid rgba(255,255,255,.10); position: relative; }
.screen::after { content:""; position:absolute; inset:0; background:linear-gradient(120deg, transparent, rgba(255,255,255,.08), transparent); transform:translateX(-65%); animation:sheen 5.5s ease-in-out infinite; pointer-events:none; }
.notch { width: 88px; height: 18px; border-radius: 99px; background: #020617; margin: 0 auto; border: 1px solid rgba(255,255,255,.08); }
.reel-title { position:relative; z-index:1; font-size: 34px; line-height: .95; letter-spacing: -.06em; font-weight: 760; }
.reel-sub { position:relative; z-index:1; color:#c4b5fd; line-height:1.45; font-size:14px; }
.progress { position:relative; z-index:1; height:6px; border-radius:999px; background:rgba(255,255,255,.14); overflow:hidden; }
.progress span { display:block; height:100%; width:78%; border-radius:inherit; background:linear-gradient(90deg, var(--violet), var(--cyan)); animation:load 8s ease-in-out infinite; }
.caption { position:relative; z-index:1; padding: 12px; border-radius: 18px; background: rgba(0,0,0,.48); border: 1px solid rgba(255,255,255,.10); font-weight: 700; line-height: 1.25; }
.grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 20px; margin-top: 24px; }
.card { background: rgba(3,7,18,.74); border: 1px solid #374151; border-radius: 22px; padding: 24px; }
.wide { grid-column: 1 / -1; }
li { margin: 14px 0; font-size: 19px; line-height: 1.35; }
.scene-strip { display: grid; grid-template-columns: repeat(5, minmax(0,1fr)); gap: 12px; }
.scene { min-height: 170px; display: flex; flex-direction: column; justify-content: space-between; padding: 16px; border-radius: 20px; background: linear-gradient(180deg, rgba(124,58,237,.22), rgba(15,23,42,.78)); border: 1px solid rgba(255,255,255,.12); }
.scene span { color: var(--cyan); font-weight: 900; letter-spacing: .12em; font-size: 12px; }
.scene strong { font-size: 18px; }
.scene p { color: #cbd5e1; margin: 8px 0 0; font-size: 13px; line-height: 1.35; }
pre { white-space: pre-wrap; max-height: 340px; overflow: hidden; color: #c4b5fd; font-size: 15px; line-height: 1.45; }
.proof { color: #bfdbfe; border-left: 3px solid var(--cyan); padding-left: 12px; }
.artifacts { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 12px; }
.artifacts span { border: 1px solid #475569; border-radius: 999px; padding: 8px 11px; color: #bfdbfe; background: rgba(30,41,59,.75); font-weight: 700; }
@keyframes sheen { 0%,55% { transform:translateX(-65%); } 100% { transform:translateX(65%); } }
@keyframes load { 0% { width: 8%; } 55%,100% { width: 94%; } }
@media (max-width: 900px) { .hero, .grid { grid-template-columns: 1fr; } .scene-strip { grid-template-columns: 1fr; } .deck { padding-top: 18px; } }
</style>
</head>
<body><main class="deck">
<section class="hero">
<div>
<div class="kicker">Hermes Creative Hackathon MVP</div>
<h1>{{ name }}<br>to short-video package</h1>
<p class="promise">{{ promise }}</p>
<div class="badges"><span class="badge">9:16 recordable demo page</span><span class="badge">Deterministic artifacts</span><span class="badge">Kimi proof in metadata</span></div>
</div>
<aside class="phone" aria-label="Vertical short preview"><div class="screen"><div class="notch"></div><div class="reel-title">{{ name }} → launch reel</div><p class="reel-sub">Repo context becomes a hook, proof beats, critic pass, captions, and publish copy.</p><div class="progress"><span></span></div><div class="caption">{{ hook }}</div></div></aside>
</section>
<section class="grid">
<div class="card"><h2>Story beats</h2><ol>{{ beats|safe }}</ol></div>
<div class="card"><h2>Architecture</h2><p>Repo → Ingest → Story → Kimi critic → Artifacts → Demo HTML.</p><p>Audience: {{ audience }}</p><p class="proof">{{ proof_line }}</p></div>
<div class="card wide"><h2>60-second recording timeline</h2><div class="scene-strip">{{ scenes|safe }}</div></div>
<div class="card"><h2>Kimi critic/editor</h2><pre>{{ kimi }}</pre></div>
<div class="card"><h2>Recording flow</h2><p>Record the phone preview first, then pan to the timeline and Kimi proof. Use the generated narration and captions for the final cut.</p><p class="proof">{{ storyboard_line }}</p></div>
<div class="card wide"><h2>Artifact checklist</h2><p>Everything below is generated into the run folder for the final submission package.</p><div class="artifacts"><span>repo_brief.md</span><span>storyboard.md</span><span>architecture.svg</span><span>narration.md</span><span>captions.srt</span><span>x_post.md</span><span>submission.md</span><span>kimi_critique.md</span><span>demo.html</span></div></div>
</section>
</main></body></html>
""", autoescape=True).render(
        name=snapshot.name,
        promise=package.promise,
        beats=beat_cards,
        audience=audience,
        kimi=kimi[:1200],
        hook=package.hook,
        scenes=scenes,
        proof_line=proof_line,
        storyboard_line=storyboard_line,
    )


def render_recording_instructions(run_dir: Path) -> str:
    return f"""# Recording instructions

1. Open `{run_dir / 'demo.html'}` in a browser.
2. Use a 9:16 or square crop and zoom until the hero fills the frame.
3. Record four moments: hook, story beats, Kimi critic card, artifact checklist.
4. Use `narration.md` for voiceover and `captions.srt` for subtitles.
5. Post with `x_post.md` and submit with `submission.md`.
"""


def _first_readme_sentence(readme: str) -> str:
    text = " ".join(line.strip("# ") for line in readme.splitlines() if line.strip())
    return text.split(". ")[0][:220] or "A technical project ready for a clearer launch story."


def _first_non_heading_line(markdown: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith(("#", "|", "```")):
            return stripped.lstrip("- ")
    return "Generated repo context, story arc, and launch artifacts are ready to record."


def _trim(value: str, limit: int) -> str:
    clean = " ".join(value.split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


def _slug(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug[:60] or "repo"
