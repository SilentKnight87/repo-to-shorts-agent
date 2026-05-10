from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from repo_to_shorts.cli import app
from repo_to_shorts.ingest import RepoSnapshot, ingest_target
from repo_to_shorts.pipeline import build_story, render_demo_html, run_analysis


def make_sample_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "sample-repo"
    repo.mkdir()
    (repo / "README.md").write_text(
        "# Sample Repo\n\nA tiny agent that turns repositories into short-video launch packages.\n",
        encoding="utf-8",
    )
    (repo / "pyproject.toml").write_text(
        "[project]\nname = 'sample-repo'\nversion = '1.2.3'\ndescription = 'Demo package'\n",
        encoding="utf-8",
    )
    src = repo / "src" / "sample"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text("__version__ = '1.2.3'\n", encoding="utf-8")
    (src / "cli.py").write_text("def main():\n    return 'ok'\n", encoding="utf-8")
    noisy = repo / ".ruff_cache" / "0.15.12"
    noisy.mkdir(parents=True)
    (noisy / "cache").write_text("noise", encoding="utf-8")
    generated = repo / "runs" / "old-run"
    generated.mkdir(parents=True)
    (generated / "demo.html").write_text("noise", encoding="utf-8")
    return repo


def test_ingest_local_repo_extracts_readme_tree_metadata_and_git_state(tmp_path: Path):
    repo = make_sample_repo(tmp_path)

    snapshot = ingest_target(str(repo))

    assert snapshot.name == "sample-repo"
    assert snapshot.source_type == "local"
    assert "tiny agent" in snapshot.readme
    assert "src/sample/cli.py" in snapshot.file_tree
    assert not any(entry.startswith(".ruff_cache/") for entry in snapshot.file_tree)
    assert not any(entry.startswith("runs/") for entry in snapshot.file_tree)
    assert snapshot.package_metadata["name"] == "sample-repo"
    assert snapshot.package_metadata["version"] == "1.2.3"
    assert snapshot.git_log == "Git history unavailable."
    assert snapshot.git_diff == "No git diff available."


def test_ingest_github_url_uses_shallow_clone_then_snapshots_repo(tmp_path: Path, monkeypatch):
    source_root = tmp_path / "source"
    source_root.mkdir()
    source = make_sample_repo(source_root)
    clone_commands = []

    def fake_run(command, **kwargs):
        if command[:3] == ["git", "clone", "--depth"]:
            clone_commands.append(command)
            destination = Path(command[-1])
            destination.mkdir(parents=True)
            for item in source.iterdir():
                if item.is_dir():
                    import shutil

                    shutil.copytree(item, destination / item.name)
                else:
                    (destination / item.name).write_text(item.read_text(encoding="utf-8"), encoding="utf-8")
            return type("Result", (), {"stdout": "", "stderr": ""})()
        raise RuntimeError("unexpected command")

    monkeypatch.setattr("repo_to_shorts.ingest.subprocess.run", fake_run)
    monkeypatch.setattr("repo_to_shorts.ingest.shutil.which", lambda name: None)

    snapshot = ingest_target("https://github.com/SilentKnight87/sample-repo.git")

    assert snapshot.source_type == "github"
    assert snapshot.name == "sample-repo"
    assert "src/sample/cli.py" in snapshot.file_tree
    assert clone_commands[0][:4] == ["git", "clone", "--depth", "1"]


def test_run_analysis_writes_launch_ready_artifact_set(tmp_path: Path):
    repo = make_sample_repo(tmp_path)
    out = tmp_path / "runs"

    run_dir = run_analysis(str(repo), audience="Python builders", out_dir=out, force=False)

    expected = {
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
    }
    assert expected == {path.name for path in run_dir.iterdir() if path.is_file()}
    metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["audience"] == "Python builders"
    assert metadata["target"] == str(repo)
    assert metadata["kimi"] == {
        "mode": "deterministic-fallback",
        "model": None,
        "provider": "none",
        "fallback_reason": "OPENROUTER_API_KEY or KIMI_API_KEY not set",
    }
    assert "Sample Repo" in (run_dir / "repo_brief.md").read_text(encoding="utf-8")
    assert "Kimi critic" in (run_dir / "kimi_critique.md").read_text(encoding="utf-8")
    assert metadata["render"] == {"mode": "none", "status": "skipped", "renderer": None, "output": None, "scene_count": 0, "error": None}
    demo_html = (run_dir / "demo.html").read_text(encoding="utf-8")
    assert "<!doctype html>" in demo_html.lower()
    assert "9:16 recordable demo page" in demo_html
    assert "60-second recording timeline" in demo_html
    assert demo_html.count('class="scene"') == 5


def test_run_analysis_with_mp4_render_adds_demo_mp4_and_metadata(tmp_path: Path, monkeypatch):
    repo = make_sample_repo(tmp_path)
    out = tmp_path / "runs"

    def fake_render_hyperframes_video(run_dir, scenes, package):
        output = Path(run_dir) / "demo.mp4"
        output.write_bytes(b"fake mp4")
        (Path(run_dir) / "hyperframes").mkdir()
        (Path(run_dir) / "hyperframes" / "index.html").write_text("<!doctype html>", encoding="utf-8")
        return type(
            "RenderResult",
            (),
            {"output_path": output, "mode": "mp4", "renderer": "hyperframes", "scene_count": len(scenes), "error": None},
        )()

    monkeypatch.setattr("repo_to_shorts.pipeline.render_hyperframes_video", fake_render_hyperframes_video)

    run_dir = run_analysis(str(repo), audience="Python builders", out_dir=out, render="mp4")

    assert (run_dir / "demo.mp4").exists()
    metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
    assert "demo.mp4" in metadata["artifacts"]
    assert "hyperframes/index.html" in metadata["artifacts"]
    assert metadata["render"] == {
        "mode": "mp4",
        "status": "success",
        "renderer": "hyperframes",
        "output": "demo.mp4",
        "scene_count": 5,
        "error": None,
    }


def test_run_analysis_with_heygen_preview_adds_preview_artifacts_and_metadata(tmp_path: Path, monkeypatch):
    repo = make_sample_repo(tmp_path)
    out = tmp_path / "runs"

    def fake_render_heygen_preview_video(run_dir, scenes, package):
        output = Path(run_dir) / "heygen-preview.mp4"
        output.write_bytes(b"fake heygen preview")
        (Path(run_dir) / "heygen-preview").mkdir()
        (Path(run_dir) / "heygen-preview" / "index.html").write_text("<!doctype html>", encoding="utf-8")
        return type(
            "RenderResult",
            (),
            {"output_path": output, "mode": "mp4", "renderer": "heygen-preview", "scene_count": len(scenes), "error": None},
        )()

    monkeypatch.setattr("repo_to_shorts.pipeline.render_heygen_preview_video", fake_render_heygen_preview_video)

    run_dir = run_analysis(str(repo), audience="Python builders", out_dir=out, render="heygen-preview")

    assert (run_dir / "heygen-preview.mp4").exists()
    metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
    assert "heygen-preview.mp4" in metadata["artifacts"]
    assert "heygen-preview/index.html" in metadata["artifacts"]
    assert metadata["render"] == {
        "mode": "mp4",
        "status": "success",
        "renderer": "heygen-preview",
        "output": "heygen-preview.mp4",
        "scene_count": 5,
        "error": None,
    }


def test_run_analysis_with_failed_mp4_render_keeps_core_artifacts_and_records_failure(tmp_path: Path, monkeypatch):
    repo = make_sample_repo(tmp_path)
    out = tmp_path / "runs"

    def fake_render_hyperframes_video(run_dir, scenes, package):
        raise RuntimeError("hyperframes exploded")

    monkeypatch.setattr("repo_to_shorts.pipeline.render_hyperframes_video", fake_render_hyperframes_video)

    run_dir = run_analysis(str(repo), audience="Python builders", out_dir=out, render="mp4")

    assert (run_dir / "demo.html").exists()
    assert not (run_dir / "demo.mp4").exists()
    metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
    assert "demo.mp4" not in metadata["artifacts"]
    assert metadata["render"] == {
        "mode": "mp4",
        "status": "failed",
        "renderer": "hyperframes",
        "output": None,
        "scene_count": 5,
        "error": "hyperframes exploded",
    }


def test_run_analysis_rejects_invalid_render_mode(tmp_path: Path):
    repo = make_sample_repo(tmp_path)

    try:
        run_analysis(str(repo), audience="Python builders", out_dir=tmp_path / "runs", render="gif")
    except ValueError as exc:
        assert "render" in str(exc)
    else:
        raise AssertionError("expected invalid render mode to fail")


def test_render_demo_html_escapes_untrusted_repo_story_audience_and_kimi_content(tmp_path: Path):
    snapshot = RepoSnapshot(
        target="malicious",
        name="<img src=x onerror=alert('name')>",
        source_type="local",
        path=tmp_path,
        readme="# Intro\n\nREADME-derived <svg onload=alert('readme')> story.",
        file_tree=[],
        package_metadata={},
    )
    audience = "<script>alert('audience')</script>"
    kimi = "Kimi says <iframe srcdoc='<script>alert(1)</script>'></iframe>"
    package = build_story(snapshot, audience)

    demo_html = render_demo_html(snapshot, audience, package, "", "", kimi)

    for raw in (
        "<img src=x onerror=alert('name')>",
        "README-derived <svg onload=alert('readme')> story",
        "<script>alert('audience')</script>",
        "<iframe srcdoc='<script>alert(1)</script>'></iframe>",
    ):
        assert raw not in demo_html
    assert "&lt;img src=x onerror=alert" in demo_html
    assert "README-derived &lt;svg onload=alert" in demo_html
    assert "&lt;script&gt;alert" in demo_html
    assert "&lt;iframe srcdoc=" in demo_html


def test_cli_analyze_smoke_writes_artifacts_to_requested_out_dir(tmp_path: Path, monkeypatch):
    repo = make_sample_repo(tmp_path)
    out = tmp_path / "custom-runs"
    runner = CliRunner()

    def fake_render_hyperframes_video(run_dir, scenes, package):
        output = Path(run_dir) / "demo.mp4"
        output.write_bytes(b"fake mp4")
        return type(
            "RenderResult",
            (),
            {"output_path": output, "mode": "mp4", "renderer": "hyperframes", "scene_count": len(scenes), "error": None},
        )()

    monkeypatch.setattr("repo_to_shorts.pipeline.render_hyperframes_video", fake_render_hyperframes_video)

    result = runner.invoke(
        app,
        [
            "analyze",
            str(repo),
            "--audience",
            "hackathon judges",
            "--out",
            str(out),
            "--kimi-model",
            "moonshotai/kimi-k2.6",
            "--render",
            "mp4",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Created run:" in result.output
    run_dirs = list(out.iterdir())
    assert len(run_dirs) == 1
    assert (run_dirs[0] / "demo.html").exists()
    assert (run_dirs[0] / "metadata.json").exists()
    assert "MP4:" in result.output
