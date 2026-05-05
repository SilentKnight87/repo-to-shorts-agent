from __future__ import annotations

from collections import Counter
from typing import Any

from repo_to_shorts.visual_qa import score_rendered_visual_artifacts

GENERIC_WORDS = {"seamless", "robust", "leverage", "optimize", "game-changing", "supercharge", "unleash"}
PROOF_TERMS = {"metadata", "demo.mp4", "file", "command", "artifact", "src/", "tests/"}


def score_creative_plan(
    brief: dict[str, Any],
    *,
    design_profile: dict[str, Any] | None = None,
    evidence_manifest: dict[str, Any] | None = None,
    mode: str = "final",
) -> dict[str, Any]:
    scenes = [scene for scene in brief.get("scenes", []) if isinstance(scene, dict)]
    blocking: list[dict[str, str]] = []
    factual: list[dict[str, str]] = []
    taste: list[dict[str, str]] = []
    visual: list[dict[str, str]] = []

    if mode == "final" and not _valid_text(brief.get("title"), min_words=4):
        blocking.append(_issue("missing_title", "Creative brief title is empty, generic, or still Untitled", "Write a repo-specific title with the product name and transformation."))
    if mode == "final" and not _valid_text(brief.get("hook"), min_words=5):
        blocking.append(_issue("missing_hook", "Creative brief hook is empty or too thin", "Write a concrete one-sentence hook that explains the repo transformation."))

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

    allowed = _allowed_evidence(evidence_manifest)
    if mode == "final":
        unsupported = []
        for index, scene in enumerate(scenes, start=1):
            evidence = _scene_evidence_values(scene)
            if not evidence:
                unsupported.append(f"scene {index}: no evidence")
                continue
            for value in evidence:
                if allowed and not _evidence_supported(value, allowed):
                    unsupported.append(f"scene {index}: {value}")
        if unsupported:
            factual.append(_issue("unsupported_evidence", "; ".join(unsupported[:5]), "Use only evidence from production/evidence_manifest.json."))

    cta = _cta_scene(scenes)
    if mode == "final" and cta:
        cta_text = " ".join([str(cta.get("headline", "")), str(cta.get("narration", "")), " ".join(_scene_evidence_values(cta))])
        forbidden = _contains_forbidden_claim(cta_text, evidence_manifest)
        if forbidden:
            factual.append(_issue("invalid_cta_command", f"CTA contains forbidden claim: {forbidden}", "Use the real repo-shorts creative/analyze CLI command."))
        elif not _contains_allowed_command(cta_text, evidence_manifest):
            factual.append(_issue("invalid_cta_command", "CTA does not include an allowed command", "Use one command from evidence_manifest.allowed_commands."))

    weighted = _score(blocking + factual, taste + visual)
    return {
        "schema_version": 2,
        "mode": mode,
        "overall": "pass" if not blocking and not factual and weighted >= 0.8 else "fail",
        "score": weighted,
        "blocking_issues": blocking,
        "factual_issues": factual,
        "taste_issues": taste,
        "visual_issues": visual,
        "revision_prompt": _revision_prompt(blocking + factual + taste + visual),
        "allowed_to_publish": not blocking and not factual and weighted >= 0.8,
    }


def score_rendered_artifact(
    *,
    metadata: dict[str, Any],
    evidence_manifest: dict[str, Any] | None = None,
    run_dir=None,
) -> dict[str, Any]:
    brief = metadata.get("creative_brief") or {}
    brief_report = score_creative_plan(
        brief,
        evidence_manifest=evidence_manifest,
        mode="final",
    )
    blocking = list(brief_report["blocking_issues"])
    factual = list(brief_report.get("factual_issues", []))
    taste = list(brief_report.get("taste_issues", []))
    visual = list(brief_report.get("visual_issues", []))

    visual_report = score_rendered_visual_artifacts(metadata, run_dir=run_dir)
    blocking.extend(visual_report.get("blocking_issues", []))
    factual.extend(visual_report.get("factual_issues", []))
    visual.extend(visual_report.get("visual_issues", []))

    validation = ((metadata.get("render") or {}).get("validation") or {})
    if not validation.get("ok"):
        blocking.append(_issue("media_validation_failed", "; ".join(validation.get("errors") or ["media validation failed"]), "Fix render duration, resolution, audio, or file output."))

    artifacts = set(metadata.get("artifacts") or [])
    for required in ("demo.mp4", "metadata.json", "captions.srt", "submission_pack.md", "production/qa_report.json"):
        if required not in artifacts:
            blocking.append(_issue("missing_required_artifact", required, "Add required artifact to metadata.artifacts and write it to the run directory."))

    weighted = _score(blocking + factual, taste + visual)
    return {
        "schema_version": 2,
        "mode": "rendered_artifact",
        "overall": "pass" if not blocking and not factual and weighted >= 0.8 else "fail",
        "score": weighted,
        "blocking_issues": blocking,
        "factual_issues": factual,
        "taste_issues": taste,
        "visual_issues": visual,
        "revision_prompt": _revision_prompt(blocking + factual + taste + visual),
        "allowed_to_publish": not blocking and not factual and weighted >= 0.8,
    }


def _merge_qa_reports(pre_render: dict, post_render: dict) -> dict:
    if pre_render is post_render:
        return pre_render
    blocking = list(pre_render.get("blocking_issues", [])) + list(post_render.get("blocking_issues", []))
    factual = list(pre_render.get("factual_issues", [])) + list(post_render.get("factual_issues", []))
    taste = list(pre_render.get("taste_issues", [])) + list(post_render.get("taste_issues", []))
    visual = list(pre_render.get("visual_issues", [])) + list(post_render.get("visual_issues", []))
    score = min(float(pre_render.get("score", 0)), float(post_render.get("score", 0)))
    return {
        "schema_version": 2,
        "mode": "combined",
        "overall": "pass" if not blocking and not factual and score >= 0.8 else "fail",
        "score": score,
        "blocking_issues": blocking,
        "factual_issues": factual,
        "taste_issues": taste,
        "visual_issues": visual,
        "revision_prompt": _revision_prompt(blocking + factual + taste + visual),
        "allowed_to_publish": not blocking and not factual and score >= 0.8,
        "pre_render": pre_render,
        "post_render": post_render,
    }


def _valid_text(value: object, *, min_words: int = 3) -> bool:
    text = str(value or "").strip()
    if not text or text.lower() in {"untitled", "title", "draft"}:
        return False
    return len(text.split()) >= min_words


def _allowed_evidence(evidence_manifest: dict[str, Any] | None) -> set[str]:
    if not evidence_manifest:
        return set()
    values: set[str] = set()
    for key in ("allowed_files", "allowed_artifacts", "allowed_commands", "allowed_output_paths", "allowed_components"):
        for item in evidence_manifest.get(key, []) or []:
            values.add(str(item).lower())
    repo_name = evidence_manifest.get("repo_name")
    if repo_name:
        values.add(f"repo_name: {repo_name}".lower())
        values.add(str(repo_name).lower())
    return values


def _scene_evidence_values(scene: dict[str, Any]) -> list[str]:
    raw = scene.get("evidence") or []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(item) for item in raw if str(item).strip()]
    return []


def _evidence_supported(value: str, allowed: set[str]) -> bool:
    lowered = value.lower().strip()
    if lowered in allowed:
        return True
    for token in allowed:
        token = token.strip().lower()
        if not token:
            continue
        if " " in token and token in lowered:
            return True
        if "/" in token and token in lowered:
            return True
        if "." in token and token in lowered:
            return True
        if token in {"metadata.json", "demo.mp4", "captions.srt", "submission_pack.md", "production/qa_report.json"} and token in lowered:
            return True
    return False


def _cta_scene(scenes: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((scene for scene in scenes if str(scene.get("type", "")).lower() == "ctaendcard"), None)


def _contains_allowed_command(text: str, evidence_manifest: dict[str, Any] | None) -> bool:
    lowered = text.lower()
    commands = [str(cmd).lower() for cmd in (evidence_manifest or {}).get("allowed_commands", [])]
    return any(cmd in lowered for cmd in commands)


def _contains_forbidden_claim(text: str, evidence_manifest: dict[str, Any] | None) -> str | None:
    lowered = text.lower()
    for claim in (evidence_manifest or {}).get("forbidden_claims", []) or []:
        claim_text = str(claim).lower()
        if claim_text and claim_text in lowered:
            return str(claim)
    return None


def _revision_prompt(issues: list[dict[str, str]]) -> str:
    if not issues:
        return ""
    lines = ["Revise the creative brief. Fix these QA failures without adding unsupported claims:"]
    for issue in issues[:8]:
        lines.append(f"- {issue['defect']}: {issue['evidence']} Fix: {issue['fix']}")
    return "\n".join(lines)


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
