from __future__ import annotations

import json
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from repo_to_shorts.compositor import generate_tts, mix_audio
from repo_to_shorts.creative_director import direct
from repo_to_shorts.ingest import ingest_target
from repo_to_shorts.manim_render import generate_manim_script, render_scene


def run_creative_pipeline(
    target: str,
    audience: str = "technical builders",
    out_dir: Path | str = Path("runs"),
    kimi_model: str | None = None,
    music_path: Path | None = None,
) -> dict:
    """Full creative pipeline: ingest → Kimi creative director → render → compose.

    Returns {"output": str(final_mp4), "run_dir": str(run_dir)}
    """
    snapshot = ingest_target(target)
    repo_analysis = _build_repo_analysis(snapshot)
    brief = direct(repo_analysis, model=kimi_model or "moonshotai/kimi-k2.6")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = Path(out_dir) / f"{timestamp}-{_slug(snapshot.name)}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Render animated video (no audio yet)
    script = generate_manim_script(
        {"scenes": brief.scenes},
        repo_analysis,
        run_dir,
        style=brief.style,
    )
    raw_video = run_dir / "video_raw.mp4"
    video_path = render_scene(script, run_dir)
    # render_scene writes to output_dir / "demo.mp4"; rename to avoid clobbering during audio merge
    if video_path.exists() and video_path != raw_video:
        video_path.rename(raw_video)
        video_path = raw_video

    # Build audio track from scene narrations
    final_video = run_dir / "demo.mp4"
    _merge_creative_video(video_path, brief.scenes, final_video, music_path=music_path)

    # Write metadata proving Kimi directed
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
        "render": {
            "mode": "mp4",
            "renderer": "pillow+ffmpeg-enhanced",
            "output": "demo.mp4",
            "scene_count": len(brief.scenes),
        },
        "artifacts": [
            "demo.mp4",
            "metadata.json",
        ],
    }
    (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    return {"output": str(final_video), "run_dir": str(run_dir)}


def _build_repo_analysis(snapshot) -> dict:
    description = snapshot.package_metadata.get("description", "")
    if not description:
        description = _first_readme_sentence(snapshot.readme)
    return {
        "repo_name": snapshot.name,
        "description": description,
        "primary_language": snapshot.package_metadata.get("language", ""),
        "key_files": snapshot.file_tree[:10],
        "purpose": description,
        "name": snapshot.name,
        "components": [f.replace("src/", "").replace(".py", "").replace("/", " ").title() for f in snapshot.file_tree[:8] if ".py" in f or ".js" in f or ".ts" in f] or ["Core", "CLI", "Pipeline", "Render"],
    }


def _merge_creative_video(
    video_path: Path,
    scenes: list[dict],
    output_path: Path,
    music_path: Path | None = None,
) -> Path:
    """Merge narrations (TTS) and optional music into the rendered video."""
    output_path = output_path.resolve()
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)

        # Generate TTS per scene
        tts_files: list[str] = []
        for i, scene in enumerate(scenes):
            narration = scene.get("narration", "")
            if narration:
                tts_path = tmpdir / f"tts_{i:02d}.wav"
                generate_tts(narration, tts_path)
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

        # Mix with optional music
        if music_path is not None and music_path.exists():
            mixed_audio = tmpdir / "mixed.aac"
            mix_audio(full_tts, music_path, mixed_audio, duration_seconds=9999)
            audio_input = mixed_audio
        else:
            audio_input = full_tts

        # Merge video + audio (video drives duration; audio plays then silence)
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(video_path.resolve()),
                "-i",
                str(audio_input.resolve()),
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(output_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

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
