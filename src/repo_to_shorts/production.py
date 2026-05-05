from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MANIFEST_NAMES = {
    "design_profile": "design_profile.json",
    "reference_pack": "reference_pack.json",
    "evidence_manifest": "evidence_manifest.json",
    "creative_brief": "creative_brief.json",
    "scene_plan": "scene_plan.json",
    "asset_manifest": "asset_manifest.json",
    "audio_plan": "audio_plan.json",
    "qa_report": "qa_report.json",
}


def write_production_manifests(run_dir: Path, **manifests: dict[str, Any]) -> list[Path]:
    production_dir = run_dir / "production"
    production_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for key, filename in MANIFEST_NAMES.items():
        payload = manifests.get(key, {})
        path = production_dir / filename
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(path)
    return written
