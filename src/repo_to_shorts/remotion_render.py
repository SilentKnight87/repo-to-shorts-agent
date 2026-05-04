from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_ARTIFACTS = ["demo.mp4", "metadata.json", "captions.srt", "submission_pack.md"]
DEFAULT_SCENE_TYPES = [
    "ColdOpen",
    "RepoEvidence",
    "PipelineMap",
    "ArtifactStack",
    "LiveProof",
    "CTAEndCard",
]


def build_remotion_input(
    *,
    repo_name: str,
    description: str,
    key_files: list[str],
    scenes: list[dict[str, Any]],
    proof: dict[str, Any],
    artifacts: list[str] | None = None,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    duration_seconds: int = 45,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "repo": {
            "name": repo_name,
            "description": description,
            "key_files": key_files[:8],
        },
        "video": {
            "width": width,
            "height": height,
            "fps": fps,
            "duration_seconds": duration_seconds,
        },
        "proof": proof,
        "scenes": [_normalize_scene(scene, index) for index, scene in enumerate(scenes)],
        "artifacts": artifacts or DEFAULT_ARTIFACTS,
    }


def write_remotion_input(run_dir: Path, data: dict[str, Any]) -> Path:
    render_dir = Path(run_dir) / "render"
    render_dir.mkdir(parents=True, exist_ok=True)
    path = render_dir / "remotion_input.json"
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def _normalize_scene(scene: dict[str, Any], index: int) -> dict[str, Any]:
    narration = str(scene.get("narration") or "")
    return {
        "type": str(scene.get("type") or _default_scene_type(index)),
        "duration_seconds": float(scene.get("duration_seconds", 6)),
        "headline": str(
            scene.get("headline")
            or scene.get("hook")
            or _headline_from_narration(narration)
        ),
        "narration": narration,
        "evidence": [str(item) for item in scene.get("evidence", [])][:4],
        "caption_emphasis": [
            str(item) for item in scene.get("caption_emphasis", [])
        ][:5],
    }


def _default_scene_type(index: int) -> str:
    return DEFAULT_SCENE_TYPES[min(index, len(DEFAULT_SCENE_TYPES) - 1)]


def _headline_from_narration(narration: str) -> str:
    first_sentence = str(narration).split(".")[0].strip()
    return first_sentence or "Repo to Shorts"
