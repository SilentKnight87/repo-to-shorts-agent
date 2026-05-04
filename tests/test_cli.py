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
