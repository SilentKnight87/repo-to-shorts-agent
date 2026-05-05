from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import HTTPServer
from pathlib import Path

import pytest

from repo_to_shorts import web as web_module
from repo_to_shorts.web import (
    _make_handler,
    list_runs,
    render_home_page,
    resolve_run_file,
    run_web_server,
)


def _start_server(runs_dir: Path, port: int = 0):
    handler = _make_handler(runs_dir)
    server = HTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, server.server_address[1]


def _stop_server(server: HTTPServer) -> None:
    server.shutdown()
    server.server_close()


class TestHealthz:
    def test_get_healthz_returns_ok(self, tmp_path: Path):
        server, port = _start_server(tmp_path)
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz") as resp:
                assert resp.status == 200
                data = json.loads(resp.read())
                assert data == {"ok": True}
        finally:
            _stop_server(server)


class TestHomePage:
    def test_home_page_includes_form_fields(self):
        html = render_home_page([])
        assert "Repo-to-Shorts Agent" in html
        assert 'name="target"' in html
        assert 'name="audience"' in html
        assert 'name="kimi_model"' in html
        assert 'data-flag="render_mp4"' in html
        assert 'name="preview"' in html
        assert 'name="skip_audio"' in html

    def test_home_page_uses_new_vhs_components(self):
        html = render_home_page([])
        # Identity & framing
        assert 'class="slate"' in html
        assert "colorbars" in html
        assert "tape-edge" in html
        # Hero
        assert "glitch-headline" in html
        assert "kicker" in html
        # Form deck
        assert 'id="generate-form"' in html
        assert 'method="POST"' in html
        assert 'action="/generate"' in html
        assert "tape-input" in html
        assert "btn-tape" in html
        assert "toggle-mode" in html
        # Generating-state takeover (hidden by default, populated by JS)
        assert "deck-broadcasting" in html
        assert "channel-row" in html
        assert 'data-stage="ingest"' in html
        assert 'data-stage="render_frames"' in html
        assert "vu-meter" in html
        # Bottom
        assert "scope-strip" in html

    def test_home_page_toggle_clusters_have_js_contract(self):
        html = render_home_page([])
        assert 'class="toggle-mode" data-toggle="tape-mode"' in html
        assert 'class="toggle-mode" data-toggle="audio-mode"' in html
        assert 'data-flag="final"' in html

    def test_home_page_loads_static_assets_not_inline(self):
        html = render_home_page([])
        # New external assets
        assert 'href="/static/style.css"' in html
        assert 'src="/static/app.js"' in html
        # Old inline blobs are gone
        assert "addEventListener" not in html
        assert "HTMLFormElement.prototype.submit" not in html
        assert ".loading-panel { display: none" not in html

    def test_home_page_tape_archive_renders_runs(self, tmp_path: Path):
        run1 = tmp_path / "20260503-092819-repo-to-shorts-agent"
        run1.mkdir()
        (run1 / "demo.html").write_text("demo")
        runs = list_runs(tmp_path, limit=10)
        html = render_home_page(runs)
        assert "TAPE ARCHIVE" in html
        assert "tape-label" in html
        assert "20260503-092819-repo-to-shorts-agent" in html

    def test_home_page_shows_latest_runs(self, tmp_path: Path):
        run1 = tmp_path / "20260503-092819-repo-to-shorts-agent"
        run1.mkdir()
        (run1 / "demo.html").write_text("demo")
        runs = list_runs(tmp_path, limit=10)
        html = render_home_page(runs)
        assert "20260503-092819-repo-to-shorts-agent" in html
        assert 'href="/runs/20260503-092819-repo-to-shorts-agent/demo.html"' in html

    def test_home_page_via_get(self, tmp_path: Path):
        server, port = _start_server(tmp_path)
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as resp:
                assert resp.status == 200
                body = resp.read().decode()
                assert "Repo-to-Shorts Agent" in body
        finally:
            _stop_server(server)


class TestGenerate:
    def test_generate_passes_correct_args(self, tmp_path: Path, monkeypatch):
        calls = []

        def fake_run_analysis(target, audience, out_dir, **kwargs):
            calls.append({"target": target, "audience": audience, "out_dir": out_dir, **kwargs})
            run_dir = tmp_path / "20260503-092819-fake-repo"
            run_dir.mkdir(parents=True, exist_ok=True)
            metadata = {
                "artifacts": ["demo.html", "metadata.json", "kimi_critique.md"],
                "kimi": {"mode": "live-api"},
                "render": {"status": "success"},
            }
            (run_dir / "metadata.json").write_text(json.dumps(metadata))
            return run_dir

        monkeypatch.setattr(web_module, "run_analysis", fake_run_analysis)

        server, port = _start_server(tmp_path)
        try:
            data = urllib.parse.urlencode({
                "target": "https://github.com/owner/repo",
                "audience": "hackathon judges",
                "kimi_model": "moonshotai/kimi-k2.6",
                "render_mp4": "on",
            }).encode()
            req = urllib.request.Request(f"http://127.0.0.1:{port}/generate", data=data, method="POST")
            with urllib.request.urlopen(req) as resp:
                assert resp.status == 200
                body = resp.read().decode()
                assert "Generation complete" in body
        finally:
            _stop_server(server)

        assert len(calls) == 1
        assert calls[0]["target"] == "https://github.com/owner/repo"
        assert calls[0]["audience"] == "hackathon judges"
        assert calls[0]["kimi_model"] == "moonshotai/kimi-k2.6"
        assert calls[0]["render"] == "mp4"

    def test_generate_empty_target_returns_400(self, tmp_path: Path):
        server, port = _start_server(tmp_path)
        try:
            data = urllib.parse.urlencode({"target": ""}).encode()
            req = urllib.request.Request(f"http://127.0.0.1:{port}/generate", data=data, method="POST")
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                urllib.request.urlopen(req)
            assert exc_info.value.code == 400
        finally:
            _stop_server(server)

    def test_generate_creative_mode(self, tmp_path: Path, monkeypatch):
        creative_calls = []
        analyze_calls = []

        def fake_run_creative_pipeline(target, audience, out_dir, **kwargs):
            creative_calls.append({"target": target, "audience": audience, "out_dir": out_dir, **kwargs})
            run_dir = tmp_path / "20260503-092819-fake-repo"
            run_dir.mkdir(parents=True, exist_ok=True)
            metadata = {
                "artifacts": ["demo.mp4", "metadata.json"],
                "kimi": {"mode": "live-api"},
                "render": {"mode": "mp4", "renderer": "pillow+ffmpeg-enhanced", "preview": True, "final": False, "validation": {"ok": True, "errors": []}},
                "creative_brief": {"style": "dark-terminal", "title": "Test", "hook": "Hook", "scenes": []},
            }
            (run_dir / "metadata.json").write_text(json.dumps(metadata))
            return {"output": str(run_dir / "demo.mp4"), "run_dir": str(run_dir)}

        def fake_run_analysis(target, audience, out_dir, **kwargs):
            analyze_calls.append({"target": target, "audience": audience, "out_dir": out_dir, **kwargs})
            run_dir = tmp_path / "20260503-092819-fake-repo"
            run_dir.mkdir(parents=True, exist_ok=True)
            metadata = {
                "artifacts": ["demo.html", "metadata.json"],
                "kimi": {"mode": "live-api"},
                "render": {"status": "success", "preview": False, "final": False, "validation": {"ok": True, "errors": []}},
            }
            (run_dir / "metadata.json").write_text(json.dumps(metadata))
            return run_dir

        monkeypatch.setattr(web_module, "run_analysis", fake_run_analysis)
        monkeypatch.setattr("repo_to_shorts.hermes_skill.run_creative_pipeline", fake_run_creative_pipeline)

        server, port = _start_server(tmp_path)
        try:
            data = urllib.parse.urlencode({
                "target": "https://github.com/owner/repo",
                "audience": "hackathon judges",
                "kimi_model": "moonshotai/kimi-k2.6",
                "creative_mode": "on",
                "preview": "on",
                "skip_audio": "on",
            }).encode()
            req = urllib.request.Request(f"http://127.0.0.1:{port}/generate", data=data, method="POST")
            with urllib.request.urlopen(req) as resp:
                assert resp.status == 200
                body = resp.read().decode()
                assert "PREVIEW DRAFT" in body
                assert "BROADCAST CUE SHEET" in body
        finally:
            _stop_server(server)

        assert len(creative_calls) == 1
        assert len(analyze_calls) == 0
        assert creative_calls[0]["target"] == "https://github.com/owner/repo"
        assert creative_calls[0]["preview"] is True
        assert creative_calls[0]["skip_audio"] is True

    def test_generate_classic_mode_when_creative_unchecked(self, tmp_path: Path, monkeypatch):
        analyze_calls = []

        def fake_run_analysis(target, audience, out_dir, **kwargs):
            analyze_calls.append({"target": target, "audience": audience, "out_dir": out_dir, **kwargs})
            run_dir = tmp_path / "20260503-092819-fake-repo"
            run_dir.mkdir(parents=True, exist_ok=True)
            metadata = {
                "artifacts": ["demo.html", "metadata.json"],
                "kimi": {"mode": "deterministic-fallback"},
                "render": {"status": "skipped", "preview": False, "final": False, "validation": {"ok": True, "errors": []}},
            }
            (run_dir / "metadata.json").write_text(json.dumps(metadata))
            return run_dir

        monkeypatch.setattr(web_module, "run_analysis", fake_run_analysis)

        server, port = _start_server(tmp_path)
        try:
            # creative_mode NOT included in form data
            data = urllib.parse.urlencode({
                "target": "local/path",
                "audience": "technical builders",
                "kimi_model": "moonshotai/kimi-k2.6",
            }).encode()
            req = urllib.request.Request(f"http://127.0.0.1:{port}/generate", data=data, method="POST")
            with urllib.request.urlopen(req) as resp:
                assert resp.status == 200
        finally:
            _stop_server(server)

        assert len(analyze_calls) == 1
        assert analyze_calls[0]["render"] == "none"


class TestSuccessPage:
    def test_success_page_labels_broadcast_complete_for_ok_final(self):
        from repo_to_shorts.web import render_success_page

        html = render_success_page(Path("/tmp/fake"), {
            "artifacts": ["demo.mp4"],
            "kimi": {"mode": "live-api"},
            "render": {"mode": "mp4", "final": True, "preview": False, "validation": {"ok": True, "errors": []}},
            "creative_brief": {"title": "Final", "hook": "Final hook", "scenes": []},
        })
        assert "// BROADCAST COMPLETE" in html
        assert "VALIDATION FAILED" not in html
        assert "PREVIEW DRAFT" not in html

    def test_success_page_labels_preview_draft(self):
        from repo_to_shorts.web import render_success_page

        html = render_success_page(Path("/tmp/fake"), {
            "artifacts": ["demo.mp4"],
            "kimi": {"mode": "live-api"},
            "render": {"mode": "mp4", "preview": True, "final": False, "validation": {"ok": True, "errors": []}},
            "creative_brief": {"title": "Draft", "hook": "Draft hook", "scenes": []},
        })
        assert "// PREVIEW DRAFT" in html
        assert "VALIDATION FAILED" not in html
        assert "BROADCAST COMPLETE" not in html

    def test_success_page_labels_validation_failed_when_not_ok(self):
        from repo_to_shorts.web import render_success_page

        html = render_success_page(Path("/tmp/fake"), {
            "artifacts": ["demo.mp4"],
            "kimi": {"mode": "deterministic-fallback"},
            "render": {"mode": "mp4", "preview": True, "final": False, "validation": {"ok": False, "errors": ["duration must be 43-62 seconds"]}},
            "creative_brief": {"title": "Draft", "hook": "Draft hook", "scenes": []},
        })
        assert "// VALIDATION FAILED" in html
        assert "duration must be 43-62 seconds" in html
        assert "BROADCAST COMPLETE" not in html

    def test_success_page_labels_package_complete_for_non_creative_runs(self):
        from repo_to_shorts.web import render_success_page

        html = render_success_page(Path("/tmp/fake"), {
            "artifacts": ["demo.html"],
            "kimi": {"mode": "deterministic-fallback"},
            "render": {"final": False, "preview": False, "validation": {"ok": True}},
            "creative_brief": {"title": "Package", "hook": "Package hook", "scenes": []},
        })
        assert "// PACKAGE COMPLETE" in html


class TestGenerateFinalMode:
    def test_generate_creative_final_mode_passes_final_flag_in_form(self, tmp_path: Path, monkeypatch):
        calls = []

        def fake_run_creative_pipeline(target, audience, out_dir, **kwargs):
            calls.append(kwargs)
            run_dir = tmp_path / "20260504-final"
            run_dir.mkdir(parents=True, exist_ok=True)
            metadata = {
                "artifacts": ["demo.mp4", "metadata.json"],
                "kimi": {"mode": "live-api"},
                "render": {"mode": "mp4", "final": True, "validation": {"ok": True, "errors": []}},
                "creative_brief": {"title": "Final", "hook": "Final hook", "scenes": []},
            }
            (run_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
            (run_dir / "demo.mp4").write_bytes(b"mp4")
            return {"output": str(run_dir / "demo.mp4"), "run_dir": str(run_dir)}

        monkeypatch.setattr("repo_to_shorts.hermes_skill.run_creative_pipeline", fake_run_creative_pipeline)

        server, port = _start_server(tmp_path)
        try:
            data = urllib.parse.urlencode({
                "target": ".",
                "audience": "builders",
                "kimi_model": "moonshotai/kimi-k2.6",
                "creative_mode": "on",
                "final": "on",
            }).encode()
            req = urllib.request.Request(f"http://127.0.0.1:{port}/generate", data=data, method="POST")
            with urllib.request.urlopen(req) as resp:
                assert resp.status == 200
        finally:
            _stop_server(server)

        assert calls[0]["final"] is True
        assert calls[0]["preview"] is False

    def test_generate_creative_final_mode_maps_skip_audio_to_no_tts(self, tmp_path: Path, monkeypatch):
        calls = []

        def fake_run_creative_pipeline(target, audience, out_dir, **kwargs):
            calls.append(kwargs)
            run_dir = tmp_path / "20260504-final"
            run_dir.mkdir(parents=True, exist_ok=True)
            metadata = {
                "artifacts": ["demo.mp4", "metadata.json"],
                "kimi": {"mode": "live-api"},
                "render": {"mode": "mp4", "final": True, "validation": {"ok": True, "errors": []}},
                "creative_brief": {"title": "Final", "hook": "Final hook", "scenes": []},
            }
            (run_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
            (run_dir / "demo.mp4").write_bytes(b"mp4")
            return {"output": str(run_dir / "demo.mp4"), "run_dir": str(run_dir)}

        monkeypatch.setattr("repo_to_shorts.hermes_skill.run_creative_pipeline", fake_run_creative_pipeline)

        server, port = _start_server(tmp_path)
        try:
            data = urllib.parse.urlencode({
                "target": ".",
                "audience": "builders",
                "kimi_model": "moonshotai/kimi-k2.6",
                "creative_mode": "on",
                "final": "on",
                "skip_audio": "on",
            }).encode()
            req = urllib.request.Request(f"http://127.0.0.1:{port}/generate", data=data, method="POST")
            with urllib.request.urlopen(req) as resp:
                assert resp.status == 200
        finally:
            _stop_server(server)

        assert calls[0]["skip_audio"] is True
        assert calls[0]["tts_provider"] == "none"

    def test_generate_creative_final_mode_shows_broadcast_complete(self, tmp_path: Path, monkeypatch):
        def fake_run_creative_pipeline(target, audience, out_dir, **kwargs):
            run_dir = tmp_path / "20260504-final"
            run_dir.mkdir(parents=True, exist_ok=True)
            metadata = {
                "artifacts": ["demo.mp4", "metadata.json"],
                "kimi": {"mode": "live-api"},
                "render": {"mode": "mp4", "final": True, "preview": False, "validation": {"ok": True, "errors": []}},
                "creative_brief": {"title": "Final", "hook": "Final hook", "scenes": []},
            }
            (run_dir / "metadata.json").write_text(json.dumps(metadata))
            (run_dir / "demo.mp4").write_bytes(b"mp4")
            return {"output": str(run_dir / "demo.mp4"), "run_dir": str(run_dir)}

        monkeypatch.setattr("repo_to_shorts.hermes_skill.run_creative_pipeline", fake_run_creative_pipeline)

        server, port = _start_server(tmp_path)
        try:
            data = urllib.parse.urlencode({
                "target": ".",
                "audience": "builders",
                "kimi_model": "moonshotai/kimi-k2.6",
                "creative_mode": "on",
                "final": "on",
            }).encode()
            req = urllib.request.Request(f"http://127.0.0.1:{port}/generate", data=data, method="POST")
            with urllib.request.urlopen(req) as resp:
                assert resp.status == 200
                body = resp.read().decode()
                assert "// BROADCAST COMPLETE" in body
                assert "VALIDATION FAILED" not in body
        finally:
            _stop_server(server)


class TestPathTraversal:
    def test_path_traversal_is_rejected(self, tmp_path: Path):
        with pytest.raises(ValueError, match="path escapes"):
            resolve_run_file(tmp_path, "/runs/../secret")

    def test_valid_run_file_resolves(self, tmp_path: Path):
        run_dir = tmp_path / "my-run"
        run_dir.mkdir()
        file_path = run_dir / "demo.html"
        file_path.write_text("demo")
        resolved = resolve_run_file(tmp_path, "/runs/my-run/demo.html")
        assert resolved == file_path.resolve()

    def test_nonexistent_file_returns_404(self, tmp_path: Path):
        server, port = _start_server(tmp_path)
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/runs/my-run/missing.html")
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                urllib.request.urlopen(req)
            assert exc_info.value.code == 404
        finally:
            _stop_server(server)

    def test_directory_access_returns_404(self, tmp_path: Path):
        run_dir = tmp_path / "my-run"
        run_dir.mkdir()
        server, port = _start_server(tmp_path)
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/runs/my-run")
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                urllib.request.urlopen(req)
            assert exc_info.value.code == 404
        finally:
            _stop_server(server)


class TestStaticFiles:
    def test_static_serves_css(self, tmp_path: Path):
        server, port = _start_server(tmp_path)
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/static/style.css") as resp:
                assert resp.status == 200
                assert resp.headers["Content-Type"].startswith("text/css")
                body = resp.read().decode()
                assert ":root" in body
                assert "--bg" in body
        finally:
            _stop_server(server)

    def test_static_serves_js(self, tmp_path: Path):
        server, port = _start_server(tmp_path)
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/static/app.js") as resp:
                assert resp.status == 200
                # mimetypes maps .js to application/javascript or text/javascript per platform
                assert "javascript" in resp.headers["Content-Type"].lower()
        finally:
            _stop_server(server)

    def test_static_serves_fonts(self, tmp_path: Path):
        server, port = _start_server(tmp_path)
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/static/fonts/Anton-Regular.woff2"
            ) as resp:
                assert resp.status == 200
                assert resp.headers["Content-Type"] == "font/woff2"
        finally:
            _stop_server(server)

    def test_static_traversal_blocked(self, tmp_path: Path):
        server, port = _start_server(tmp_path)
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/static/../web.py")
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                urllib.request.urlopen(req)
            assert exc_info.value.code == 404
        finally:
            _stop_server(server)


class TestErrorPage:
    def test_error_page_uses_new_vhs_classes(self):
        from repo_to_shorts.web import render_error_page

        html = render_error_page("boom", 500)
        assert "glitch-headline" in html
        assert "data-rotate-error" in html
        assert "tape-edge" in html
        # Default headline before JS rotation; one of the rotating set
        assert any(
            phrase in html
            for phrase in (
                "TRACKING ERROR",
                "TAPE ATE THE REEL",
                "SIGNAL LOST",
                "DROPOUT",
                "BAD HEAD",
            )
        )
        assert "boom" in html


class TestRunWebServer:
    def test_run_web_server_accepts_runs_dir(self, tmp_path: Path, monkeypatch):
        started = []

        def mock_init(self, address, handler):
            started.append(address)
            # Don't actually bind; just record
            self.server_address = address
            self.RequestHandlerClass = handler

        monkeypatch.setattr(HTTPServer, "__init__", mock_init)
        monkeypatch.setattr(HTTPServer, "serve_forever", lambda self: None)
        monkeypatch.setattr(HTTPServer, "server_close", lambda self: None)

        run_web_server(host="127.0.0.1", port=8765, runs_dir=tmp_path)
        assert started == [("127.0.0.1", 8765)]
