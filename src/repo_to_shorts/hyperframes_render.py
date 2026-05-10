from __future__ import annotations

import html
import json
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from repo_to_shorts.render import RenderResult, VideoScene

if TYPE_CHECKING:
    from repo_to_shorts.pipeline import StoryPackage


def hyperframes_available() -> bool:
    return shutil.which("node") is not None and shutil.which("npx") is not None and shutil.which("ffmpeg") is not None


def ensure_hyperframes_runtime() -> None:
    if shutil.which("node") is None:
        raise RuntimeError("Node.js 22+ is required for HyperFrames rendering. Install Node and retry.")
    if shutil.which("npx") is None:
        raise RuntimeError("npx is required for HyperFrames rendering. Install npm/npx and retry.")
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required for HyperFrames rendering. Install ffmpeg and retry.")


def render_hyperframes_video(
    run_dir: Path,
    scenes: list[VideoScene],
    package: "StoryPackage",
    output_name: str = "demo.mp4",
) -> RenderResult:
    """Render a repo short with HyperFrames HTML + GSAP, producing demo.mp4."""
    ensure_hyperframes_runtime()
    project_dir = (run_dir / "hyperframes").resolve()
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "index.html").write_text(render_hyperframes_html(scenes, package), encoding="utf-8")
    (project_dir / "package.json").write_text(
        json.dumps(
            {
                "scripts": {
                    "lint": "hyperframes lint",
                    "render": "hyperframes render --quality standard --output ../demo.mp4",
                },
                "devDependencies": {"hyperframes": "latest"},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    _run_hyperframes(["npx", "--yes", "hyperframes", "lint", str(project_dir)], cwd=run_dir)
    output_path = (run_dir / output_name).resolve()
    _run_hyperframes(
        [
            "npx",
            "--yes",
            "hyperframes",
            "render",
            str(project_dir),
            "--quality",
            "standard",
            "--output",
            str(output_path),
        ],
        cwd=run_dir,
    )
    return RenderResult(output_path=output_path, mode="mp4", renderer="hyperframes", scene_count=len(scenes))


def render_hyperframes_html(scenes: list[VideoScene], package: "StoryPackage") -> str:
    duration = max(len(scenes) * 4, 4)
    scene_markup = []
    for index, scene in enumerate(scenes):
        start = index * 4
        title = html.escape(scene.title)
        body = html.escape(scene.body)
        footer = html.escape(scene.footer or "Repo-to-Shorts")
        accent = html.escape(scene.accent)
        scene_markup.append(
            f"""
      <section id="scene-{index + 1}" class="scene clip" data-start="{start}" data-duration="4" data-track-index="{index + 1}" style="--accent: {accent};">
        <div class="scene-content">
          <div class="eyebrow">{footer}</div>
          <h1>{title}</h1>
          <p>{body}</p>
          <div class="pulse-line"></div>
        </div>
      </section>"""
        )
    safe_hook = html.escape(package.hook)
    safe_cta = html.escape(package.cta)
    timeline_blocks = []
    for index in range(len(scenes)):
        selector = f"#scene-{index + 1}"
        start = index * 4
        timeline_blocks.append(
            f"""
      tl.set('{selector}', {{ autoAlpha: 1 }}, {start});
      tl.from('{selector} .eyebrow', {{ y: 34, autoAlpha: 0, duration: 0.45, ease: 'power3.out' }}, {start + 0.15});
      tl.from('{selector} h1', {{ y: 60, autoAlpha: 0, duration: 0.65, ease: 'power3.out' }}, {start + 0.35});
      tl.from('{selector} p', {{ y: 44, autoAlpha: 0, duration: 0.55, ease: 'power2.out' }}, {start + 0.75});
      tl.fromTo('{selector} .pulse-line', {{ scaleX: 0 }}, {{ scaleX: 1, duration: 2.4, ease: 'none' }}, {start + 1.0});
      tl.to('{selector}', {{ scale: 1.035, duration: 3.2, ease: 'none' }}, {start});
      tl.to('{selector}', {{ autoAlpha: 0, duration: 0.35, ease: 'power2.in' }}, {start + 3.62});
      tl.set('{selector}', {{ autoAlpha: 0 }}, {start + 4});"""
        )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: 1080px; height: 1920px; overflow: hidden; background: #020617; font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif; }}
      #root {{ position: relative; width: 1080px; height: 1920px; overflow: hidden; background: radial-gradient(circle at 50% 0%, rgba(34,211,238,.26), transparent 31%), linear-gradient(180deg, #111827 0%, #020617 70%); color: #f8fafc; }}
      .grain {{ position: absolute; inset: 0; z-index: 1; opacity: .16; background-image: repeating-linear-gradient(0deg, rgba(255,255,255,.06) 0 1px, transparent 1px 4px); mix-blend-mode: overlay; }}
      .chrome {{ position: absolute; inset: 58px; z-index: 2; border: 1px solid rgba(255,255,255,.13); border-radius: 46px; box-shadow: inset 0 0 80px rgba(34,211,238,.08), 0 40px 140px rgba(0,0,0,.45); }}
      .scene {{ position: absolute; inset: 0; z-index: 4; visibility: hidden; transform-origin: center; }}
      .scene-content {{ width: 100%; height: 100%; padding: 168px 92px 128px; display: flex; flex-direction: column; justify-content: center; gap: 34px; }}
      .scene-content::before {{ content: ''; position: absolute; inset: 180px 64px 290px; border-radius: 54px; border: 2px solid color-mix(in srgb, var(--accent), white 18%); background: linear-gradient(145deg, rgba(15,23,42,.88), rgba(2,6,23,.72)); box-shadow: 0 0 110px color-mix(in srgb, var(--accent), transparent 60%); z-index: -1; }}
      .eyebrow {{ width: max-content; max-width: 880px; padding: 14px 22px; border-radius: 999px; background: var(--accent); color: #020617; font-size: 25px; font-weight: 900; letter-spacing: .13em; text-transform: uppercase; }}
      h1 {{ font-size: 92px; line-height: .92; letter-spacing: -.07em; max-width: 850px; text-wrap: balance; }}
      p {{ color: #dbeafe; font-size: 43px; line-height: 1.22; max-width: 850px; }}
      .pulse-line {{ width: 100%; height: 12px; border-radius: 999px; transform-origin: left; background: linear-gradient(90deg, var(--accent), #22d3ee, #a78bfa); box-shadow: 0 0 34px var(--accent); }}
      .caption {{ position: absolute; left: 120px; right: 120px; bottom: 82px; z-index: 8; padding: 18px 24px; border-radius: 24px; background: rgba(0,0,0,.58); border: 1px solid rgba(255,255,255,.15); color: #e0f2fe; font-size: 24px; line-height: 1.18; font-weight: 720; }}
      .brand {{ position: absolute; top: 96px; left: 92px; right: 92px; z-index: 8; display: flex; justify-content: space-between; align-items: center; color: #67e8f9; font-size: 24px; font-weight: 850; letter-spacing: .14em; text-transform: uppercase; }}
      .ticker {{ color: #c4b5fd; font-size: 21px; letter-spacing: 0; text-transform: none; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{duration}" data-width="1080" data-height="1920">
      <div class="grain" data-layout-ignore></div>
      <div class="chrome" data-layout-ignore></div>
      <div class="brand"><span>Repo-to-Shorts</span><span class="ticker">HyperFrames render</span></div>
      {''.join(scene_markup)}
      <div id="caption" class="caption clip" data-start="0" data-duration="{duration}" data-track-index="99">{safe_hook} {safe_cta}</div>
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      gsap.set('.scene', {{ autoAlpha: 0 }});
      {''.join(timeline_blocks)}
      tl.from('#caption', {{ y: 30, autoAlpha: 0, duration: 0.55, ease: 'power2.out' }}, 0.6);
      tl.to('#caption', {{ opacity: 0.82, duration: {max(duration - 1, 1)}, ease: 'none' }}, 1.0);
      window.__timelines['main'] = tl;
    </script>
  </body>
</html>
"""


def _run_hyperframes(command: list[str], cwd: Path) -> None:
    try:
        subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        detail = stderr or stdout or f"exit code {exc.returncode}"
        raise RuntimeError(f"HyperFrames command failed: {' '.join(command)}\n{detail}") from exc
