from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from repo_to_shorts.kimi import _call_openrouter_api


@dataclass
class CreativeBrief:
    style: str
    title: str
    hook: str
    scenes: list = field(default_factory=list)
    music_mood: str = "ambient"
    total_duration: int = 60


def direct(repo_analysis: dict, model: str = "moonshotai/kimi-k2.6") -> CreativeBrief:
    """Kimi 2.6 creative director: analyze repo → output creative brief."""
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("KIMI_API_KEY")
    if not api_key:
        return _deterministic_fallback(repo_analysis)

    prompt = _build_director_prompt(repo_analysis)
    try:
        response = _call_openrouter_api(prompt, model, "https://openrouter.ai/api/v1")
        return _parse_brief(response)
    except Exception:  # noqa: BLE001 - fallback should preserve CLI reliability.
        return _deterministic_fallback(repo_analysis)


def _build_director_prompt(analysis: dict) -> str:
    """Build the creative director prompt from repo analysis."""
    return f"""You are an elite creative director making a hackathon demo video that must feel like Runway/Linear, not a generated slideshow.
Your job is to convert code evidence into a sharp 60-second vertical short with a real point of view.

REPO: {analysis.get('repo_name')}
DESCRIPTION: {analysis.get('description', '')}
LANGUAGE: {analysis.get('primary_language', '')}
KEY_FILES: {analysis.get('key_files', [])}
COMPONENTS: {analysis.get('components', [])}
PURPOSE: {analysis.get('purpose', '')}
AUDIENCE: technical builders, hackathon judges, AI agent people

Output valid JSON only:
{{
  "style": "dark-terminal|clean-academic|playful|cinematic",
  "title": "specific cinematic title, not generic",
  "hook": "opening hook line, 5-10 words, strong",
  "scenes": [
    {{
      "duration_seconds": 8,
      "visual_tool": "pretext|svg|manim|ascii",
      "narration": "spoken narration, 1-2 sentences, concrete and visual",
      "music_mood": "tension|reveal|energy|calm",
      "transition": "cut|fade|slide-left|zoom"
    }}
  ],
  "music_mood": "electronic|orchestral|minimal",
  "total_duration": 60
}}

Creative rules:
- 5 scenes totaling exactly 60 seconds.
- Do NOT list files as narration. Use files/components as proof underneath the story.
- Say what the repo makes possible, why it matters, and what the viewer should feel.
- Use strong verbs and concrete imagery. No vague SaaS words: optimize, leverage, seamless, robust, game-changing.
- Scene arc: hook → problem → mechanism → proof → payoff.
- Keep narration speakable. Short sentences. No corporate mush.
- For this app specifically, emphasize the meta demo: the app generates the video that presents the app.
"""


def _deterministic_fallback(analysis: dict) -> CreativeBrief:
    """Fallback when no API key — still decent, not slop."""
    repo = analysis.get("repo_name", "This Repo")
    return CreativeBrief(
        style="dark-terminal",
        title=f"{repo}: The Repo That Edits Itself Into a Trailer",
        hook="A codebase walks into a cinema.",
        scenes=[
            {"duration_seconds": 8, "visual_tool": "pretext",
             "narration": f"This is {repo}. Not a README summary. A machine that turns source code into a watchable launch story.",
             "music_mood": "tension", "transition": "fade"},
            {"duration_seconds": 12, "visual_tool": "svg",
             "narration": "The problem is simple: great repos still need explanation. This one scans the code, finds the signal, and builds the narrative spine.",
             "music_mood": "reveal", "transition": "cut"},
            {"duration_seconds": 16, "visual_tool": "manim",
             "narration": "Hermes handles the workflow. Kimi plays creative director. The renderer turns architecture into motion instead of dumping bullets on a slide.",
             "music_mood": "energy", "transition": "slide-left"},
            {"duration_seconds": 14, "visual_tool": "ascii",
             "narration": "Every claim is tied back to code evidence: files, components, metadata, and a generated MP4 packaged for review.",
             "music_mood": "energy", "transition": "fade"},
            {"duration_seconds": 10, "visual_tool": "pretext",
             "narration": "And the demo is meta: this app generates the video that sells the app. That is the whole trick.",
             "music_mood": "calm", "transition": "fade"},
        ],
        music_mood="electronic",
        total_duration=60,
    )


def _parse_brief(content: str) -> CreativeBrief:
    """Parse JSON response from Kimi into CreativeBrief."""
    # Handle possible markdown code fences
    text = content.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    data = _loads_brief_json(text)
    return CreativeBrief(
        style=data.get("style", "dark-terminal"),
        title=data.get("title", "Untitled"),
        hook=data.get("hook", ""),
        scenes=data.get("scenes", []),
        music_mood=data.get("music_mood", "ambient"),
        total_duration=data.get("total_duration", 60),
    )


def _loads_brief_json(text: str) -> dict:
    """Load a JSON object from model output, tolerating prose around it."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        data = json.loads(text[start : end + 1], strict=False)
    if not isinstance(data, dict):
        raise ValueError("Creative brief must be a JSON object")
    return data
