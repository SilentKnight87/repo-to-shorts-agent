from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from repo_to_shorts.hermes_skill import _build_repo_analysis, _merge_creative_video, run_creative_pipeline


class FakeSnapshot:
    name = "test-repo"
    source_type = "local"
    package_metadata = {"description": "A test repo", "language": "Python"}
    file_tree = ["src/app.py", "src/core.py", "README.md"]
    readme = "# Test Repo\n\nThis is a test."


def test_build_repo_analysis():
    snapshot = FakeSnapshot()
    analysis = _build_repo_analysis(snapshot)
    assert analysis["repo_name"] == "test-repo"
    assert analysis["description"] == "A test repo"
    assert analysis["primary_language"] == "Python"
    assert "src/app.py" in analysis["key_files"]
    assert "name" in analysis


def test_build_repo_analysis_fallback_description():
    snapshot = FakeSnapshot()
    snapshot.package_metadata = {}
    analysis = _build_repo_analysis(snapshot)
    assert "This is a test" in analysis["description"]


@patch("repo_to_shorts.hermes_skill.ingest_target")
@patch("repo_to_shorts.hermes_skill.direct")
@patch("repo_to_shorts.hermes_skill.generate_manim_script")
@patch("repo_to_shorts.hermes_skill.render_scene")
@patch("repo_to_shorts.hermes_skill._merge_creative_video")
def test_run_creative_pipeline_success(
    mock_merge,
    mock_render,
    mock_script,
    mock_direct,
    mock_ingest,
    tmp_path: Path,
):
    mock_ingest.return_value = FakeSnapshot()
    mock_direct.return_value = MagicMock(
        style="dark-terminal",
        title="Test Title",
        hook="Test hook",
        scenes=[
            {"duration_seconds": 5, "visual_tool": "manim", "narration": "Scene one", "music_mood": "tension", "transition": "fade"},
            {"duration_seconds": 5, "visual_tool": "pretext", "narration": "Scene two", "music_mood": "calm", "transition": "cut"},
        ],
        music_mood="electronic",
        total_duration=10,
    )
    mock_script.return_value = tmp_path / "script.json"
    mock_render.return_value = tmp_path / "video.mp4"
    mock_merge.return_value = tmp_path / "demo.mp4"

    result = run_creative_pipeline(".", out_dir=tmp_path)

    assert "output" in result
    assert "run_dir" in result
    assert "demo.mp4" in result["output"]
    mock_ingest.assert_called_once_with(".")
    mock_direct.assert_called_once()
    mock_script.assert_called_once()
    mock_render.assert_called_once()
    mock_merge.assert_called_once()

    # Verify metadata was written
    run_dir = Path(result["run_dir"])
    metadata_path = run_dir / "metadata.json"
    assert metadata_path.exists()
    import json
    metadata = json.loads(metadata_path.read_text())
    assert metadata["creative_brief"]["style"] == "dark-terminal"
    assert metadata["creative_brief"]["title"] == "Test Title"
    assert len(metadata["creative_brief"]["scenes"]) == 2
    assert metadata["kimi"]["model"] == "moonshotai/kimi-k2.6"


@patch("repo_to_shorts.hermes_skill.generate_tts")
@patch("repo_to_shorts.hermes_skill.subprocess.run")
def test_merge_creative_video_with_narration(mock_run, mock_tts, tmp_path: Path):
    video = tmp_path / "video.mp4"
    video.write_text("fake video")
    output = tmp_path / "out.mp4"

    scenes = [
        {"narration": "Hello world", "duration_seconds": 3},
        {"narration": "Second scene", "duration_seconds": 3},
    ]

    mock_tts.return_value = tmp_path / "tts.wav"

    _merge_creative_video(video, scenes, output)

    assert mock_tts.call_count == 2
    assert mock_run.call_count >= 2  # concat + merge


@patch("repo_to_shorts.hermes_skill.subprocess.run")
def test_merge_creative_video_no_narration(mock_run, tmp_path: Path):
    video = tmp_path / "video.mp4"
    video.write_text("fake video")
    output = tmp_path / "out.mp4"

    scenes = [{"narration": "", "duration_seconds": 3}]

    _merge_creative_video(video, scenes, output)

    # Should just copy video when no narration
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "ffmpeg" in args
    assert "-c" in args or "copy" in args
