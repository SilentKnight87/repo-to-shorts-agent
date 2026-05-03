from __future__ import annotations

import shutil
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from repo_to_shorts.ingest import RepoSnapshot

if TYPE_CHECKING:
    from repo_to_shorts.pipeline import StoryPackage


@dataclass(frozen=True)
class VideoScene:
    title: str
    body: str
    footer: str = ""
    accent: str = "#8b5cf6"


@dataclass(frozen=True)
class RenderConfig:
    width: int = 1080
    height: int = 1920
    fps: int = 30
    seconds_per_scene: int = 10
    output_name: str = "demo.mp4"


@dataclass(frozen=True)
class RenderResult:
    output_path: Path
    mode: str
    renderer: str
    scene_count: int
    error: str | None = None


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def ensure_render_runtime() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required for --render mp4. Install ffmpeg and retry.")
    if shutil.which("ffprobe") is None:
        raise RuntimeError("ffprobe is required for --render mp4. Install ffmpeg and retry.")
    try:
        import PIL  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("Pillow is required for --render mp4. Install with: pip install -e '.[render]'.") from exc


def build_video_scenes(
    snapshot: RepoSnapshot,
    audience: str,
    package: "StoryPackage",
    kimi_critique: str,
) -> list[VideoScene]:
    description = snapshot.package_metadata.get("description") or _trim(snapshot.readme.replace("#", " "), 120)
    kimi_excerpt = _trim(kimi_critique.replace("\n", " "), 230)
    return [
        VideoScene(
            title=f"{snapshot.name} → short-video package",
            body=_trim(package.hook, 320),
            footer="Repo-to-Shorts Agent",
            accent="#22d3ee",
        ),
        VideoScene(
            title="Problem",
            body=_trim(f"{audience} need the story, proof, and launch package, not another wall of code.", 320),
            footer="Turn repo context into a clear narrative",
            accent="#f97316",
        ),
        VideoScene(
            title="Repo proof",
            body=_trim(f"Ingests README, file tree, metadata, git log, and diff signals. Extracted why: {description}", 360),
            footer="Local repos and GitHub URLs supported",
            accent="#8b5cf6",
        ),
        VideoScene(
            title="Kimi critic/editor",
            body=_trim(kimi_excerpt or package.beats[-1], 360),
            footer="Live Kimi when configured, honest fallback when not",
            accent="#10b981",
        ),
        VideoScene(
            title="Launch package",
            body=_trim(f"Artifacts: repo brief, storyboard, SVG architecture, narration, captions, X/Discord copy, demo.html, and optional demo.mp4. {package.cta}", 360),
            footer="Open the artifact. Record or post the MP4. Ship.",
            accent="#ec4899",
        ),
    ]


def render_scene_png(scene: VideoScene, output_path: Path, config: RenderConfig = RenderConfig()) -> Path:
    ensure_render_runtime()
    from PIL import Image, ImageDraw

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (config.width, config.height), "#030712")
    draw = ImageDraw.Draw(image)

    _draw_background(draw, config, scene.accent)
    title_font = _load_font(86)
    body_font = _load_font(52)
    footer_font = _load_font(38)
    small_font = _load_font(30)

    draw.text((80, 92), "REPO-TO-SHORTS", font=small_font, fill="#67e8f9")
    draw.rounded_rectangle((64, 180, config.width - 64, 1570), radius=44, fill="#111827", outline=scene.accent, width=4)
    draw.text((104, 248), _wrap(scene.title, 18), font=title_font, fill="#f9fafb", spacing=12)

    body_lines = _wrap(scene.body, 30)
    draw.multiline_text((104, 650), body_lines, font=body_font, fill="#ddd6fe", spacing=18)

    draw.rounded_rectangle((80, 1630, config.width - 80, 1818), radius=34, fill="#0f172a", outline="#334155", width=3)
    draw.multiline_text((120, 1680), _wrap(scene.footer, 42), font=footer_font, fill="#bfdbfe", spacing=10)
    draw.text((80, 1856), "Generated vertical MP4 frame • 9:16", font=small_font, fill="#94a3b8")

    image.save(output_path)
    return output_path


def render_video(run_dir: Path, scenes: list[VideoScene], config: RenderConfig | None = None) -> RenderResult:
    config = config or RenderConfig()
    ensure_render_runtime()
    frames_dir = run_dir / "video_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    frame_paths = [render_scene_png(scene, frames_dir / f"scene_{index:02d}.png", config) for index, scene in enumerate(scenes, start=1)]

    concat_file = frames_dir / "frames.txt"
    concat_lines = []
    for frame in frame_paths:
        concat_lines.append(f"file '{frame.resolve()}'")
        concat_lines.append(f"duration {config.seconds_per_scene}")
    concat_lines.append(f"file '{frame_paths[-1].resolve()}'")
    concat_file.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")

    output_path = run_dir / config.output_name
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-f",
        "lavfi",
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-shortest",
        "-vf",
        f"fps={config.fps},format=yuv420p",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    return RenderResult(output_path=output_path, mode="mp4", renderer="pillow+ffmpeg", scene_count=len(scenes))


def _trim(value: str, limit: int) -> str:
    collapsed = " ".join(value.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1].rstrip() + "…"


def _wrap(value: str, width: int) -> str:
    return "\n".join(textwrap.wrap(value, width=width, max_lines=8, placeholder="…"))


def _load_font(size: int):
    from PIL import ImageFont

    for path in (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ):
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_background(draw, config: RenderConfig, accent: str) -> None:
    for y in range(0, config.height, 8):
        shade = int(7 + (y / config.height) * 18)
        draw.rectangle((0, y, config.width, y + 8), fill=(3, shade, 18 + shade))
    for offset in range(0, config.width, 135):
        draw.line((offset, 0, offset - 460, config.height), fill="#111827", width=3)
    draw.ellipse((-260, -260, 520, 520), fill=accent)
    draw.ellipse((-220, -220, 480, 480), fill="#030712")
