from pathlib import Path

from repo_to_shorts.remotion_render import (
    DEFAULT_ARTIFACTS,
    _default_scene_type,
    _headline_from_narration,
    _normalize_scene,
    build_remotion_input,
    write_remotion_input,
)


def test_build_remotion_input_contains_repo_proof_scenes_and_artifacts():
    scenes = [
        {
            "type": "ColdOpen",
            "duration_seconds": 3,
            "headline": "This repo made the video you're watching.",
            "narration": "This repo made the video you're watching.",
            "evidence": ["repo-to-shorts-agent"],
        },
        {
            "type": "LiveProof",
            "duration_seconds": 6,
            "headline": "Kimi proof is in the metadata.",
            "narration": "The run records live Kimi usage.",
            "evidence": ["metadata.json"],
        },
    ]

    data = build_remotion_input(
        repo_name="repo-to-shorts-agent",
        description="Turns repos into launch-ready shorts.",
        key_files=["README.md", "src/repo_to_shorts/pipeline.py"],
        scenes=scenes,
        proof={
            "kimi_mode": "live-api",
            "kimi_provider": "openrouter",
            "kimi_model": "moonshotai/kimi-k2.6",
            "render_validation": "pass",
        },
        artifacts=["demo.mp4", "metadata.json", "captions.srt", "submission_pack.md"],
    )

    assert data["schema_version"] == 1
    assert data["repo"]["name"] == "repo-to-shorts-agent"
    assert data["video"] == {
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "duration_seconds": 45,
    }
    assert data["proof"]["kimi_mode"] == "live-api"
    assert data["scenes"][0]["type"] == "ColdOpen"
    assert data["artifacts"] == [
        "demo.mp4",
        "metadata.json",
        "captions.srt",
        "submission_pack.md",
    ]


def test_write_remotion_input_writes_versioned_manifest(tmp_path: Path):
    path = write_remotion_input(
        tmp_path,
        {
            "schema_version": 1,
            "repo": {"name": "repo"},
            "video": {
                "width": 1080,
                "height": 1920,
                "fps": 30,
                "duration_seconds": 45,
            },
            "proof": {},
            "scenes": [],
            "artifacts": [],
        },
    )

    assert path == tmp_path / "render" / "remotion_input.json"
    assert path.exists()
    assert '"schema_version": 1' in path.read_text(encoding="utf-8")


def test_build_remotion_input_limits_key_files_and_uses_default_artifacts():
    data = build_remotion_input(
        repo_name="repo",
        description="description",
        key_files=[f"file-{index}.py" for index in range(12)],
        scenes=[],
        proof={},
    )

    assert data["repo"]["key_files"] == [f"file-{index}.py" for index in range(8)]
    assert data["artifacts"] == DEFAULT_ARTIFACTS


def test_normalize_scene_preserves_values_and_limits_lists():
    scene = _normalize_scene(
        {
            "type": "LiveProof",
            "duration_seconds": "7.5",
            "headline": "Proof is inspectable.",
            "narration": "Metadata records live model proof.",
            "evidence": ["a", "b", "c", "d", "e"],
            "caption_emphasis": ["one", "two", "three", "four", "five", "six"],
        },
        4,
    )

    assert scene == {
        "type": "LiveProof",
        "duration_seconds": 7.5,
        "headline": "Proof is inspectable.",
        "narration": "Metadata records live model proof.",
        "evidence": ["a", "b", "c", "d"],
        "caption_emphasis": ["one", "two", "three", "four", "five"],
    }


def test_normalize_scene_defaults_type_and_headline_from_narration():
    scene = _normalize_scene(
        {
            "duration_seconds": 2,
            "narration": "The pipeline turns repositories into video packages. Fast.",
        },
        2,
    )

    assert scene["type"] == "PipelineMap"
    assert scene["duration_seconds"] == 2.0
    assert scene["headline"] == "The pipeline turns repositories into video packages"


def test_default_scene_type_caps_at_cta_end_card():
    assert [_default_scene_type(index) for index in range(8)] == [
        "ColdOpen",
        "RepoEvidence",
        "PipelineMap",
        "ArtifactStack",
        "LiveProof",
        "CTAEndCard",
        "CTAEndCard",
        "CTAEndCard",
    ]


def test_headline_from_narration_uses_fallback_for_blank_text():
    assert _headline_from_narration("") == "Repo to Shorts"
