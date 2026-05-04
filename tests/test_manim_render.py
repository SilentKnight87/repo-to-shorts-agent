from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from repo_to_shorts.manim_render import (
    _active_caption_chunk,
    _caption_chunks,
    _fit_caption_lines,
    generate_manim_script,
    render_scene,
)


def test_generate_manim_script_returns_valid_descriptor(tmp_path: Path):
    scene = {"scenes": [{"type": "title_reveal", "duration": 3.0}]}
    repo_analysis = {"name": "test-repo", "description": "A test repo", "components": ["a", "b"]}
    output_dir = tmp_path / "out"

    script_path = generate_manim_script(scene, repo_analysis, output_dir)

    assert isinstance(script_path, Path)
    assert script_path.exists()
    data = json.loads(script_path.read_text(encoding="utf-8"))
    assert data["style"] == "dark-terminal"
    assert data["width"] == 1080
    assert data["height"] == 1920
    assert data["fps"] == 30
    assert data["repo_name"] == "test-repo"
    assert data["description"] == "A test repo"
    assert data["components"] == ["a", "b"]
    assert data["scenes"] == [{"type": "title_reveal", "duration": 3.0}]


def test_generate_manim_script_defaults_style(tmp_path: Path):
    scene = {"scenes": []}
    repo_analysis = {"name": "test-repo", "description": "", "components": []}
    output_dir = tmp_path / "out"

    script_path = generate_manim_script(scene, repo_analysis, output_dir, style="unknown-style")

    data = json.loads(script_path.read_text(encoding="utf-8"))
    assert data["style"] == "dark-terminal"


def test_generate_manim_script_accepts_fast_preview_fps(tmp_path: Path):
    scene = {"scenes": [], "fps": 12}
    repo_analysis = {"name": "test-repo", "description": "", "components": []}

    script_path = generate_manim_script(scene, repo_analysis, tmp_path / "out")

    data = json.loads(script_path.read_text(encoding="utf-8"))
    assert data["fps"] == 12


def test_generate_manim_script_filters_secret_key_files(tmp_path: Path):
    scene = {"scenes": [], "fps": 30}
    repo_analysis = {
        "name": "test-repo",
        "description": "Test",
        "components": [],
        "key_files": [".env", "src/app.py", "id_rsa", "docs/README.md"],
    }

    script_path = generate_manim_script(scene, repo_analysis, tmp_path / "out")

    data = json.loads(script_path.read_text(encoding="utf-8"))
    assert data["key_files"] == ["src/app.py", "docs/README.md"]


def test_generate_manim_script_keeps_common_repo_layout_key_files(tmp_path: Path):
    scene = {"scenes": [], "fps": 30}
    repo_analysis = {
        "name": "test-repo",
        "description": "Test",
        "components": [],
        "key_files": ["app/main.py", "frontend/App.tsx", "Cargo.toml", ".env", "id_rsa"],
    }

    script_path = generate_manim_script(scene, repo_analysis, tmp_path / "out")

    data = json.loads(script_path.read_text(encoding="utf-8"))
    assert data["key_files"] == ["app/main.py", "frontend/App.tsx", "Cargo.toml"]


def test_caption_chunks_create_karaoke_phrases():
    chunks = _caption_chunks("This repo turns source code into a launch film with proof", words_per_chunk=3)

    assert chunks == [
        "This repo turns",
        "source code into",
        "a launch film",
        "with proof",
    ]


def test_active_caption_chunk_advances_with_scene_time():
    text = "This repo turns source code into a launch film with proof"

    assert _active_caption_chunk(text, 0.0)[0] == "This repo turns"
    assert _active_caption_chunk(text, 0.5)[0] == "a launch film"
    assert _active_caption_chunk(text, 1.0)[0] == "with proof"


def test_fit_caption_lines_keeps_long_chunks_inside_safe_width():
    pytest.importorskip("PIL")
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (1080, 1920))
    draw = ImageDraw.Draw(image)
    lines, font = _fit_caption_lines(draw, "the product works. the story doesn't.", 828)

    assert 1 <= len(lines) <= 2
    assert all(draw.textlength(line, font=font) <= 828 for line in lines)


def test_render_scene_creates_mp4(monkeypatch, tmp_path: Path):
    pytest.importorskip("PIL")
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        output = Path(command[-1])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"fake mp4")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(
        "repo_to_shorts.manim_render.shutil.which",
        lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else None,
    )
    monkeypatch.setattr("repo_to_shorts.manim_render.subprocess.run", fake_run)

    scene = {"scenes": [{"type": "title_reveal", "duration": 0.1}]}
    repo_analysis = {"name": "test-repo", "description": "Test", "components": []}
    output_dir = tmp_path / "out"
    script_path = generate_manim_script(scene, repo_analysis, output_dir)

    result = render_scene(script_path, output_dir)

    assert isinstance(result, Path)
    assert result.name == "demo.mp4"
    assert result.exists()

    ffmpeg_commands = [cmd for cmd in commands if cmd and cmd[0] == "ffmpeg"]
    assert len(ffmpeg_commands) >= 1
    encode_cmd = ffmpeg_commands[-1]
    assert "-framerate" in encode_cmd
    assert "-pix_fmt" in encode_cmd
    assert "yuv420p" in encode_cmd
    assert "-c:v" in encode_cmd
    assert "libx264" in encode_cmd
    assert "-movflags" in encode_cmd
    assert "+faststart" in encode_cmd


def test_render_scene_with_empty_scenes(monkeypatch, tmp_path: Path):
    calls = []

    def fake_render_scene_frames(*, scene, start_index, fps, **kwargs):
        calls.append(scene)
        return start_index + int(float(scene.get("duration", 3.0)) * fps)

    def fake_run(command, **kwargs):
        output = Path(command[-1])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"fake mp4")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(
        "repo_to_shorts.manim_render.shutil.which",
        lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else None,
    )
    monkeypatch.setattr("repo_to_shorts.manim_render.subprocess.run", fake_run)
    monkeypatch.setattr("repo_to_shorts.manim_render._render_scene_frames", fake_render_scene_frames)

    scene = {"scenes": []}
    repo_analysis = {"name": "test-repo", "description": "Test", "components": []}
    output_dir = tmp_path / "out"
    script_path = generate_manim_script(scene, repo_analysis, output_dir)

    result = render_scene(script_path, output_dir)

    assert result.exists()
    assert [c["type"] for c in calls] == ["title_reveal", "component_boxes", "summary"]
