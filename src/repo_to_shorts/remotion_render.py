from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from repo_to_shorts.render import RenderConfig, RenderResult

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
        "artifacts": list(DEFAULT_ARTIFACTS) if artifacts is None else list(artifacts),
    }


def write_remotion_input(run_dir: Path, data: dict[str, Any]) -> Path:
    render_dir = Path(run_dir) / "render"
    render_dir.mkdir(parents=True, exist_ok=True)
    path = render_dir / "remotion_input.json"
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def remotion_available(project_root: Path | None = None) -> bool:
    root = project_root or Path.cwd()
    package_json = root / "package.json"
    if shutil.which("node") is None or shutil.which("npm") is None:
        return False
    if not package_json.exists():
        return False
    try:
        package_data = json.loads(package_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    scripts = package_data.get("scripts")
    return isinstance(scripts, dict) and "render:remotion" in scripts


def render_remotion_video(
    run_dir: Path,
    scenes: list[dict[str, Any]],
    *,
    repo_name: str,
    description: str,
    key_files: list[str],
    proof: dict[str, Any],
    config: RenderConfig | None = None,
    project_root: Path | None = None,
) -> RenderResult:
    scene_count = len(scenes)
    if not remotion_available(project_root):
        return RenderResult(
            output_path=None,
            mode="mp4",
            renderer="remotion",
            scene_count=scene_count,
            error="Remotion unavailable: node/npm/package script missing",
        )

    cfg = config or RenderConfig()
    input_path = write_remotion_input(
        run_dir,
        build_remotion_input(
            repo_name=repo_name,
            description=description,
            key_files=key_files,
            scenes=scenes,
            proof=proof,
            width=cfg.width,
            height=cfg.height,
            fps=cfg.fps,
            duration_seconds=_duration_seconds(scenes, cfg),
        ),
    )
    output_path = Path(run_dir) / cfg.output_name
    command = [
        "npm",
        "run",
        "render:remotion",
        "--",
        "--input",
        str(input_path.resolve()),
        "--output",
        str(output_path.resolve()),
    ]
    try:
        subprocess.run(
            command,
            cwd=str((project_root or Path.cwd()).resolve()),
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        return RenderResult(
            output_path=None,
            mode="mp4",
            renderer="remotion",
            scene_count=scene_count,
            error=f"Remotion render failed: {_format_subprocess_error(exc)}",
        )

    if not output_path.exists():
        return RenderResult(
            output_path=None,
            mode="mp4",
            renderer="remotion",
            scene_count=scene_count,
            error=f"Remotion render did not create {output_path.name}",
        )
    return RenderResult(
        output_path=output_path,
        mode="mp4",
        renderer="remotion",
        scene_count=scene_count,
        error=None,
    )


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
        "evidence": _string_list(scene.get("evidence"), limit=4),
        "caption_emphasis": _string_list(scene.get("caption_emphasis"), limit=5),
    }


def _duration_seconds(scenes: list[dict[str, Any]], config: RenderConfig) -> int:
    scene_duration = sum(float(scene.get("duration_seconds", 0)) for scene in scenes)
    return int(scene_duration) or config.seconds_per_scene * max(len(scenes), 1)


def _string_list(value: Any, *, limit: int) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value][:limit]
    if isinstance(value, list | tuple):
        return [str(item) for item in value][:limit]
    return [str(value)][:limit]


def _format_subprocess_error(exc: OSError | subprocess.CalledProcessError) -> str:
    if isinstance(exc, subprocess.CalledProcessError):
        captured = _trim_process_output(exc.stderr or exc.stdout)
        if captured:
            return f"{type(exc).__name__}: {captured}"
    return str(exc)


def _trim_process_output(output: Any, *, limit: int = 800) -> str:
    if output is None:
        return ""
    text = output.decode("utf-8", errors="replace") if isinstance(output, bytes) else str(output)
    text = text.strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}..."


def _default_scene_type(index: int) -> str:
    return DEFAULT_SCENE_TYPES[min(index, len(DEFAULT_SCENE_TYPES) - 1)]


def _headline_from_narration(narration: str) -> str:
    first_sentence = str(narration).split(".")[0].strip()
    return first_sentence or "Repo to Shorts"
