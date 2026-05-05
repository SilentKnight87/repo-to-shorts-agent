from __future__ import annotations

import html
import json
import mimetypes
import socket
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from repo_to_shorts.pipeline import run_analysis
from repo_to_shorts.progress import ProgressTracker

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_RUNS_DIR = Path("runs")
DEFAULT_AUDIENCE = "Nous Research Hermes Agent Creative Hackathon judges"
DEFAULT_KIMI_MODEL = "moonshotai/kimi-k2.6"


class RepoShortsHTTPServer(HTTPServer):
    allow_reuse_address = True

    def server_bind(self) -> None:
        """Bind without reverse DNS lookups, which can hang on macOS/LAN hosts."""
        if self.allow_reuse_address:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)
        self.server_address = self.socket.getsockname()
        host, port = self.server_address[:2]
        self.server_name = str(host)
        self.server_port = int(port)


def list_runs(runs_dir: Path, limit: int = 10) -> list[Path]:
    if not runs_dir.exists():
        return []
    runs = [p for p in runs_dir.iterdir() if p.is_dir()]
    runs.sort(key=lambda p: p.name, reverse=True)
    return runs[:limit]


def _page_shell(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="preload" as="font" type="font/woff2" href="/static/fonts/Anton-Regular.woff2" crossorigin>
<link rel="preload" as="font" type="font/woff2" href="/static/fonts/JetBrainsMono-Variable.woff2" crossorigin>
<link rel="stylesheet" href="/static/style.css">
</head>
<body><main class="shell">{body}</main>
<script src="/static/app.js" defer></script>
</body>
</html>"""


def render_home_page(runs: list[Path], message: str | None = None) -> str:
    archive_rows = []
    for idx, run in enumerate(runs, start=1):
        reel_no = f"{idx:03d}"
        date_part = run.name.split("-")[0] if "-" in run.name else run.name
        if len(date_part) == 8 and date_part.isdigit():
            display_date = f"{date_part[0:4]}-{date_part[4:6]}-{date_part[6:8]}"
        else:
            display_date = html.escape(date_part)
        primary_target = None
        for candidate in ("demo.mp4", "demo.html", "metadata.json"):
            if (run / candidate).exists():
                primary_target = candidate
                break
        if primary_target:
            href = f"/runs/{html.escape(run.name)}/{html.escape(primary_target)}"
            link_html = f'<a class="btn-tape btn-tape--ghost" href="{href}">⏬ MASTER</a>'
        else:
            link_html = '<span class="btn-tape btn-tape--ghost is-idle">NO MASTER</span>'
        archive_rows.append(
            '<div class="tape-label">'
            f'<span class="tape-label__reel">REEL · {reel_no}</span>'
            f'<span class="tape-label__date">{display_date}</span>'
            '<span class="tape-label__runtime">60s</span>'
            f'<span class="tape-label__name">{html.escape(run.name)}</span>'
            f'{link_html}'
            "</div>"
        )
    if archive_rows:
        archive_html = "\n".join(archive_rows)
    else:
        archive_html = (
            '<div class="tape-label tape-label--empty">'
            '<span class="tape-label__reel">NO TAPES IN ARCHIVE — ROLL ONE TO START.</span>'
            "</div>"
        )

    message_html = (
        f'<div class="status-pill is-live">{html.escape(message)}</div>' if message else ""
    )

    colorbars = (
        '<div class="colorbars colorbars--banner" aria-hidden="true">'
        '<div class="colorbars__bar colorbars__bar--silver"></div>'
        '<div class="colorbars__bar colorbars__bar--yellow"></div>'
        '<div class="colorbars__bar colorbars__bar--cyan"></div>'
        '<div class="colorbars__bar colorbars__bar--green"></div>'
        '<div class="colorbars__bar colorbars__bar--magenta"></div>'
        '<div class="colorbars__bar colorbars__bar--red"></div>'
        '<div class="colorbars__bar colorbars__bar--blue"></div>'
        "</div>"
    )

    vu_segments = "".join("<span></span>" for _ in range(20))

    body = f"""
<div class="tape-edge tape-edge--top" aria-hidden="true"></div>
<header class="slate">
  <span class="slate-state is-rec">● REC</span>
  <span class="slate-title">CH 02 — HERMES STUDIO</span>
  <span class="slate-tc" data-timecode>00:00:00:00</span>
</header>
{colorbars}
<section class="hero">
  <div class="kicker">// SIGNAL IN. STORY OUT.</div>
  <h1 class="glitch-headline" data-glitch>REPO &rarr; REEL.</h1>
  <p class="lede">Paste a repo. Kimi writes the brief. Hermes cuts the reel.</p>
  <p class="skill-badge"><span class="skill-badge__chip">SKILL</span> Same workflow as <code>hermes</code> &rarr; <code>/repo-shorts-creative &lt;target&gt;</code></p>
  {message_html}
</section>
<form id="generate-form" class="deck deck-control" method="POST" action="/generate">
  <div class="tape-input">
    <label class="tape-input__label" for="field-target">CH · INPUT</label>
    <input class="tape-input__field" type="text" id="field-target" name="target" placeholder="https://github.com/owner/repo" required>
  </div>
  <div class="tape-input">
    <label class="tape-input__label" for="field-audience">AUDIENCE TARGET</label>
    <input class="tape-input__field" type="text" id="field-audience" name="audience" value="{html.escape(DEFAULT_AUDIENCE)}">
  </div>
  <div class="tape-input">
    <label class="tape-input__label" for="field-kimi">MODEL FEED</label>
    <input class="tape-input__field" type="text" id="field-kimi" name="kimi_model" value="{html.escape(DEFAULT_KIMI_MODEL)}">
  </div>
  <div class="toggle-row">
    <div class="toggle-mode" data-toggle="tape-mode" role="radiogroup" aria-label="Tape mode">
      <span class="toggle-mode__caption">MODE</span>
      <div class="toggle-mode__pill is-lit" data-tape-mode="sp" role="radio" tabindex="0" aria-checked="true">SP</div>
      <div class="toggle-mode__pill" data-tape-mode="lp" role="radio" tabindex="-1" aria-checked="false">LP</div>
      <div class="toggle-mode__pill" data-tape-mode="ep" role="radio" tabindex="-1" aria-checked="false">EP</div>
    </div>
    <div class="toggle-mode" data-toggle="audio-mode" role="radiogroup" aria-label="Audio mode">
      <span class="toggle-mode__caption">AUDIO</span>
      <div class="toggle-mode__pill" data-audio-mode="dolby" role="radio" tabindex="-1" aria-checked="false">DOLBY</div>
      <div class="toggle-mode__pill is-lit" data-audio-mode="off" role="radio" tabindex="0" aria-checked="true">OFF</div>
    </div>
  </div>
  <input type="hidden" name="creative_mode" value="on" data-flag="creative_mode">
  <input type="hidden" name="preview" value="on" data-flag="preview">
  <input type="hidden" name="skip_audio" value="on" data-flag="skip_audio">
  <input type="hidden" name="" value="" data-flag="render_mp4">
  <input type="hidden" name="" value="" data-flag="final">
  <input type="hidden" name="session_id" value="" id="session-id">
  <div class="btn-row">
    <button type="button" class="btn-tape btn-tape--ghost" data-action="ingest">⏏ INGEST</button>
    <button type="submit" class="btn-tape btn-tape--primary">▶ ROLL TAPE</button>
    <button type="button" class="btn-tape btn-tape--ghost" data-action="fallbacks" aria-pressed="false">⚙ FALLBACKS</button>
  </div>
  <div class="deck-divider" aria-hidden="true"></div>
  <div class="channel-row" data-stage="kimi" data-state="stby">
    <span class="ch-label">CH·KIMI</span>
    <div class="ch-bar"><div class="ch-fill"></div></div>
    <span class="ch-status">READY</span>
  </div>
  <div class="channel-row" data-stage="hermes" data-state="stby">
    <span class="ch-label">CH·HERMES</span>
    <div class="ch-bar"><div class="ch-fill"></div></div>
    <span class="ch-status">READY</span>
  </div>
  <div class="channel-row" data-stage="tape" data-state="stby">
    <span class="ch-label">CH·TAPE</span>
    <div class="ch-bar"><div class="ch-fill"></div></div>
    <span class="ch-status">READY</span>
  </div>
  <div class="channel-row" data-stage="output" data-state="idle">
    <span class="ch-label">CH·OUTPUT</span>
    <div class="ch-bar"><div class="ch-fill"></div></div>
    <span class="ch-status">IDLE</span>
  </div>
  <div class="deck deck-broadcasting" data-broadcasting hidden>
    <div class="kicker">// NOW BROADCASTING</div>
    <div class="glitch-headline" data-glitch>RENDERING FRAMES&hellip;</div>
    <div class="channel-row" data-stage="ingest" data-state="stby">
      <span class="ch-label">▣ INGEST</span>
      <div class="ch-bar"><div class="ch-fill"></div></div>
      <span class="ch-status">STBY</span>
    </div>
    <div class="channel-row" data-stage="analyze" data-state="stby">
      <span class="ch-label">▣ ANALYZE</span>
      <div class="ch-bar"><div class="ch-fill"></div></div>
      <span class="ch-status">STBY</span>
    </div>
    <div class="channel-row" data-stage="kimi_brief" data-state="stby">
      <span class="ch-label">▣ KIMI BRIEF</span>
      <div class="ch-bar"><div class="ch-fill"></div></div>
      <span class="ch-status">STBY</span>
    </div>
    <div class="channel-row" data-stage="render_frames" data-state="stby">
      <span class="ch-label">○ FRAMES</span>
      <div class="ch-bar"><div class="ch-fill"></div></div>
      <span class="ch-status">STBY</span>
    </div>
    <div class="channel-row" data-stage="tts" data-state="stby">
      <span class="ch-label">○ NARRATION</span>
      <div class="ch-bar"><div class="ch-fill"></div></div>
      <span class="ch-status">STBY</span>
    </div>
    <div class="channel-row" data-stage="compose" data-state="stby">
      <span class="ch-label">○ COMPOSE</span>
      <div class="ch-bar"><div class="ch-fill"></div></div>
      <span class="ch-status">STBY</span>
    </div>
    <div class="channel-row" data-stage="finalize" data-state="stby">
      <span class="ch-label">○ MASTER</span>
      <div class="ch-bar"><div class="ch-fill"></div></div>
      <span class="ch-status">STBY</span>
    </div>
    <div class="vu-meter" aria-hidden="true">{vu_segments}</div>
  </div>
</form>
<section class="tape-archive">
  <h2 class="section-heading">TAPE ARCHIVE</h2>
  {archive_html}
</section>
<div class="scope-strip" aria-hidden="true">TBC · SC-H · DROPOUT 0.0% · AGC ON · 1080×1920 · 30FPS</div>
<div class="tape-edge tape-edge--bottom" aria-hidden="true"></div>
"""
    return _page_shell("Repo-to-Shorts Agent", body)


def render_success_page(run_dir: Path, run_metadata: dict) -> str:
    artifact_copy = {
        "demo.mp4": "Vertical video export for direct playback.",
        "demo.html": "Browser-recordable motion preview fallback.",
        "metadata.json": "Run proof: model mode, render mode, and manifest.",
        "kimi_critique.md": "Creative critique and edit pass.",
        "storyboard.md": "Scene beats and narration structure.",
        "captions.srt": "Caption timing for social video.",
    }
    artifact_tiles = []
    for name in run_metadata.get("artifacts", []):
        safe_name = html.escape(name)
        href = f"/runs/{html.escape(run_dir.name)}/{safe_name}"
        description = artifact_copy.get(name, "Downloadable artifact from this run.")
        artifact_tiles.append(
            f'<a class="tape-label tape-label--artifact" href="{href}">'
            f'<span class="tape-label__name">{safe_name}</span>'
            f'<span class="tape-label__desc">{html.escape(description)}</span>'
            "</a>"
        )

    kimi_info = run_metadata.get("kimi", {}) if isinstance(run_metadata.get("kimi"), dict) else {}
    render_info = run_metadata.get("render", {}) if isinstance(run_metadata.get("render"), dict) else {}
    brief = run_metadata.get("creative_brief", {}) if isinstance(run_metadata.get("creative_brief"), dict) else {}
    scenes = brief.get("scenes", []) if isinstance(brief, dict) else []
    title_text = brief.get("title", "Broadcast complete") if isinstance(brief, dict) else "Broadcast complete"
    hook_text = brief.get("hook", "") if isinstance(brief, dict) else ""

    validation = render_info.get("validation") if isinstance(render_info, dict) else {}
    validation_ok = bool(validation.get("ok")) if isinstance(validation, dict) else True
    is_preview = bool(render_info.get("preview")) if isinstance(render_info, dict) else False
    is_final = bool(render_info.get("final")) if isinstance(render_info, dict) else False

    if not validation_ok:
        state_label = "VALIDATION FAILED"
    elif is_preview:
        state_label = "PREVIEW DRAFT"
    elif is_final:
        state_label = "BROADCAST COMPLETE"
    else:
        state_label = "PACKAGE COMPLETE"

    validation_errors = validation.get("errors", []) if isinstance(validation, dict) else []

    scene_rows = []
    for idx, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            continue
        scene_rows.append(
            '<div class="scene-row channel-row" data-stage="scene">'
            f'<span class="ch-label scene-row__num">{idx:02d}</span>'
            f'<span class="scene-row__tool">{html.escape(str(scene.get("visual_tool", "scene")).upper())}</span>'
            f'<span class="scene-row__narration">{html.escape(str(scene.get("narration", "")))}</span>'
            "</div>"
        )
    if not scene_rows:
        scene_rows.append('<div class="scene-row scene-row--empty">No scenes recorded.</div>')

    video_html = ""
    has_video = (run_dir / "demo.mp4").exists()
    if has_video:
        video_url = f"/runs/{html.escape(run_dir.name)}/demo.mp4"
        video_html = (
            '<div class="crt-viewport">'
            f'<video class="crt-viewport__video" controls playsinline src="{video_url}"></video>'
            '<div class="crt-viewport__overlay" aria-hidden="true"></div>'
            "</div>"
        )
    else:
        video_html = (
            '<div class="crt-viewport crt-viewport--empty">'
            '<div class="crt-viewport__overlay" aria-hidden="true">● NO SIGNAL</div>'
            "</div>"
        )

    reel_no = "001"
    head_part = run_dir.name.split("-")[0] if "-" in run_dir.name else ""
    if head_part.isdigit() and len(head_part) >= 3:
        reel_no = head_part[-3:]

    runtime_text = "00:01:00"
    if isinstance(render_info, dict) and render_info.get("duration"):
        runtime_text = html.escape(str(render_info.get("duration")))

    kimi_mode = html.escape(str(kimi_info.get("mode", "unknown"))) if isinstance(kimi_info, dict) else "unknown"
    render_mode = html.escape(str(render_info.get("mode", "unknown"))) if isinstance(render_info, dict) else "unknown"
    renderer_name = html.escape(str(render_info.get("renderer", "unknown"))) if isinstance(render_info, dict) else "unknown"

    kimi_pill_class = "is-lock" if kimi_mode == "live-api" else "is-rec"
    render_pill_class = "is-lock" if render_mode in ("mp4", "live-api") else "is-rec"

    primary_download_html = ""
    if has_video:
        primary_download_html = (
            f'<a class="btn-tape btn-tape--primary" href="/runs/{html.escape(run_dir.name)}/demo.mp4">⏬ MASTER</a>'
        )
    else:
        for fallback in ("demo.html", "metadata.json"):
            if (run_dir / fallback).exists():
                primary_download_html = (
                    f'<a class="btn-tape btn-tape--primary" href="/runs/{html.escape(run_dir.name)}/{fallback}">⏬ {html.escape(fallback.upper())}</a>'
                )
                break

    secondary_download_html = ""
    if has_video and (run_dir / "demo.html").exists():
        secondary_download_html = (
            f'<a class="btn-tape btn-tape--ghost" href="/runs/{html.escape(run_dir.name)}/demo.html">⏬ HTML PROOF</a>'
        )

    colorbars = (
        '<div class="colorbars colorbars--banner" aria-hidden="true">'
        '<div class="colorbars__bar colorbars__bar--silver"></div>'
        '<div class="colorbars__bar colorbars__bar--yellow"></div>'
        '<div class="colorbars__bar colorbars__bar--cyan"></div>'
        '<div class="colorbars__bar colorbars__bar--green"></div>'
        '<div class="colorbars__bar colorbars__bar--magenta"></div>'
        '<div class="colorbars__bar colorbars__bar--red"></div>'
        '<div class="colorbars__bar colorbars__bar--blue"></div>'
        "</div>"
    )

    artifact_block = (
        "\n".join(artifact_tiles)
        if artifact_tiles
        else '<div class="tape-label tape-label--empty"><span class="tape-label__name">No artifacts listed.</span></div>'
    )

    body = f"""
<div class="tape-edge tape-edge--top" aria-hidden="true"></div>
<header class="slate slate--lock">
  <span class="slate-state is-lock">▣ SIGNAL LOCKED</span>
  <span class="slate-title">REEL.{reel_no} — MASTER</span>
  <span class="slate-tc">00:01:00:00</span>
</header>
{colorbars}
<section class="hero hero--success">
  <div class="kicker">{html.escape('// ' + state_label)}</div>
  <h1 class="glitch-headline glitch-headline--md">{html.escape(str(title_text))}</h1>
  <p class="lede">{html.escape(str(hook_text))}</p>
  {'<div class="deck error-log"><pre class="error-message">' + html.escape(chr(10).join(validation_errors)) + '</pre></div>' if validation_errors else ''}
</section>
<section class="result-grid">
  <div class="deck master-viewer">
    {video_html}
    <dl class="master-meta">
      <div class="master-meta__row"><dt>TAPE</dt><dd>REEL.{reel_no}</dd></div>
      <div class="master-meta__row"><dt>KIMI</dt><dd>{kimi_mode}</dd></div>
      <div class="master-meta__row"><dt>MASTER</dt><dd>1080×1920</dd></div>
      <div class="master-meta__row"><dt>RUNTIME</dt><dd>{runtime_text}</dd></div>
    </dl>
    <div class="status-row">
      <span class="status-pill {kimi_pill_class}">KIMI · {kimi_mode}</span>
      <span class="status-pill {render_pill_class}">RENDER · {render_mode}</span>
      <span class="status-pill is-idle">RENDERER · {renderer_name}</span>
    </div>
    <div class="btn-row btn-row--transport">
      {primary_download_html}
      <a class="btn-tape btn-tape--ghost" href="/">⏏ NEW REEL</a>
      {secondary_download_html}
    </div>
    <p class="caption">RUN · <code>{html.escape(str(run_dir))}</code></p>
  </div>
  <aside class="deck cue-sheet">
    <h2 class="section-heading">BROADCAST CUE SHEET</h2>
    {''.join(scene_rows)}
  </aside>
</section>
<section class="artifact-tiles">
  <h2 class="section-heading">ARTIFACTS</h2>
  <div class="artifact-tiles__grid">
    {artifact_block}
  </div>
</section>
<div class="scope-strip" aria-hidden="true">TBC · SC-H · DROPOUT 0.0% · AGC ON · 1080×1920 · 30FPS</div>
<div class="tape-edge tape-edge--bottom" aria-hidden="true"></div>
"""
    return _page_shell("Generation complete", body)


def render_error_page(message: str, status: int = 400) -> str:
    colorbars_broken = (
        '<div class="colorbars colorbars--banner colorbars--broken" aria-hidden="true">'
        '<div class="colorbars__bar colorbars__bar--silver"></div>'
        '<div class="colorbars__bar colorbars__bar--yellow"></div>'
        '<div class="colorbars__bar colorbars__bar--cyan"></div>'
        '<div class="colorbars__bar colorbars__bar--green"></div>'
        '<div class="colorbars__bar colorbars__bar--magenta"></div>'
        '<div class="colorbars__bar colorbars__bar--red"></div>'
        '<div class="colorbars__bar colorbars__bar--blue"></div>'
        "</div>"
    )

    body = f"""
<div class="tape-edge tape-edge--top tape-edge--dropout" aria-hidden="true"></div>
<header class="slate slate--error">
  <span class="slate-state is-rec">● SIGNAL LOST</span>
  <span class="slate-title">CH 02 — TRACKING ERROR</span>
  <span class="slate-tc">--:--:--:--</span>
</header>
{colorbars_broken}
<section class="hero hero--error">
  <div class="kicker">// TAPE ATE THE REEL.</div>
  <h1 class="glitch-headline glitch-headline--error" data-rotate-error>TRACKING ERROR.</h1>
</section>
<section class="deck error-log">
  <pre class="error-message">! {html.escape(message)}</pre>
</section>
<div class="btn-row btn-row--center">
  <a class="btn-tape btn-tape--primary" href="/">⏏ EJECT TAPE</a>
</div>
<div class="scope-strip" aria-hidden="true">STATUS {status} · TRACKING ERROR · TAPE EJECTED</div>
<div class="tape-edge tape-edge--bottom tape-edge--dropout" aria-hidden="true"></div>
"""
    return _page_shell(f"Error {status}", body)


def resolve_run_file(runs_dir: Path, request_path: str) -> Path:
    relative = request_path.removeprefix("/runs/")
    candidate = (runs_dir / relative).resolve()
    runs_resolved = runs_dir.resolve()
    if runs_resolved not in candidate.parents and candidate != runs_resolved:
        raise ValueError("path escapes runs directory")
    return candidate


STATIC_DIR = Path(__file__).resolve().parent / "static"


def resolve_static_file(request_path: str) -> Path:
    relative = request_path.removeprefix("/static/")
    candidate = (STATIC_DIR / relative).resolve()
    static_resolved = STATIC_DIR.resolve()
    if static_resolved not in candidate.parents and candidate != static_resolved:
        raise ValueError("path escapes static directory")
    return candidate


def _guess_content_type(path: Path) -> str:
    ctype, _ = mimetypes.guess_type(str(path))
    if ctype:
        return ctype
    suffix = path.suffix.lower()
    if suffix == ".woff2":
        return "font/woff2"
    if suffix == ".woff":
        return "font/woff"
    return "application/octet-stream"


def _make_handler(runs_dir: Path):
    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):  # noqa: ANN001
            pass

        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            if path == "/healthz":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True}).encode())
                return

            if path == "/progress":
                query = urllib.parse.parse_qs(parsed.query)
                session_id = query.get("session", [""])[0]
                session = ProgressTracker.get_session(session_id) if session_id else None
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                if session:
                    self.wfile.write(json.dumps(session.to_dict()).encode())
                else:
                    stages = [
                        {"name": name, "label": label, "status": "pending", "detail": ""}
                        for name, label in ProgressTracker.STAGES
                    ]
                    self.wfile.write(
                        json.dumps(
                            {
                                "session_id": session_id,
                                "percent": 0,
                                "complete": 0,
                                "total": len(stages),
                                "active_stage": None,
                                "active_label": None,
                                "active_detail": "Waiting for generation to start…",
                                "error": None,
                                "stages": stages,
                            }
                        ).encode()
                    )
                return

            if path == "/":
                body = render_home_page(list_runs(runs_dir)).encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(body)
                return

            if path.startswith("/static/"):
                try:
                    file_path = resolve_static_file(path)
                except ValueError:
                    self.send_response(404)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(b"Not found")
                    return

                if not file_path.exists() or file_path.is_dir():
                    self.send_response(404)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(b"Not found")
                    return

                self.send_response(200)
                self.send_header("Content-Type", _guess_content_type(file_path))
                self.send_header("Content-Length", str(file_path.stat().st_size))
                self.send_header("Cache-Control", "public, max-age=3600")
                self.end_headers()
                with file_path.open("rb") as f:
                    self.wfile.write(f.read())
                return

            if path.startswith("/runs/"):
                try:
                    file_path = resolve_run_file(runs_dir, path)
                except ValueError:
                    self.send_response(404)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(render_error_page("Not found", 404).encode())
                    return

                if not file_path.exists() or file_path.is_dir():
                    self.send_response(404)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(render_error_page("Not found", 404).encode())
                    return

                self.send_response(200)
                self.send_header("Content-Type", _guess_content_type(file_path))
                self.send_header("Content-Length", str(file_path.stat().st_size))
                self.end_headers()
                with file_path.open("rb") as f:
                    self.wfile.write(f.read())
                return

            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(render_error_page("Not found", 404).encode())

        def do_POST(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            if path == "/generate":
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                form = urllib.parse.parse_qs(body, keep_blank_values=True)

                target = form.get("target", [""])[0].strip()
                audience = form.get("audience", [DEFAULT_AUDIENCE])[0].strip() or DEFAULT_AUDIENCE
                kimi_model = form.get("kimi_model", [DEFAULT_KIMI_MODEL])[0].strip() or DEFAULT_KIMI_MODEL
                render_mp4 = "render_mp4" in form
                creative_mode = "creative_mode" in form
                preview = "preview" in form
                skip_audio = "skip_audio" in form
                final = "final" in form
                if final:
                    preview = False
                session_id = form.get("session_id", [""])[0].strip()

                if not target:
                    self.send_response(400)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(render_error_page("Target is required.", 400).encode())
                    return

                if creative_mode and session_id and not ProgressTracker.get_session(session_id):
                    ProgressTracker.create_session(session_id)

                try:
                    if creative_mode:
                        from repo_to_shorts.hermes_skill import run_creative_pipeline

                        result = run_creative_pipeline(
                            target,
                            audience=audience,
                            out_dir=runs_dir,
                            kimi_model=kimi_model,
                            session_id=session_id,
                            preview=preview,
                            skip_audio=skip_audio,
                            final=final,
                        )
                        run_dir = Path(result["run_dir"])
                    else:
                        render = "mp4" if render_mp4 else "none"
                        run_dir = run_analysis(target, audience=audience, out_dir=runs_dir, kimi_model=kimi_model, render=render)
                    metadata = json.loads((run_dir / "metadata.json").read_text())
                    page = render_success_page(run_dir, metadata).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(page)
                except Exception as exc:  # noqa: BLE001
                    self.send_response(500)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(render_error_page(str(exc), 500).encode())
                return

            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(render_error_page("Not found", 404).encode())

    return _Handler


def run_web_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, runs_dir: Path | str = DEFAULT_RUNS_DIR) -> None:
    runs_dir = Path(runs_dir)
    handler = _make_handler(runs_dir)
    server = RepoShortsHTTPServer((host, port), handler)
    print(f"Starting Repo-to-Shorts web UI at http://{host}:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
