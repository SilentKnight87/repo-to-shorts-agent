from __future__ import annotations

import html
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from repo_to_shorts.hyperframes_render import ensure_hyperframes_runtime
from repo_to_shorts.render import RenderResult, VideoScene

if TYPE_CHECKING:
    from repo_to_shorts.pipeline import StoryPackage

HEYGEN_API_BASE = "https://api.heygen.com"


@dataclass(frozen=True)
class HeyGenConfig:
    api_key: str
    avatar_id: str
    voice_id: str
    width: int = 1080
    height: int = 1920
    poll_seconds: float = 5.0
    timeout_seconds: int = 900

    @classmethod
    def from_env(cls) -> "HeyGenConfig":
        api_key = os.getenv("HEYGEN_API_KEY", "").strip()
        avatar_id = os.getenv("HEYGEN_AVATAR_ID", "").strip()
        voice_id = os.getenv("HEYGEN_VOICE_ID", "").strip()
        missing = [
            name
            for name, value in (
                ("HEYGEN_API_KEY", api_key),
                ("HEYGEN_AVATAR_ID", avatar_id),
                ("HEYGEN_VOICE_ID", voice_id),
            )
            if not value
        ]
        if missing:
            raise RuntimeError("HeyGen rendering requires environment variables: " + ", ".join(missing))
        return cls(api_key=api_key, avatar_id=avatar_id, voice_id=voice_id)


def render_heygen_video(
    run_dir: Path,
    scenes: list[VideoScene],
    package: "StoryPackage",
    output_name: str = "demo.mp4",
) -> RenderResult:
    """Render a live HeyGen avatar video, downloading the completed MP4.

    This is intentionally isolated from the core artifact path because HeyGen is
    credentialed, asynchronous, and credit-consuming. If it fails, the pipeline
    records the failure without trashing the generated markdown/HTML package.
    """
    config = HeyGenConfig.from_env()
    heygen_dir = run_dir / "heygen"
    heygen_dir.mkdir(parents=True, exist_ok=True)
    payload = build_heygen_payload(scenes, package, config)
    (heygen_dir / "request.json").write_text(json.dumps(_redact_payload(payload), indent=2) + "\n", encoding="utf-8")

    video_id = _create_video(payload, config.api_key)
    (heygen_dir / "video_id.txt").write_text(video_id + "\n", encoding="utf-8")
    status = _wait_for_video(video_id, config)
    (heygen_dir / "status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")

    video_url = status.get("data", {}).get("video_url") or status.get("data", {}).get("video_url_caption")
    if not video_url:
        raise RuntimeError(f"HeyGen completed without a downloadable video URL for video_id={video_id}")

    output_path = (run_dir / output_name).resolve()
    _download(video_url, output_path)
    return RenderResult(output_path=output_path, mode="mp4", renderer="heygen", scene_count=len(scenes))


def render_heygen_preview_video(
    run_dir: Path,
    scenes: list[VideoScene],
    package: "StoryPackage",
    output_name: str = "heygen-preview.mp4",
) -> RenderResult:
    """Render a local HyperFrames preview of the HeyGen avatar treatment.

    This does not spend HeyGen credits. It shows the proposed composition: a
    presenter/avatar lane plus repo proof cards, then preserves the exact live
    HeyGen request shape in heygen-preview/request.example.json.
    """
    ensure_hyperframes_runtime()
    project_dir = (run_dir / "heygen-preview").resolve()
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "index.html").write_text(render_heygen_preview_html(scenes, package), encoding="utf-8")
    example_config = HeyGenConfig(api_key="REDACTED", avatar_id="YOUR_HEYGEN_AVATAR_ID", voice_id="YOUR_HEYGEN_VOICE_ID")
    (project_dir / "request.example.json").write_text(
        json.dumps(build_heygen_payload(scenes, package, example_config), indent=2) + "\n",
        encoding="utf-8",
    )
    output_path = (run_dir / output_name).resolve()
    _run(["npx", "--yes", "hyperframes", "lint", str(project_dir)], cwd=run_dir)
    _run(
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
    return RenderResult(output_path=output_path, mode="mp4", renderer="heygen-preview", scene_count=len(scenes))


def build_heygen_payload(scenes: list[VideoScene], package: "StoryPackage", config: HeyGenConfig) -> dict[str, Any]:
    script = build_heygen_script(scenes, package)
    return {
        "title": "Repo-to-Shorts avatar cut",
        "caption": True,
        "dimension": {"width": config.width, "height": config.height},
        "video_inputs": [
            {
                "character": {
                    "type": "avatar",
                    "avatar_id": config.avatar_id,
                    "avatar_style": "normal",
                    "scale": 1.0,
                    "offset": {"x": 0.22, "y": 0.0},
                    "matting": True,
                },
                "voice": {"type": "text", "voice_id": config.voice_id, "input_text": script, "speed": 1.05},
                "background": {"type": "color", "value": "#020617"},
            }
        ],
    }


def build_heygen_script(scenes: list[VideoScene], package: "StoryPackage", limit: int = 4800) -> str:
    lines = [package.hook, package.promise]
    lines.extend(f"{scene.title}. {scene.body}" for scene in scenes[:5])
    lines.append(package.cta)
    script = " ".join(_clean_text(line) for line in lines if line).strip()
    return script[:limit].rsplit(" ", 1)[0] if len(script) > limit else script


def render_heygen_preview_html(scenes: list[VideoScene], package: "StoryPackage") -> str:
    duration = max(len(scenes) * 4, 4)
    cards = []
    timeline = []
    for index, scene in enumerate(scenes):
        start = index * 4
        selector = f"#proof-{index + 1}"
        accent = html.escape(scene.accent)
        cards.append(
            f"""
      <section id="proof-{index + 1}" class="proof-card clip" data-start="{start}" data-duration="4" data-track-index="{index + 1}" style="--accent: {accent};">
        <div class="label">{html.escape(scene.footer or 'Repo proof')}</div>
        <h1>{html.escape(scene.title)}</h1>
        <p>{html.escape(scene.body)}</p>
      </section>"""
        )
        timeline.append(
            f"""
      tl.fromTo('{selector}', {{ x: -80, y: 30, autoAlpha: 0 }}, {{ x: 0, y: 0, autoAlpha: 1, duration: 0.55, ease: 'power3.out' }}, {start + 0.15});
      tl.fromTo('{selector} h1', {{ y: 46, autoAlpha: 0 }}, {{ y: 0, autoAlpha: 1, duration: 0.55, ease: 'power2.out' }}, {start + 0.35});
      tl.fromTo('{selector} p', {{ y: 34, autoAlpha: 0 }}, {{ y: 0, autoAlpha: 1, duration: 0.45, ease: 'power2.out' }}, {start + 0.7});
      tl.to('{selector}', {{ autoAlpha: 0, x: -28, duration: 0.35, ease: 'power2.in' }}, {start + 3.6});
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
      #root {{ position: relative; width: 1080px; height: 1920px; overflow: hidden; color: #f8fafc; background: radial-gradient(circle at 78% 22%, rgba(34,211,238,.38), transparent 26%), radial-gradient(circle at 18% 82%, rgba(168,85,247,.28), transparent 34%), linear-gradient(180deg, #0f172a 0%, #020617 74%); }}
      .grid {{ position: absolute; inset: 0; opacity: .13; background-image: linear-gradient(rgba(255,255,255,.18) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.18) 1px, transparent 1px); background-size: 72px 72px; }}
      .brand {{ position: absolute; top: 76px; left: 76px; right: 76px; z-index: 8; display: flex; justify-content: space-between; color: #67e8f9; font-size: 24px; font-weight: 900; letter-spacing: .12em; text-transform: uppercase; }}
      .avatar-stage {{ position: absolute; right: 54px; top: 240px; width: 420px; height: 640px; z-index: 5; border-radius: 46px; background: linear-gradient(180deg, rgba(15,23,42,.92), rgba(2,6,23,.72)); border: 1px solid rgba(255,255,255,.14); box-shadow: 0 40px 140px rgba(0,0,0,.42), 0 0 90px rgba(34,211,238,.18); overflow: hidden; }}
      .avatar-head {{ position: absolute; left: 86px; top: 78px; width: 248px; height: 248px; border-radius: 50%; background: radial-gradient(circle at 48% 36%, #fde68a, #f59e0b 52%, #7c2d12); box-shadow: 0 0 52px rgba(251,191,36,.34); }}
      .avatar-body {{ position: absolute; left: 58px; bottom: -96px; width: 304px; height: 360px; border-radius: 58px 58px 0 0; background: linear-gradient(135deg, #22d3ee, #8b5cf6); }}
      .mouth {{ position: absolute; left: 172px; top: 238px; width: 76px; height: 20px; border-radius: 999px; background: #431407; transform-origin: center; }}
      .sound {{ position: absolute; left: 48px; right: 48px; bottom: 44px; height: 84px; display: flex; align-items: end; justify-content: center; gap: 8px; }}
      .sound span {{ display: block; width: 12px; height: 24px; border-radius: 999px; background: #67e8f9; opacity: .8; }}
      .proof-card {{ position: absolute; left: 62px; top: 296px; width: 590px; min-height: 740px; z-index: 6; visibility: hidden; padding: 54px; border-radius: 42px; background: linear-gradient(145deg, rgba(15,23,42,.96), rgba(2,6,23,.88)); border: 3px solid color-mix(in srgb, var(--accent), white 26%); box-shadow: 0 0 110px color-mix(in srgb, var(--accent), transparent 56%), 0 34px 110px rgba(0,0,0,.52); }}
      .label {{ display: inline-flex; margin-bottom: 34px; padding: 12px 18px; border-radius: 999px; background: var(--accent); color: #020617; font-size: 22px; font-weight: 950; text-transform: uppercase; letter-spacing: .1em; }}
      h1 {{ font-size: 72px; line-height: .93; letter-spacing: -.06em; margin-bottom: 30px; }}
      p {{ color: #dbeafe; font-size: 34px; line-height: 1.22; }}
      .caption {{ position: absolute; left: 72px; right: 72px; bottom: 82px; z-index: 9; padding: 26px 30px; border-radius: 30px; background: rgba(0,0,0,.64); border: 1px solid rgba(255,255,255,.16); color: #e0f2fe; font-size: 28px; line-height: 1.16; font-weight: 800; }}
      .badge {{ position: absolute; right: 72px; bottom: 226px; z-index: 10; padding: 16px 22px; border-radius: 999px; background: rgba(8,47,73,.94); border: 2px solid rgba(103,232,249,.68); color: #ecfeff; font-size: 24px; font-weight: 950; box-shadow: 0 16px 50px rgba(0,0,0,.42); }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{duration}" data-width="1080" data-height="1920">
      <div class="grid" data-layout-ignore></div>
      <div class="brand"><span>Repo-to-Shorts</span><span>HeyGen avatar cut</span></div>
      <div class="avatar-stage clip" data-start="0" data-duration="{duration}" data-track-index="80">
        <div class="avatar-head"></div><div class="mouth"></div><div class="avatar-body"></div>
        <div class="sound"><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div>
      </div>
      {''.join(cards)}
      <div class="badge clip" data-start="0" data-duration="{duration}" data-track-index="81">Live mode swaps this mock for a real HeyGen avatar</div>
      <div id="caption" class="caption clip" data-start="0" data-duration="{duration}" data-track-index="99">{html.escape(package.hook)} {html.escape(package.cta)}</div>
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      gsap.set('.proof-card', {{ autoAlpha: 0 }});
      tl.from('.avatar-stage', {{ x: 80, autoAlpha: 0, duration: 0.7, ease: 'power3.out' }}, 0.1);
      tl.to('.mouth', {{ scaleY: 2.2, duration: .16, repeat: {max(duration * 4, 4)}, yoyo: true, ease: 'sine.inOut' }}, 0.3);
      tl.to('.sound span', {{ height: 72, duration: .32, stagger: .04, repeat: {max(duration * 2, 2)}, yoyo: true, ease: 'sine.inOut' }}, 0.3);
      {''.join(timeline)}
      tl.from('#caption', {{ y: 30, autoAlpha: 0, duration: 0.55, ease: 'power2.out' }}, 0.6);
      window.__timelines['main'] = tl;
    </script>
  </body>
</html>
"""


def _create_video(payload: dict[str, Any], api_key: str) -> str:
    response = _json_request("POST", "/v2/video/generate", api_key, payload)
    error = response.get("error")
    if error:
        raise RuntimeError(f"HeyGen create failed: {error}")
    video_id = response.get("data", {}).get("video_id") or response.get("video_id")
    if not video_id:
        raise RuntimeError(f"HeyGen create response did not include video_id: {response}")
    return str(video_id)


def _wait_for_video(video_id: str, config: HeyGenConfig) -> dict[str, Any]:
    deadline = time.monotonic() + config.timeout_seconds
    while True:
        query = urllib.parse.urlencode({"video_id": video_id})
        status = _json_request("GET", f"/v1/video_status.get?{query}", config.api_key)
        data = status.get("data", {})
        state = data.get("status") or status.get("status")
        if state == "completed":
            return status
        if state == "failed":
            raise RuntimeError(f"HeyGen render failed for video_id={video_id}: {data.get('error') or status}")
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Timed out waiting for HeyGen video_id={video_id}; last status={state!r}")
        time.sleep(config.poll_seconds)


def _json_request(method: str, path: str, api_key: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        HEYGEN_API_BASE + path,
        data=body,
        method=method,
        headers={"x-api-key": api_key, "content-type": "application/json", "accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HeyGen HTTP {exc.code}: {detail}") from exc


def _download(url: str, output_path: Path) -> None:
    with urllib.request.urlopen(url, timeout=120) as response, output_path.open("wb") as handle:
        handle.write(response.read())


def _run(command: list[str], cwd: Path) -> None:
    try:
        subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or f"exit code {exc.returncode}").strip()
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{detail}") from exc


def _clean_text(value: str) -> str:
    return " ".join(value.replace("`", "").split())


def _redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(payload).replace(os.getenv("HEYGEN_VOICE_ID", "<never>"), "REDACTED_VOICE_ID"))
