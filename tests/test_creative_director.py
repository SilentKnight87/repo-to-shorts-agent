from __future__ import annotations

import json

from repo_to_shorts.creative_director import (
    CreativeBrief,
    _build_director_prompt,
    _deterministic_fallback,
    _loads_brief_json,
    _parse_brief,
    direct,
)


def test_direct_returns_valid_creative_brief_with_mocked_api(monkeypatch):
    calls: list[tuple[str, str, str, dict | None]] = []

    def fake_call(prompt: str, model: str, base_url: str, *, response_format: dict | None = None) -> str:
        calls.append((prompt, model, base_url, response_format))
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
    assert result.mode == "live-api"
    assert result.provider == "openrouter"
    assert result.model == "moonshotai/kimi-k2.6"
    assert result.fallback_reason is None
    assert calls[0][1] == "moonshotai/kimi-k2.6"
    assert "my-repo" in calls[0][0]
    assert calls[0][3] == {"type": "json_object"}


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
    assert result.mode == "deterministic-fallback"
    assert result.provider == "openrouter"
    assert result.model == "moonshotai/kimi-k2.6"
    assert result.fallback_reason is None


def test_final_director_prompt_requires_postable_duration_and_secret_filtering():
    prompt = _build_director_prompt(
        {
            "repo_name": "repo-to-shorts",
            "description": "Turns repos into shorts",
            "key_files": ["src/app.py"],
            "components": ["CLI"],
        },
        final=True,
    )

    assert "45-60 seconds" in prompt
    assert "at least 5 scenes" in prompt
    assert ".env" in prompt
    assert "secret" in prompt.lower()
    assert "concrete repo evidence" in prompt.lower()


def test_final_director_prompt_requests_remotion_scene_contract():
    prompt = _build_director_prompt(
        {
            "repo_name": "repo-to-shorts",
            "description": "Turns repos into shorts",
            "key_files": ["README.md", "src/repo_to_shorts/pipeline.py"],
            "components": ["CLI", "Kimi", "Renderer"],
        },
        final=True,
    )

    assert "schema_version" in prompt
    assert "ColdOpen" in prompt
    assert "PipelineMap" in prompt
    assert "ArtifactStack" in prompt
    assert "LiveProof" in prompt
    assert "CTAEndCard" in prompt
    assert "evidence" in prompt
    assert "caption_emphasis" in prompt
    assert "Do not make generic architecture slides" in prompt


def test_parse_brief_accepts_storyboard_contract():
    raw = json.dumps({
        "schema_version": 1,
        "creative_direction": {"angle": "meta demo"},
        "storyboard": [
            {
                "type": "ColdOpen",
                "duration_seconds": 3,
                "headline": "This repo made the video.",
                "narration": "This repo made the video.",
                "evidence": ["repo_name"],
                "caption_emphasis": ["repo", "video"],
            }
        ],
        "music_mood": "electronic",
        "total_duration": 45,
    })
    result = _parse_brief(raw)
    assert result.scenes[0]["type"] == "ColdOpen"
    assert result.scenes[0]["headline"] == "This repo made the video."
    assert result.scenes[0]["evidence"] == ["repo_name"]
    assert result.scenes[0]["visual_tool"] == "pretext"


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
    monkeypatch.setattr("repo_to_shorts.creative_director._call_openrouter_api", lambda *_, **__: "not json")
    result = direct({"repo_name": "bad-json-repo"})
    assert result.title == "bad-json-repo: The Repo That Edits Itself Into a Trailer"
    assert len(result.scenes) == 5
    assert result.mode == "api-error-fallback"
    assert result.provider == "openrouter"
    assert result.model == "moonshotai/kimi-k2.6"
    assert result.fallback_reason is not None
    assert "Kimi API failed" in result.fallback_reason
    assert "JSONDecodeError" in result.fallback_reason


def test_direct_live_success_records_proof_fields(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(
        "repo_to_shorts.creative_director._call_openrouter_api",
        lambda *_, **__: json.dumps({
            "style": "cinematic",
            "title": "Live Title",
            "hook": "Live hook.",
            "scenes": [{"duration_seconds": 12, "narration": "Scene."}],
            "music_mood": "minimal",
            "total_duration": 48,
        }),
    )

    result = direct({"repo_name": "live-repo"}, model="moonshotai/custom")

    assert result.mode == "live-api"
    assert result.provider == "openrouter"
    assert result.model == "moonshotai/custom"
    assert result.fallback_reason is None


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


def test_parse_brief_preserves_taste_fields():
    raw = json.dumps({
        "style": "cinematic",
        "title": "Taste Title",
        "hook": "Watch the repo become a reel.",
        "distribution_channel": "x_short",
        "reference_pack": [{"label": "premium console"}],
        "visual_world": "cinematic engineering console",
        "motion_principles": ["motion guides attention"],
        "shot_list": ["raw repo input", "proof metadata"],
        "continuity_rules": ["captions stay inside safe area"],
        "negative_prompts": ["generic AI SaaS soup"],
        "scenes": [{"type": "ColdOpen", "duration_seconds": 5, "headline": "REPO BECOMES REEL"}],
        "total_duration": 50,
    })

    result = _parse_brief(raw)

    assert result.distribution_channel == "x_short"
    assert result.reference_pack == [{"label": "premium console"}]
    assert result.visual_world == "cinematic engineering console"
    assert result.motion_principles == ["motion guides attention"]
    assert result.shot_list == ["raw repo input", "proof metadata"]
    assert result.continuity_rules == ["captions stay inside safe area"]
    assert result.negative_prompts == ["generic AI SaaS soup"]


def test_director_prompt_includes_design_profile_and_reference_pack():
    prompt = _build_director_prompt(
        {"repo_name": "repo", "description": "desc", "key_files": ["README.md"]},
        final=True,
        design_profile={"name": "Console", "colors": {"neutral": "#080A0F"}},
        reference_pack={"references": [{"label": "premium console"}], "avoid": ["generic AI SaaS soup"]},
    )

    assert "DESIGN PROFILE" in prompt
    assert "Console" in prompt
    assert "REFERENCE PACK" in prompt
    assert "premium console" in prompt
    assert "generic AI SaaS soup" in prompt
    assert "visual_world" in prompt
    assert "negative_prompts" in prompt


def test_direct_passes_taste_args(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    calls = []

    def fake_call(prompt, model, base_url, *, response_format=None):
        calls.append(prompt)
        return json.dumps({
            "style": "cinematic",
            "title": "Taste",
            "hook": "Hook",
            "scenes": [{"type": "ColdOpen", "duration_seconds": 5, "headline": "Test"}],
            "distribution_channel": "x_short",
        })

    monkeypatch.setattr("repo_to_shorts.creative_director._call_openrouter_api", fake_call)

    result = direct(
        {"repo_name": "repo", "description": "desc"},
        final=True,
        design_profile={"name": "Profile"},
        reference_pack={"references": [{"label": "ref"}]},
    )

    assert result.distribution_channel == "x_short"
    assert "DESIGN PROFILE" in calls[0]
    assert "REFERENCE PACK" in calls[0]
