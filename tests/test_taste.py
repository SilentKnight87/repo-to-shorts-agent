from __future__ import annotations

from pathlib import Path

from repo_to_shorts.taste import build_reference_pack, load_design_profile


def test_load_design_profile_reads_frontmatter(tmp_path: Path):
    design = tmp_path / "DESIGN.md"
    design.write_text(
        """---
name: Repo-to-Shorts Cinematic Console
colors:
  neutral: "#080A0F"
  tertiary: "#6EE7F9"
rounded:
  md: 8px
---

## Overview
Terminal-native, premium, fast, and credible.
""",
        encoding="utf-8",
    )

    profile = load_design_profile(design)

    assert profile["name"] == "Repo-to-Shorts Cinematic Console"
    assert profile["colors"]["neutral"] == "#080A0F"
    assert profile["rounded"]["md"] == "8px"
    assert "Terminal-native" in profile["notes"]


def test_load_design_profile_fallback_when_missing(tmp_path: Path):
    profile = load_design_profile(tmp_path / "missing.md")

    assert profile["name"] == "Repo-to-Shorts Default Taste"
    assert profile["colors"]["neutral"] == "#080A0F"
    assert profile["source"] is None


def test_build_reference_pack_uses_design_and_taste_research(tmp_path: Path):
    design = tmp_path / "DESIGN.md"
    taste = tmp_path / "taste-research.md"
    design.write_text("---\nname: Console\n---\n## Do\nUse references before generating.", encoding="utf-8")
    taste.write_text(
        "# Taste\n\n## X signals gathered\n\n### 1. References beat vibes\n\nImplementation implication:\n- Add a `reference_pack` concept.\n",
        encoding="utf-8",
    )

    pack = build_reference_pack(design, taste)

    assert pack["schema_version"] == 1
    assert pack["sources"][0]["path"].endswith("DESIGN.md")
    assert pack["references"][0]["label"] == "premium console"
    assert "generic AI SaaS soup" in pack["avoid"]


def test_build_reference_pack_handles_missing_files(tmp_path: Path):
    pack = build_reference_pack(tmp_path / "missing-design.md", tmp_path / "missing-taste.md")

    assert pack["schema_version"] == 1
    assert pack["sources"] == []
    assert len(pack["references"]) == 2
