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
    distribution_channel: str = "x_short"
    reference_pack: list = field(default_factory=list)
    visual_world: str = "cinematic engineering console"
    tone: str = "retro VHS broadcast"
    visual_style: str = ""
    motion_principles: list[str] = field(default_factory=list)
    shot_list: list[str] = field(default_factory=list)
    continuity_rules: list[str] = field(default_factory=list)
    negative_prompts: list[str] = field(default_factory=list)
    quality_bar: dict = field(default_factory=dict)


def direct(
    repo_analysis: dict,
    model: str = "moonshotai/kimi-k2.6",
    *,
    final: bool = False,
    design_profile: dict | None = None,
    reference_pack: dict | None = None,
    revision_feedback: str | None = None,
    evidence_manifest: dict | None = None,
) -> CreativeBrief:
    """Kimi 2.6 creative director: analyze repo → output creative brief."""
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("KIMI_API_KEY")
    if not api_key:
        return _deterministic_fallback(repo_analysis, model=model)

    prompt = _build_director_prompt(
        repo_analysis,
        final=final,
        design_profile=design_profile,
        reference_pack=reference_pack,
        revision_feedback=revision_feedback,
        evidence_manifest=evidence_manifest,
    )
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


def _build_director_prompt(
    analysis: dict,
    *,
    model: str = "moonshotai/kimi-k2.6",
    final: bool = False,
    design_profile: dict | None = None,
    reference_pack: dict | None = None,
    revision_feedback: str | None = None,
    evidence_manifest: dict | None = None,
) -> str:
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
        prompt = f"""You are an elite creative director making a 45-60 second 9:16 vertical short for the Nous Research Hermes Agent Creative Hackathon.

The submission video runs as a SILENT VIDEO with cinematic 80s synthwave music underneath. There is NO voiceover. The visuals must carry the entire story. Headlines on screen, kinetic typography, repo evidence — these are the storytelling tools. Treat narration as optional flavor that informs caption emphasis, not as a script that will be spoken.

The aesthetic is retro VHS broadcast deck — same energy as the project's web UI: tape labels, channel chyrons, scanlines, REC/STBY/LIVE indicators, SMPTE color bars, glitch headlines, JetBrains Mono and Avenir Next Condensed type. Stranger Things meets Drive soundtrack. Blade Runner 2049 cinematography. Builder-focused, never corporate.

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
  "title": "specific cinematic title, never generic",
  "hook": "one concrete one-sentence hook, 12-22 words max",
  "creative_direction": {{
    "angle": "the repo making the video about itself, retro VHS broadcast feel",
    "tone": "wordless VHS broadcast — late-80s news graphics meet cinematic synthwave intro",
    "visual_style": "retro VHS broadcast deck — tape labels, channel chyrons, REC/LIVE/STBY indicators, SMPTE color-bar pacing, kinetic editorial type, Carpenter/Drive/Stranger Things"
  }},
  "storyboard": [
    {{
      "type": "ColdOpen",
      "duration_seconds": 3,
      "headline": "This repo made the video you're watching.",
      "narration": "This repo made the video you're watching.",
      "evidence": ["repo_name: {analysis.get('repo_name', '')}"],
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

Music-driven scene timing — CRITICAL:
- The video plays underneath an 80s cinematic synthwave track at ~95 BPM. 4 bars ≈ 10 seconds, 2 bars ≈ 5 seconds, 8 bars ≈ 20 seconds.
- Choose scene durations from this list, in this priority: 5s, 10s, 7.5s, 4s, 8s, 12s. Avoid odd values like 7s, 9s, 11s — they feel out of phase with the music.
- The total duration must still land in 45-60s. A typical layout: 5 + 10 + 7.5 + 10 + 7.5 + 5 + 5 = 50s.
- The first scene (ColdOpen) should be 4-5s — punchy hook on the first downbeat.
- The last scene (CTAEndCard) should be 5s — clean exit on a bar boundary.

Headlines — CRITICAL:
- Each scene's `headline` is the primary visual element. Make it READ like a VHS broadcast chyron: 5-9 words, declarative, present tense, no marketing words.
- Use mono-uppercase-friendly phrases: "DEMO VIDEOS EAT 6 HOURS", "KIMI READS THE REPO", "PROOF IS IN METADATA.JSON", "SHIP THE SHORT".
- Headlines must connect to repo evidence in the same scene's `evidence` field.

Narration is optional flavor (the video is silent):
- You may write narration text — it's used for caption emphasis and submission copy — but assume nobody hears it.
- Keep narration to 1 sentence per scene, 8-15 words. Don't pad.
- The video story is told entirely through headlines + evidence + scene types + the music's natural arc.

Storyboard arc:
1. Hook (ColdOpen, 4-5s) — meta-claim about the repo making this video
2. Pain (PainPoint or RepoEvidence, 5-10s) — what's broken about demo videos today
3. Mechanism (PipelineMap, 7.5-10s) — the workflow as a flow chart
4. Proof (LiveProof, 5-7.5s) — metadata.json with kimi.mode=live-api highlighted
5. Artifacts (ArtifactStack or DemoPreview, 5-7.5s) — what comes out of the box
6. CTA (CTAEndCard, 5s) — command line + GitHub URL

Anti-patterns — never produce these:
- Generic architecture diagrams with floating boxes
- Bottom caption boxes that repeat across scenes
- Bokeh / dark blob backgrounds
- Marketing words (optimize, leverage, seamless, robust, game-changing, unleash, supercharge)
- Vague pain ("demo videos are hard") — use specifics ("6 hours screen-recording slides")
"""
    if design_profile or reference_pack:
        design_context = json.dumps(design_profile or {}, indent=2)[:4000]
        reference_context = json.dumps(reference_pack or {}, indent=2)[:4000]
        taste_block = f"""
DESIGN PROFILE:
{design_context}

REFERENCE PACK:
{reference_context}

Additional output fields required in the JSON root:
- "distribution_channel": "x_short" (the platform this short is made for)
- "reference_pack": list of reference labels used
- "visual_world": string describing the visual world (e.g. "cinematic engineering console")
- "motion_principles": list of motion rules (e.g. ["motion guides attention"])
- "shot_list": list of shot descriptions
- "continuity_rules": list of rules for scene-to-scene consistency
- "negative_prompts": list of things to explicitly avoid
"""
        prompt += taste_block
    if evidence_manifest:
        evidence_context = json.dumps(evidence_manifest, indent=2)[:4000]
        prompt += f"""

ALLOWED EVIDENCE:
{evidence_context}

Factuality rules:
- Use only values that appear in ALLOWED EVIDENCE lists: allowed_files, allowed_artifacts, allowed_commands, allowed_output_paths, allowed_components, and repo_name.
- Do not invent npm scripts, output folders, publishing steps, integrations, or files.
- Do not cite evidence keys like "allowed_commands" or "allowed_artifacts"; always use concrete values (e.g., "repo-shorts creative . --final", "README.md").
- CTAEndCard must cite one allowed command exactly (or as a substring in a short phrase, e.g., "Run: repo-shorts creative . --final").
"""
    if revision_feedback:
        prompt += f"""

REVISION FEEDBACK:
{revision_feedback}

Revise the JSON response to fix every QA failure. Do not remove source evidence. Do not add unsupported claims.
If feedback mentions missing_title, provide a repo-specific root-level "title".
If feedback mentions missing_hook, provide a root-level "hook" with repo-specific transformation framing.
For unsupported_evidence, replace any key-like evidence values with concrete allowed evidence values from the ALLOWED EVIDENCE lists.
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
    creative_direction = data.get("creative_direction", {})
    if not isinstance(creative_direction, dict):
        creative_direction = {}
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
        distribution_channel=data.get("distribution_channel", "x_short"),
        reference_pack=data.get("reference_pack", []),
        visual_world=data.get("visual_world", "cinematic engineering console"),
        tone=data.get("tone", creative_direction.get("tone", "")),
        visual_style=data.get("visual_style", creative_direction.get("visual_style", "")),
        motion_principles=data.get("motion_principles", creative_direction.get("motion_principles", [])),
        shot_list=data.get("shot_list", creative_direction.get("shot_list", [])),
        continuity_rules=data.get("continuity_rules", creative_direction.get("continuity_rules", [])),
        negative_prompts=data.get("negative_prompts", creative_direction.get("negative_prompts", [])),
        quality_bar=data.get("quality_bar", creative_direction.get("quality_bar", {})),
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
