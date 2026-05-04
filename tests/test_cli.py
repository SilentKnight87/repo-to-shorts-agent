from typer.testing import CliRunner

from repo_to_shorts.cli import _slug, app

runner = CliRunner()


def test_slug_normalizes_text():
    assert _slug("Repo To Shorts!!!") == "repo-to-shorts"


def test_web_help_shows_host_and_port(monkeypatch):
    monkeypatch.setattr("repo_to_shorts.cli.run_web_server", lambda **kwargs: None)
    result = runner.invoke(app, ["web", "--help"])
    assert result.exit_code == 0
    assert "--host" in result.output
    assert "--port" in result.output
    assert "127.0.0.1" in result.output


def test_creative_help_shows_options():
    result = runner.invoke(app, ["creative", "--help"])
    assert result.exit_code == 0
    assert "--audience" in result.output
    assert "--kimi-model" in result.output
    assert "--music" in result.output
    assert "Generate a creative short" in result.output


def test_creative_help_shows_final_tts_options():
    result = runner.invoke(app, ["creative", "--help"])
    assert result.exit_code == 0
    assert "--final" in result.output
    assert "--tts-provider" in result.output
    assert "--fallback-tts-provider" in result.output
    assert "--voice" in result.output
    assert "--no-generated-music" in result.output


def test_creative_passes_full_submission_command(monkeypatch, tmp_path):
    captured = {}

    def fake_run_creative_pipeline(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return {"output": str(tmp_path / "demo.mp4"), "run_dir": str(tmp_path)}

    music = tmp_path / "music.mp3"
    music.write_bytes(b"music")
    monkeypatch.setattr("repo_to_shorts.hermes_skill.run_creative_pipeline", fake_run_creative_pipeline)

    result = runner.invoke(
        app,
        [
            "creative",
            ".",
            "--audience",
            "judges",
            "--out",
            str(tmp_path),
            "--kimi-model",
            "moonshotai/kimi-k2.6",
            "--music",
            str(music),
            "--preview",
            "--skip-audio",
            "--final",
            "--tts-provider",
            "xai",
            "--fallback-tts-provider",
            "openai",
            "--voice",
            "orpheus",
            "--no-generated-music",
        ],
    )

    assert result.exit_code == 0
    assert captured["kwargs"]["command"] == [
        "repo-shorts",
        "creative",
        ".",
        "--audience",
        "judges",
        "--out",
        str(tmp_path),
        "--kimi-model",
        "moonshotai/kimi-k2.6",
        "--music",
        str(music),
        "--preview",
        "--skip-audio",
        "--final",
        "--tts-provider",
        "xai",
        "--fallback-tts-provider",
        "openai",
        "--voice",
        "orpheus",
        "--no-generated-music",
    ]


def test_creative_submission_command_preserves_missing_music_path(monkeypatch):
    captured = {}

    def fake_run_creative_pipeline(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return {"output": "demo.mp4", "run_dir": "runs/test"}

    monkeypatch.setattr("repo_to_shorts.hermes_skill.run_creative_pipeline", fake_run_creative_pipeline)

    result = runner.invoke(app, ["creative", ".", "--music", "missing.mp3"])

    assert result.exit_code == 0
    assert "--music" in captured["kwargs"]["command"]
    assert "missing.mp3" in captured["kwargs"]["command"]
