from __future__ import annotations

from repo_to_shorts.taste_qa import score_creative_plan, score_rendered_artifact


def _evidence_manifest() -> dict:
    return {
        "schema_version": 2,
        "repo_name": "repo-to-shorts-agent",
        "allowed_files": ["README.md", "src/repo_to_shorts/cli.py"],
        "allowed_artifacts": ["demo.mp4", "metadata.json", "captions.srt", "submission_pack.md"],
        "allowed_commands": ["repo-shorts creative . --final", "repo-shorts analyze . --out runs"],
        "allowed_output_paths": ["runs/<timestamp>-repo-to-shorts-agent/"],
        "forbidden_claims": ["npm run build-short", "./dist/shorts/"],
    }


def test_score_creative_plan_passes_specific_postable_plan():
    brief = {
        "title": "Repo-to-Shorts Creates Launch Video from Code",
        "hook": "A codebase becomes a polished short-video package.",
        "distribution_channel": "x_short",
        "scenes": [
            {"type": "ColdOpen", "headline": "REPO BECOMES REEL", "duration_seconds": 5, "evidence": ["README.md"]},
            {"type": "PipelineMap", "headline": "KIMI READS THE REPO", "duration_seconds": 10, "evidence": ["src/repo_to_shorts/cli.py"]},
            {"type": "LiveProof", "headline": "PROOF IN METADATA", "duration_seconds": 7.5, "evidence": ["metadata.json"]},
            {"type": "ArtifactStack", "headline": "SHORT PACKAGE BUILT", "duration_seconds": 7.5, "evidence": ["demo.mp4"]},
            {"type": "CTAEndCard", "headline": "SHIP THE SHORT", "duration_seconds": 5, "evidence": ["repo-shorts creative . --final"]},
        ],
    }

    report = score_creative_plan(brief, design_profile={"colors": {"neutral": "#080A0F"}}, evidence_manifest=_evidence_manifest(), mode="final")

    assert report["overall"] == "pass"
    assert report["allowed_to_publish"] is True
    assert report["score"] >= 0.8
    assert report["blocking_issues"] == []


def test_score_creative_plan_fails_generic_slop():
    brief = {
        "title": "Introducing an AI-powered workflow for teams",
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
    brief = {"title": "Empty Title Here", "scenes": []}

    report = score_creative_plan(brief, design_profile={})

    assert report["overall"] == "fail"
    assert report["allowed_to_publish"] is False
    defects = {issue["defect"] for issue in report["blocking_issues"]}
    assert "missing_scenes" in defects


def test_score_creative_plan_flags_weak_hook():
    brief = {
        "title": "Bad Hook Demo Plan Test",
        "scenes": [
            {"type": "ColdOpen", "headline": "WELCOME TO THE SHOW", "duration_seconds": 4, "evidence": []},
            {"type": "Card", "headline": "Something happens", "duration_seconds": 4, "evidence": []},
            {"type": "CTAEndCard", "headline": "CTA", "duration_seconds": 4, "evidence": []},
        ],
    }

    report = score_creative_plan(brief, design_profile={})

    defects = {issue["defect"] for issue in report["blocking_issues"]}
    assert "weak_hook" in defects


def test_score_creative_plan_blocks_untitled_empty_hook_and_fake_cta():
    brief = {
        "title": "Untitled",
        "hook": "",
        "scenes": [
            {"type": "ColdOpen", "headline": "THIS REPO MADE THIS VIDEO", "duration_seconds": 5, "evidence": ["README.md"]},
            {"type": "PipelineMap", "headline": "REPO BRIEF SCENES RENDER SHIP", "duration_seconds": 10, "evidence": ["src/repo_to_shorts/cli.py"]},
            {"type": "LiveProof", "headline": "PROOF IS IN METADATA.JSON", "duration_seconds": 7.5, "evidence": ["metadata.json"]},
            {"type": "ArtifactStack", "headline": "MP4 CAPTIONS SUBMISSION COPY", "duration_seconds": 10, "evidence": ["demo.mp4", "captions.srt"]},
            {"type": "CTAEndCard", "headline": "NPM RUN BUILD-SHORT", "duration_seconds": 5, "evidence": ["output folder: ./dist/shorts/"]},
        ],
    }

    report = score_creative_plan(brief, evidence_manifest=_evidence_manifest(), mode="final")

    assert report["allowed_to_publish"] is False
    defects = {issue["defect"] for issue in report["blocking_issues"] + report["factual_issues"]}
    assert "missing_title" in defects
    assert "missing_hook" in defects
    assert "invalid_cta_command" in defects
    assert "unsupported_evidence" in defects
    assert report["revision_prompt"]


def test_score_creative_plan_accepts_real_cli_cta_and_evidence():
    brief = {
        "title": "Repo-to-Shorts Turns Code Into Launch Video",
        "hook": "A repo becomes a validated short-video package.",
        "scenes": [
            {"type": "ColdOpen", "headline": "THIS REPO MADE THIS VIDEO", "duration_seconds": 5, "evidence": ["README.md"]},
            {"type": "PipelineMap", "headline": "KIMI READS THE REPO", "duration_seconds": 10, "evidence": ["src/repo_to_shorts/cli.py"]},
            {"type": "LiveProof", "headline": "PROOF IS IN METADATA.JSON", "duration_seconds": 7.5, "evidence": ["metadata.json"]},
            {"type": "ArtifactStack", "headline": "MP4 CAPTIONS SUBMISSION COPY", "duration_seconds": 10, "evidence": ["demo.mp4", "captions.srt"]},
            {"type": "CTAEndCard", "headline": "REPO-SHORTS CREATIVE DOT FINAL", "duration_seconds": 5, "evidence": ["repo-shorts creative . --final"]},
        ],
    }

    report = score_creative_plan(brief, evidence_manifest=_evidence_manifest(), mode="final")

    assert report["overall"] == "pass"
    assert report["allowed_to_publish"] is True
    assert report["blocking_issues"] == []
    assert report["factual_issues"] == []


def test_score_creative_plan_accepts_allowed_evidence_substrings():
    brief = {
        "title": "Repo-to-Shorts Turns Code Into Launch Video",
        "hook": "A repo becomes a validated short-video package.",
        "scenes": [
            {"type": "ColdOpen", "headline": "THIS REPO MADE THIS VIDEO", "duration_seconds": 5, "evidence": ["README.md exists"]},
            {"type": "PipelineMap", "headline": "KIMI READS THE REPO", "duration_seconds": 10, "evidence": ["repo-shorts creative . --final"]},
            {"type": "LiveProof", "headline": "PROOF IS IN METADATA", "duration_seconds": 7.5, "evidence": ["metadata.json in production/qa_report.json"]},
            {"type": "ArtifactStack", "headline": "SHORT PACKAGE BUILT", "duration_seconds": 7.5, "evidence": ["captions.srt", "demo.mp4 available"]},
            {"type": "CTAEndCard", "headline": "RUN THE COMMAND", "duration_seconds": 5, "evidence": ["repo-shorts analyze . --out runs"]},
        ],
    }

    report = score_creative_plan(brief, evidence_manifest=_evidence_manifest(), mode="final")

    factual = {issue["defect"] for issue in report["factual_issues"]}
    assert "unsupported_evidence" not in factual


def test_score_rendered_artifact_blocks_bad_validation_and_missing_metadata():
    report = score_rendered_artifact(
        metadata={
            "creative_brief": {"title": "Untitled", "hook": "", "scenes": []},
            "kimi": {"mode": "live-api"},
            "render": {"validation": {"ok": False, "errors": ["duration must be 43-62 seconds"]}},
            "artifacts": ["demo.mp4"],
        },
        evidence_manifest=_evidence_manifest(),
    )

    assert report["allowed_to_publish"] is False
    defects = {issue["defect"] for issue in report["blocking_issues"]}
    assert "media_validation_failed" in defects
    assert "missing_required_artifact" in defects
    assert "missing_title" in defects


def test_score_creative_plan_rejects_live_run_with_untitled_and_fake_npm_cta():
    bad_live_brief = {
        "title": "Untitled",
        "hook": "",
        "scenes": [
            {"type": "ColdOpen", "headline": "THIS REPO MADE THIS VIDEO", "duration_seconds": 5, "evidence": ["repo_name: repo-to-shorts-agent", "README.md exists", "live render pipeline active"]},
            {"type": "PainPoint", "headline": "DEMO VIDEOS EAT SIX HOURS", "duration_seconds": 7.5, "evidence": ["docs/PRD.md"]},
            {"type": "PipelineMap", "headline": "REPO BRIEF SCENES RENDER SHIP", "duration_seconds": 10, "evidence": ["COMPONENTS: Core, CLI, Pipeline, Render"]},
            {"type": "LiveProof", "headline": "PROOF IS IN METADATA.JSON", "duration_seconds": 7.5, "evidence": ["kimi.mode=live-api in metadata.json"]},
            {"type": "ArtifactStack", "headline": "MP4 CAPTIONS NARRATION SUBMISSION COPY", "duration_seconds": 10, "evidence": ["generated artifacts: storyboard, narration, captions, MP4, metadata"]},
            {"type": "CTAEndCard", "headline": "NPM RUN BUILD-SHORT", "duration_seconds": 5, "evidence": ["output folder: ./dist/shorts/"]},
        ],
    }

    report = score_creative_plan(bad_live_brief, evidence_manifest=_evidence_manifest(), mode="final")

    assert report["allowed_to_publish"] is False
    defects = {issue["defect"] for issue in report["blocking_issues"] + report["factual_issues"]}
    assert {"missing_title", "missing_hook", "invalid_cta_command", "unsupported_evidence"} <= defects
