from __future__ import annotations

import json
import os
import subprocess
import tempfile
import urllib.request
from pathlib import Path

EDGE_TTS_VOICE = "en-US-AvaMultilingualNeural"
EDGE_TTS_RATE = "+8%"
EDGE_TTS_PITCH = "+2Hz"
EDGE_TTS_VOLUME = "+0%"


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

        # Build karaoke captions
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

        burn_karaoke_captions(stitched, captions, output_path)

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


def generate_tts(
    text: str,
    output_path: Path,
    *,
    provider: str = "edge",
    fallback_provider: str | None = None,
    voice: str | None = None,
    allow_say_fallback: bool = False,
) -> Path:
    """Generate TTS audio using the selected provider.

    Creative/postable renders should fail loudly if Edge TTS is unavailable instead
    of silently degrading to macOS ``say``. ``allow_say_fallback`` exists only for
    explicit local/offline use.
    """
    if provider == "none":
        raise RuntimeError("TTS provider is none; skip audio composition instead")

    output_path = output_path.resolve()
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        try:
            source_path = _generate_tts_source(text, tmpdir / "tts", provider, voice, allow_say_fallback)
        except Exception:
            if not fallback_provider or fallback_provider == "none":
                raise
            try:
                source_path = _generate_tts_source(
                    text,
                    tmpdir / "tts_fallback",
                    fallback_provider,
                    voice,
                    allow_say_fallback,
                )
            except Exception as fallback_exc:
                raise RuntimeError(
                    f"TTS provider {provider!r} failed, and fallback provider "
                    f"{fallback_provider!r} also failed."
                ) from fallback_exc

        cmd_ffmpeg = [
            "ffmpeg",
            "-y",
            "-i",
            str(source_path.resolve()),
            "-ar",
            "44100",
            "-ac",
            "2",
            str(output_path),
        ]
        subprocess.run(cmd_ffmpeg, check=True, capture_output=True, text=True)
    return output_path


def _generate_tts_source(
    text: str,
    output_path: Path,
    provider: str,
    voice: str | None,
    allow_say_fallback: bool,
) -> Path:
    if provider == "xai":
        return _generate_xai_tts(text, output_path, voice)
    if provider == "openai":
        return _generate_openai_tts(text, output_path, voice)
    if provider == "edge":
        return _generate_edge_tts(text, output_path, voice, allow_say_fallback)
    if provider == "none":
        raise RuntimeError("TTS provider is none; skip audio composition instead")
    raise RuntimeError(f"Unsupported TTS provider: {provider}")


def _generate_xai_tts(text: str, output_path: Path, voice: str | None) -> Path:
    try:
        api_key = os.environ["XAI_API_KEY"]
    except KeyError as exc:
        raise RuntimeError("XAI_API_KEY is required for xai TTS provider") from exc

    url = "https://api.x.ai/v1/tts"
    payload = {"model": "grok-2-voice", "input": text, "voice": voice or "orpheus", "response_format": "mp3"}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    return _request_tts_mp3(url, payload, headers, output_path)


def _generate_openai_tts(text: str, output_path: Path, voice: str | None) -> Path:
    try:
        api_key = os.environ["OPENAI_API_KEY"]
    except KeyError as exc:
        raise RuntimeError("OPENAI_API_KEY is required for openai TTS provider") from exc

    url = "https://api.openai.com/v1/audio/speech"
    payload = {"model": "gpt-4o-mini-tts", "input": text, "voice": voice or "alloy", "response_format": "mp3"}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    return _request_tts_mp3(url, payload, headers, output_path)


def _generate_edge_tts(text: str, output_path: Path, voice: str | None, allow_say_fallback: bool) -> Path:
    mp3_path = output_path.with_suffix(".mp3").resolve()

    # Try edge-tts first for neural voice quality.
    try:
        cmd = [
            "edge-tts",
            "--voice",
            voice or EDGE_TTS_VOICE,
            "--rate",
            EDGE_TTS_RATE,
            "--pitch",
            EDGE_TTS_PITCH,
            "--volume",
            EDGE_TTS_VOLUME,
            "--text",
            text,
            "--write-media",
            str(mp3_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return mp3_path
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        if not allow_say_fallback:
            raise RuntimeError(
                "Edge TTS failed; install/configure edge-tts or pass "
                "allow_say_fallback=True for non-postable local drafts."
            ) from exc

        # Explicit opt-in fallback only; never silently degrade creative renders.
        aiff_path = output_path.with_suffix(".aiff").resolve()
        cmd_say = ["say", "-o", str(aiff_path), text]
        subprocess.run(cmd_say, check=True, capture_output=True, text=True)
        return aiff_path


def _request_tts_mp3(url: str, payload: dict[str, str], headers: dict[str, str], output_path: Path) -> Path:
    mp3_path = output_path.with_suffix(".mp3").resolve()
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=60) as response:
        mp3_path.write_bytes(response.read())
    return mp3_path


def mix_audio(voice_path: Path, music_path: Path | None, output_path: Path, duration_seconds: int) -> Path:
    """Mix voice and music with ducking. If no music, just normalize voice."""
    output_path = output_path.resolve()
    if music_path is not None:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(voice_path.resolve()),
            "-stream_loop",
            "-1",
            "-i",
            str(music_path.resolve()),
            "-filter_complex",
            "[0:a]loudnorm=I=-16:TP=-1.5:LRA=11,apad[voice];"
            "[1:a]volume=0.18,highpass=f=70,lowpass=f=7000[bed];"
            "[bed][voice]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=300[ducked];"
            "[voice][ducked]amix=inputs=2:duration=longest:dropout_transition=0,alimiter=limit=0.95[out]",
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


def burn_karaoke_captions(video_path: Path, captions: list[dict], output_path: Path) -> Path:
    """Burn karaoke-style captions into video using ffmpeg drawtext.

    Shows 2-3 words at a time, highlighting each phrase sequentially.
    Falls back to copying the video if this ffmpeg build lacks drawtext.
    """
    output_path = output_path.resolve()
    if not _ffmpeg_has_filter("drawtext"):
        _copy_video(video_path, output_path)
        return output_path

    filter_parts = []
    font_path = "/System/Library/Fonts/HelveticaNeue.ttc"
    if not os.path.exists(font_path):
        font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"

    for cap in captions:
        words = cap["text"].split()
        duration = cap["duration"]
        start = cap["start"]
        if not words:
            continue

        # Group words into chunks of 2-3 for readability
        chunk_size = 3 if len(words) > 6 else 2
        chunks = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]
        chunk_duration = duration / len(chunks)

        for chunk_index, chunk in enumerate(chunks):
            chunk_start = start + chunk_index * chunk_duration
            chunk_end = chunk_start + chunk_duration + 0.3  # slight overlap for smoothness
            text = _escape_drawtext(" ".join(chunk))
            filter_parts.append(
                f"drawtext=fontfile={font_path}"
                f":text='{text}'"
                f":fontsize=72"
                f":fontcolor=0x22D3EE"
                f":borderw=4"
                f":bordercolor=0x000000"
                f":box=1"
                f":boxcolor=0x000000@0.6"
                f":boxborderw=20"
                f":x=(w-text_w)/2"
                f":y=(h*3/4)"
                f":enable='between(t\\,{chunk_start}\\,{chunk_end})'"
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


def burn_captions(video_path: Path, captions: list[dict], output_path: Path) -> Path:
    """Burn SRT-style captions into video using ffmpeg drawtext (legacy, full-line).

    captions: list of {text, start, duration}
    """
    output_path = output_path.resolve()
    if not _ffmpeg_has_filter("drawtext"):
        _copy_video(video_path, output_path)
        return output_path

    filter_parts = []
    font_path = "/System/Library/Fonts/HelveticaNeue.ttc"
    import os
    if not os.path.exists(font_path):
        font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"

    for cap in captions:
        text = _escape_drawtext(cap["text"])
        start = cap["start"]
        end = cap["start"] + cap["duration"]
        filter_parts.append(
            f"drawtext=fontfile={font_path}"
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


def generate_ambient_music(output_path: Path, duration: int = 60) -> Path:
    """Generate a simple electronic synth bed using ffmpeg lavfi."""
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fade_out_start = max(float(duration) - 2.0, 0.0)
    synth_expr = (
        "aevalsrc="
        "0.10*sin(2*PI*55*t)+0.075*sin(2*PI*110*t)+"
        "0.045*sin(2*PI*165*t)+0.030*sin(2*PI*220*t)"
        f":s=44100:d={duration}"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        synth_expr,
        "-af",
        "tremolo=f=4.5:d=0.35,lowpass=f=1800,highpass=f=45,"
        "acompressor=threshold=-18dB:ratio=3:attack=20:release=250,"
        "afade=t=in:st=0:d=1.2,"
        f"afade=t=out:st={fade_out_start:.2f}:d=2,volume=0.16",
        "-t",
        str(duration),
        "-c:a",
        "libmp3lame",
        "-b:a",
        "128k",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return output_path


def _ffmpeg_has_filter(name: str) -> bool:
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-filters"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    return any(line.split()[1:2] == [name] for line in result.stdout.splitlines() if line.split())


def _copy_video(video_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(video_path.resolve()), "-c", "copy", str(output_path.resolve())],
        check=True,
        capture_output=True,
        text=True,
    )


def _escape_drawtext(text: str) -> str:
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace("'", "\\'")
    return text
