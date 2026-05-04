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
    x_post_draft = _generated_copy_or_fallback(
        run_dir / "x_post.md",
        _fallback_x_post_draft(kimi),
    )
    discord_submission_draft = _generated_copy_or_fallback(
        run_dir / "submission.md",
        _fallback_discord_submission_draft(brief),
    )

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

{x_post_draft}

## Discord Submission Draft

{discord_submission_draft}

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


def _generated_copy_or_fallback(path: Path, fallback: str) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return fallback


def _fallback_x_post_draft(kimi: dict[str, Any]) -> str:
    return f"""I built Repo-to-Shorts Agent for the Hermes Agent Creative Hackathon.

Paste a repo, and Hermes runs a Kimi-directed workflow that turns code evidence into a launch-ready vertical short: narration, captions, MP4, metadata proof, and submission copy.

Kimi proof: `{kimi.get("mode", "unknown")}` via `{kimi.get("model", "unknown")}`."""


def _fallback_discord_submission_draft(brief: dict[str, Any]) -> str:
    return f"""Repo-to-Shorts Agent turns a GitHub repo or local codebase into a short-video package for launches and hackathon demos.

Hermes orchestrates the workflow. Kimi acts as creative director. The CLI writes `demo.mp4`, `metadata.json`, `captions.srt`, and this submission pack.

Generated hook: {brief.get("hook", "See generated creative brief.")}"""


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
    secret_markers = (
        "api_key=",
        "api-key=",
        "openrouter-api-key=",
        "xai-api-key=",
        "openai-api-key=",
        "token=",
        "access-token=",
        "secret=",
        "secret-key=",
        "sk-",
        "sk_or_",
    )
    return any(marker in lowered for marker in secret_markers)
