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
        assert 'name="render_mp4"' in html

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
                "render": {"mode": "mp4", "renderer": "pillow+ffmpeg-enhanced"},
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
                "render": {"status": "success"},
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
            }).encode()
            req = urllib.request.Request(f"http://127.0.0.1:{port}/generate", data=data, method="POST")
            with urllib.request.urlopen(req) as resp:
                assert resp.status == 200
                body = resp.read().decode()
                assert "Generation complete" in body
                assert "Creative brief" in body
        finally:
            _stop_server(server)

        assert len(creative_calls) == 1
        assert len(analyze_calls) == 0
        assert creative_calls[0]["target"] == "https://github.com/owner/repo"

    def test_generate_classic_mode_when_creative_unchecked(self, tmp_path: Path, monkeypatch):
        analyze_calls = []

        def fake_run_analysis(target, audience, out_dir, **kwargs):
            analyze_calls.append({"target": target, "audience": audience, "out_dir": out_dir, **kwargs})
            run_dir = tmp_path / "20260503-092819-fake-repo"
            run_dir.mkdir(parents=True, exist_ok=True)
            metadata = {
                "artifacts": ["demo.html", "metadata.json"],
                "kimi": {"mode": "deterministic-fallback"},
                "render": {"status": "skipped"},
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
