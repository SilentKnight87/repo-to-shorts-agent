from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def compose(scenes: list[dict], output_path: Path, music_path: Path | None = None) -> Path:
    """Compose scenes into final video with TTS narration, music, captions.

    Args:
        scenes: list of dicts with keys:
            - video_path: Path to scene MP4
            - narration: str, text to speak
            - duration_seconds: int
        output_path: final MP4 path
        music_path: optional background music MP3

    Returns:
        output_path
    """
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)

        # Generate TTS per scene
        tts_paths: list[Path] = []
        for i, scene in enumerate(scenes):
            tts_path = tmpdir / f"scene_{i:03d}_tts.wav"
            generate_tts(scene["narration"], tts_path)
            tts_paths.append(tts_path)

        # Mix audio per scene
        mixed_paths: list[Path] = []
        for i, scene in enumerate(scenes):
            mixed_path = tmpdir / f"scene_{i:03d}_audio.aac"
            mix_audio(tts_paths[i], music_path, mixed_path, scene["duration_seconds"])
            mixed_paths.append(mixed_path)

        # Build per-scene videos with replaced audio
        scene_videos: list[Path] = []
        for i, scene in enumerate(scenes):
            scene_out = tmpdir / f"scene_{i:03d}_composed.mp4"
            _replace_audio(scene["video_path"], mixed_paths[i], scene_out)
            scene_videos.append(scene_out)

        # Stitch scenes
        stitched = tmpdir / "stitched.mp4"
        _stitch_scenes(scene_videos, stitched)

        # Build captions
        captions: list[dict] = []
        current_time = 0.0
        for scene in scenes:
            captions.append(
                {
                    "text": scene["narration"],
                    "start": current_time,
                    "duration": scene["duration_seconds"],
                }
            )
            current_time += scene["duration_seconds"]

        burn_captions(stitched, captions, output_path)

    return output_path


def _replace_audio(video_path: Path, audio_path: Path, output_path: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path.resolve()),
        "-i",
        str(audio_path.resolve()),
        "-c:v",
        "copy",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-shortest",
        str(output_path.resolve()),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def _stitch_scenes(scene_paths: list[Path], output_path: Path) -> None:
    concat_file = output_path.parent / "concat_list.txt"
    lines = [f"file '{p.resolve()}'" for p in scene_paths]
    concat_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file.resolve()),
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        "-vf",
        "fps=30,format=yuv420p,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        str(output_path.resolve()),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def generate_tts(text: str, output_path: Path) -> Path:
    """Generate TTS audio using macOS `say` command.

    Uses: say -o <output.aiff> <text>
    Then converts to WAV via ffmpeg for mixing.
    """
    output_path = output_path.resolve()
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        aiff_path = tmpdir / "tts.aiff"
        cmd_say = ["say", "-o", str(aiff_path.resolve()), text]
        subprocess.run(cmd_say, check=True, capture_output=True, text=True)

        cmd_ffmpeg = [
            "ffmpeg",
            "-y",
            "-i",
            str(aiff_path.resolve()),
            "-ar",
            "44100",
            "-ac",
            "2",
            str(output_path),
        ]
        subprocess.run(cmd_ffmpeg, check=True, capture_output=True, text=True)
    return output_path


def mix_audio(voice_path: Path, music_path: Path | None, output_path: Path, duration_seconds: int) -> Path:
    """Mix voice and music with ducking. If no music, just normalize voice."""
    output_path = output_path.resolve()
    if music_path is not None:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(voice_path.resolve()),
            "-i",
            str(music_path.resolve()),
            "-filter_complex",
            "[1:a]volume=0.25[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=0[out]",
            "-map",
            "[out]",
            "-t",
            str(duration_seconds),
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(output_path),
        ]
    else:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(voice_path.resolve()),
            "-af",
            "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-t",
            str(duration_seconds),
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(output_path),
        ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return output_path


def burn_captions(video_path: Path, captions: list[dict], output_path: Path) -> Path:
    """Burn SRT-style captions into video using ffmpeg drawtext.

    captions: list of {text, start, duration}
    """
    output_path = output_path.resolve()
    filter_parts = []
    for cap in captions:
        text = _escape_drawtext(cap["text"])
        start = cap["start"]
        end = cap["start"] + cap["duration"]
        filter_parts.append(
            f"drawtext=fontfile=/System/Library/Fonts/Menlo.ttc"
            f":text='{text}'"
            f":fontsize=56"
            f":fontcolor=white"
            f":box=1"
            f":boxcolor=black@0.6"
            f":boxborderw=12"
            f":x=(w-text_w)/2"
            f":y=(h*3/4)"
            f":enable='between(t\\,{start}\\,{end})'"
        )
    vf = ",".join(filter_parts)
    if vf:
        vf += ",format=yuv420p"
    else:
        vf = "format=yuv420p"

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path.resolve()),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return output_path


def _escape_drawtext(text: str) -> str:
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace("'", "\\'")
    return text
