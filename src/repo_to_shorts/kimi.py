from __future__ import annotations

import os
from dataclasses import dataclass

from repo_to_shorts.ingest import RepoSnapshot


@dataclass(frozen=True)
class KimiCritique:
    mode: str
    text: str


def critique_story(snapshot: RepoSnapshot, audience: str, storyboard: str) -> KimiCritique:
    """Kimi critic/script-editor adapter with deterministic fallback.

    Real Kimi can be enabled later by setting KIMI_API_KEY and wiring an OpenAI-compatible
    Moonshot/Kimi chat completion call here. The MVP intentionally avoids network calls unless
    credentials and a production adapter are explicitly configured.
    """
    if os.environ.get("KIMI_API_KEY"):
        return KimiCritique(
            mode="configured-placeholder",
            text=(
                "# Kimi critic/script-editor pass\n\n"
                "KIMI_API_KEY is configured. MVP keeps generation deterministic overnight; "
                "replace `repo_to_shorts.kimi.critique_story` with the documented Moonshot/Kimi "
                "chat-completions call to enable live critique.\n\n"
                f"Editorial note: sharpen the opening promise for {audience} and keep the demo "
                f"centered on {snapshot.name}."
            ),
        )
    return KimiCritique(
        mode="deterministic-fallback",
        text=(
            "# Kimi critic/script-editor pass\n\n"
            "Mode: deterministic fallback because KIMI_API_KEY is not set.\n\n"
            "## Critique\n"
            f"- Lead with the problem before naming `{snapshot.name}`.\n"
            f"- Keep claims concrete for {audience}: input repo, extracted facts, generated launch package.\n"
            "- Show the browser demo artifact on screen; it is the fastest proof that the agent shipped assets, not notes.\n"
            "- End with the Kimi pass itself so judges see critic/editor separation.\n\n"
            "## How to enable real Kimi later\n"
            "1. Set `KIMI_API_KEY` in the runtime environment.\n"
            "2. Add a Moonshot/Kimi OpenAI-compatible chat completion call in `repo_to_shorts.kimi`.\n"
            "3. Send repo brief + storyboard, then write the returned critique into this file.\n"
        ),
    )
