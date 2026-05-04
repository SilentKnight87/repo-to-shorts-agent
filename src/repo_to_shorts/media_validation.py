from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def validate_media(
    video_path: Path,
    *,
    require_audio: bool = True,
    min_duration: float = 43.0,
    max_duration: float = 62.0,
    expected_width: int = 1080,
    expected_height: int = 1920,
    audio_tolerance_seconds: float = 1.5,
) -> dict[str, Any]:
    video_path = video_path.resolve()
    errors: list[str] = []
    result: dict[str, Any] = {
        "ok": False,
        "path": str(video_path),
        "exists": video_path.exists(),
        "size_bytes": video_path.stat().st_size if video_path.exists() else 0,
        "has_video": False,
        "has_audio": False,
        "duration_seconds": None,
        "audio_duration_seconds": None,
        "resolution": None,
        "errors": errors,
    }

    if not video_path.exists() or result["size_bytes"] == 0:
        errors.append("demo.mp4 must exist and be non-empty")
        return result

    try:
        probe = _ffprobe(video_path)
    except RuntimeError as exc:
        errors.append(str(exc))
        return result

    streams = probe.get("streams", [])
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)

    duration = _float_or_none(probe.get("format", {}).get("duration"))
    result["duration_seconds"] = duration

    if video_stream:
        result["has_video"] = True
        width = int(video_stream.get("width") or 0)
        height = int(video_stream.get("height") or 0)
        result["resolution"] = f"{width}x{height}"
        if width != expected_width or height != expected_height:
            errors.append(f"resolution must be {expected_width}x{expected_height}")
    else:
        errors.append("video stream is required")

    if audio_stream:
        result["has_audio"] = True
        result["audio_duration_seconds"] = _float_or_none(audio_stream.get("duration"))
    elif require_audio:
        errors.append("audio stream is required")

    if duration is None or duration < min_duration or duration > max_duration:
        errors.append(f"duration must be {int(min_duration)}-{int(max_duration)} seconds")

    audio_duration = result["audio_duration_seconds"]
    if require_audio and duration is not None and audio_duration is not None:
        if abs(float(duration) - float(audio_duration)) > audio_tolerance_seconds:
            errors.append(f"audio duration must be within {audio_tolerance_seconds} seconds of video duration")

    result["ok"] = not errors
    return result


def _ffprobe(video_path: Path) -> dict[str, Any]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]
    try:
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(f"ffprobe failed: {exc}") from exc
    return json.loads(completed.stdout)


def _float_or_none(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
