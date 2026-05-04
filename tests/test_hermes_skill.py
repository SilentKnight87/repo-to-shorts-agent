from __future__ import annotations

import json
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


def test_build_repo_analysis_filters_secret_like_paths():
    snapshot = FakeSnapshot()
    snapshot.file_tree = [
        ".env",
        ".env.local",
        "runs/20260503/demo.mp4",
        "src/app.py",
        "tests/test_app.py",
        "private_key.pem",
        "docs/PRD.md",
    ]

    analysis = _build_repo_analysis(snapshot)

    assert analysis["key_files"] == ["src/app.py", "tests/test_app.py", "docs/PRD.md"]
    assert ".env" not in str(analysis)
    assert "private_key.pem" not in str(analysis)


def test_build_repo_analysis_keeps_common_repo_layout_evidence():
    snapshot = FakeSnapshot()
    snapshot.file_tree = [
        "app/main.py",
        "lib/core.py",
        "cmd/server/main.go",
        "go.mod",
        "Dockerfile",
        ".env",
        "runs/demo.mp4",
    ]

    analysis = _build_repo_analysis(snapshot)

    assert analysis["key_files"] == [
        "app/main.py",
        "lib/core.py",
        "cmd/server/main.go",
        "go.mod",
        "Dockerfile",
    ]
    assert ".env" not in analysis["key_files"]
    assert "runs/demo.mp4" not in analysis["key_files"]


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
    metadata = json.loads(metadata_path.read_text())
    assert metadata["creative_brief"]["style"] == "dark-terminal"
    assert metadata["creative_brief"]["title"] == "Test Title"
    assert len(metadata["creative_brief"]["scenes"]) == 2
    assert metadata["kimi"]["model"] == "moonshotai/kimi-k2.6"


@patch("repo_to_shorts.hermes_skill.write_submission_pack")
@patch("repo_to_shorts.hermes_skill.validate_media")
@patch("repo_to_shorts.hermes_skill.ingest_target")
@patch("repo_to_shorts.hermes_skill.direct")
@patch("repo_to_shorts.hermes_skill.generate_manim_script")
@patch("repo_to_shorts.hermes_skill.render_scene")
@patch("repo_to_shorts.hermes_skill._merge_creative_video")
def test_run_creative_pipeline_final_writes_validation_submission_and_srt(
    mock_merge,
    mock_render,
    mock_script,
    mock_direct,
    mock_ingest,
    mock_validate,
    mock_submission,
    tmp_path: Path,
):
    mock_ingest.return_value = FakeSnapshot()
    mock_direct.return_value = MagicMock(
        style="dark-terminal",
        title="Final Title",
        hook="Final hook",
        scenes=[
            {"duration_seconds": 10, "narration": "Scene one."},
            {"duration_seconds": 10, "narration": "Scene two."},
            {"duration_seconds": 10, "narration": "Scene three."},
            {"duration_seconds": 10, "narration": "Scene four."},
            {"duration_seconds": 10, "narration": "Scene five."},
        ],
        music_mood="electronic",
        total_duration=50,
    )
    mock_script.return_value = tmp_path / "script.json"
    raw = tmp_path / "video.mp4"
    raw.write_bytes(b"raw")
    mock_render.return_value = raw
    mock_validate.return_value = {"ok": True, "duration_seconds": 50, "resolution": "1080x1920", "has_audio": True, "errors": []}

    result = run_creative_pipeline(
        ".",
        out_dir=tmp_path,
        final=True,
        tts_provider="xai",
        fallback_tts_provider="openai",
        voice="orpheus",
        command=["repo-shorts", "creative", ".", "--final"],
    )

    run_dir = Path(result["run_dir"])
    metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))

    mock_direct.assert_called_once()
    assert mock_direct.call_args.kwargs["final"] is True
    mock_merge.assert_called_once()
    assert mock_merge.call_args.kwargs["tts_provider"] == "xai"
    assert mock_merge.call_args.kwargs["fallback_tts_provider"] == "openai"
    assert mock_merge.call_args.kwargs["voice"] == "orpheus"
    mock_validate.assert_called_once()
    mock_submission.assert_called_once()
    assert (run_dir / "captions.srt").exists()
    assert metadata["render"]["final"] is True
    assert metadata["render"]["validation"]["ok"] is True
    assert metadata["tts"]["provider"] == "xai"
    assert "captions.srt" in metadata["artifacts"]
    assert "submission_pack.md" in metadata["artifacts"]


@patch("repo_to_shorts.hermes_skill.validate_media")
@patch("repo_to_shorts.hermes_skill.ingest_target")
@patch("repo_to_shorts.hermes_skill.direct")
@patch("repo_to_shorts.hermes_skill.generate_manim_script")
@patch("repo_to_shorts.hermes_skill.render_scene")
@patch("repo_to_shorts.hermes_skill._merge_creative_video")
def test_run_creative_pipeline_final_fails_bad_validation(
    mock_merge,
    mock_render,
    mock_script,
    mock_direct,
    mock_ingest,
    mock_validate,
    tmp_path: Path,
):
    mock_ingest.return_value = FakeSnapshot()
    mock_direct.return_value = MagicMock(
        style="dark-terminal",
        title="Bad",
        hook="Bad",
        scenes=[{"duration_seconds": 10, "narration": "Scene."} for _ in range(5)],
        music_mood="electronic",
        total_duration=50,
    )
    mock_script.return_value = tmp_path / "script.json"
    raw = tmp_path / "video.mp4"
    raw.write_bytes(b"raw")
    mock_render.return_value = raw
    mock_validate.return_value = {"ok": False, "errors": ["audio stream is required"]}

    try:
        run_creative_pipeline(".", out_dir=tmp_path, final=True)
    except RuntimeError as exc:
        assert "audio stream is required" in str(exc)
    else:
        raise AssertionError("final mode should fail when validation fails")


@patch("repo_to_shorts.hermes_skill.burn_karaoke_captions")
@patch("repo_to_shorts.hermes_skill.mix_audio")
@patch("repo_to_shorts.hermes_skill.generate_ambient_music")
@patch("repo_to_shorts.hermes_skill.generate_tts")
@patch("repo_to_shorts.hermes_skill.subprocess.run")
def test_merge_creative_video_with_narration(
    mock_run, mock_tts, mock_generate_music, mock_mix_audio, mock_burn_captions, tmp_path: Path
):
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
    mock_generate_music.assert_called_once()
    assert mock_mix_audio.call_args.kwargs["duration_seconds"] == 6
    mock_burn_captions.assert_called_once()
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
