from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib import request

from repo_to_shorts.ingest import RepoSnapshot

DEFAULT_KIMI_MODEL = "moonshotai/kimi-k2.6"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


@dataclass(frozen=True)
class KimiCritique:
    mode: str
    text: str
    model: str | None = None
    provider: str = "none"
    fallback_reason: str | None = None


def critique_story(snapshot: RepoSnapshot, audience: str, storyboard: str, model: str | None = None) -> KimiCritique:
    """Run a live Kimi critic/script-editor pass when credentials exist, else fallback honestly."""
    selected_model = model or os.environ.get("KIMI_MODEL") or DEFAULT_KIMI_MODEL
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("KIMI_API_KEY")
    if not api_key:
        return _fallback_critique(snapshot, audience, fallback_reason="OPENROUTER_API_KEY or KIMI_API_KEY not set")

    base_url = os.environ.get("OPENROUTER_BASE_URL") or os.environ.get("KIMI_BASE_URL") or DEFAULT_OPENROUTER_BASE_URL
    prompt = build_kimi_prompt(snapshot, audience, storyboard, live_model=selected_model)
    try:
        text = _call_openrouter_api(prompt, selected_model, base_url)
    except Exception as exc:  # noqa: BLE001 - fallback should preserve CLI reliability.
        fallback = _fallback_critique(snapshot, audience, fallback_reason=f"Kimi API failed: {exc.__class__.__name__}")
        return KimiCritique(
            mode="api-error-fallback",
            text=fallback.text,
            model=selected_model,
            provider="openrouter",
            fallback_reason=f"Kimi API failed: {exc.__class__.__name__}",
        )

    return KimiCritique(
        mode="live-api",
        text=text,
        model=selected_model,
        provider="openrouter",
        fallback_reason=None,
    )


def build_kimi_prompt(snapshot: RepoSnapshot, audience: str, storyboard: str, live_model: str | None = None) -> str:
    metadata = "\n".join(f"- {key}: {value}" for key, value in snapshot.package_metadata.items()) or "- none"
    tree = "\n".join(f"- {entry}" for entry in snapshot.file_tree[:40]) or "- no files found"
    live_context = (
        f"This is a live Kimi API call through OpenRouter using model `{live_model}`. "
        "Do not describe this run as fallback-only. You may still mention that deterministic fallback exists for no-key runs."
        if live_model
        else "This is a deterministic fallback/no-key context."
    )
    return f"""You are Kimi acting as a creative critic and short-form technical video editor.

Goal: improve a Hermes Agent Creative Hackathon demo package without inventing claims.
Repo: {snapshot.name}
Target audience: {audience}
Kimi run context: {live_context}

Package metadata:
{metadata}

File tree:
{tree}

README excerpt:
{snapshot.readme[:2500]}

Recent git log:
{snapshot.git_log[:1200]}

Current git diff/stat:
{snapshot.git_diff[:1200]}

Storyboard:
{storyboard}

Return only the final answer in Markdown. Do not include reasoning or analysis.

Return:
1. Sharper 1-sentence hook.
2. Critique of the current story.
3. Revised 60-second narration.
4. Strong final CTA.
5. Any risky/unclear claims to avoid.
"""


def _call_openrouter_api(prompt: str, model: str, base_url: str) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("KIMI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY or KIMI_API_KEY not set")

    endpoint = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a creative critic and technical short-video editor."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 3000,
        "reasoning": {"enabled": False},
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.environ.get("OPENROUTER_REFERER", "https://github.com/SilentKnight87/repo-to-shorts-agent"),
        "X-Title": os.environ.get("OPENROUTER_TITLE", "Repo-to-Shorts Agent"),
    }
    req = request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with request.urlopen(req, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    message = data["choices"][0]["message"]
    return message.get("content") or message.get("reasoning") or ""


def _fallback_critique(snapshot: RepoSnapshot, audience: str, fallback_reason: str) -> KimiCritique:
    return KimiCritique(
        mode="deterministic-fallback",
        text=(
            "# Kimi critic/script-editor pass\n\n"
            f"Mode: deterministic fallback because {fallback_reason}.\n\n"
            "## Critique\n"
            f"- Lead with the problem before naming `{snapshot.name}`.\n"
            f"- Keep claims concrete for {audience}: input repo, extracted facts, generated launch package.\n"
            "- Show the browser demo artifact on screen; it is the fastest proof that the agent shipped assets, not notes.\n"
            "- End with the Kimi pass itself so judges see critic/editor separation.\n\n"
            "## How to enable live Kimi\n"
            "1. Set `OPENROUTER_API_KEY` in the runtime environment.\n"
            f"2. Use model `{DEFAULT_KIMI_MODEL}` or pass `--kimi-model`.\n"
            "3. Re-run `repo-shorts analyze` and verify `metadata.json` shows `live-api`.\n"
        ),
        model=None,
        provider="none",
        fallback_reason=fallback_reason,
    )
