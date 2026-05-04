from __future__ import annotations

import json

from repo_to_shorts.creative_director import (
    CreativeBrief,
    _deterministic_fallback,
    _loads_brief_json,
    _parse_brief,
    direct,
)


def test_direct_returns_valid_creative_brief_with_mocked_api(monkeypatch):
    calls: list[tuple[str, str, str]] = []

    def fake_call(prompt: str, model: str, base_url: str) -> str:
        calls.append((prompt, model, base_url))
        brief = {
            "style": "clean-academic",
            "title": "Test Title",
            "hook": "Code that speaks.",
            "scenes": [
                {
                    "duration_seconds": 10,
                    "visual_tool": "manim",
                    "narration": "Scene one.",
                    "music_mood": "tension",
                    "transition": "fade",
                }
            ],
            "music_mood": "electronic",
            "total_duration": 60,
        }
        return json.dumps(brief)

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr("repo_to_shorts.creative_director._call_openrouter_api", fake_call)

    analysis = {
        "repo_name": "my-repo",
        "description": "A test repo",
        "primary_language": "Python",
        "key_files": ["main.py"],
        "purpose": "testing",
    }
    result = direct(analysis, model="moonshotai/kimi-k2.6")

    assert isinstance(result, CreativeBrief)
    assert result.style == "clean-academic"
    assert result.title == "Test Title"
    assert result.hook == "Code that speaks."
    assert len(result.scenes) == 1
    assert result.scenes[0]["visual_tool"] == "manim"
    assert result.music_mood == "electronic"
    assert result.total_duration == 60
    assert calls[0][1] == "moonshotai/kimi-k2.6"
    assert "my-repo" in calls[0][0]


def test_direct_fallback_when_no_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("KIMI_API_KEY", raising=False)

    analysis = {
        "repo_name": "fallback-repo",
        "description": "Fallback test",
        "primary_language": "Rust",
        "key_files": ["lib.rs"],
        "purpose": "demo",
    }
    result = direct(analysis)

    assert isinstance(result, CreativeBrief)
    assert result.style == "dark-terminal"
    assert result.title == "fallback-repo: The Repo That Edits Itself Into a Trailer"
    assert result.hook == "A codebase walks into a cinema."
    assert len(result.scenes) == 5
    assert result.total_duration == 60


def test_parse_brief_handles_markdown_code_fences():
    raw = """```json
{
  "style": "playful",
  "title": "Fenced Title",
  "hook": "Hook line.",
  "scenes": [],
  "music_mood": "ambient",
  "total_duration": 45
}
```"""
    result = _parse_brief(raw)
    assert result.style == "playful"
    assert result.title == "Fenced Title"
    assert result.hook == "Hook line."
    assert result.total_duration == 45


def test_parse_brief_handles_plain_json():
    raw = json.dumps({
        "style": "cinematic",
        "title": "Plain Title",
        "hook": "Plain hook.",
        "scenes": [{"duration_seconds": 5, "visual_tool": "svg"}],
        "music_mood": "orchestral",
        "total_duration": 30,
    })
    result = _parse_brief(raw)
    assert result.style == "cinematic"
    assert result.title == "Plain Title"
    assert result.total_duration == 30
    assert len(result.scenes) == 1


def test_loads_brief_json_extracts_object_from_model_chatter():
    raw = "Here is the brief:\n{\n  \"style\": \"cinematic\",\n  \"title\": \"Recovered\"\n}\nShip it."
    data = _loads_brief_json(raw)
    assert data["style"] == "cinematic"
    assert data["title"] == "Recovered"


def test_direct_falls_back_when_model_returns_malformed_json(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr("repo_to_shorts.creative_director._call_openrouter_api", lambda *_: "not json")
    result = direct({"repo_name": "bad-json-repo"})
    assert result.title == "bad-json-repo: The Repo That Edits Itself Into a Trailer"
    assert len(result.scenes) == 5


def test_deterministic_fallback_returns_expected_structure():
    analysis = {
        "repo_name": "test-repo",
        "description": "A repo for testing",
        "primary_language": "Go",
        "key_files": ["main.go"],
        "purpose": "testing fallback",
    }
    result = _deterministic_fallback(analysis)

    assert isinstance(result, CreativeBrief)
    assert result.style == "dark-terminal"
    assert result.title == "test-repo: The Repo That Edits Itself Into a Trailer"
    assert result.hook == "A codebase walks into a cinema."
    assert len(result.scenes) == 5
    assert result.music_mood == "electronic"
    assert result.total_duration == 60

    tools = [scene["visual_tool"] for scene in result.scenes]
    assert tools == ["pretext", "svg", "manim", "ascii", "pretext"]

    durations = [scene["duration_seconds"] for scene in result.scenes]
    assert sum(durations) == 60
