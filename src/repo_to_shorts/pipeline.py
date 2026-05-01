from __future__ import annotations

import html
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from jinja2 import Template

from repo_to_shorts.ingest import RepoSnapshot, ingest_target
from repo_to_shorts.kimi import critique_story

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


def run_analysis(target: str, audience: str, out_dir: Path | str = Path("runs"), force: bool = False) -> Path:
    snapshot = ingest_target(target)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = Path(out_dir) / f"{timestamp}-{_slug(snapshot.name)}"
    if run_dir.exists() and not force:
        raise FileExistsError(f"Run directory already exists: {run_dir}. Use --force to overwrite.")
    run_dir.mkdir(parents=True, exist_ok=True)

    package = build_story(snapshot, audience)
    repo_brief = render_repo_brief(snapshot, audience, package)
    storyboard = render_storyboard(snapshot, audience, package)
    kimi = critique_story(snapshot, audience, storyboard)

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

    metadata = {
        "target": target,
        "source_type": snapshot.source_type,
        "repo_name": snapshot.name,
        "audience": audience,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "artifacts": list(ARTIFACTS),
        "kimi": {"mode": kimi.mode},
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
    return Template("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ name }} — Repo-to-Shorts Demo</title>
<style>
:root { color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif; }
body { margin: 0; background: radial-gradient(circle at top left, #312e81, #030712 45%); color: #f9fafb; }
.deck { width: min(1080px, 94vw); margin: 0 auto; padding: 48px 0; }
.hero { border: 1px solid #7c3aed; border-radius: 28px; padding: 42px; background: rgba(17,24,39,.82); box-shadow: 0 30px 90px rgba(0,0,0,.45); }
h1 { font-size: clamp(42px, 8vw, 88px); line-height: .9; margin: 0 0 18px; }
.kicker { color: #22d3ee; font-weight: 800; letter-spacing: .16em; text-transform: uppercase; }
.promise { font-size: 24px; color: #ddd6fe; max-width: 840px; }
.grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 20px; margin-top: 24px; }
.card { background: rgba(3,7,18,.74); border: 1px solid #374151; border-radius: 22px; padding: 24px; }
li { margin: 14px 0; font-size: 20px; }
.badge { display: inline-block; padding: 8px 12px; border-radius: 999px; background: #065f46; color: #bbf7d0; font-weight: 700; }
pre { white-space: pre-wrap; max-height: 260px; overflow: hidden; color: #c4b5fd; }
</style>
</head>
<body><main class="deck">
<section class="hero">
<div class="kicker">Hermes Creative Hackathon MVP</div>
<h1>{{ name }}<br>to short-video package</h1>
<p class="promise">{{ promise }}</p>
<span class="badge">Launch-ready artifacts generated deterministically</span>
</section>
<section class="grid">
<div class="card"><h2>Story beats</h2><ol>{{ beats|safe }}</ol></div>
<div class="card"><h2>Architecture</h2><p>Repo → Ingest → Story → Kimi critic → Artifacts → Demo HTML.</p><p>Audience: {{ audience }}</p></div>
<div class="card"><h2>Kimi critic/editor</h2><pre>{{ kimi }}</pre></div>
<div class="card"><h2>Recording flow</h2><p>Open this page, zoom to 125%, record the hero, story beats, Kimi pass, then artifact checklist.</p></div>
</section>
</main></body></html>
""", autoescape=True).render(name=snapshot.name, promise=package.promise, beats=beat_cards, audience=audience, kimi=kimi[:1200])


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


def _slug(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug[:60] or "repo"
