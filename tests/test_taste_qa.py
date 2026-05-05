from __future__ import annotations

from repo_to_shorts.taste_qa import score_creative_plan


def test_score_creative_plan_passes_specific_postable_plan():
    brief = {
        "title": "Repo Becomes Reel",
        "distribution_channel": "x_short",
        "scenes": [
            {"type": "ColdOpen", "headline": "REPO BECOMES REEL", "duration_seconds": 5, "evidence": ["repo_name"]},
            {"type": "PipelineMap", "headline": "KIMI READS THE REPO", "duration_seconds": 10, "evidence": ["src/pipeline.py"]},
            {"type": "LiveProof", "headline": "PROOF IN METADATA", "duration_seconds": 7.5, "evidence": ["metadata.json"]},
            {"type": "ArtifactStack", "headline": "SHORT PACKAGE BUILT", "duration_seconds": 7.5, "evidence": ["demo.mp4"]},
            {"type": "CTAEndCard", "headline": "SHIP THE SHORT", "duration_seconds": 5, "evidence": ["repo-shorts creative"]},
        ],
    }

    report = score_creative_plan(brief, design_profile={"colors": {"neutral": "#080A0F"}})

    assert report["overall"] == "pass"
    assert report["allowed_to_publish"] is True
    assert report["score"] >= 0.8
    assert report["blocking_issues"] == []


def test_score_creative_plan_fails_generic_slop():
    brief = {
        "title": "Introducing an AI-powered workflow",
        "scenes": [
            {"type": "ColdOpen", "headline": "INTRODUCING SEAMLESS AI POWERED WORKFLOW FOR YOUR ENTIRE TEAM TO OPTIMIZE EVERYTHING TODAY", "duration_seconds": 4, "evidence": []},
            {"type": "Card", "headline": "OPTIMIZE YOUR WORKFLOW WITH AI POWERED TOOLS", "duration_seconds": 4, "evidence": []},
            {"type": "Card", "headline": "LEVERAGE ROBUST AUTOMATION", "duration_seconds": 4, "evidence": []},
        ],
    }

    report = score_creative_plan(brief, design_profile={})

    assert report["overall"] == "fail"
    assert report["allowed_to_publish"] is False
    defects = {issue["defect"] for issue in report["blocking_issues"] + report["taste_issues"]}
    assert "missing_repo_specificity" in defects
    assert "caption_density_high" in defects
    assert "missing_final_cta" in defects


def test_score_creative_plan_empty_scenes():
    brief = {"title": "Empty", "scenes": []}

    report = score_creative_plan(brief, design_profile={})

    assert report["overall"] == "fail"
    assert report["allowed_to_publish"] is False
    defects = {issue["defect"] for issue in report["blocking_issues"]}
    assert "missing_scenes" in defects


def test_score_creative_plan_flags_weak_hook():
    brief = {
        "title": "Bad Hook",
        "scenes": [
            {"type": "ColdOpen", "headline": "WELCOME TO THE SHOW", "duration_seconds": 4, "evidence": []},
            {"type": "Card", "headline": "Something happens", "duration_seconds": 4, "evidence": []},
            {"type": "CTAEndCard", "headline": "CTA", "duration_seconds": 4, "evidence": []},
        ],
    }

    report = score_creative_plan(brief, design_profile={})

    defects = {issue["defect"] for issue in report["blocking_issues"]}
    assert "weak_hook" in defects
