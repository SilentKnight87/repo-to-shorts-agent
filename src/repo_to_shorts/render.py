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
            title=f"{snapshot.name}",
            body=_trim(package.hook, 320),
            footer="Repo-to-Shorts Agent",
            accent="#22d3ee",
        ),
        VideoScene(
            title="The Problem",
            body=_trim(f"{audience} need the story, proof, and launch package, not another wall of code.", 320),
            footer="Turn repo context into a clear narrative",
            accent="#f97316",
        ),
        VideoScene(
            title="Repo Intelligence",
            body=_trim(f"Ingests README, file tree, metadata, git log, and diff signals. Extracted why: {description}", 360),
            footer="Local repos and GitHub URLs supported",
            accent="#8b5cf6",
        ),
        VideoScene(
            title="Kimi Creative Director",
            body=_trim(kimi_excerpt or package.beats[-1], 360),
            footer="Live Kimi when configured, honest fallback when not",
            accent="#10b981",
        ),
        VideoScene(
            title="Launch Package",
            body=_trim(f"Artifacts: repo brief, storyboard, SVG architecture, narration, captions, X/Discord copy, demo.html, and optional demo.mp4. {package.cta}", 360),
            footer="Open the artifact. Record or post the MP4. Ship.",
            accent="#ec4899",
        ),
    ]


def _load_font(size: int, bold: bool = False):
    from PIL import ImageFont

    candidates = []
    if bold:
        candidates = [
            "/System/Library/Fonts/HelveticaNeue.ttc",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]
    else:
        candidates = [
            "/System/Library/Fonts/HelveticaNeue.ttc",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Georgia.ttf",
        ]

    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _draw_gradient_bg(image, config: RenderConfig, accent: str) -> None:
    from PIL import ImageDraw
    draw = ImageDraw.Draw(image)
    w, h = config.width, config.height
    ac = _hex_to_rgb(accent)

    # Dark base gradient
    for y in range(h):
        t = y / h
        r = int(5 + t * 8)
        g = int(5 + t * 10)
        b = int(15 + t * 20)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # Accent radial glow (top-center)
    for radius in range(600, 0, -4):
        color = (min(255, ac[0] + 30), min(255, ac[1] + 30), min(255, ac[2] + 30))
        draw.ellipse(
            [(w//2 - radius, -200), (w//2 + radius, 400)],
            outline=(*color,),
            width=3,
        )

    # Subtle grid lines
    for offset in range(0, w, 120):
        draw.line([(offset, 0), (offset - 400, h)], fill=(255, 255, 255, 8), width=1)

    # Bottom glow
    for radius in range(400, 0, -6):
        draw.ellipse(
            [(w//2 - radius, h - 300), (w//2 + radius, h + 100)],
            outline=(ac[0]//4, ac[1]//4, ac[2]//4),
            width=2,
        )


def _draw_glow_text(draw, text: str, x: int, y: int, font, fill: str, glow_color: str | None = None, glow_radius: int = 12):
    """Draw text with a soft glow behind it."""
    if glow_color:
        gc = _hex_to_rgb(glow_color)
        for _ in range(glow_radius, 0, -3):
            draw.text((x, y), text, font=font, fill=(*gc,))
    draw.text((x, y), text, font=font, fill=fill)


def render_scene_png(scene: VideoScene, output_path: Path, config: RenderConfig = RenderConfig()) -> Path:
    ensure_render_runtime()
    from PIL import Image, ImageDraw

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (config.width, config.height), "#050507")
    draw = ImageDraw.Draw(image)

    _draw_gradient_bg(image, config, scene.accent)

    # Load fonts
    title_font = _load_font(92, bold=True)
    body_font = _load_font(48)
    small_font = _load_font(28)
    tag_font = _load_font(24)

    w, h = config.width, config.height
    ac = _hex_to_rgb(scene.accent)

    # Top brand bar
    draw.text((80, 60), "REPO-TO-SHORTS", font=small_font, fill="#67e8f9")
    draw.line([(80, 110), (w - 80, 110)], fill=(255, 255, 255, 30), width=1)

    # Main card with glassmorphism effect
    card_margin = 64
    card_top = 160
    card_bottom = h - 280
    draw.rounded_rectangle(
        [(card_margin, card_top), (w - card_margin, card_bottom)],
        radius=48,
        fill=(10, 10, 18, 180),
        outline=(*ac,),
        width=3,
    )

    # Inner glow on card top edge
    draw.line(
        [(card_margin + 20, card_top + 2), (w - card_margin - 20, card_top + 2)],
        fill=(*ac,),
        width=2,
    )

    # Accent tag
    tag_text = scene.footer.upper()
    tag_bbox = draw.textbbox((0, 0), tag_text, font=tag_font)
    tag_width = tag_bbox[2] - tag_bbox[0] + 32
    tag_height = tag_bbox[3] - tag_bbox[1] + 16
    draw.rounded_rectangle(
        [(card_margin + 40, card_top + 40), (card_margin + 40 + tag_width, card_top + 40 + tag_height)],
        radius=999,
        fill=(*ac,),
    )
    draw.text(
        (card_margin + 40 + 16, card_top + 40 + 6),
        tag_text,
        font=tag_font,
        fill=(0, 0, 0),
    )

    # Title
    title_lines = _wrap(scene.title, 16)
    draw.text(
        (card_margin + 40, card_top + 120),
        title_lines,
        font=title_font,
        fill="#f9fafb",
        spacing=16,
    )

    # Decorative line under title
    title_bbox = draw.textbbox((card_margin + 40, card_top + 120), title_lines, font=title_font, spacing=16)
    line_y = title_bbox[3] + 30
    draw.line(
        [(card_margin + 40, line_y), (card_margin + 40 + 200, line_y)],
        fill=(*ac,),
        width=4,
    )

    # Body text
    body_lines = _wrap(scene.body, 28)
    draw.multiline_text(
        (card_margin + 40, line_y + 50),
        body_lines,
        font=body_font,
        fill="#ddd6fe",
        spacing=20,
    )

    # Bottom info bar
    info_y = h - 200
    draw.rounded_rectangle(
        [(card_margin, info_y), (w - card_margin, info_y + 100)],
        radius=32,
        fill=(15, 15, 25, 200),
        outline=(255, 255, 255, 20),
        width=2,
    )

    # File type indicator
    draw.rounded_rectangle(
        [(card_margin + 30, info_y + 25), (card_margin + 30 + 80, info_y + 75)],
        radius=8,
        fill=(*ac,),
    )
    draw.text(
        (card_margin + 30 + 14, info_y + 32),
        "MP4",
        font=tag_font,
        fill=(0, 0, 0),
    )

    draw.text(
        (card_margin + 140, info_y + 32),
        "1080 × 1920  •  9:16 vertical  •  Generated by Repo-to-Shorts",
        font=small_font,
        fill="#94a3b8",
    )

    image.save(output_path, quality=95)
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
        f"zoompan=z='min(zoom+0.0015,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={config.width}x{config.height},fps={config.fps},format=yuv420p",
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
