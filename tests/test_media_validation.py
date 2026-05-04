from __future__ import annotations

import json
import subprocess
from pathlib import Path

from repo_to_shorts.media_validation import validate_media


def test_validate_media_accepts_postable_mp4(monkeypatch, tmp_path: Path):
    video = tmp_path / "demo.mp4"
    video.write_bytes(b"mp4")
    probe = {
        "format": {"duration": "58.25"},
        "streams": [
            {"codec_type": "video", "width": 1080, "height": 1920, "duration": "58.25"},
            {"codec_type": "audio", "duration": "57.5"},
        ],
    }

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, json.dumps(probe), "")

    monkeypatch.setattr("repo_to_shorts.media_validation.subprocess.run", fake_run)

    result = validate_media(video, require_audio=True)

    assert result["ok"] is True
    assert result["duration_seconds"] == 58.25
    assert result["resolution"] == "1080x1920"
    assert result["has_video"] is True
    assert result["has_audio"] is True
    assert result["errors"] == []


def test_validate_media_rejects_bad_duration_resolution_and_missing_audio(monkeypatch, tmp_path: Path):
    video = tmp_path / "demo.mp4"
    video.write_bytes(b"mp4")
    probe = {
        "format": {"duration": "13"},
        "streams": [
            {"codec_type": "video", "width": 1280, "height": 720, "duration": "13"},
        ],
    }

    monkeypatch.setattr(
        "repo_to_shorts.media_validation.subprocess.run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, json.dumps(probe), ""),
    )

    result = validate_media(video, require_audio=True)

    assert result["ok"] is False
    assert "duration must be 43-62 seconds" in result["errors"]
    assert "resolution must be 1080x1920" in result["errors"]
    assert "audio stream is required" in result["errors"]


def test_validate_media_allows_silent_when_audio_not_required(monkeypatch, tmp_path: Path):
    video = tmp_path / "demo.mp4"
    video.write_bytes(b"mp4")
    probe = {
        "format": {"duration": "50"},
        "streams": [
            {"codec_type": "video", "width": 1080, "height": 1920, "duration": "50"},
        ],
    }

    monkeypatch.setattr(
        "repo_to_shorts.media_validation.subprocess.run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, json.dumps(probe), ""),
    )

    result = validate_media(video, require_audio=False)

    assert result["ok"] is True
    assert result["has_audio"] is False


def test_validate_media_reports_invalid_ffprobe_json(monkeypatch, tmp_path: Path):
    video = tmp_path / "demo.mp4"
    video.write_bytes(b"mp4")

    monkeypatch.setattr(
        "repo_to_shorts.media_validation.subprocess.run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, "not json", ""),
    )

    result = validate_media(video, require_audio=True)

    assert result["ok"] is False
    assert any("ffprobe" in error or "invalid JSON" in error for error in result["errors"])


def test_validate_media_requires_audio_duration_when_audio_required(monkeypatch, tmp_path: Path):
    video = tmp_path / "demo.mp4"
    video.write_bytes(b"mp4")
    probe = {
        "format": {"duration": "50"},
        "streams": [
            {"codec_type": "video", "width": 1080, "height": 1920, "duration": "50"},
            {"codec_type": "audio"},
        ],
    }

    monkeypatch.setattr(
        "repo_to_shorts.media_validation.subprocess.run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, json.dumps(probe), ""),
    )

    result = validate_media(video, require_audio=True)

    assert result["ok"] is False
    assert "audio duration is required" in result["errors"]
