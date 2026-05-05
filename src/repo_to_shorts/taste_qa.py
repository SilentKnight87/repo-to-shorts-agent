from __future__ import annotations

from collections import Counter
from typing import Any

GENERIC_WORDS = {"seamless", "robust", "leverage", "optimize", "game-changing", "supercharge", "unleash"}
PROOF_TERMS = {"metadata", "demo.mp4", "repo", "file", "command", "artifact", "src/", "tests/"}


def score_creative_plan(brief: dict[str, Any], *, design_profile: dict[str, Any] | None = None) -> dict[str, Any]:
    scenes = [scene for scene in brief.get("scenes", []) if isinstance(scene, dict)]
    blocking: list[dict[str, str]] = []
    taste: list[dict[str, str]] = []

    if not scenes:
        blocking.append(_issue("missing_scenes", "No scenes in creative plan", "Generate at least 5 scenes for final mode."))
    if scenes and not _scene_reveals_purpose(scenes[0]):
        blocking.append(_issue("weak_hook", "First scene does not reveal project purpose or transformation", "Rewrite ColdOpen around repo transformation."))
    if not any(str(scene.get("type", "")).lower() == "ctaendcard" for scene in scenes):
        blocking.append(_issue("missing_final_cta", "No CTAEndCard scene found", "Add final scene with command, artifact, or repo link."))

    layout_counts = Counter(str(scene.get("type", "")).lower() for scene in scenes)
    for layout, count in layout_counts.items():
        if layout and count > 2:
            taste.append(_issue("layout_repetition", f"{count} scenes use layout {layout}", "Vary scene types or mark repetition as intentional."))

    for index, scene in enumerate(scenes, start=1):
        headline = str(scene.get("headline") or scene.get("narration") or "")
        word_count = len(headline.split())
        if word_count > 12:
            taste.append(_issue("caption_density_high", f"Scene {index} has {word_count} headline words", "Split into two beats or shorten to 3-7 words."))
        lowered = headline.lower()
        if any(word in lowered for word in GENERIC_WORDS):
            taste.append(_issue("generic_ai_copy", f"Scene {index} uses generic AI copy: {headline}", "Replace with repo-specific proof language."))

    if not _has_repo_specificity(brief, scenes):
        blocking.append(_issue("missing_repo_specificity", "Plan could describe any AI repo by swapping the name", "Add file, command, artifact, metadata, or architecture evidence."))

    weighted = _score(blocking, taste)
    return {
        "schema_version": 1,
        "overall": "pass" if not blocking and weighted >= 0.8 else "fail",
        "score": weighted,
        "blocking_issues": blocking,
        "taste_issues": taste,
        "allowed_to_publish": not blocking and weighted >= 0.8,
    }


def _issue(defect: str, evidence: str, fix: str) -> dict[str, str]:
    return {"defect": defect, "evidence": evidence, "fix": fix}


def _scene_reveals_purpose(scene: dict[str, Any]) -> bool:
    text = " ".join(str(scene.get(key, "")) for key in ("headline", "narration", "type")).lower()
    return any(term in text for term in ("repo", "reel", "short", "video", "trailer", "demo", "code"))


def _has_repo_specificity(brief: dict[str, Any], scenes: list[dict[str, Any]]) -> bool:
    haystack = str(brief).lower()
    if any(term in haystack for term in PROOF_TERMS):
        return True
    return any(scene.get("evidence") for scene in scenes)


def _score(blocking: list[dict[str, str]], taste: list[dict[str, str]]) -> float:
    score = 1.0
    score -= 0.25 * len(blocking)
    score -= 0.08 * len(taste)
    return max(0.0, round(score, 2))
