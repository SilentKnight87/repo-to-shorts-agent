from __future__ import annotations

import json
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from repo_to_shorts.compositor import generate_ambient_music, generate_tts, mix_audio
from repo_to_shorts.creative_director import direct
from repo_to_shorts.ingest import ingest_target
from repo_to_shorts.manim_render import generate_manim_script, render_scene
from repo_to_shorts.media_validation import validate_media
from repo_to_shorts.progress import ProgressTracker
from repo_to_shorts.submissions import write_submission_pack

SAFE_FILE_PREFIXES = (
    "src/",
    "tests/",
    "test/",
    "docs/",
    "app/",
    "lib/",
    "packages/",
    "cmd/",
    "internal/",
    "web/",
    "frontend/",
    "backend/",
)
SAFE_FILE_NAMES = {"README.md", "pyproject.toml", "package.json", "Cargo.toml", "go.mod", "Dockerfile", "Makefile"}
SECRET_FILE_MARKERS = (".env", "secret", "token", "private", "id_rsa", ".pem", ".key")


def run_creative_pipeline(
    target: str,
    audience: str = "technical builders",
    out_dir: Path | str = Path("runs"),
    kimi_model: str | None = None,
    music_path: Path | None = None,
    session_id: str | None = None,
    preview: bool = False,
    skip_audio: bool = False,
    final: bool = False,
    tts_provider: str = "edge",
    fallback_tts_provider: str | None = None,
    voice: str | None = None,
    generated_music: bool = True,
    command: list[str] | None = None,
) -> dict:
    """Full creative pipeline: ingest → Kimi creative director → render → compose.

    Returns {"output": str(final_mp4), "run_dir": str(run_dir)}
    """
    if music_path is not None and not music_path.exists():
        raise ValueError(f"Music file not found: {music_path}")

    if session_id:
        ProgressTracker.create_session(session_id)
    if final:
        preview = False
        skip_audio = tts_provider == "none"

    def _start(stage: str, detail: str = "") -> None:
        if session_id:
            ProgressTracker.start_stage(session_id, stage, detail)

    def _complete(stage: str, detail: str = "") -> None:
        if session_id:
            ProgressTracker.complete_stage(session_id, stage, detail)

    def _error(msg: str) -> None:
        if session_id:
            ProgressTracker.set_error(session_id, msg)

    try:
        _start("ingest", f"Reading {target}")
        snapshot = ingest_target(target)
        _complete("ingest", f"Read {snapshot.name}")

        _start("analyze", "Building repo analysis")
        repo_analysis = _build_repo_analysis(snapshot)
        _complete("analyze", f"Analyzed {repo_analysis.get('repo_name', 'repo')}")

        _start("kimi_brief", "Calling creative director")
        brief = direct(repo_analysis, model=kimi_model or "moonshotai/kimi-k2.6", final=final)
        if preview:
            brief.scenes = _preview_scenes(brief.scenes)
            brief.total_duration = int(sum(float(scene.get("duration_seconds", 4)) for scene in brief.scenes))
        _complete("kimi_brief", f"Brief: {brief.title}")

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        run_dir = Path(out_dir) / f"{timestamp}-{_slug(snapshot.name)}"
        run_dir.mkdir(parents=True, exist_ok=True)

        _start("render_frames", f"Rendering {len(brief.scenes)} scenes")
        script = generate_manim_script(
            {"scenes": brief.scenes, "fps": 12 if preview else 30},
            repo_analysis,
            run_dir,
            style=brief.style,
        )
        raw_video = run_dir / "video_raw.mp4"
        video_path = render_scene(script, run_dir)
        if video_path.exists() and video_path != raw_video:
            video_path.rename(raw_video)
            video_path = raw_video
        _complete("render_frames", f"Rendered {len(brief.scenes)} scenes")

        captions_path = _write_captions_srt(brief.scenes, run_dir / "captions.srt")

        _start("tts", "Generating narration")
        final_video = run_dir / "demo.mp4"
        if skip_audio:
            _copy_video(video_path, final_video)
        else:
            _merge_creative_video(
                video_path,
                brief.scenes,
                final_video,
                music_path=music_path,
                tts_provider=tts_provider,
                fallback_tts_provider=fallback_tts_provider,
                voice=voice,
                generated_music=generated_music,
            )
        _complete("tts", "Skipped audio for preview" if skip_audio else f"Generated voice for {len(brief.scenes)} scenes")

        _start("compose", "Mixing audio and video")
        _complete("compose", "Video composed")

        validation = validate_media(final_video, require_audio=not skip_audio)
        if final and not validation.get("ok"):
            errors = validation.get("errors") or ["media validation failed"]
            raise RuntimeError("; ".join(errors))

        _start("finalize", "Writing metadata")
        metadata = {
            "target": target,
            "source_type": snapshot.source_type,
            "repo_name": snapshot.name,
            "audience": audience,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "creative_brief": {
                "style": brief.style,
                "title": brief.title,
                "hook": brief.hook,
                "scenes": brief.scenes,
                "music_mood": brief.music_mood,
                "total_duration": brief.total_duration,
            },
            "kimi": {
                "mode": "live-api" if _has_api_key() else "deterministic-fallback",
                "model": kimi_model or "moonshotai/kimi-k2.6",
                "provider": "openrouter",
            },
            "tts": {
                "provider": tts_provider,
                "fallback_provider": fallback_tts_provider,
                "voice": voice,
                "skipped": skip_audio,
            },
            "render": {
                "mode": "mp4",
                "renderer": "pillow+ffmpeg-enhanced",
                "output": "demo.mp4",
                "scene_count": len(brief.scenes),
                "preview": preview,
                "audio": _render_audio_label(
                    skip_audio=skip_audio,
                    music_path=music_path,
                    generated_music=generated_music,
                ),
                "final": final,
                "validation": validation,
            },
            "artifacts": [
                "demo.mp4",
                captions_path.name,
                "submission_pack.md",
                "metadata.json",
            ],
        }
        write_submission_pack(
            run_dir,
            command=command or ["repo-shorts", "creative", target],
            metadata=metadata,
            validation=validation,
        )
        (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        _complete("finalize", "Artifacts packaged")

        return {"output": str(final_video), "run_dir": str(run_dir)}
    except Exception as exc:
        _error(str(exc))
        raise


def _preview_scenes(scenes: list[dict]) -> list[dict]:
    if not scenes:
        return []
    selected = [dict(scene) for scene in scenes[:3]]
    durations = [4, 5, 4]
    for index, scene in enumerate(selected):
        scene["duration_seconds"] = durations[index] if index < len(durations) else 4
    return selected


def _copy_video(video_path: Path, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(video_path.resolve()), "-c", "copy", str(output_path.resolve())],
        check=True,
        capture_output=True,
        text=True,
    )
    return output_path


def _write_captions_srt(scenes: list[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    current_time = 0.0
    blocks: list[str] = []
    for index, scene in enumerate(scenes, start=1):
        duration = float(scene.get("duration_seconds", 10))
        narration = str(scene.get("narration", "")).strip()
        start = current_time
        end = current_time + duration
        current_time = end
        if not narration:
            continue
        blocks.append(f"{index}\n{_srt_timestamp(start)} --> {_srt_timestamp(end)}\n{narration}")
    output_path.write_text("\n\n".join(blocks) + ("\n" if blocks else ""), encoding="utf-8")
    return output_path


def _srt_timestamp(seconds: float) -> str:
    milliseconds = int(round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _render_audio_label(*, skip_audio: bool, music_path: Path | None, generated_music: bool) -> str:
    if skip_audio:
        return "skipped"
    if music_path is not None:
        return "tts+supplied-music"
    if generated_music:
        return "tts+generated-music"
    return "tts-only"


def _build_repo_analysis(snapshot) -> dict:
    description = snapshot.package_metadata.get("description", "")
    if not description:
        description = _first_readme_sentence(snapshot.readme)
    key_files = _safe_file_tree(snapshot.file_tree)
    return {
        "repo_name": snapshot.name,
        "description": description,
        "primary_language": snapshot.package_metadata.get("language", ""),
        "key_files": key_files,
        "purpose": description,
        "name": snapshot.name,
        "components": [f.replace("src/", "").replace(".py", "").replace("/", " ").title() for f in key_files[:8] if ".py" in f or ".js" in f or ".ts" in f] or ["Core", "CLI", "Pipeline", "Render"],
    }


def _safe_file_tree(file_tree: list[str], limit: int = 10) -> list[str]:
    safe = []
    for path in file_tree:
        lowered = path.lower()
        if lowered.startswith("runs/") or any(marker in lowered for marker in SECRET_FILE_MARKERS):
            continue
        if path in SAFE_FILE_NAMES or path.startswith(SAFE_FILE_PREFIXES):
            safe.append(path)
        if len(safe) >= limit:
            break
    return safe


def _merge_creative_video(
    video_path: Path,
    scenes: list[dict],
    output_path: Path,
    music_path: Path | None = None,
    tts_provider: str = "edge",
    fallback_tts_provider: str | None = None,
    voice: str | None = None,
    generated_music: bool = True,
) -> Path:
    """Merge narrations (TTS) and optional/generated music into the rendered video."""
    output_path = output_path.resolve()
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)

        # Generate TTS per scene
        tts_files: list[str] = []
        scene_durations: list[float] = []
        for i, scene in enumerate(scenes):
            narration = scene.get("narration", "")
            duration = scene.get("duration_seconds", 10)
            scene_durations.append(float(duration))
            if narration:
                tts_path = tmpdir / f"tts_{i:02d}.wav"
                generate_tts(
                    narration,
                    tts_path,
                    provider=tts_provider,
                    fallback_provider=fallback_tts_provider,
                    voice=voice,
                )
                tts_files.append(str(tts_path.resolve()))

        if not tts_files:
            # No narration: just copy video
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(video_path.resolve()), "-c", "copy", str(output_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            return output_path

        # Concatenate all TTS segments
        concat_list = tmpdir / "tts_concat.txt"
        concat_list.write_text("\n".join(f"file '{f}'" for f in tts_files) + "\n", encoding="utf-8")
        full_tts = tmpdir / "full_tts.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(full_tts)],
            check=True,
            capture_output=True,
            text=True,
        )

        # Generate ambient music if none provided
        total_duration = max(1, int(round(sum(scene_durations))))
        if music_path is None or not music_path.exists():
            if generated_music:
                music_path = tmpdir / "ambient_music.mp3"
                generate_ambient_music(music_path, duration=max(total_duration, 30))
            else:
                music_path = None

        # Mix voice + music
        mixed_audio = tmpdir / "mixed.aac"
        mix_audio(full_tts, music_path, mixed_audio, duration_seconds=total_duration)

        # Merge video + audio first
        video_with_audio = tmpdir / "video_audio.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(video_path.resolve()),
                "-i",
                str(mixed_audio.resolve()),
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                str(video_with_audio),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        _copy_video(video_with_audio, output_path)

    return output_path


def _has_api_key() -> bool:
    import os
    return bool(os.environ.get("OPENROUTER_API_KEY") or os.environ.get("KIMI_API_KEY"))


def _first_readme_sentence(readme: str) -> str:
    text = " ".join(line.strip("# ") for line in readme.splitlines() if line.strip())
    return text.split(". ")[0][:220] or "A technical project ready for a clearer launch story."


def _slug(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug[:60] or "repo"
