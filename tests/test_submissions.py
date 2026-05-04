from __future__ import annotations

from pathlib import Path

from repo_to_shorts.submissions import write_submission_pack


def test_write_submission_pack_includes_hermes_kimi_media_and_copy(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    metadata = {
        "repo_name": "repo-to-shorts-agent",
        "target": ".",
        "audience": "Nous Research Hermes Agent Creative Hackathon judges",
        "kimi": {"mode": "live-api", "provider": "openrouter", "model": "moonshotai/kimi-k2.6"},
        "render": {"output": "demo.mp4"},
        "creative_brief": {"title": "Repo-to-Shorts", "hook": "A repo becomes a short."},
    }
    validation = {"ok": True, "duration_seconds": 58.25, "resolution": "1080x1920", "has_audio": True, "errors": []}

    path = write_submission_pack(
        run_dir,
        command=["repo-shorts", "creative", ".", "--final"],
        metadata=metadata,
        validation=validation,
    )

    text = path.read_text(encoding="utf-8")
    assert path == run_dir / "submission_pack.md"
    assert "Hermes Orchestration Proof" in text
    assert "repo-shorts creative . --final" in text
    assert "moonshotai/kimi-k2.6" in text
    assert "live-api" in text
    assert "58.25" in text
    assert "X Post Draft" in text
    assert "Discord Submission Draft" in text
    assert "Known Limits" in text


def test_write_submission_pack_redacts_secret_like_command_values(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    metadata = {"repo_name": "demo", "kimi": {"mode": "deterministic-fallback"}, "creative_brief": {}}
    validation = {"ok": False, "errors": ["missing audio"]}

    path = write_submission_pack(
        run_dir,
        command=["OPENAI_API_KEY=fake-secret-value", "repo-shorts", "creative", ".", "--final"],
        metadata=metadata,
        validation=validation,
    )

    text = path.read_text(encoding="utf-8")
    assert "fake-secret-value" not in text
    assert "[REDACTED]" in text
