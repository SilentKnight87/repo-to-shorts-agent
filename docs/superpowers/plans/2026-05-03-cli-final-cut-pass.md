# CLI Final-Cut Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `repo-shorts creative --final` produce a validated, submission-ready short-video package with Kimi proof, provider-based TTS, captions, and Hermes orchestration copy.

**Architecture:** Keep `repo-shorts creative` as the deterministic production engine. Add small helper modules for media validation and submission packaging, extend the existing compositor with provider-based TTS, then wire final-mode behavior through `cli.py` and `hermes_skill.py`. Hermes remains the external operator that runs the CLI and inspects artifacts; the generated package records that orchestration truthfully.

**Tech Stack:** Python 3.13, Typer, urllib, ffmpeg/ffprobe, Pillow render path, OpenRouter Kimi adapter, xAI/OpenAI TTS APIs via HTTP, pytest, Ruff.

---

## File Structure

- Create `src/repo_to_shorts/media_validation.py`
  - One responsibility: inspect an MP4 with ffprobe and return a structured validation result.
- Create `src/repo_to_shorts/submissions.py`
  - One responsibility: write `submission_pack.md` from metadata, command, and validation data.
- Modify `src/repo_to_shorts/compositor.py`
  - Extend `generate_tts()` with `provider`, `fallback_provider`, and `voice` options while preserving Edge behavior.
- Modify `src/repo_to_shorts/creative_director.py`
  - Add final-mode prompt constraints without changing fallback reliability.
- Modify `src/repo_to_shorts/hermes_skill.py`
  - Add final-mode orchestration, secret-safe repo analysis, SRT writing, validation, submission pack writing, and expanded metadata.
- Modify `src/repo_to_shorts/cli.py`
  - Add `--final`, `--tts-provider`, `--fallback-tts-provider`, `--voice`, and `--no-generated-music`.
- Modify tests under `tests/`
  - Keep network calls mocked. No test may call real xAI/OpenAI/OpenRouter.

---

### Task 1: Media Validation And Submission Pack Helpers

**Files:**
- Create: `src/repo_to_shorts/media_validation.py`
- Create: `src/repo_to_shorts/submissions.py`
- Create: `tests/test_media_validation.py`
- Create: `tests/test_submissions.py`

- [ ] **Step 1: Write failing tests for media validation**

Add `tests/test_media_validation.py`:

```python
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
```

- [ ] **Step 2: Write failing tests for submission pack**

Add `tests/test_submissions.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_media_validation.py tests/test_submissions.py -q
```

Expected: import failures for `repo_to_shorts.media_validation` and `repo_to_shorts.submissions`.

- [ ] **Step 4: Implement `media_validation.py`**

Create `src/repo_to_shorts/media_validation.py` with:

```python
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def validate_media(
    video_path: Path,
    *,
    require_audio: bool = True,
    min_duration: float = 43.0,
    max_duration: float = 62.0,
    expected_width: int = 1080,
    expected_height: int = 1920,
    audio_tolerance_seconds: float = 1.5,
) -> dict[str, Any]:
    video_path = video_path.resolve()
    errors: list[str] = []
    result: dict[str, Any] = {
        "ok": False,
        "path": str(video_path),
        "exists": video_path.exists(),
        "size_bytes": video_path.stat().st_size if video_path.exists() else 0,
        "has_video": False,
        "has_audio": False,
        "duration_seconds": None,
        "audio_duration_seconds": None,
        "resolution": None,
        "errors": errors,
    }

    if not video_path.exists() or result["size_bytes"] == 0:
        errors.append("demo.mp4 must exist and be non-empty")
        return result

    try:
        probe = _ffprobe(video_path)
    except RuntimeError as exc:
        errors.append(str(exc))
        return result

    streams = probe.get("streams", [])
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)

    duration = _float_or_none(probe.get("format", {}).get("duration"))
    result["duration_seconds"] = duration

    if video_stream:
        result["has_video"] = True
        width = int(video_stream.get("width") or 0)
        height = int(video_stream.get("height") or 0)
        result["resolution"] = f"{width}x{height}"
        if width != expected_width or height != expected_height:
            errors.append(f"resolution must be {expected_width}x{expected_height}")
    else:
        errors.append("video stream is required")

    if audio_stream:
        result["has_audio"] = True
        result["audio_duration_seconds"] = _float_or_none(audio_stream.get("duration"))
    elif require_audio:
        errors.append("audio stream is required")

    if duration is None or duration < min_duration or duration > max_duration:
        errors.append(f"duration must be {int(min_duration)}-{int(max_duration)} seconds")

    audio_duration = result["audio_duration_seconds"]
    if require_audio and duration is not None and audio_duration is not None:
        if abs(float(duration) - float(audio_duration)) > audio_tolerance_seconds:
            errors.append(f"audio duration must be within {audio_tolerance_seconds} seconds of video duration")

    result["ok"] = not errors
    return result


def _ffprobe(video_path: Path) -> dict[str, Any]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]
    try:
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(f"ffprobe failed: {exc}") from exc
    return json.loads(completed.stdout)


def _float_or_none(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
```

- [ ] **Step 5: Implement `submissions.py`**

Create `src/repo_to_shorts/submissions.py` with:

```python
from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any


def write_submission_pack(
    run_dir: Path,
    *,
    command: list[str],
    metadata: dict[str, Any],
    validation: dict[str, Any] | None = None,
) -> Path:
    run_dir = run_dir.resolve()
    validation = validation or {}
    kimi = metadata.get("kimi", {})
    brief = metadata.get("creative_brief", {})
    repo_name = metadata.get("repo_name") or metadata.get("target") or "repo"
    command_text = _redact_command(command)
    validation_errors = validation.get("errors") or []
    validation_status = "pass" if validation.get("ok") else "needs attention"

    text = f"""# Submission Pack

## Hermes Orchestration Proof

- Hermes/operator command: `{command_text}`
- Run directory: `{run_dir}`
- Repo: `{repo_name}`
- Kimi mode: `{kimi.get("mode", "unknown")}`
- Kimi provider: `{kimi.get("provider", "unknown")}`
- Kimi model: `{kimi.get("model", "unknown")}`
- Media validation: `{validation_status}`
- Demo MP4: `demo.mp4`

Hermes orchestrated the workflow by running the CLI, inspecting the generated proof files, and preparing this package. Repo-to-Shorts produced the artifacts.

## MP4 Validation

- Duration: `{validation.get("duration_seconds", "unknown")}`
- Resolution: `{validation.get("resolution", "unknown")}`
- Audio stream: `{validation.get("has_audio", "unknown")}`
- Errors: `{", ".join(validation_errors) if validation_errors else "none"}`

## X Post Draft

I built Repo-to-Shorts Agent for the Hermes Agent Creative Hackathon.

Paste a repo, and Hermes runs a Kimi-directed workflow that turns code evidence into a launch-ready vertical short: narration, captions, MP4, metadata proof, and submission copy.

Kimi proof: `{kimi.get("mode", "unknown")}` via `{kimi.get("model", "unknown")}`.

## Discord Submission Draft

Repo-to-Shorts Agent turns a GitHub repo or local codebase into a short-video package for launches and hackathon demos.

Hermes orchestrates the workflow. Kimi acts as creative director. The CLI writes `demo.mp4`, `metadata.json`, `captions.srt`, and this submission pack.

Generated hook: {brief.get("hook", "See generated creative brief.")}

## Recording Beats

1. Show the command or Hermes task.
2. Show the generated run directory.
3. Open `metadata.json` and show Kimi mode/model/provider.
4. Play `demo.mp4`.
5. Use the X/Discord copy above.

## Known Limits

- This MVP creates a local package; it does not post externally.
- Music is generated or supplied locally; no paid music API is required.
- Kimi proof is honest: fallback modes are recorded when live API calls fail.
"""
    path = run_dir / "submission_pack.md"
    path.write_text(text, encoding="utf-8")
    return path


def _redact_command(command: list[str]) -> str:
    safe_parts = []
    for part in command:
        if _looks_secret(part):
            if "=" in part:
                safe_parts.append(part.split("=", 1)[0] + "=[REDACTED]")
            else:
                safe_parts.append("[REDACTED]")
        else:
            safe_parts.append(shlex.quote(part))
    return " ".join(safe_parts)


def _looks_secret(value: str) -> bool:
    lowered = value.lower()
    return (
        "api_key=" in lowered
        or "token=" in lowered
        or "secret=" in lowered
        or "sk-" in value
        or "sk_or_" in lowered
    )
```

- [ ] **Step 6: Verify task tests and commit**

Run:

```bash
.venv/bin/python -m pytest tests/test_media_validation.py tests/test_submissions.py -q
.venv/bin/ruff check src/repo_to_shorts/media_validation.py src/repo_to_shorts/submissions.py tests/test_media_validation.py tests/test_submissions.py
```

Expected: all pass.

Commit:

```bash
git add src/repo_to_shorts/media_validation.py src/repo_to_shorts/submissions.py tests/test_media_validation.py tests/test_submissions.py
git commit -m "feat: add final media validation and submission pack"
```

---

### Task 2: Provider-Based TTS

**Files:**
- Modify: `src/repo_to_shorts/compositor.py`
- Modify: `tests/test_compositor.py`

- [ ] **Step 1: Add failing provider tests**

Append to `tests/test_compositor.py`:

```python
def test_generate_tts_uses_xai_provider(monkeypatch, tmp_path: Path):
    requests = []
    commands = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b"fake mp3"

    def fake_urlopen(request, timeout=60):
        requests.append(request)
        return FakeResponse()

    def fake_run(command, **kwargs):
        commands.append(command)
        out = Path(command[-1])
        out.write_bytes(b"fake wav")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setenv("XAI_API_KEY", "test-xai")
    monkeypatch.setattr("repo_to_shorts.compositor.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("repo_to_shorts.compositor.subprocess.run", fake_run)

    result = generate_tts("Ship this repo.", tmp_path / "tts.wav", provider="xai", voice="orpheus")

    assert result == (tmp_path / "tts.wav").resolve()
    assert requests
    assert requests[0].full_url == "https://api.x.ai/v1/tts"
    assert requests[0].headers["Authorization"] == "Bearer test-xai"
    assert b"Ship this repo." in requests[0].data
    assert b"orpheus" in requests[0].data
    assert commands[0][0] == "ffmpeg"


def test_generate_tts_falls_back_from_xai_to_openai(monkeypatch, tmp_path: Path):
    urls = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b"fake mp3"

    def fake_urlopen(request, timeout=60):
        urls.append(request.full_url)
        if "x.ai" in request.full_url:
            raise OSError("xai down")
        return FakeResponse()

    monkeypatch.setenv("XAI_API_KEY", "test-xai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    monkeypatch.setattr("repo_to_shorts.compositor.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr(
        "repo_to_shorts.compositor.subprocess.run",
        lambda command, **kwargs: (Path(command[-1]).write_bytes(b"fake wav"), subprocess.CompletedProcess(command, 0, "", ""))[1],
    )

    result = generate_tts("Fallback voice.", tmp_path / "tts.wav", provider="xai", fallback_provider="openai")

    assert result == (tmp_path / "tts.wav").resolve()
    assert urls == ["https://api.x.ai/v1/tts", "https://api.openai.com/v1/audio/speech"]


def test_generate_tts_none_provider_raises_clear_error(tmp_path: Path):
    try:
        generate_tts("No voice.", tmp_path / "tts.wav", provider="none")
    except RuntimeError as exc:
        assert "TTS provider is none" in str(exc)
    else:
        raise AssertionError("provider=none should not generate audio")
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_compositor.py::test_generate_tts_uses_xai_provider tests/test_compositor.py::test_generate_tts_falls_back_from_xai_to_openai tests/test_compositor.py::test_generate_tts_none_provider_raises_clear_error -q
```

Expected: `generate_tts()` does not accept provider arguments yet.

- [ ] **Step 3: Extend `generate_tts()` minimally**

Modify `src/repo_to_shorts/compositor.py`:

- import `json`, `os`, and `urllib.request`
- keep constants for Edge
- change signature to:

```python
def generate_tts(
    text: str,
    output_path: Path,
    *,
    provider: str = "edge",
    fallback_provider: str | None = None,
    voice: str | None = None,
    allow_say_fallback: bool = False,
) -> Path:
```

Implementation rules:

- if `provider == "none"`, raise `RuntimeError("TTS provider is none; skip audio composition instead")`
- try primary provider
- if it fails and `fallback_provider` exists and is not `"none"`, try fallback
- support providers `xai`, `openai`, and `edge`
- convert any MP3/WAV response to final WAV with ffmpeg using the existing conversion style

Add helpers:

```python
def _generate_tts_source(text: str, output_path: Path, provider: str, voice: str | None, allow_say_fallback: bool) -> Path:
    ...

def _generate_xai_tts(text: str, output_path: Path, voice: str | None) -> Path:
    ...

def _generate_openai_tts(text: str, output_path: Path, voice: str | None) -> Path:
    ...

def _generate_edge_tts(text: str, output_path: Path, voice: str | None, allow_say_fallback: bool) -> Path:
    ...
```

Use these request contracts:

```python
# xAI
url = "https://api.x.ai/v1/tts"
payload = {"model": "grok-2-voice", "input": text, "voice": voice or "orpheus", "response_format": "mp3"}
headers = {"Authorization": f"Bearer {os.environ['XAI_API_KEY']}", "Content-Type": "application/json"}

# OpenAI
url = "https://api.openai.com/v1/audio/speech"
payload = {"model": "gpt-4o-mini-tts", "input": text, "voice": voice or "alloy", "response_format": "mp3"}
headers = {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"}
```

- [ ] **Step 4: Preserve existing Edge tests**

Existing tests in `tests/test_compositor.py` must still pass:

```bash
.venv/bin/python -m pytest tests/test_compositor.py -q
```

Expected: all compositor tests pass.

- [ ] **Step 5: Commit**

Run:

```bash
.venv/bin/ruff check src/repo_to_shorts/compositor.py tests/test_compositor.py
git add src/repo_to_shorts/compositor.py tests/test_compositor.py
git commit -m "feat: add provider based tts"
```

---

### Task 3: Final-Mode Creative Direction And Secret-Safe Evidence

**Files:**
- Modify: `src/repo_to_shorts/creative_director.py`
- Modify: `src/repo_to_shorts/hermes_skill.py`
- Modify: `src/repo_to_shorts/manim_render.py`
- Modify: `tests/test_creative_director.py`
- Modify: `tests/test_hermes_skill.py`
- Modify: `tests/test_manim_render.py`

- [ ] **Step 1: Add failing tests**

Add to `tests/test_hermes_skill.py`:

```python
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
```

Add to `tests/test_creative_director.py`:

```python
from repo_to_shorts.creative_director import _build_director_prompt


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
```

Add to `tests/test_manim_render.py`:

```python
def test_generate_manim_script_filters_secret_key_files(tmp_path: Path):
    scene = {"scenes": [], "fps": 30}
    repo_analysis = {
        "name": "test-repo",
        "description": "Test",
        "components": [],
        "key_files": [".env", "src/app.py", "id_rsa", "docs/README.md"],
    }

    script_path = generate_manim_script(scene, repo_analysis, tmp_path / "out")

    data = json.loads(script_path.read_text(encoding="utf-8"))
    assert data["key_files"] == ["src/app.py", "docs/README.md"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_hermes_skill.py::test_build_repo_analysis_filters_secret_like_paths tests/test_creative_director.py::test_final_director_prompt_requires_postable_duration_and_secret_filtering tests/test_manim_render.py::test_generate_manim_script_filters_secret_key_files -q
```

Expected: failures because final prompt and path filtering are not implemented.

- [ ] **Step 3: Implement secret-safe file filtering**

In `src/repo_to_shorts/hermes_skill.py`, add:

```python
SAFE_FILE_PREFIXES = ("src/", "tests/", "docs/")
SAFE_FILE_NAMES = {"README.md", "pyproject.toml", "package.json"}
SECRET_FILE_MARKERS = (".env", "secret", "token", "private", "id_rsa", ".pem", ".key")


def _safe_file_tree(file_tree: list[str], limit: int = 10) -> list[str]:
    safe = []
    for path in file_tree:
        lowered = path.lower()
        if lowered.startswith("runs/") or any(marker in lowered for marker in SECRET_FILE_MARKERS):
            continue
        if path in SAFE_FILE_NAMES or path.startswith(SAFE_FILE_PREFIXES):
            safe.append(path)
        if len(safe) >= limit:
            break
    return safe
```

Use `_safe_file_tree(snapshot.file_tree)` in `_build_repo_analysis()` for `key_files` and components.

In `src/repo_to_shorts/manim_render.py`, add a matching local helper or import-safe copy to filter `key_files` before writing the descriptor. Keep it small and avoid importing from `hermes_skill.py` if that creates circular imports.

- [ ] **Step 4: Add final-mode director prompt**

Change `direct()` signature in `src/repo_to_shorts/creative_director.py`:

```python
def direct(repo_analysis: dict, model: str = "moonshotai/kimi-k2.6", *, final: bool = False) -> CreativeBrief:
```

Pass `final` into `_build_director_prompt(analysis, final=final)`.

Change `_build_director_prompt()` signature:

```python
def _build_director_prompt(analysis: dict, *, final: bool = False) -> str:
```

Append final rules when `final` is true:

```text
Final export constraints:
- Total runtime must be 45-60 seconds.
- Use at least 5 scenes.
- Use concrete repo evidence from KEY_FILES and COMPONENTS.
- Do not include .env, secret, token, private key, credential, or generated run files in visual evidence or narration.
- Make the first 3 seconds understandable without audio.
- Include a final CTA suitable for a hackathon submission.
```

- [ ] **Step 5: Verify and commit**

Run:

```bash
.venv/bin/python -m pytest tests/test_hermes_skill.py tests/test_creative_director.py tests/test_manim_render.py -q
.venv/bin/ruff check src/repo_to_shorts/creative_director.py src/repo_to_shorts/hermes_skill.py src/repo_to_shorts/manim_render.py tests/test_creative_director.py tests/test_hermes_skill.py tests/test_manim_render.py
```

Commit:

```bash
git add src/repo_to_shorts/creative_director.py src/repo_to_shorts/hermes_skill.py src/repo_to_shorts/manim_render.py tests/test_creative_director.py tests/test_hermes_skill.py tests/test_manim_render.py
git commit -m "polish: tighten final creative direction"
```

---

### Task 4: Final CLI Orchestration

**Files:**
- Modify: `src/repo_to_shorts/cli.py`
- Modify: `src/repo_to_shorts/hermes_skill.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_hermes_skill.py`

- [ ] **Step 1: Add failing CLI option tests**

Update `tests/test_cli.py`:

```python
def test_creative_help_shows_final_tts_options():
    result = runner.invoke(app, ["creative", "--help"])
    assert result.exit_code == 0
    assert "--final" in result.output
    assert "--tts-provider" in result.output
    assert "--fallback-tts-provider" in result.output
    assert "--voice" in result.output
    assert "--no-generated-music" in result.output
```

- [ ] **Step 2: Add failing pipeline orchestration tests**

Add to `tests/test_hermes_skill.py`:

```python
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
```

Ensure `tests/test_hermes_skill.py` imports `json`.

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_cli.py::test_creative_help_shows_final_tts_options tests/test_hermes_skill.py::test_run_creative_pipeline_final_writes_validation_submission_and_srt tests/test_hermes_skill.py::test_run_creative_pipeline_final_fails_bad_validation -q
```

Expected: CLI options and pipeline arguments are missing.

- [ ] **Step 4: Wire CLI options**

In `src/repo_to_shorts/cli.py`, add parameters to `creative()`:

```python
final: bool = typer.Option(False, "--final", help="Run submission-grade final export with validation."),
tts_provider: str = typer.Option("edge", "--tts-provider", help="TTS provider: xai, openai, edge, or none."),
fallback_tts_provider: str | None = typer.Option(None, "--fallback-tts-provider", help="Fallback TTS provider."),
voice: str | None = typer.Option(None, "--voice", help="Provider-specific voice id."),
generated_music: bool = typer.Option(True, "--generated-music/--no-generated-music", help="Generate ambient music when no --music is supplied."),
```

Before calling `run_creative_pipeline`, build:

```python
command = ["repo-shorts", "creative", target, "--audience", audience, "--out", str(out)]
if kimi_model:
    command.extend(["--kimi-model", kimi_model])
if final:
    command.append("--final")
command.extend(["--tts-provider", tts_provider])
if fallback_tts_provider:
    command.extend(["--fallback-tts-provider", fallback_tts_provider])
if voice:
    command.extend(["--voice", voice])
if not generated_music:
    command.append("--no-generated-music")
```

Pass new values into `run_creative_pipeline()`.

- [ ] **Step 5: Wire final pipeline behavior**

In `src/repo_to_shorts/hermes_skill.py`:

- import `validate_media` and `write_submission_pack`
- extend `run_creative_pipeline()` signature:

```python
final: bool = False,
tts_provider: str = "edge",
fallback_tts_provider: str | None = None,
voice: str | None = None,
generated_music: bool = True,
command: list[str] | None = None,
```

- if `final` is true, force `preview = False` and `skip_audio = tts_provider == "none"`
- call `direct(..., final=final)`
- pass TTS options into `_merge_creative_video()`
- write `captions.srt` for every creative run using a helper:

```python
def _write_captions_srt(scenes: list[dict], output_path: Path) -> Path:
    ...
```

- call `validate_media(final_video, require_audio=not skip_audio)`
- in final mode, raise `RuntimeError("; ".join(validation["errors"]))` if validation is not ok
- add metadata sections:

```python
"tts": {
    "provider": tts_provider,
    "fallback_provider": fallback_tts_provider,
    "voice": voice,
    "skipped": skip_audio,
},
"render": {
    ...
    "final": final,
    "validation": validation,
},
```

- call `write_submission_pack(run_dir, command=command or ["repo-shorts", "creative", target], metadata=metadata, validation=validation)`
- include `captions.srt` and `submission_pack.md` in artifacts

Extend `_merge_creative_video()` signature:

```python
tts_provider: str = "edge",
fallback_tts_provider: str | None = None,
voice: str | None = None,
generated_music: bool = True,
```

Inside `_merge_creative_video()`, call:

```python
generate_tts(narration, tts_path, provider=tts_provider, fallback_provider=fallback_tts_provider, voice=voice)
```

Only call `generate_ambient_music()` when `generated_music` is true. If no music exists and `generated_music` is false, pass `None` to `mix_audio()`.

- [ ] **Step 6: Verify and commit**

Run:

```bash
.venv/bin/python -m pytest tests/test_cli.py tests/test_hermes_skill.py -q
.venv/bin/ruff check src/repo_to_shorts/cli.py src/repo_to_shorts/hermes_skill.py tests/test_cli.py tests/test_hermes_skill.py
```

Commit:

```bash
git add src/repo_to_shorts/cli.py src/repo_to_shorts/hermes_skill.py tests/test_cli.py tests/test_hermes_skill.py
git commit -m "feat: add final creative cli mode"
```

---

### Task 5: Full Verification And Final Smoke

**Files:**
- Modify only if verification exposes defects.

- [ ] **Step 1: Run full automated checks**

Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
```

Expected: all tests pass and Ruff is clean.

- [ ] **Step 2: Run deterministic final smoke without network**

Run:

```bash
env -u OPENROUTER_API_KEY -u KIMI_API_KEY -u XAI_API_KEY -u OPENAI_API_KEY \
.venv/bin/repo-shorts creative . \
  --audience "Nous Research Hermes Agent Creative Hackathon judges" \
  --out runs \
  --final \
  --tts-provider none
```

Expected:

- command exits 0
- creates a fresh run directory under `runs/`
- writes `demo.mp4`, `metadata.json`, `captions.srt`, and `submission_pack.md`
- metadata says Kimi fallback honestly
- validation allows no audio because `--tts-provider none`

- [ ] **Step 3: Run live final smoke if keys are present**

Check only key names, not values:

```bash
sed -n 's/=.*//p' .env
```

If `OPENROUTER_API_KEY`, `XAI_API_KEY`, and `OPENAI_API_KEY` exist, run:

```bash
set -a
. ./.env
set +a
.venv/bin/repo-shorts creative . \
  --audience "Nous Research Hermes Agent Creative Hackathon judges" \
  --kimi-model moonshotai/kimi-k2.6 \
  --tts-provider xai \
  --fallback-tts-provider openai \
  --out runs \
  --final
```

Expected:

- command exits 0
- `metadata.json` records `kimi.mode`
- if live Kimi succeeds, metadata records `mode=live-api`
- `metadata.json` includes render validation
- `submission_pack.md` includes Hermes orchestration proof

- [ ] **Step 4: Inspect generated artifacts**

Run:

```bash
latest="$(ls -td runs/* | head -1)"
python -m json.tool "$latest/metadata.json" | sed -n '1,180p'
sed -n '1,220p' "$latest/submission_pack.md"
ls -lh "$latest/demo.mp4" "$latest/captions.srt"
```

Expected: proof fields are present and no secret values are printed.

- [ ] **Step 5: Commit any verification fixes**

If fixes were needed:

```bash
git add <changed-files>
git commit -m "fix: stabilize final creative export"
```

If no fixes were needed, do not create an empty commit.
