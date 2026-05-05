from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


def score_rendered_visual_artifacts(
    metadata: dict[str, Any],
    *,
    run_dir: Path | None = None,
) -> dict[str, Any]:
    brief = metadata.get("creative_brief") or {}
    scenes = [scene for scene in brief.get("scenes", []) if isinstance(scene, dict)]
    render_manifest: dict[str, Any] = {}
    issues = []
    blocking = []
    visual = []
    render_metadata = metadata.get("render") or {}

    if not scenes:
        blocking.append(_issue("missing_scenes_for_render_qa", "No scenes in creative brief for render QA", "Generate a full scene plan with at least 5 scenes."))
        return {"blocking_issues": blocking, "taste_issues": [], "visual_issues": visual}

    if run_dir is not None:
        input_path = Path(run_dir) / "render" / "remotion_input.json"
        if input_path.exists():
            render_manifest = _load_json(input_path)
            if render_metadata.get("renderer") == "remotion":
                issues.extend(_validate_remotion_manifest(render_manifest, len(scenes)))

    render_scenes = [
        scene for scene in render_manifest.get("scenes", []) if isinstance(scene, dict)
    ] or scenes
    layout_counts = Counter(str(scene.get("layout") or scene.get("visual_role") or "").lower() for scene in render_scenes)
    unique_layouts = [layout for layout in layout_counts if layout]
    if not unique_layouts:
        visual.append(_issue("render_visual_layout_missing", "Scenes do not define any layout metadata", "Add per-scene layout or visual_role from the creative director."))
    elif len(unique_layouts) == 1 and len(scenes) > 2:
        visual.append(_issue("render_layout_monotony", "Every scene uses the same layout", "Vary layout/visual role across scenes to show progression."))

    creative_direction = render_manifest.get("creative_direction", {})
    if not isinstance(creative_direction, dict):
        creative_direction = {}
    visual_world = brief.get("visual_world") or creative_direction.get("visual_world")
    motion_principles = brief.get("motion_principles") or creative_direction.get("motion_principles")
    if not (str(visual_world or "").strip()):
        visual.append(_issue("missing_visual_world", "Missing creative visual world description", "Set creative_direction.visual_world with a concrete style direction."))
    if not motion_principles:
        visual.append(_issue("missing_motion_principles", "Missing motion principles", "Set motion principles to guide transitions and pacing."))

    return {
        "blocking_issues": blocking,
        "taste_issues": [],
        "visual_issues": issues + visual,
    }


def _validate_remotion_manifest(manifest: dict[str, Any], scene_count: int) -> list[dict[str, str]]:
    if not manifest or not isinstance(manifest, dict):
        return [_issue("invalid_remotion_manifest", "Remotion manifest missing", "Re-run render input generation.")]
    if len(manifest.get("scenes", [])) != scene_count:
        return [_issue(
            "remotion_scene_count_mismatch",
            "Remotion scene count does not match creative brief",
            "Fix input synthesis to include the same scenes passed to rendering.",
        )]
    return []


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _issue(defect: str, evidence: str, fix: str) -> dict[str, str]:
    return {"defect": defect, "evidence": evidence, "fix": fix}
