from __future__ import annotations

import json
from pathlib import Path

from repo_to_shorts.ingest import RepoSnapshot
from repo_to_shorts.kimi import (
    DEFAULT_KIMI_MODEL,
    KimiCritique,
    build_kimi_prompt,
    critique_story,
)


def sample_snapshot(tmp_path: Path) -> RepoSnapshot:
    return RepoSnapshot(
        target=str(tmp_path),
        name="sample-repo",
        source_type="local",
        path=tmp_path,
        readme="# Sample Repo\n\nTurns repositories into launch-ready short-video packages.",
        file_tree=["README.md", "src/app.py"],
        package_metadata={"description": "Demo package"},
        git_log="abc123 initial commit",
        git_diff=" src/app.py | 2 ++",
    )


def test_build_kimi_prompt_includes_repo_audience_storyboard_and_return_contract(tmp_path: Path):
    snapshot = sample_snapshot(tmp_path)

    prompt = build_kimi_prompt(snapshot, "hackathon judges", "# Storyboard\nProof beat", live_model="moonshotai/kimi-k2.6")

    assert "sample-repo" in prompt
    assert "hackathon judges" in prompt
    assert "# Storyboard" in prompt
    assert "src/app.py" in prompt
    assert "live Kimi API call" in prompt
    assert "moonshotai/kimi-k2.6" in prompt
    assert "Return:" in prompt
    assert "risky/unclear claims" in prompt


def test_critique_story_falls_back_without_openrouter_or_kimi_key(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("KIMI_API_KEY", raising=False)
    snapshot = sample_snapshot(tmp_path)

    result = critique_story(snapshot, "hackathon judges", "storyboard")

    assert result == KimiCritique(
        mode="deterministic-fallback",
        text=result.text,
        model=None,
        provider="none",
        fallback_reason="OPENROUTER_API_KEY or KIMI_API_KEY not set",
    )
    assert "deterministic fallback" in result.text


def test_critique_story_uses_openrouter_kimi_26_when_key_present(monkeypatch, tmp_path: Path):
    snapshot = sample_snapshot(tmp_path)
    calls: list[tuple[str, str, str]] = []

    def fake_call(prompt: str, model: str, base_url: str) -> str:
        calls.append((prompt, model, base_url))
        return "# Live Kimi critique\n\nSharper hook here."

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("KIMI_API_KEY", raising=False)
    monkeypatch.setattr("repo_to_shorts.kimi._call_openrouter_api", fake_call)

    result = critique_story(snapshot, "hackathon judges", "storyboard")

    assert result.mode == "live-api"
    assert result.model == DEFAULT_KIMI_MODEL == "moonshotai/kimi-k2.6"
    assert result.provider == "openrouter"
    assert result.fallback_reason is None
    assert "Live Kimi critique" in result.text
    assert calls[0][1] == "moonshotai/kimi-k2.6"
    assert "sample-repo" in calls[0][0]


def test_critique_story_records_api_error_as_fallback(monkeypatch, tmp_path: Path):
    snapshot = sample_snapshot(tmp_path)

    def fake_call(prompt: str, model: str, base_url: str) -> str:
        raise TimeoutError("network sad trombone")

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr("repo_to_shorts.kimi._call_openrouter_api", fake_call)

    result = critique_story(snapshot, "hackathon judges", "storyboard")

    assert result.mode == "api-error-fallback"
    assert result.model == DEFAULT_KIMI_MODEL
    assert result.provider == "openrouter"
    assert result.fallback_reason == "Kimi API failed: TimeoutError"
    assert "deterministic fallback" in result.text


def test_call_openrouter_api_sends_openai_compatible_chat_request(monkeypatch):
    requests = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return json.dumps({"choices": [{"message": {"content": "live result"}}]}).encode("utf-8")

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return FakeResponse()

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr("repo_to_shorts.kimi.request.urlopen", fake_urlopen)

    result = __import__("repo_to_shorts.kimi", fromlist=["_call_openrouter_api"])._call_openrouter_api(
        "prompt", "moonshotai/kimi-k2.6", "https://openrouter.ai/api/v1"
    )

    assert result == "live result"
    request, timeout = requests[0]
    assert request.full_url == "https://openrouter.ai/api/v1/chat/completions"
    assert timeout == 60
    payload = json.loads(request.data.decode("utf-8"))
    assert payload["model"] == "moonshotai/kimi-k2.6"
    assert payload["messages"][1] == {"role": "user", "content": "prompt"}
    assert payload["max_tokens"] == 3000
    assert payload["reasoning"] == {"enabled": False}
    assert request.headers["Authorization"] == "Bearer test-key"


def test_call_openrouter_api_can_request_json_object_response(monkeypatch):
    requests = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return json.dumps({"choices": [{"message": {"content": "{\"ok\": true}"}}]}).encode("utf-8")

    def fake_urlopen(request, timeout):
        requests.append(request)
        return FakeResponse()

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr("repo_to_shorts.kimi.request.urlopen", fake_urlopen)

    result = __import__("repo_to_shorts.kimi", fromlist=["_call_openrouter_api"])._call_openrouter_api(
        "prompt",
        "moonshotai/kimi-k2.6",
        "https://openrouter.ai/api/v1",
        response_format={"type": "json_object"},
    )

    assert result == "{\"ok\": true}"
    payload = json.loads(requests[0].data.decode("utf-8"))
    assert payload["response_format"] == {"type": "json_object"}
