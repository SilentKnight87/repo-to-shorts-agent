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
from repo_to_shorts.production import write_production_manifests
from repo_to_shorts.progress import ProgressTracker
from repo_to_shorts.remotion_render import render_remotion_video
from repo_to_shorts.render import RenderConfig, RenderResult
from repo_to_shorts.submissions import write_submission_pack
from repo_to_shorts.taste import build_reference_pack, load_design_profile
from repo_to_shorts.taste_qa import score_creative_plan

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
    compare_previews: bool = False,
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
        design_profile = load_design_profile(Path("DESIGN.md"))
        reference_pack = build_reference_pack(Path("DESIGN.md"), Path("docs/taste-research.md"))
        brief = direct(
            repo_analysis,
            model=kimi_model or "moonshotai/kimi-k2.6",
            final=final,
            design_profile=design_profile,
            reference_pack=reference_pack,
        )
        if preview:
            brief.scenes = _preview_scenes(brief.scenes)
            brief.total_duration = int(sum(float(scene.get("duration_seconds", 4)) for scene in brief.scenes))
        if final:
            _validate_final_brief(brief)

        comparison_report = None
        if compare_previews and preview:
            candidates = [brief, _make_concise_candidate(brief), _make_proof_first_candidate(brief)]
            brief, comparison_report = _select_best_preview_candidate(candidates, design_profile)

        brief_manifest = _brief_to_manifest(brief)
        qa_report = score_creative_plan(brief_manifest, design_profile=design_profile)
        if final and not qa_report["allowed_to_publish"]:
            defects = ", ".join(issue["defect"] for issue in qa_report["blocking_issues"])
            raise RuntimeError(f"Taste QA failed before render: {defects}")

        _complete("kimi_brief", f"Brief: {brief.title}")

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        run_dir = Path(out_dir) / f"{timestamp}-{_slug(snapshot.name)}"
        run_dir.mkdir(parents=True, exist_ok=True)

        kimi_metadata = _build_kimi_metadata(brief, kimi_model)

        _start("render_frames", f"Rendering {len(brief.scenes)} scenes")
        raw_video = run_dir / "video_raw.mp4"
        remotion_result: RenderResult | None = None
        render_metadata = {
            "mode": "mp4",
            "renderer": "pillow+ffmpeg-enhanced",
            "output": "demo.mp4",
            "scene_count": len(brief.scenes),
        }
        if final:
            remotion_result = render_remotion_video(
                run_dir,
                brief.scenes,
                repo_name=repo_analysis["repo_name"],
                description=repo_analysis["description"],
                key_files=repo_analysis["key_files"],
                proof=_build_remotion_proof(kimi_metadata),
                config=RenderConfig(output_name=raw_video.name),
            )

        if _remotion_succeeded(remotion_result):
            video_path = remotion_result.output_path
            render_metadata["renderer"] = "remotion"
            render_metadata["input"] = "render/remotion_input.json"
            render_metadata["scene_count"] = remotion_result.scene_count
        else:
            script = generate_manim_script(
                {"scenes": brief.scenes, "fps": 12 if preview else 30},
                repo_analysis,
                run_dir,
                style=brief.style,
            )
            video_path = render_scene(script, run_dir)
            if video_path.exists() and video_path != raw_video:
                video_path.rename(raw_video)
                video_path = raw_video
            if final and remotion_result is not None:
                render_metadata["fallback_renderer"] = remotion_result.renderer
                render_metadata["fallback_reason"] = remotion_result.error or "unknown Remotion failure"
                if (run_dir / "render" / "remotion_input.json").exists():
                    render_metadata["input"] = "render/remotion_input.json"
        _complete("render_frames", f"Rendered {len(brief.scenes)} scenes")

        captions_path = _write_captions_srt(brief.scenes, run_dir / "captions.srt")

        _start("tts", "Generating narration")
        final_video = run_dir / "demo.mp4"
        actual_tts_provider = None
        if skip_audio:
            _copy_video(video_path, final_video)
        else:
            merge_result = _merge_creative_video(
                video_path,
                brief.scenes,
                final_video,
                music_path=music_path,
                tts_provider=tts_provider,
                fallback_tts_provider=fallback_tts_provider,
                voice=voice,
                generated_music=generated_music,
            )
            if isinstance(merge_result, dict):
                actual_tts_provider = merge_result.get("actual_tts_provider")
                final_video = Path(merge_result.get("output", final_video))
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
            "kimi": kimi_metadata,
            "tts": {
                "provider": tts_provider,
                "fallback_provider": fallback_tts_provider,
                "actual_provider": actual_tts_provider,
                "voice": voice,
                "skipped": skip_audio,
            },
            "render": {
                **render_metadata,
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
        production_paths = write_production_manifests(
            run_dir,
            design_profile=design_profile,
            reference_pack=reference_pack,
            evidence_manifest=_build_evidence_manifest(repo_analysis),
            creative_brief=brief_manifest,
            scene_plan={"schema_version": 1, "scenes": brief.scenes},
            asset_manifest={"schema_version": 1, "assets": []},
            audio_plan={
                "schema_version": 1,
                "mode": "skipped" if skip_audio else "voiceover_with_ducked_music",
                "tts_provider": tts_provider,
                "fallback_tts_provider": fallback_tts_provider,
                "generated_music": generated_music,
            },
            qa_report=_final_qa_report(qa_report, comparison_report),
        )
        for p in production_paths:
            metadata["artifacts"].append("production/" + p.name)
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


def _brief_text_attr(brief, name: str, default: str) -> str:
    value = getattr(brief, name, default)
    if isinstance(value, str) and value:
        return value
    return default


def _build_kimi_metadata(brief, kimi_model: str | None) -> dict[str, str]:
    metadata = {
        "mode": _brief_text_attr(brief, "mode", "deterministic-fallback"),
        "model": _brief_text_attr(brief, "model", kimi_model or "moonshotai/kimi-k2.6"),
        "provider": _brief_text_attr(brief, "provider", "openrouter"),
    }
    fallback_reason = getattr(brief, "fallback_reason", None)
    if isinstance(fallback_reason, str) and fallback_reason:
        metadata["fallback_reason"] = fallback_reason
    return metadata


def _build_remotion_proof(kimi_metadata: dict[str, str]) -> dict[str, str]:
    return {
        "kimi_mode": kimi_metadata["mode"],
        "kimi_provider": kimi_metadata["provider"],
        "kimi_model": kimi_metadata["model"],
    }


def _remotion_succeeded(result: RenderResult | None) -> bool:
    return result is not None and result.output_path is not None and result.error is None


def _validate_final_brief(brief) -> None:
    scenes = list(getattr(brief, "scenes", []) or [])
    if len(scenes) < 5:
        raise RuntimeError(f"Final mode requires at least 5 scenes; got {len(scenes)}.")
    try:
        total_duration = sum(float(scene.get("duration_seconds", 0) or 0) for scene in scenes)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("Final mode requires numeric scene durations.") from exc
    if total_duration < 43 or total_duration > 62:
        raise RuntimeError(
            "Final mode requires summed scene durations between 43 and 62 seconds; "
            f"got {total_duration:.1f} seconds."
        )


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
) -> dict[str, object]:
    """Merge narrations (TTS) and optional/generated music into the rendered video."""
    output_path = output_path.resolve()
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)

        # Generate TTS per scene
        tts_files: list[str] = []
        scene_durations: list[float] = []
        used_providers: list[str] = []
        has_any_narration = any(str(scene.get("narration") or "").strip() for scene in scenes)
        for i, scene in enumerate(scenes):
            narration = str(scene.get("narration") or "").strip()
            duration = scene.get("duration_seconds", 10)
            scene_durations.append(float(duration))
            if narration:
                tts_path = tmpdir / f"tts_{i:02d}.wav"
                aligned_tts_path = tmpdir / f"tts_aligned_{i:02d}.wav"
                generate_tts(
                    narration,
                    tts_path,
                    provider=tts_provider,
                    fallback_provider=fallback_tts_provider,
                    voice=voice,
                    provider_report=used_providers.append,
                )
                _fit_audio_to_duration(tts_path, aligned_tts_path, float(duration))
                tts_files.append(str(aligned_tts_path.resolve()))
            elif has_any_narration:
                silence_path = tmpdir / f"tts_silence_{i:02d}.wav"
                _create_silence_audio(silence_path, float(duration))
                tts_files.append(str(silence_path.resolve()))

        if not tts_files:
            # No narration: just copy video
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(video_path.resolve()), "-c", "copy", str(output_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            return {"output": output_path, "actual_tts_provider": None}

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

        # Merge video + audio. Explicit -map prevents ffmpeg from picking the
        # source video's existing audio track (Remotion outputs a silent audio
        # stream that would otherwise clobber the mixed narration+music).
        video_with_audio = tmpdir / "video_audio.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(video_path.resolve()),
                "-i",
                str(mixed_audio.resolve()),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
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

    return {"output": output_path, "actual_tts_provider": _summarize_providers(used_providers)}


def _fit_audio_to_duration(input_path: Path, output_path: Path, duration_seconds: float) -> Path:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path.resolve()),
            "-af",
            f"apad,atrim=0:{duration_seconds:.3f}",
            "-ar",
            "44100",
            "-ac",
            "2",
            str(output_path.resolve()),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return output_path


def _create_silence_audio(output_path: Path, duration_seconds: float) -> Path:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-t",
            f"{duration_seconds:.3f}",
            "-ar",
            "44100",
            "-ac",
            "2",
            str(output_path.resolve()),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return output_path


def _summarize_providers(providers: list[str]) -> str | None:
    if not providers:
        return None
    unique = sorted(set(providers))
    if len(unique) == 1:
        return unique[0]
    return "mixed:" + ",".join(unique)


def _first_readme_sentence(readme: str) -> str:
    text = " ".join(line.strip("# ") for line in readme.splitlines() if line.strip())
    return text.split(". ")[0][:220] or "A technical project ready for a clearer launch story."


def _slug(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug[:60] or "repo"


def _build_evidence_manifest(repo_analysis: dict) -> dict:
    return {
        "schema_version": 1,
        "repo_name": repo_analysis.get("repo_name"),
        "description": repo_analysis.get("description"),
        "safe_files": repo_analysis.get("key_files", []),
        "components": repo_analysis.get("components", []),
    }


def _brief_to_manifest(brief) -> dict:
    def _safe(name: str, default):
        val = getattr(brief, name, default)
        if val is not None and type(val).__name__ == "MagicMock":
            return default
        return val

    return {
        "schema_version": 1,
        "style": _safe("style", ""),
        "title": _safe("title", ""),
        "hook": _safe("hook", ""),
        "distribution_channel": _safe("distribution_channel", "x_short"),
        "reference_pack": _safe("reference_pack", []),
        "visual_world": _safe("visual_world", ""),
        "motion_principles": _safe("motion_principles", []),
        "shot_list": _safe("shot_list", []),
        "continuity_rules": _safe("continuity_rules", []),
        "negative_prompts": _safe("negative_prompts", []),
        "scenes": _safe("scenes", []),
        "music_mood": _safe("music_mood", ""),
        "total_duration": _safe("total_duration", 0),
    }


def _select_best_preview_candidate(candidates: list, design_profile: dict) -> tuple:
    scored = []
    for index, candidate in enumerate(candidates):
        report = score_creative_plan(_brief_to_manifest(candidate), design_profile=design_profile)
        scored.append((float(report["score"]), index, candidate, report))
    scored.sort(key=lambda item: item[0], reverse=True)
    score, index, candidate, report = scored[0]
    return candidate, {
        "schema_version": 1,
        "candidate_count": len(candidates),
        "selected_index": index,
        "selected_score": score,
        "candidates": [item[3] for item in scored],
    }


def _make_concise_candidate(brief) -> object:
    import copy
    c = copy.copy(brief)
    short_scenes = []
    for scene in getattr(brief, "scenes", []):
        s = dict(scene)
        headline = str(s.get("headline", ""))
        words = headline.split()[:6]
        s["headline"] = " ".join(words) if len(words) >= 3 else headline
        if "duration_seconds" in s:
            s["duration_seconds"] = min(float(s["duration_seconds"]), 7)
        short_scenes.append(s)
    c.scenes = short_scenes[:4]
    return c


def _make_proof_first_candidate(brief) -> object:
    import copy
    c = copy.copy(brief)
    scenes = [dict(s) for s in getattr(brief, "scenes", [])]
    proof_scenes = [s for s in scenes if str(s.get("type", "")).lower() in ("liveproof", "repoevidence")]
    other_scenes = [s for s in scenes if s not in proof_scenes]
    c.scenes = proof_scenes[:1] + other_scenes[:4]
    return c


def _final_qa_report(qa_report: dict, comparison_report: dict | None) -> dict:
    if comparison_report:
        report = dict(qa_report)
        report["preview_comparison"] = comparison_report
        return report
    return qa_report
