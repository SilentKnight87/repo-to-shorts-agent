from __future__ import annotations

from pathlib import Path

import pytest

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


def test_write_submission_pack_uses_generated_copy_when_available(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    x_post = "Exact generated X copy.\nSecond line stays intact."
    discord_submission = "Exact generated Discord copy.\nWith the final submission details."
    (run_dir / "x_post.md").write_text(x_post, encoding="utf-8")
    (run_dir / "submission.md").write_text(discord_submission, encoding="utf-8")

    path = write_submission_pack(
        run_dir,
        command=["repo-shorts", "creative", ".", "--final"],
        metadata={"repo_name": "demo", "kimi": {"mode": "live-api"}, "creative_brief": {}},
        validation={"ok": True, "errors": []},
    )

    text = path.read_text(encoding="utf-8")
    assert x_post in text
    assert discord_submission in text


@pytest.mark.parametrize(
    "flag",
    ["--api-key=fake-secret-value", "--openrouter-api-key=fake-secret-value"],
)
def test_write_submission_pack_redacts_hyphenated_secret_flags(tmp_path: Path, flag: str):
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    path = write_submission_pack(
        run_dir,
        command=[flag, "repo-shorts", "creative", ".", "--final"],
        metadata={"repo_name": "demo", "kimi": {"mode": "deterministic-fallback"}, "creative_brief": {}},
        validation={"ok": False, "errors": ["missing audio"]},
    )

    text = path.read_text(encoding="utf-8")
    assert "fake-secret-value" not in text
    assert "[REDACTED]" in text


@pytest.mark.parametrize(
    "command",
    [
        ["repo-shorts", "creative", "--api-key", "fake-secret-value", "."],
        ["repo-shorts", "creative", "--openrouter-api-key", "fake-secret-value", "."],
        ["repo-shorts", "creative", "--token", "fake-secret-value", "."],
        ["repo-shorts", "creative", "--secret", "fake-secret-value", "."],
    ],
)
def test_write_submission_pack_redacts_values_after_split_secret_flags(tmp_path: Path, command: list[str]):
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    path = write_submission_pack(
        run_dir,
        command=command,
        metadata={"repo_name": "demo", "kimi": {"mode": "deterministic-fallback"}, "creative_brief": {}},
        validation={"ok": False, "errors": ["missing audio"]},
    )

    text = path.read_text(encoding="utf-8")
    assert "fake-secret-value" not in text
    assert "[REDACTED]" in text
