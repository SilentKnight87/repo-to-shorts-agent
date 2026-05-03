from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from repo_to_shorts.ingest import RepoSnapshot
from repo_to_shorts.pipeline import StoryPackage
from repo_to_shorts.render import (
    RenderConfig,
    VideoScene,
    build_video_scenes,
    ensure_render_runtime,
    ffmpeg_available,
    render_scene_png,
    render_video,
)


def sample_snapshot(tmp_path: Path) -> RepoSnapshot:
    return RepoSnapshot(
        target=str(tmp_path),
        name="sample-repo",
        source_type="local",
        path=tmp_path,
        readme="# Sample\n\nA repo-to-video package.",
        file_tree=["README.md", "src/app.py"],
        package_metadata={"description": "Demo package"},
        git_log="abc123 initial",
        git_diff="No git diff available.",
    )


def sample_package() -> StoryPackage:
    return StoryPackage(
        hook="A repo lands on your desk and becomes a launch-ready short.",
        promise="For hackathon judges, this turns source code into a story package.",
        beats=[
            "Ingest README, file tree, metadata, git log, and diff signals.",
            "Extract the why: Demo package.",
            "Shape a three-act technical short.",
            "Render deterministic assets without credentials.",
            "Run a Kimi critic/script-editor pass.",
        ],
        cta="Open demo.html or demo.mp4 and ship the submission.",
    )


def test_runtime_checks_report_ffmpeg_availability(monkeypatch):
    monkeypatch.setattr("repo_to_shorts.render.shutil.which", lambda name: f"/usr/bin/{name}" if name in {"ffmpeg", "ffprobe"} else None)

    assert ffmpeg_available() is True

    monkeypatch.setattr("repo_to_shorts.render.shutil.which", lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else None)
    assert ffmpeg_available() is False
    with pytest.raises(RuntimeError, match="ffprobe"):
        ensure_render_runtime()

    monkeypatch.setattr("repo_to_shorts.render.shutil.which", lambda name: None)
    assert ffmpeg_available() is False
    with pytest.raises(RuntimeError, match="ffmpeg"):
        ensure_render_runtime()


def test_render_models_have_vertical_defaults():
    scene = VideoScene(title="Hook", body="Body", footer="Footer")
    config = RenderConfig()

    assert scene.accent == "#8b5cf6"
    assert config.width == 1080
    assert config.height == 1920
    assert config.fps == 30
    assert config.seconds_per_scene == 10
    assert config.output_name == "demo.mp4"


def test_build_video_scenes_creates_bounded_five_scene_plan(tmp_path: Path):
    scenes = build_video_scenes(sample_snapshot(tmp_path), "hackathon judges", sample_package(), "Kimi critique " * 200)

    assert len(scenes) == 5
    assert any("sample-repo" in scene.title or "sample-repo" in scene.body for scene in scenes)
    assert any("Kimi" in scene.title or "Kimi" in scene.body for scene in scenes)
    assert any("Launch" in scene.title or "ship" in scene.body.lower() for scene in scenes)
    assert all(len(scene.body) <= 360 for scene in scenes)


def test_render_scene_png_writes_vertical_image(tmp_path: Path):
    pytest.importorskip("PIL")
    scene = VideoScene(title="Hook", body="Paste a repo. Get a short.", footer="Repo-to-Shorts")
    output = render_scene_png(scene, tmp_path / "frame.png", RenderConfig())

    assert output.exists()
    from PIL import Image

    with Image.open(output) as image:
        assert image.size == (1080, 1920)


def test_render_video_stitches_frames_with_ffmpeg(monkeypatch, tmp_path: Path):
    pytest.importorskip("PIL")
    commands = []

    def fake_run(command, check, capture_output, text):
        commands.append(command)
        output = Path(command[-1])
        output.write_bytes(b"fake mp4")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("repo_to_shorts.render.ensure_render_runtime", lambda: None)
    monkeypatch.setattr("repo_to_shorts.render.subprocess.run", fake_run)

    scenes = [VideoScene(title="One", body="Body"), VideoScene(title="Two", body="Body")]
    result = render_video(tmp_path, scenes, RenderConfig(seconds_per_scene=1))

    assert result.output_path == tmp_path / "demo.mp4"
    assert result.output_path.exists()
    assert result.mode == "mp4"
    assert result.renderer == "pillow+ffmpeg"
    assert result.scene_count == 2
    command = commands[0]
    assert command[0] == "ffmpeg"
    assert "libx264" in command
    assert any("format=yuv420p" in arg for arg in command)
    assert "aac" in command
