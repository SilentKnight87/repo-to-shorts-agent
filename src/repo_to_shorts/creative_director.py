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
    mode: str = "deterministic-fallback"
    provider: str = "openrouter"
    model: str = "moonshotai/kimi-k2.6"
    fallback_reason: str | None = None


def direct(repo_analysis: dict, model: str = "moonshotai/kimi-k2.6", *, final: bool = False) -> CreativeBrief:
    """Kimi 2.6 creative director: analyze repo → output creative brief."""
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("KIMI_API_KEY")
    if not api_key:
        return _deterministic_fallback(repo_analysis, model=model)

    prompt = _build_director_prompt(repo_analysis, final=final)
    try:
        response = _call_openrouter_api(
            prompt,
            model,
            "https://openrouter.ai/api/v1",
            response_format={"type": "json_object"},
        )
        brief = _parse_brief(response)
        brief.mode = "live-api"
        brief.provider = "openrouter"
        brief.model = model
        brief.fallback_reason = None
        return brief
    except Exception as exc:  # noqa: BLE001 - fallback should preserve CLI reliability.
        return _deterministic_fallback(
            repo_analysis,
            mode="api-error-fallback",
            provider="openrouter",
            model=model,
            fallback_reason=f"Kimi API failed: {exc.__class__.__name__}",
        )


def _build_director_prompt(analysis: dict, *, final: bool = False) -> str:
    """Build the creative director prompt from repo analysis."""
    prompt = f"""You are an elite creative director making a hackathon demo video that must feel like Runway/Linear, not a generated slideshow.
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
    if final:
        prompt = f"""You are an elite creative director making a hackathon demo video that must feel like Runway/Linear, not a generated slideshow.
Your job is to convert code evidence into a sharp 45-60 second vertical short with a real point of view.

REPO: {analysis.get('repo_name')}
DESCRIPTION: {analysis.get('description', '')}
LANGUAGE: {analysis.get('primary_language', '')}
KEY_FILES: {analysis.get('key_files', [])}
COMPONENTS: {analysis.get('components', [])}
PURPOSE: {analysis.get('purpose', '')}
AUDIENCE: technical builders, hackathon judges, AI agent people

Output valid JSON only as a root object with this exact schema:
{{
  "schema_version": 1,
  "creative_direction": {{
    "angle": "meta demo",
    "tone": "sharp, cinematic, builder-focused",
    "visual_style": "retro-futuristic editorial"
  }},
  "storyboard": [
    {{
      "type": "ColdOpen",
      "duration_seconds": 3,
      "headline": "This repo made the video you're watching.",
      "narration": "This repo made the video you're watching.",
      "evidence": ["repo_name"],
      "caption_emphasis": ["repo", "video"]
    }}
  ],
  "quality_bar": {{
    "avoid": ["generic architecture slide", "bottom caption box", "fake proof"],
    "must_show": ["live Kimi proof", "generated MP4", "repo evidence"]
  }},
  "music_mood": "electronic|orchestral|minimal",
  "total_duration": 45
}}

Scene type vocabulary (use these exact type names):
- ColdOpen: 1.5-3s, huge kinetic hook, product clear in one glance.
- RepoEvidence: repo name, purpose, key files, language/framework when available.
- PainPoint: fast text beat about demo-making friction.
- PipelineMap: ingest -> Kimi brief -> render -> artifacts.
- ArtifactStack: repo brief, storyboard, narration, captions, MP4, metadata, submission copy.
- LiveProof: highlight metadata.json Kimi fields and render validation.
- DemoPreview: stylized browser/phone preview of the generated package or MP4.
- CTAEndCard: command, output folder, final promise.

Final export constraints:
- Total runtime must be 45-60 seconds.
- Use at least 5 scenes and at most 8 scenes.
- Use concrete repo evidence from KEY_FILES and COMPONENTS.
- Do not include .env, secret, token, private key, credential, or generated run files in visual evidence or narration.
- Make the first 3 seconds understandable without audio.
- Include a final CTA suitable for a hackathon submission.
- Every scene must have one primary visual idea.
- Every claim must connect to repo evidence, generated artifact evidence, or metadata proof.
- Do not make generic architecture slides, floating cards for their own sake, dark blob backgrounds, or repeated architecture slides.
"""
    return prompt


def _deterministic_fallback(
    analysis: dict,
    *,
    mode: str = "deterministic-fallback",
    provider: str = "openrouter",
    model: str = "moonshotai/kimi-k2.6",
    fallback_reason: str | None = None,
) -> CreativeBrief:
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
        mode=mode,
        provider=provider,
        model=model,
        fallback_reason=fallback_reason,
    )


_SCENE_TYPE_TO_VISUAL_TOOL: dict[str, str] = {
    "coldopen": "pretext",
    "repoevidence": "svg",
    "painpoint": "ascii",
    "pipelinemap": "svg",
    "artifactstack": "ascii",
    "liveproof": "manim",
    "demopreview": "manim",
    "ctaendcard": "pretext",
}


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
    raw_scenes = data.get("storyboard") or data.get("scenes", [])
    scenes = [_normalize_scene(scene) for scene in raw_scenes]
    return CreativeBrief(
        style=data.get("style", "dark-terminal"),
        title=data.get("title", "Untitled"),
        hook=data.get("hook", ""),
        scenes=scenes,
        music_mood=data.get("music_mood", "ambient"),
        total_duration=data.get("total_duration", 60),
        mode=data.get("mode", "deterministic-fallback"),
        provider=data.get("provider", "openrouter"),
        model=data.get("model", "moonshotai/kimi-k2.6"),
        fallback_reason=data.get("fallback_reason"),
    )


def _normalize_scene(scene: dict) -> dict:
    """Normalize a scene dict from old or new schema into a unified shape."""
    normalized = dict(scene)
    # Ensure new fields exist
    normalized.setdefault("type", normalized.get("visual_tool", "statement").title())
    normalized.setdefault("headline", normalized.get("hook", ""))
    normalized.setdefault("evidence", [])
    normalized.setdefault("caption_emphasis", [])
    # Ensure backward-compatible fields exist for manim renderer
    scene_type = str(normalized.get("type", "")).lower()
    normalized.setdefault("visual_tool", _SCENE_TYPE_TO_VISUAL_TOOL.get(scene_type, "pretext"))
    normalized.setdefault("transition", "fade")
    normalized.setdefault("music_mood", "tension")
    return normalized


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
