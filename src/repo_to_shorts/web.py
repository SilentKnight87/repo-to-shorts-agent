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
<style>
:root {{
  --bg: #050507;
  --panel: rgba(255,255,255,.045);
  --panel-strong: rgba(255,255,255,.075);
  --line: rgba(255,255,255,.10);
  --line-soft: rgba(255,255,255,.06);
  --text: #f7f8f8;
  --muted: #8a8f98;
  --soft: #d0d6e0;
  --accent: #7c72ff;
  --accent-2: #16d9e3;
  --good: #30d158;
  --warn: #ffd60a;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  min-height: 100vh;
  color: var(--text);
  background:
    radial-gradient(circle at 20% 0%, rgba(124,114,255,.30), transparent 32rem),
    radial-gradient(circle at 90% 18%, rgba(22,217,227,.18), transparent 28rem),
    linear-gradient(180deg, #050507 0%, #090a0f 50%, #050507 100%);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-feature-settings: "cv01", "ss03";
}}
body::before {{
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background-image: linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px);
  background-size: 72px 72px;
  mask-image: linear-gradient(to bottom, rgba(0,0,0,.75), transparent 75%);
}}
a {{ color: var(--soft); text-decoration: none; }}
a:hover {{ color: var(--text); }}
.shell {{ width: min(1180px, calc(100vw - 40px)); margin: 0 auto; padding: 28px 0 64px; position: relative; }}
.nav {{ display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 42px; }}
.brand {{ display: flex; gap: 12px; align-items: center; font-weight: 610; letter-spacing: -.02em; }}
.mark {{ width: 34px; height: 34px; border-radius: 10px; background: linear-gradient(135deg, var(--accent), var(--accent-2)); box-shadow: 0 0 46px rgba(124,114,255,.42); }}
.badges {{ display: flex; flex-wrap: wrap; gap: 8px; }}
.pill {{ border: 1px solid var(--line); background: rgba(255,255,255,.04); color: var(--soft); border-radius: 999px; padding: 7px 11px; font-size: 12px; font-weight: 520; }}
.hero {{ display: grid; grid-template-columns: minmax(0, 1.1fr) 430px; gap: 28px; align-items: stretch; }}
.hero-copy {{ padding: 38px 0 26px; }}
.kicker {{ color: var(--accent-2); text-transform: uppercase; letter-spacing: .16em; font-size: 12px; font-weight: 700; margin-bottom: 18px; }}
h1 {{ font-size: clamp(48px, 8vw, 88px); line-height: .92; letter-spacing: -0.07em; margin: 0 0 22px; font-weight: 560; max-width: 820px; }}
.lede {{ font-size: 18px; line-height: 1.65; color: var(--muted); max-width: 690px; margin: 0; }}
.card {{ background: linear-gradient(180deg, var(--panel-strong), var(--panel)); border: 1px solid var(--line); border-radius: 24px; box-shadow: 0 24px 80px rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.08); }}
.form-card {{ padding: 20px; }}
.form-card h2, .section-title {{ margin: 0 0 14px; font-size: 17px; letter-spacing: -.02em; }}
label {{ display: block; color: var(--muted); font-size: 12px; font-weight: 640; text-transform: uppercase; letter-spacing: .12em; margin: 16px 0 8px; }}
input[type="text"] {{
  width: 100%; min-height: 50px; padding: 0 14px; border-radius: 13px; border: 1px solid var(--line);
  background: rgba(0,0,0,.32); color: var(--text); font-size: 14px; outline: none;
}}
input[type="text"]:focus {{ border-color: rgba(124,114,255,.7); box-shadow: 0 0 0 4px rgba(124,114,255,.14); }}
.checks {{ display: grid; gap: 8px; margin: 14px 0 18px; }}
.checks label {{ display: flex; align-items: center; gap: 10px; text-transform: none; letter-spacing: 0; margin: 0; font-size: 13px; font-weight: 520; color: var(--soft); }}
button {{ width: 100%; min-height: 52px; border: 0; border-radius: 14px; color: white; font-weight: 720; letter-spacing: -.01em; background: linear-gradient(135deg, #6f6cff, #10c8d8); cursor: pointer; box-shadow: 0 18px 54px rgba(124,114,255,.32); }}
button:hover {{ filter: brightness(1.08); }}
button:disabled {{ cursor: wait; opacity: .76; filter: saturate(.9); }}
.note {{ color: var(--muted); font-size: 12px; line-height: 1.5; margin: 12px 0 0; }}
.loading-panel {{ display: none; margin-top: 14px; padding: 14px; border: 1px solid rgba(22,217,227,.22); border-radius: 16px; background: rgba(22,217,227,.075); color: var(--soft); line-height: 1.45; }}
.loading-panel strong {{ display: block; color: var(--text); margin-bottom: 4px; }}
.loading-row {{ display: flex; gap: 12px; align-items: flex-start; }}
.spinner {{ width: 18px; height: 18px; border-radius: 999px; border: 2px solid rgba(255,255,255,.20); border-top-color: var(--accent-2); animation: spin .85s linear infinite; flex: 0 0 auto; margin-top: 2px; }}
.form-card.is-submitting .loading-panel {{ display: block; }}
.form-card.is-submitting .note {{ color: var(--accent-2); }}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}
.progress-bar-shell {{ width: 100%; height: 6px; background: rgba(255,255,255,.08); border-radius: 999px; margin-top: 14px; overflow: hidden; }}
.progress-bar-fill {{ height: 100%; background: linear-gradient(90deg, var(--accent), var(--accent-2)); border-radius: 999px; transition: width .4s ease; }}
.progress-stages {{ display: grid; gap: 6px; margin-top: 12px; }}
.progress-stage {{ display: grid; grid-template-columns: 18px 1fr; gap: 8px; align-items: center; font-size: 12px; color: var(--muted); }}
.progress-stage.done {{ color: var(--good); }}
.progress-stage.active {{ color: var(--text); font-weight: 640; }}
.progress-stage .dot {{ width: 8px; height: 8px; border-radius: 50%; background: currentColor; opacity: .5; }}
.progress-stage.active .dot {{ opacity: 1; box-shadow: 0 0 8px currentColor; }}
.progress-stage.done .dot {{ opacity: 1; }}

.demo-frame {{ margin-top: 36px; display: grid; grid-template-columns: 1fr 330px; gap: 22px; }}
.preview {{ padding: 20px; min-height: 360px; overflow: hidden; position: relative; }}
.preview::after {{ content: ""; position: absolute; width: 260px; height: 260px; right: -80px; top: -80px; background: radial-gradient(circle, rgba(124,114,255,.32), transparent 70%); }}
.terminal {{ background: #050507; border: 1px solid var(--line-soft); border-radius: 18px; padding: 16px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; color: #b6bed0; line-height: 1.7; }}
.prompt {{ color: var(--accent-2); }}
.studio-grid {{ margin-top: 36px; display: grid; grid-template-columns: 360px 1fr; gap: 22px; align-items: stretch; }}
.phone {{ position: relative; min-height: 600px; padding: 14px; border-radius: 38px; background: linear-gradient(145deg, rgba(255,255,255,.16), rgba(255,255,255,.035)); border: 1px solid rgba(255,255,255,.16); box-shadow: 0 34px 100px rgba(0,0,0,.46), inset 0 1px 0 rgba(255,255,255,.18); }}
.phone-screen {{ position: relative; height: 100%; min-height: 570px; overflow: hidden; border-radius: 28px; background: radial-gradient(circle at 50% 0%, rgba(22,217,227,.24), transparent 30%), linear-gradient(180deg, #131624, #06070b 72%); border: 1px solid rgba(255,255,255,.10); padding: 18px; display: flex; flex-direction: column; justify-content: space-between; }}
.phone-screen::before {{ content: ""; position: absolute; inset: 0; background: linear-gradient(120deg, transparent, rgba(255,255,255,.08), transparent); transform: translateX(-58%); animation: sheen 5.8s ease-in-out infinite; }}
.notch {{ width: 90px; height: 20px; border-radius: 999px; background: #050507; margin: 0 auto 24px; border: 1px solid rgba(255,255,255,.08); }}
.reel-title {{ position: relative; font-size: 34px; line-height: .96; letter-spacing: -.06em; font-weight: 650; max-width: 260px; }}
.reel-caption {{ position: relative; color: var(--muted); font-size: 13px; line-height: 1.5; max-width: 260px; }}
.timeline {{ position: relative; display: grid; gap: 8px; margin: 24px 0; }}
.timeline span {{ height: 42px; border-radius: 12px; background: linear-gradient(90deg, rgba(124,114,255,.42), rgba(22,217,227,.18)); border: 1px solid rgba(255,255,255,.10); }}
.timeline span:nth-child(2) {{ width: 76%; background: linear-gradient(90deg, rgba(255,255,255,.18), rgba(124,114,255,.24)); }}
.timeline span:nth-child(3) {{ width: 88%; background: linear-gradient(90deg, rgba(22,217,227,.30), rgba(255,255,255,.10)); }}
.glass-toolbar {{ position: relative; display: flex; gap: 8px; flex-wrap: wrap; }}
.glass-toolbar span {{ border: 1px solid rgba(255,255,255,.14); background: rgba(255,255,255,.08); border-radius: 999px; padding: 8px 10px; color: var(--soft); font-size: 11px; backdrop-filter: blur(14px); }}
.studio-panel {{ padding: 20px; display: grid; gap: 18px; }}
.metric-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }}
.metric {{ border: 1px solid var(--line-soft); border-radius: 18px; padding: 14px; background: rgba(255,255,255,.035); }}
.metric strong {{ display: block; font-size: 22px; letter-spacing: -.04em; }}
.metric span {{ color: var(--muted); font-size: 12px; }}
.artifact-gallery {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }}
.artifact-card {{ min-height: 118px; padding: 14px; border: 1px solid var(--line-soft); border-radius: 18px; background: linear-gradient(180deg, rgba(255,255,255,.055), rgba(255,255,255,.025)); position: relative; overflow: hidden; }}
.artifact-card::after {{ content: ""; position: absolute; width: 90px; height: 90px; right: -30px; bottom: -30px; background: radial-gradient(circle, rgba(124,114,255,.22), transparent 70%); }}
.artifact-card strong {{ display: block; margin-bottom: 6px; }}
.artifact-card span {{ color: var(--muted); font-size: 12px; line-height: 1.45; }}
.status-strip {{ display: grid; gap: 8px; }}
.status-row {{ display: flex; justify-content: space-between; gap: 14px; padding: 10px 0; border-bottom: 1px solid var(--line-soft); color: var(--muted); font-size: 13px; }}
.status-row strong {{ color: var(--soft); }}
@keyframes sheen {{ 0%, 55% {{ transform: translateX(-64%); }} 100% {{ transform: translateX(64%); }} }}
.steps {{ padding: 20px; }}
.step {{ display: grid; grid-template-columns: 26px 1fr; gap: 10px; padding: 13px 0; border-bottom: 1px solid var(--line-soft); }}
.step:last-child {{ border-bottom: 0; }}
.num {{ width: 26px; height: 26px; border-radius: 50%; display: grid; place-items: center; background: rgba(124,114,255,.16); color: #c7c3ff; font-size: 12px; font-weight: 700; }}
.step strong {{ display: block; font-size: 14px; }}
.step span {{ color: var(--muted); font-size: 13px; line-height: 1.45; }}
.runs {{ margin-top: 24px; display: grid; gap: 12px; }}
.run {{ padding: 14px; display: flex; align-items: center; justify-content: space-between; gap: 16px; }}
.run-name {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; color: var(--soft); }}
.links {{ display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; }}
.links a {{ border: 1px solid var(--line); background: rgba(255,255,255,.04); border-radius: 999px; padding: 7px 10px; font-size: 12px; }}
.result-grid {{ display: grid; grid-template-columns: minmax(0, 430px) 1fr; gap: 24px; align-items: start; }}
.video-card {{ padding: 14px; }}
video {{ width: 100%; max-height: 76vh; border-radius: 18px; background: #000; border: 1px solid var(--line); }}
.meta {{ padding: 22px; }}
.meta h1 {{ font-size: clamp(34px, 5vw, 58px); }}
.scene-list {{ display: grid; gap: 10px; margin: 18px 0; padding: 0; list-style: none; }}
.scene-list li {{ padding: 14px; border: 1px solid var(--line-soft); border-radius: 14px; background: rgba(255,255,255,.035); color: var(--soft); }}
.status {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 16px 0; }}
.error {{ padding: 24px; border-color: rgba(255,69,58,.3); }}
@media (max-width: 900px) {{ .hero, .demo-frame, .studio-grid, .result-grid {{ grid-template-columns: 1fr; }} .metric-grid, .artifact-gallery {{ grid-template-columns: 1fr; }} .shell {{ width: min(100vw - 24px, 1180px); }} }}
</style>
</head>
<body><main class="shell">{body}</main>
<script>
document.addEventListener("DOMContentLoaded", () => {{
  const form = document.getElementById("generate-form");
  if (!form) return;

  const sessionInput = document.getElementById("session-id");
  const detailEl = document.getElementById("progress-detail");
  const barFill = document.getElementById("progress-bar-fill");
  const stagesEl = document.getElementById("progress-stages");
  let pollInterval = null;

  function uuid() {{
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {{
      const r = Math.random() * 16 | 0;
      return (c === "x" ? r : (r & 0x3 | 0x8)).toString(16);
    }});
  }}

  function renderStages(stages, active) {{
    if (!stagesEl) return;
    stagesEl.innerHTML = stages.map(s => {{
      const cls = s.status === "complete" ? "done" : (s.name === active ? "active" : "");
      return `<div class="progress-stage ${{cls}}"><div class="dot"></div><div>${{html_escape(s.label)}}</div></div>`;
    }}).join("");
  }}

  function html_escape(str) {{
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }}

  async function pollProgress(sessionId) {{
    try {{
      const res = await fetch(`/progress?session=${{encodeURIComponent(sessionId)}}`);
      const data = await res.json();
      if (barFill) barFill.style.width = (data.percent || 0) + "%";
      if (detailEl && data.active_detail) detailEl.textContent = data.active_detail;
      if (detailEl && data.error) detailEl.textContent = "Error: " + data.error;
      renderStages(data.stages || [], data.active_stage);
      if (data.percent >= 100 || data.error) {{
        clearInterval(pollInterval);
        pollInterval = null;
      }}
    }} catch (e) {{
      // ignore polling errors
    }}
  }}

  form.addEventListener("submit", (event) => {{
    if (form.dataset.submitting === "true") {{
      event.preventDefault();
      return;
    }}

    event.preventDefault();
    form.dataset.submitting = "true";
    form.classList.add("is-submitting");
    form.setAttribute("aria-busy", "true");

    const sid = uuid();
    if (sessionInput) sessionInput.value = sid;

    const button = form.querySelector('button[type="submit"]');
    if (button) {{
      button.disabled = true;
      button.textContent = "Generating…";
    }}

    renderStages([
      {{name:"ingest", label:"Ingesting repo", status:"pending"}},
      {{name:"analyze", label:"Analyzing structure", status:"pending"}},
      {{name:"kimi_brief", label:"Writing creative brief", status:"pending"}},
      {{name:"render_frames", label:"Rendering frames", status:"pending"}},
      {{name:"tts", label:"Generating voice", status:"pending"}},
      {{name:"compose", label:"Composing video", status:"pending"}},
      {{name:"finalize", label:"Packaging artifacts", status:"pending"}},
    ], "ingest");

    pollProgress(sid);
    pollInterval = setInterval(() => pollProgress(sid), 1500);

    window.setTimeout(() => {{
      HTMLFormElement.prototype.submit.call(form);
    }}, 80);
  }});
}});
</script>
</body>
</html>"""


def render_home_page(runs: list[Path], message: str | None = None) -> str:
    run_items = []
    for run in runs:
        artifacts = []
        for name in ("demo.mp4", "metadata.json", "demo.html", "kimi_critique.md"):
            if (run / name).exists():
                artifacts.append(f'<a href="/runs/{html.escape(run.name)}/{html.escape(name)}">{html.escape(name)}</a>')
        links = "".join(artifacts) or '<span class="note">no artifacts yet</span>'
        run_items.append(f'<article class="card run"><div class="run-name">{html.escape(run.name)}</div><div class="links">{links}</div></article>')
    runs_html = "\n".join(run_items) or '<article class="card run"><div class="run-name">No runs yet. Paste a repo and make one.</div></article>'
    message_html = f'<div class="pill">{html.escape(message)}</div>' if message else ""

    body = f"""
<nav class="nav">
  <div class="brand"><div class="mark"></div><span>Repo-to-Shorts Agent</span></div>
  <div class="badges"><span class="pill">Hermes Agent</span><span class="pill">Kimi 2.6</span><span class="pill">Vertical MP4</span></div>
</nav>
<section class="hero">
  <div class="hero-copy">
    <div class="kicker">Creative hackathon demo machine</div>
    <h1>Turn a GitHub repo into a cinematic launch short.</h1>
    <p class="lede">Paste a repo. Kimi writes the creative brief. Hermes turns code structure into narration, motion, captions, and a downloadable 9:16 demo video. The submission is meta: this app generates the video about itself.</p>
    {message_html}
  </div>
  <form id="generate-form" class="card form-card" method="POST" action="/generate">
    <h2>Generate a short</h2>
    <label>Target repo or GitHub URL</label>
    <input type="text" name="target" placeholder="https://github.com/owner/repo or local path like ." required>
    <label>Audience</label>
    <input type="text" name="audience" value="{html.escape(DEFAULT_AUDIENCE)}">
    <label>Kimi model</label>
    <input type="text" name="kimi_model" value="{html.escape(DEFAULT_KIMI_MODEL)}">
    <div class="checks">
      <label><input type="checkbox" name="creative_mode" checked> Creative short: animated, narrated, hackathon-ready</label>
      <label><input type="checkbox" name="preview" checked> Fast preview: ~13s at 12fps for iteration</label>
      <label><input type="checkbox" name="skip_audio" checked> Skip audio for fastest visual loop</label>
      <label><input type="checkbox" name="render_mp4"> Classic MP4 fallback</label>
    </div>
    <input type="hidden" name="session_id" value="" id="session-id">
    <button type="submit">Generate short package</button>
    <div class="loading-panel" role="status" aria-live="polite" aria-atomic="true">
      <div class="loading-row">
        <div class="spinner" aria-hidden="true"></div>
        <div>
          <strong>Generating your short package…</strong>
          <span id="progress-detail">Analyzing the repo, writing the Kimi creative brief, rendering motion, and packaging artifacts. Fast preview is the default loop; uncheck Skip audio for a voice/music smoke test, and uncheck Fast preview only for final export.</span>
        </div>
      </div>
      <div class="progress-bar-shell" id="progress-bar-shell"><div class="progress-bar-fill" id="progress-bar-fill" style="width:0%"></div></div>
      <div class="progress-stages" id="progress-stages"></div>
    </div>
    <p class="note">Default mode is fast visual preview, around 20 seconds. Uncheck Skip audio for a ~40 second audio preview. Full final export is deliberately last.</p>
  </form>
</section>
<section class="studio-grid" aria-label="Studio preview">
  <div class="phone" aria-hidden="true">
    <div class="phone-screen">
      <div>
        <div class="notch"></div>
        <div class="kicker">Live preview</div>
        <div class="reel-title">Repo signal, edited like a launch film.</div>
        <div class="timeline"><span></span><span></span><span></span></div>
        <p class="reel-caption">A vertical storyboard with code architecture, narration beats, captions, and proof metadata — ready to screen-record or export.</p>
      </div>
      <div class="glass-toolbar"><span>1080×1920</span><span>Kimi brief</span><span>Captions</span><span>MP4 optional</span></div>
    </div>
  </div>
  <div class="card studio-panel">
    <div>
      <div class="section-title">Demo cockpit</div>
      <p class="lede">Not a form. A command center for turning repo evidence into a polished short package: creative direction, motion plan, video preview, and judge-facing artifacts.</p>
    </div>
    <div class="metric-grid">
      <div class="metric"><strong>7</strong><span>generation stages with live status</span></div>
      <div class="metric"><strong>9:16</strong><span>cinematic vertical output</span></div>
      <div class="metric"><strong>0 keys</strong><span>required for deterministic fallback</span></div>
    </div>
    <div class="artifact-gallery" aria-label="Generated artifact gallery">
      <div class="artifact-card"><strong>Launch video</strong><span>demo.mp4 when rendering is enabled, or a browser-recordable demo.html fallback.</span></div>
      <div class="artifact-card"><strong>Creative system</strong><span>Kimi critique, storyboard, narration script, captions, and scene-by-scene visual direction.</span></div>
      <div class="artifact-card"><strong>Proof layer</strong><span>metadata.json records model mode, render mode, artifact manifest, and reproducible run path.</span></div>
      <div class="artifact-card"><strong>Submission kit</strong><span>X post, Discord copy, architecture SVG, and recording notes for a clean hackathon handoff.</span></div>
    </div>
    <div class="terminal">
      <span class="prompt">repo-shorts</span> ingest GitHub URL<br>
      <span class="prompt">kimi-2.6</span> sharpen hook + creative direction<br>
      <span class="prompt">renderer</span> compose cinematic architecture scenes<br>
      <span class="prompt">proof</span> package every artifact for review
    </div>
  </div>
</section>
<section>
  <h2 class="section-title">Latest runs</h2>
  <div class="runs">{runs_html}</div>
</section>
"""
    return _page_shell("Repo-to-Shorts Agent", body)


def render_success_page(run_dir: Path, run_metadata: dict) -> str:
    artifacts = []
    artifact_cards = []
    artifact_copy = {
        "demo.mp4": "Vertical video export for direct playback.",
        "demo.html": "Browser-recordable motion preview fallback.",
        "metadata.json": "Run proof: model mode, render mode, and manifest.",
        "kimi_critique.md": "Creative critique and edit pass.",
        "storyboard.md": "Scene beats and narration structure.",
        "captions.srt": "Caption timing for social video.",
    }
    for name in run_metadata.get("artifacts", []):
        safe_name = html.escape(name)
        href = f"/runs/{html.escape(run_dir.name)}/{safe_name}"
        artifacts.append(f'<a href="{href}">{safe_name}</a>')
        description = artifact_copy.get(name, "Downloadable artifact from this run.")
        artifact_cards.append(f'<a class="artifact-card" href="{href}"><strong>{safe_name}</strong><span>{html.escape(description)}</span></a>')

    kimi_info = run_metadata.get("kimi", {})
    render_info = run_metadata.get("render", {})
    brief = run_metadata.get("creative_brief", {})
    scenes = brief.get("scenes", []) if isinstance(brief, dict) else []
    scenes_html = "\n".join(
        f'<li><strong>{idx + 1}. {html.escape(scene.get("visual_tool", "scene"))}</strong><br>{html.escape(scene.get("narration", ""))}</li>'
        for idx, scene in enumerate(scenes)
    )
    video_html = ""
    if (run_dir / "demo.mp4").exists():
        video_url = f"/runs/{html.escape(run_dir.name)}/demo.mp4"
        video_html = f'<video controls playsinline src="{video_url}"></video>'

    body = f"""
<nav class="nav"><a class="brand" href="/"><div class="mark"></div><span>Repo-to-Shorts Agent</span></a><div class="badges"><a class="pill" href="/">New run</a></div></nav>
<section class="result-grid">
  <div class="card video-card">{video_html or '<p class="note">No video artifact found.</p>'}</div>
  <div class="card meta">
    <div class="kicker">Generation complete</div>
    <h1>{html.escape(brief.get('title', 'Generation complete') if isinstance(brief, dict) else 'Generation complete')}</h1>
    <p class="lede">{html.escape(brief.get('hook', '') if isinstance(brief, dict) else '')}</p>
    <div class="status">
      <span class="pill">Kimi: {html.escape(kimi_info.get('mode', 'unknown'))}</span>
      <span class="pill">Render: {html.escape(render_info.get('mode', 'unknown'))}</span>
      <span class="pill">Renderer: {html.escape(render_info.get('renderer', 'unknown'))}</span>
    </div>
    <p class="note">Run: <code>{html.escape(str(run_dir))}</code></p>
    <h2 class="section-title">Artifact gallery</h2>
    <div class="artifact-gallery">{''.join(artifact_cards) or '<p class="note">No artifacts listed in metadata.</p>'}</div>
    <h2 class="section-title">Creative brief</h2>
    <ul class="scene-list">{scenes_html}</ul>
    <div class="links">{''.join(artifacts)}</div>
  </div>
</section>
"""
    return _page_shell("Generation complete", body)


def render_error_page(message: str, status: int = 400) -> str:
    body = f"""
<nav class="nav"><a class="brand" href="/"><div class="mark"></div><span>Repo-to-Shorts Agent</span></a></nav>
<section class="card error"><div class="kicker">Error {status}</div><h1>Generation hit a wall.</h1><p class="lede">{html.escape(message)}</p><p><a class="pill" href="/">Back to home</a></p></section>
"""
    return _page_shell(f"Error {status}", body)


def resolve_run_file(runs_dir: Path, request_path: str) -> Path:
    relative = request_path.removeprefix("/runs/")
    candidate = (runs_dir / relative).resolve()
    runs_resolved = runs_dir.resolve()
    if runs_resolved not in candidate.parents and candidate != runs_resolved:
        raise ValueError("path escapes runs directory")
    return candidate


def _guess_content_type(path: Path) -> str:
    ctype, _ = mimetypes.guess_type(str(path))
    return ctype or "application/octet-stream"


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
