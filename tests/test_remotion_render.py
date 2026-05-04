import subprocess
from pathlib import Path

from repo_to_shorts.remotion_render import (
    DEFAULT_ARTIFACTS,
    _default_scene_type,
    _headline_from_narration,
    _normalize_scene,
    build_remotion_input,
    remotion_available,
    render_remotion_video,
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


def test_build_remotion_input_copies_default_artifacts_and_preserves_empty_list():
    defaulted = build_remotion_input(
        repo_name="repo",
        description="description",
        key_files=[],
        scenes=[],
        proof={},
    )
    explicit_empty = build_remotion_input(
        repo_name="repo",
        description="description",
        key_files=[],
        scenes=[],
        proof={},
        artifacts=[],
    )

    assert defaulted["artifacts"] == DEFAULT_ARTIFACTS
    assert defaulted["artifacts"] is not DEFAULT_ARTIFACTS
    assert explicit_empty["artifacts"] == []


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


def test_normalize_scene_accepts_scalar_tuple_and_none_lists():
    scalar_scene = _normalize_scene(
        {
            "narration": "Scalar proof.",
            "evidence": "metadata.json",
            "caption_emphasis": ("live", "proof"),
        },
        0,
    )
    none_scene = _normalize_scene(
        {
            "narration": "No proof list.",
            "evidence": None,
            "caption_emphasis": None,
        },
        1,
    )

    assert scalar_scene["evidence"] == ["metadata.json"]
    assert scalar_scene["caption_emphasis"] == ["live", "proof"]
    assert none_scene["evidence"] == []
    assert none_scene["caption_emphasis"] == []


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


def test_remotion_available_requires_node_npm_package_json_and_render_script(
    monkeypatch,
    tmp_path: Path,
):
    monkeypatch.setattr(
        "repo_to_shorts.remotion_render.shutil.which",
        lambda name: f"/usr/bin/{name}" if name in {"node", "npm"} else None,
    )

    assert remotion_available(tmp_path) is False

    (tmp_path / "package.json").write_text(
        '{"scripts":{"test":"pytest"}}',
        encoding="utf-8",
    )
    assert remotion_available(tmp_path) is False

    (tmp_path / "package.json").write_text(
        '{"scripts":{"render:remotion":"node remotion/render.mjs"}}',
        encoding="utf-8",
    )
    assert remotion_available(tmp_path) is True

    monkeypatch.setattr("repo_to_shorts.remotion_render.shutil.which", lambda name: None)
    assert remotion_available(tmp_path) is False


def test_render_remotion_video_returns_unavailable_result(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        "repo_to_shorts.remotion_render.remotion_available",
        lambda project_root=None: False,
    )

    result = render_remotion_video(
        tmp_path,
        [{"type": "ColdOpen", "headline": "Hook", "narration": "Hook."}],
        repo_name="repo",
        description="Description",
        key_files=["README.md"],
        proof={"kimi_mode": "deterministic-fallback"},
    )

    assert result.output_path is None
    assert result.mode == "mp4"
    assert result.renderer == "remotion"
    assert result.scene_count == 1
    assert result.error is not None
    assert result.error.startswith("Remotion unavailable:")


def test_render_remotion_video_invokes_npm_and_returns_result(
    monkeypatch,
    tmp_path: Path,
):
    project_root = tmp_path / "project"
    run_dir = tmp_path / "run"
    commands = []

    def fake_run(command, cwd, check, capture_output, text):
        commands.append((command, cwd, check, capture_output, text))
        output = Path(command[-1])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"fake mp4")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("repo_to_shorts.remotion_render.subprocess.run", fake_run)
    monkeypatch.setattr(
        "repo_to_shorts.remotion_render.remotion_available",
        lambda root=None: root == project_root,
    )

    result = render_remotion_video(
        run_dir,
        [
            {"type": "ColdOpen", "headline": "Hook", "narration": "Hook.", "duration_seconds": 3},
            {"type": "CTAEndCard", "headline": "Ship", "narration": "Ship.", "duration_seconds": 4},
        ],
        repo_name="repo",
        description="Description",
        key_files=["README.md"],
        proof={"kimi_mode": "live-api"},
        project_root=project_root,
    )

    assert result.output_path == run_dir / "demo.mp4"
    assert result.mode == "mp4"
    assert result.renderer == "remotion"
    assert result.scene_count == 2
    assert result.error is None
    assert result.output_path.exists()
    assert (run_dir / "render" / "remotion_input.json").exists()
    command, cwd, check, capture_output, text = commands[0]
    assert command == [
        "npm",
        "run",
        "render:remotion",
        "--",
        "--input",
        str((run_dir / "render" / "remotion_input.json").resolve()),
        "--output",
        str((run_dir / "demo.mp4").resolve()),
    ]
    assert cwd == str(project_root.resolve())
    assert check is True
    assert capture_output is True
    assert text is True


def test_render_remotion_video_returns_failure_for_subprocess_error(
    monkeypatch,
    tmp_path: Path,
):
    def fake_run(command, cwd, check, capture_output, text):
        raise subprocess.CalledProcessError(1, command, stderr="boom")

    monkeypatch.setattr("repo_to_shorts.remotion_render.subprocess.run", fake_run)
    monkeypatch.setattr(
        "repo_to_shorts.remotion_render.remotion_available",
        lambda project_root=None: True,
    )

    result = render_remotion_video(
        tmp_path,
        [{"type": "ColdOpen", "headline": "Hook", "narration": "Hook."}],
        repo_name="repo",
        description="Description",
        key_files=[],
        proof={},
    )

    assert result.output_path is None
    assert result.mode == "mp4"
    assert result.renderer == "remotion"
    assert result.scene_count == 1
    assert result.error is not None
    assert result.error.startswith("Remotion render failed:")


def test_render_remotion_video_returns_failure_when_output_is_missing(
    monkeypatch,
    tmp_path: Path,
):
    monkeypatch.setattr(
        "repo_to_shorts.remotion_render.subprocess.run",
        lambda command, cwd, check, capture_output, text: subprocess.CompletedProcess(command, 0, "", ""),
    )
    monkeypatch.setattr(
        "repo_to_shorts.remotion_render.remotion_available",
        lambda project_root=None: True,
    )

    result = render_remotion_video(
        tmp_path,
        [{"type": "ColdOpen", "headline": "Hook", "narration": "Hook."}],
        repo_name="repo",
        description="Description",
        key_files=[],
        proof={},
    )

    assert result.output_path is None
    assert result.mode == "mp4"
    assert result.renderer == "remotion"
    assert result.scene_count == 1
    assert result.error == "Remotion render did not create demo.mp4"
