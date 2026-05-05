from __future__ import annotations

import json
from pathlib import Path

from repo_to_shorts.production import write_production_manifests


def test_write_production_manifests_creates_expected_files(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    data = {
        "design_profile": {"schema_version": 1, "name": "Console"},
        "reference_pack": {"schema_version": 1, "references": []},
        "evidence_manifest": {"repo_name": "repo", "safe_files": ["README.md"]},
        "creative_brief": {"title": "Title"},
        "scene_plan": {"scenes": [{"type": "ColdOpen"}]},
        "asset_manifest": {"assets": []},
        "audio_plan": {"mode": "voiceover_with_ducked_music"},
        "qa_report": {"overall": "pass"},
    }

    written = write_production_manifests(run_dir, **data)

    assert sorted(path.name for path in written) == [
        "asset_manifest.json",
        "audio_plan.json",
        "creative_brief.json",
        "design_profile.json",
        "evidence_manifest.json",
        "qa_report.json",
        "reference_pack.json",
        "scene_plan.json",
    ]
    assert json.loads((run_dir / "production" / "design_profile.json").read_text())["name"] == "Console"


def test_write_production_manifests_creates_zeros_for_missing_keys(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    written = write_production_manifests(run_dir, design_profile={"name": "Minimal"})

    assert len(written) == 8
    assert json.loads((run_dir / "production" / "design_profile.json").read_text())["name"] == "Minimal"
    assert json.loads((run_dir / "production" / "qa_report.json").read_text()) == {}
