from __future__ import annotations

import html
import json
import mimetypes
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from repo_to_shorts.pipeline import run_analysis

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_RUNS_DIR = Path("runs")
DEFAULT_AUDIENCE = "technical builders"
DEFAULT_KIMI_MODEL = "moonshotai/kimi-k2.6"


def list_runs(runs_dir: Path, limit: int = 10) -> list[Path]:
    if not runs_dir.exists():
        return []
    runs = [p for p in runs_dir.iterdir() if p.is_dir()]
    runs.sort(key=lambda p: p.name, reverse=True)
    return runs[:limit]


def render_home_page(runs: list[Path], message: str | None = None) -> str:
    runs_html = ""
    for run in runs:
        artifacts = []
        for name in ("demo.html", "demo.mp4", "metadata.json", "kimi_critique.md"):
            if (run / name).exists():
                artifacts.append(
                    f'<a href="/runs/{html.escape(run.name)}/{html.escape(name)}">{html.escape(name)}</a>'
                )
        artifacts_str = " | ".join(artifacts) if artifacts else "no artifacts yet"
        runs_html += f"<li>{html.escape(run.name)}<br>{artifacts_str}</li>\n"

    message_html = f'<p style="color:green;">{html.escape(message)}</p>' if message else ""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Repo-to-Shorts Agent</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 720px; margin: 40px auto; padding: 0 20px; }}
input[type="text"] {{ width: 100%; padding: 8px; margin: 6px 0 16px; }}
button {{ padding: 10px 18px; }}
ul {{ list-style: none; padding: 0; }}
li {{ margin: 10px 0; padding: 10px; background: #f5f5f5; border-radius: 6px; }}
a {{ margin-right: 10px; }}
</style>
</head>
<body>
<h1>Repo-to-Shorts Agent</h1>
{message_html}
<form method="POST" action="/generate">
<label>Target repo or GitHub URL</label>
<input type="text" name="target" placeholder="e.g. https://github.com/owner/repo or ." required>
<label>Audience</label>
<input type="text" name="audience" value="{html.escape(DEFAULT_AUDIENCE)}">
<label>Kimi model</label>
<input type="text" name="kimi_model" value="{html.escape(DEFAULT_KIMI_MODEL)}">
<label><input type="checkbox" name="render_mp4"> Render classic MP4</label><br>
<label><input type="checkbox" name="creative_mode" checked> Creative short (animated + narrated)</label><br>
<button type="submit">Generate short package</button>
</form>
<h2>Latest runs</h2>
<ul>
{runs_html}
</ul>
<p><small>API keys come from environment variables only. Default host: 127.0.0.1</small></p>
</body>
</html>"""


def render_success_page(run_dir: Path, run_metadata: dict) -> str:
    artifacts = []
    for name in run_metadata.get("artifacts", []):
        safe_name = html.escape(name)
        artifacts.append(
            f'<li><a href="/runs/{html.escape(run_dir.name)}/{safe_name}">{safe_name}</a></li>'
        )

    kimi_info = run_metadata.get("kimi", {})
    render_info = run_metadata.get("render", {})
    brief = run_metadata.get("creative_brief", {})

    brief_html = ""
    if brief:
        scenes = brief.get("scenes", [])
        scenes_html = "\n".join(
            f'<li>{html.escape(s.get("visual_tool",""))}: {html.escape(s.get("narration",""))[:80]}...</li>'
            for s in scenes
        )
        brief_html = f"""
<h2>Creative brief ({html.escape(brief.get('style',''))})</h2>
<p><strong>Title:</strong> {html.escape(brief.get('title',''))}</p>
<p><strong>Hook:</strong> {html.escape(brief.get('hook',''))}</p>
<ol>{scenes_html}</ol>
"""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Generation complete</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 720px; margin: 40px auto; padding: 0 20px; }}
a {{ margin-right: 10px; }}
</style>
</head>
<body>
<h1>Generation complete</h1>
<p>Run: <code>{html.escape(str(run_dir))}</code></p>
<p>Kimi: {html.escape(kimi_info.get("mode", "unknown"))}</p>
<p>Render: {html.escape(render_info.get("mode", "unknown"))} / {html.escape(render_info.get("renderer", "unknown"))}</p>
{brief_html}
<ul>
{"".join(artifacts)}
</ul>
<p><a href="/">Back to home</a></p>
</body>
</html>"""


def render_error_page(message: str, status: int = 400) -> str:
    return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Error</title></head>
<body>
<h1>Error {status}</h1>
<p>{html.escape(message)}</p>
<p><a href="/">Back to home</a></p>
</body>
</html>"""


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
            # Suppress default logging to keep tests quiet
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

            if path == "/":
                runs = list_runs(runs_dir)
                body = render_home_page(runs).encode()
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

                if not target:
                    self.send_response(400)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(render_error_page("Target is required.", 400).encode())
                    return

                try:
                    if creative_mode:
                        from repo_to_shorts.hermes_skill import run_creative_pipeline
                        result = run_creative_pipeline(
                            target,
                            audience=audience,
                            out_dir=runs_dir,
                            kimi_model=kimi_model,
                        )
                        run_dir = Path(result["run_dir"])
                    else:
                        render = "mp4" if render_mp4 else "none"
                        run_dir = run_analysis(
                            target,
                            audience=audience,
                            out_dir=runs_dir,
                            kimi_model=kimi_model,
                            render=render,
                        )
                    metadata = json.loads((run_dir / "metadata.json").read_text())
                    page = render_success_page(run_dir, metadata).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(page)
                except Exception as exc:  # noqa: BLE001 - show concise error page rather than traceback.
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


def run_web_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    runs_dir: Path | str = DEFAULT_RUNS_DIR,
) -> None:
    runs_dir = Path(runs_dir)
    handler = _make_handler(runs_dir)
    server = HTTPServer((host, port), handler)
    print(f"Starting Repo-to-Shorts web UI at http://{host}:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
