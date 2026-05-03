from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

STYLES: dict[str, dict[str, str]] = {
    "dark-terminal": {
        "bg": "#0d1117",
        "fg": "#c9d1d9",
        "accent": "#58a6ff",
        "secondary": "#238636",
        "highlight": "#f0883e",
        "font_title": "#f0f6fc",
        "box_bg": "#161b22",
        "box_border": "#30363d",
    },
    "clean-academic": {
        "bg": "#ffffff",
        "fg": "#1f2937",
        "accent": "#2563eb",
        "secondary": "#059669",
        "highlight": "#d97706",
        "font_title": "#111827",
        "box_bg": "#f3f4f6",
        "box_border": "#d1d5db",
    },
    "playful": {
        "bg": "#1e1b4b",
        "fg": "#e0e7ff",
        "accent": "#ec4899",
        "secondary": "#8b5cf6",
        "highlight": "#f59e0b",
        "font_title": "#ffffff",
        "box_bg": "#312e81",
        "box_border": "#4338ca",
    },
    "cinematic": {
        "bg": "#0f0f0f",
        "fg": "#d4d4d4",
        "accent": "#e50914",
        "secondary": "#b20710",
        "highlight": "#f5c518",
        "font_title": "#ffffff",
        "box_bg": "#1a1a1a",
        "box_border": "#333333",
    },
}

DEFAULT_WIDTH = 1080
DEFAULT_HEIGHT = 1920
DEFAULT_FPS = 30


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _lerp_color(a: str, b: str, t: float) -> str:
    ar, ag, ab = _hex_to_rgb(a)
    br, bg, bb = _hex_to_rgb(b)
    r = int(ar + (br - ar) * t)
    g = int(ag + (bg - ag) * t)
    b_col = int(ab + (bb - ab) * t)
    return f"#{r:02x}{g:02x}{b_col:02x}"


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
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


def generate_manim_script(
    scene: dict[str, Any],
    repo_analysis: dict[str, Any],
    output_dir: Path,
    style: str = "dark-terminal",
) -> Path:
    """Generate a self-contained scene descriptor (fallback when Manim is unavailable).

    Returns the path to a JSON descriptor that ``render_scene`` can consume.
    """
    if style not in STYLES:
        style = "dark-terminal"

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    descriptor = {
        "style": style,
        "width": DEFAULT_WIDTH,
        "height": DEFAULT_HEIGHT,
        "fps": DEFAULT_FPS,
        "repo_name": repo_analysis.get("name", "Repository"),
        "description": repo_analysis.get("description", ""),
        "components": repo_analysis.get("components", []),
        "scenes": scene.get("scenes", []),
    }

    script_path = output_dir / "manim_scene_descriptor.json"
    script_path.write_text(json.dumps(descriptor, indent=2) + "\n", encoding="utf-8")
    return script_path


def render_scene(script_path: Path, output_dir: Path, quality: str = "ql") -> Path:
    """Render a descriptor into an animated vertical MP4 using Pillow + ffmpeg.

    ``quality`` is accepted for API compatibility but ignored in the fallback.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    descriptor = json.loads(script_path.read_text(encoding="utf-8"))
    style = STYLES.get(descriptor.get("style", "dark-terminal"), STYLES["dark-terminal"])
    width = descriptor.get("width", DEFAULT_WIDTH)
    height = descriptor.get("height", DEFAULT_HEIGHT)
    fps = descriptor.get("fps", DEFAULT_FPS)
    repo_name = descriptor.get("repo_name", "Repository")
    description = descriptor.get("description", "")
    components = descriptor.get("components", [])
    scenes = descriptor.get("scenes", [])

    if not scenes:
        scenes = [
            {"type": "title_reveal", "duration": 3.0},
            {"type": "component_boxes", "duration": 5.0},
            {"type": "summary", "duration": 3.0},
        ]

    frames_dir = output_dir / "manim_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    frame_index = 0
    for scene in scenes:
        frame_index = _render_scene_frames(
            scene=scene,
            style=style,
            width=width,
            height=height,
            fps=fps,
            repo_name=repo_name,
            description=description,
            components=components,
            frames_dir=frames_dir,
            start_index=frame_index,
        )

    total_frames = frame_index
    output_path = output_dir / "demo.mp4"
    _encode_frames_to_mp4(frames_dir, total_frames, fps, width, height, output_path)
    return output_path


def _render_scene_frames(
    scene: dict[str, Any],
    style: dict[str, str],
    width: int,
    height: int,
    fps: int,
    repo_name: str,
    description: str,
    components: list[str],
    frames_dir: Path,
    start_index: int,
) -> int:
    scene_type = scene.get("type", scene.get("visual_tool", "title_reveal"))
    duration = float(scene.get("duration_seconds", scene.get("duration", 3.0)))
    # Map creative brief visual tools to render scene types
    tool_to_type = {
        "pretext": "title_reveal",
        "svg": "component_boxes",
        "manim": "component_boxes",
        "ascii": "summary",
    }
    scene_type = tool_to_type.get(scene_type, scene_type)
    total_frames = int(duration * fps)

    title_font = _load_font(92)
    subtitle_font = _load_font(54)
    body_font = _load_font(48)
    small_font = _load_font(36)

    for i in range(total_frames):
        t = i / total_frames if total_frames > 0 else 1.0
        image = Image.new("RGB", (width, height), style["bg"])
        draw = ImageDraw.Draw(image)
        _draw_gradient_background(draw, width, height, style)

        if scene_type == "title_reveal":
            _draw_title_scene(image, t, width, height, style, repo_name, description, title_font, subtitle_font)
        elif scene_type == "component_boxes":
            _draw_component_scene(image, t, width, height, style, components, title_font, body_font, small_font)
        else:
            _draw_summary_scene(image, t, width, height, style, repo_name, description, title_font, body_font)

        image.save(frames_dir / f"frame_{start_index + i:06d}.png")

    return start_index + total_frames


def _draw_gradient_background(
    draw: ImageDraw.ImageDraw,
    width: int,
    height: int,
    style: dict[str, str],
) -> None:
    bg_rgb = _hex_to_rgb(style["bg"])
    accent_rgb = _hex_to_rgb(style["accent"])
    for y in range(0, height, 4):
        t = y / height
        r = int(bg_rgb[0] + (accent_rgb[0] - bg_rgb[0]) * t * 0.15)
        g = int(bg_rgb[1] + (accent_rgb[1] - bg_rgb[1]) * t * 0.15)
        b = int(bg_rgb[2] + (accent_rgb[2] - bg_rgb[2]) * t * 0.15)
        draw.rectangle((0, y, width, y + 4), fill=(r, g, b))


def _ease_out_quad(t: float) -> float:
    return 1 - (1 - t) * (1 - t)


def _fade_alpha(t: float, start: float = 0.0, end: float = 1.0) -> int:
    if t < start:
        return 0
    if t > end:
        return 255
    return int(255 * ((t - start) / (end - start)))


def _draw_title_scene(
    image: Image.Image,
    t: float,
    width: int,
    height: int,
    style: dict[str, str],
    repo_name: str,
    description: str,
    title_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    subtitle_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    draw = ImageDraw.Draw(image)
    # Animated accent circle
    et = _ease_out_quad(min(t * 1.5, 1.0))
    radius = int(300 * et)
    draw.ellipse((width // 2 - radius, 200 - radius // 2, width // 2 + radius, 200 + radius * 3), fill=style["accent"])

    # Title fade + slide up
    alpha = _fade_alpha(t, 0.1, 0.5)
    if alpha > 0:
        y_offset = int(40 * (1 - _ease_out_quad(min((t - 0.1) / 0.4, 1.0))))
        title_y = 500 + y_offset
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.text((width // 2, title_y), repo_name, font=title_font, fill=style["font_title"], anchor="mm")
        if alpha < 255:
            overlay = Image.blend(Image.new("RGBA", image.size, (0, 0, 0, 0)), overlay, alpha / 255)
        image.paste(overlay, (0, 0), overlay)

    # Subtitle typewriter
    alpha2 = _fade_alpha(t, 0.4, 0.8)
    if alpha2 > 0:
        visible_chars = int(len(description) * min((t - 0.4) / 0.4, 1.0))
        text = description[:visible_chars]
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.text((width // 2, 750), text, font=subtitle_font, fill=style["fg"], anchor="mm")
        if alpha2 < 255:
            overlay = Image.blend(Image.new("RGBA", image.size, (0, 0, 0, 0)), overlay, alpha2 / 255)
        image.paste(overlay, (0, 0), overlay)

    # Cursor blink
    if t > 0.4 and int(t * 10) % 2 == 0 and alpha2 < 255:
        cursor_x = width // 2 + int(draw.textlength(description[:visible_chars], font=subtitle_font) / 2) + 10
        draw.rectangle((cursor_x, 720, cursor_x + 6, 780), fill=style["accent"])


def _draw_component_scene(
    image: Image.Image,
    t: float,
    width: int,
    height: int,
    style: dict[str, str],
    components: list[str],
    title_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    body_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    small_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    # Section title
    alpha = _fade_alpha(t, 0.0, 0.2)
    if alpha > 0:
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.text((width // 2, 140), "Architecture", font=title_font, fill=style["font_title"], anchor="mm")
        if alpha < 255:
            overlay = Image.blend(Image.new("RGBA", (width, height), (0, 0, 0, 0)), overlay, alpha / 255)
        image.paste(overlay, (0, 0), overlay)

    if not components:
        components = ["Ingest", "Story", "Kimi", "Artifacts", "Demo"]

    box_width = 760
    box_height = 140
    start_y = 340
    gap = 40

    for idx, comp in enumerate(components):
        comp_t_start = 0.15 + idx * 0.12
        comp_t = max(0.0, min(1.0, (t - comp_t_start) / 0.3))
        if comp_t <= 0:
            continue

        et = _ease_out_quad(comp_t)
        alpha = int(255 * et)
        y_offset = int(30 * (1 - et))

        x = (width - box_width) // 2
        y = start_y + idx * (box_height + gap) + y_offset

        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)

        # Box
        overlay_draw.rounded_rectangle(
            (x, y, x + box_width, y + box_height),
            radius=28,
            fill=style["box_bg"],
            outline=style["accent"] if idx == 0 else style["box_border"],
            width=4,
        )

        # Component name
        overlay_draw.text((x + 40, y + box_height // 2), comp, font=body_font, fill=style["font_title"], anchor="lm")

        # Index badge
        badge_size = 48
        badge_x = x + box_width - 70
        badge_y = y + box_height // 2
        overlay_draw.ellipse(
            (badge_x - badge_size // 2, badge_y - badge_size // 2, badge_x + badge_size // 2, badge_y + badge_size // 2),
            fill=style["accent"],
        )
        overlay_draw.text((badge_x, badge_y), str(idx + 1), font=small_font, fill=style["bg"], anchor="mm")

        # Connector line to next box (animate drawing)
        if idx < len(components) - 1:
            line_t = max(0.0, min(1.0, (comp_t - 0.5) / 0.5))
            if line_t > 0:
                next_y = start_y + (idx + 1) * (box_height + gap)
                line_end_y = y + box_height + int((next_y - (y + box_height)) * line_t)
                overlay_draw.line(
                    (width // 2, y + box_height, width // 2, line_end_y),
                    fill=style["accent"],
                    width=4,
                )
                # Arrow head
                if line_t > 0.8:
                    arrow_size = 12
                    overlay_draw.polygon(
                        [
                            (width // 2, line_end_y + arrow_size),
                            (width // 2 - arrow_size, line_end_y - arrow_size // 2),
                            (width // 2 + arrow_size, line_end_y - arrow_size // 2),
                        ],
                        fill=style["accent"],
                    )

        if alpha < 255:
            overlay = Image.blend(Image.new("RGBA", (width, height), (0, 0, 0, 0)), overlay, alpha / 255)
        image.paste(overlay, (0, 0), overlay)


def _draw_summary_scene(
    image: Image.Image,
    t: float,
    width: int,
    height: int,
    style: dict[str, str],
    repo_name: str,
    description: str,
    title_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    body_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    alpha = _fade_alpha(t, 0.0, 0.4)
    if alpha <= 0:
        return

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    overlay_draw.text((width // 2, 400), repo_name, font=title_font, fill=style["font_title"], anchor="mm")

    # Wrap description roughly
    words = description.split()
    lines = []
    line = []
    for word in words:
        line.append(word)
        if len(" ".join(line)) > 34:
            lines.append(" ".join(line[:-1]))
            line = [line[-1]]
    if line:
        lines.append(" ".join(line))

    visible_lines = int(len(lines) * min(t / 0.6, 1.0))
    text = "\n".join(lines[:visible_lines])
    overlay_draw.multiline_text((width // 2, 620), text, font=body_font, fill=style["fg"], anchor="mm", spacing=16)

    if t > 0.6:
        cta_alpha = _fade_alpha(t, 0.6, 0.9)
        if cta_alpha > 0:
            cta_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            cta_draw = ImageDraw.Draw(cta_overlay)
            cta_draw.rounded_rectangle(
                (width // 2 - 300, 1100, width // 2 + 300, 1220),
                radius=24,
                fill=style["accent"],
            )
            cta_draw.text((width // 2, 1160), "Launch Ready", font=title_font, fill=style["bg"], anchor="mm")
            if cta_alpha < 255:
                cta_overlay = Image.blend(Image.new("RGBA", (width, height), (0, 0, 0, 0)), cta_overlay, cta_alpha / 255)
            overlay = Image.alpha_composite(overlay, cta_overlay)

    if alpha < 255:
        overlay = Image.blend(Image.new("RGBA", (width, height), (0, 0, 0, 0)), overlay, alpha / 255)
    image.paste(overlay, (0, 0), overlay)


def _encode_frames_to_mp4(
    frames_dir: Path,
    total_frames: int,
    fps: int,
    width: int,
    height: int,
    output_path: Path,
) -> None:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is required for MP4 rendering.")

    pattern = str(frames_dir / "frame_%06d.png")
    command = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(fps),
        "-i",
        pattern,
        "-s",
        f"{width}x{height}",
        "-pix_fmt",
        "yuv420p",
        "-c:v",
        "libx264",
        "-movflags",
        "+faststart",
        "-an",
        str(output_path),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
