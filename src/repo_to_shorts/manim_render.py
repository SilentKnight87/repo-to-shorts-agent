from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont

DEFAULT_WIDTH = 1080
DEFAULT_HEIGHT = 1920
DEFAULT_FPS = 30
SAFE_FILE_PREFIXES = ("src/", "tests/", "docs/")
SAFE_FILE_NAMES = {"README.md", "pyproject.toml", "package.json"}
SECRET_FILE_MARKERS = (".env", "secret", "token", "private", "id_rsa", ".pem", ".key")

STYLES: dict[str, dict[str, str]] = {
    "dark-terminal": {
        "bg": "#050507",
        "fg": "#f7f8f8",
        "muted": "#8a8f98",
        "soft": "#d0d6e0",
        "accent": "#7c72ff",
        "accent2": "#16d9e3",
        "panel": "#11131a",
        "line": "#2a2d3a",
        "good": "#30d158",
    },
    "cinematic": {
        "bg": "#030304",
        "fg": "#ffffff",
        "muted": "#9ca3af",
        "soft": "#e5e7eb",
        "accent": "#ff3b30",
        "accent2": "#ffd60a",
        "panel": "#141416",
        "line": "#33333a",
        "good": "#30d158",
    },
    "clean-academic": {
        "bg": "#f7f8ff",
        "fg": "#111827",
        "muted": "#4b5563",
        "soft": "#1f2937",
        "accent": "#405cf5",
        "accent2": "#06b6d4",
        "panel": "#ffffff",
        "line": "#dbe1f0",
        "good": "#059669",
    },
    "playful": {
        "bg": "#120b2f",
        "fg": "#ffffff",
        "muted": "#c4b5fd",
        "soft": "#ede9fe",
        "accent": "#ec4899",
        "accent2": "#22d3ee",
        "panel": "#24104f",
        "line": "#5b21b6",
        "good": "#a3e635",
    },
}


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int, max_lines: int = 6) -> list[str]:
    words = (text or "").replace("\n", " ").split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        trial = " ".join([*current, word])
        if draw.textlength(trial, font=font) <= max_width or not current:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(" ".join(current))
    return lines


def _ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def _fade(t: float, start: float, end: float) -> int:
    if t <= start:
        return 0
    if t >= end:
        return 255
    return int(255 * _ease((t - start) / (end - start)))


def _slug_label(value: str) -> str:
    value = value.replace("src/", "").replace("tests/", "").replace(".py", "").replace(".ts", "")
    return value.replace("/", " › ").replace("_", " ").title()[:42]


def _safe_key_files(key_files: list[str], limit: int = 10) -> list[str]:
    safe = []
    for path in key_files:
        lowered = path.lower()
        if lowered.startswith("runs/") or any(marker in lowered for marker in SECRET_FILE_MARKERS):
            continue
        if path in SAFE_FILE_NAMES or path.startswith(SAFE_FILE_PREFIXES):
            safe.append(path)
        if len(safe) >= limit:
            break
    return safe


def _caption_chunks(text: str, words_per_chunk: int = 3) -> list[str]:
    words = [word.strip() for word in (text or "").replace("\n", " ").split() if word.strip()]
    if not words:
        return []
    if len(words) <= 4:
        return [" ".join(words)]
    chunk_size = 4 if len(words) > 18 else words_per_chunk
    return [" ".join(words[index : index + chunk_size]) for index in range(0, len(words), chunk_size)]


def _active_caption_chunk(text: str, t: float) -> tuple[str, int, int]:
    chunks = _caption_chunks(text)
    if not chunks:
        return "", 0, 0
    index = min(len(chunks) - 1, int(max(0.0, min(0.999, t)) * len(chunks)))
    return chunks[index], index, len(chunks)


def _draw_centered_text_with_shadow(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: str,
    *,
    anchor: str = "mm",
    shadow: tuple[int, int, int, int] = (0, 0, 0, 230),
) -> None:
    x, y = xy
    for dx, dy in ((0, 8), (0, 4), (3, 3), (-3, 3)):
        draw.text((x + dx, y + dy), text, font=font, fill=shadow, anchor=anchor)
    draw.text((x, y), text, font=font, fill=fill, anchor=anchor)


def _fit_caption_lines(draw: ImageDraw.ImageDraw, text: str, max_width: int) -> tuple[list[str], ImageFont.ImageFont]:
    for size in (76, 68, 60, 52, 46):
        font = _font(size, bold=True)
        lines = _wrap(draw, text.upper(), font, max_width, max_lines=2)
        if lines and all(draw.textlength(line, font=font) <= max_width for line in lines):
            return lines, font
    font = _font(42, bold=True)
    return _wrap(draw, text.upper(), font, max_width, max_lines=2), font


def generate_manim_script(scene: dict[str, Any], repo_analysis: dict[str, Any], output_dir: Path, style: str = "dark-terminal") -> Path:
    if style not in STYLES:
        style = "dark-terminal"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    descriptor = {
        "style": style,
        "width": DEFAULT_WIDTH,
        "height": DEFAULT_HEIGHT,
        "fps": int(scene.get("fps", DEFAULT_FPS)),
        "repo_name": repo_analysis.get("name") or repo_analysis.get("repo_name") or "Repository",
        "description": repo_analysis.get("description", ""),
        "components": repo_analysis.get("components", []),
        "key_files": _safe_key_files(repo_analysis.get("key_files", [])),
        "primary_language": repo_analysis.get("primary_language", ""),
        "scenes": scene.get("scenes", []),
    }
    script_path = output_dir / "manim_scene_descriptor.json"
    script_path.write_text(json.dumps(descriptor, indent=2) + "\n", encoding="utf-8")
    return script_path


def render_scene(script_path: Path, output_dir: Path, quality: str = "ql") -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    descriptor = json.loads(script_path.read_text(encoding="utf-8"))
    style = STYLES.get(descriptor.get("style", "dark-terminal"), STYLES["dark-terminal"])
    width = int(descriptor.get("width", DEFAULT_WIDTH))
    height = int(descriptor.get("height", DEFAULT_HEIGHT))
    fps = int(descriptor.get("fps", DEFAULT_FPS))
    scenes = descriptor.get("scenes") or []
    if not scenes:
        scenes = [
            {"type": "title_reveal", "duration": 3.0, "duration_seconds": 3, "visual_tool": "pretext", "narration": "A repo becomes a launch story."},
            {"type": "component_boxes", "duration": 5.0, "duration_seconds": 5, "visual_tool": "svg", "narration": "The architecture turns into motion."},
            {"type": "summary", "duration": 3.0, "duration_seconds": 3, "visual_tool": "ascii", "narration": "Generated by Hermes Agent."},
        ]

    frames_dir = output_dir / "manim_frames"
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True)

    frame_index = 0
    total_scenes = len(scenes)
    for idx, scene in enumerate(scenes):
        frame_index = _render_scene_frames(
            scene=scene,
            scene_index=idx,
            scene_count=total_scenes,
            descriptor=descriptor,
            style=style,
            width=width,
            height=height,
            fps=fps,
            frames_dir=frames_dir,
            start_index=frame_index,
        )

    output_path = output_dir / "demo.mp4"
    _encode_frames_to_mp4(frames_dir, frame_index, fps, width, height, output_path)
    return output_path


def _base_frame(width: int, height: int, style: dict[str, str], t: float, scene_index: int) -> Image.Image:
    bg = _hex_to_rgb(style["bg"])
    accent = _hex_to_rgb(style["accent"])
    accent2 = _hex_to_rgb(style["accent2"])
    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img, "RGBA")

    for y in range(0, height, 6):
        k = y / height
        pulse = (math.sin(t * math.tau + scene_index) + 1) / 2
        r = int(bg[0] + accent[0] * (0.05 + 0.10 * k) + accent2[0] * 0.035 * pulse)
        g = int(bg[1] + accent[1] * (0.05 + 0.10 * k) + accent2[1] * 0.035 * pulse)
        b = int(bg[2] + accent[2] * (0.05 + 0.10 * k) + accent2[2] * 0.035 * pulse)
        draw.rectangle((0, y, width, y + 6), fill=(min(r, 255), min(g, 255), min(b, 255), 255))

    grid_alpha = 22
    offset = int((t * 90) % 90)
    for x in range(-offset, width, 90):
        draw.line((x, 0, x, height), fill=(255, 255, 255, grid_alpha), width=1)
    for y in range(offset - 90, height, 90):
        draw.line((0, y, width, y), fill=(255, 255, 255, grid_alpha), width=1)

    for n in range(4):
        cx = int(width * (0.18 + 0.28 * n) + math.sin(t * math.tau + n) * 42)
        cy = int(height * (0.10 + 0.18 * ((n + scene_index) % 4)) + math.cos(t * math.tau * 0.7 + n) * 56)
        radius = 220 + n * 36
        color = accent if n % 2 == 0 else accent2
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(*color, 22))
    return img.filter(ImageFilter.GaussianBlur(radius=0.2))


def _render_scene_frames(
    scene: dict[str, Any],
    scene_index: int,
    scene_count: int,
    descriptor: dict[str, Any],
    style: dict[str, str],
    width: int,
    height: int,
    fps: int,
    frames_dir: Path,
    start_index: int,
) -> int:
    duration = max(2.0, float(scene.get("duration_seconds", scene.get("duration", 6.0))))
    total_frames = int(duration * fps)
    tool = scene.get("visual_tool", "pretext")
    repo_name = descriptor.get("repo_name", "Repository")
    description = descriptor.get("description", "")
    components = descriptor.get("components", []) or ["Ingest", "Creative Director", "Renderer", "TTS", "Demo MP4"]
    key_files = descriptor.get("key_files", []) or []
    language = descriptor.get("primary_language", "")

    for i in range(total_frames):
        t = i / max(total_frames - 1, 1)
        image = _base_frame(width, height, style, t, scene_index)
        if tool in {"svg", "manim"}:
            _draw_system_map(image, t, style, repo_name, components, scene_index, scene_count)
        elif tool == "ascii":
            _draw_code_evidence(image, t, style, repo_name, key_files, language)
        else:
            _draw_story_card(image, t, style, repo_name, description, scene, scene_index, scene_count)
        _draw_caption_and_chrome(image, t, style, scene, scene_index, scene_count)
        _draw_scene_transition(image, t)
        image.save(frames_dir / f"frame_{start_index + i:06d}.png", quality=92)
    return start_index + total_frames


def _draw_chrome(draw: ImageDraw.ImageDraw, width: int, style: dict[str, str], scene_index: int, scene_count: int) -> None:
    mono = _font(28)
    small = _font(24, bold=True)
    draw.rounded_rectangle((54, 54, width - 54, 118), radius=28, fill=(255, 255, 255, 14), outline=(*_hex_to_rgb(style["line"]), 190), width=1)
    draw.text((84, 86), "REPO → SHORTS", font=small, fill=style["soft"], anchor="lm")
    draw.text((width - 84, 86), f"SCENE {scene_index + 1:02d}/{scene_count:02d}", font=mono, fill=style["muted"], anchor="rm")


def _draw_scene_transition(image: Image.Image, t: float) -> None:
    fade = max(0.0, 1.0 - min(t, 1.0 - t) / 0.08)
    if fade <= 0:
        return
    draw = ImageDraw.Draw(image, "RGBA")
    width, height = image.size
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0, int(150 * fade)))


def _draw_caption_and_chrome(image: Image.Image, t: float, style: dict[str, str], scene: dict[str, Any], scene_index: int, scene_count: int) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    width, height = image.size
    _draw_chrome(draw, width, style, scene_index, scene_count)

    caption = scene.get("narration", "")
    chunk, chunk_index, chunk_count = _active_caption_chunk(caption, t)
    if chunk:
        eyebrow_font = _font(24, bold=True)
        y = int(height * 0.765)
        pulse = 0.5 + 0.5 * math.sin((t * max(chunk_count, 1) % 1) * math.pi)
        glow_alpha = int(80 + 70 * pulse)
        accent = _hex_to_rgb(style["accent2"])
        panel_w = width - 132
        panel_h = 174
        x0 = (width - panel_w) // 2
        y0 = y - panel_h // 2
        caption_lines, caption_font = _fit_caption_lines(draw, chunk, panel_w - 120)
        draw.rounded_rectangle((x0 - 14, y0 - 12, x0 + panel_w + 14, y0 + panel_h + 16), radius=46, fill=(*accent, glow_alpha // 3))
        draw.rounded_rectangle((x0, y0, x0 + panel_w, y0 + panel_h), radius=38, fill=(0, 0, 0, 185), outline=(*accent, 220), width=2)
        draw.text((width // 2, y0 + 30), f"CAPTION {chunk_index + 1:02d}/{chunk_count:02d}", font=eyebrow_font, fill=style["accent2"], anchor="mm")
        first_y = y0 + 92 if len(caption_lines) == 1 else y0 + 76
        for line_idx, line in enumerate(caption_lines):
            _draw_centered_text_with_shadow(draw, (width // 2, first_y + line_idx * 60), line, caption_font, style["fg"])

    progress_w = int((width - 108) * t)
    draw.rounded_rectangle((54, height - 34, width - 54, height - 24), radius=8, fill=(255, 255, 255, 28))
    draw.rounded_rectangle((54, height - 34, 54 + progress_w, height - 24), radius=8, fill=style["accent2"])


def _draw_story_card(image: Image.Image, t: float, style: dict[str, str], repo_name: str, description: str, scene: dict[str, Any], scene_index: int, scene_count: int) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    width, height = image.size
    title = scene.get("title") or (scene.get("narration", "") or repo_name)
    title_font = _font(96 if scene_index == 0 else 82, bold=True)
    body_font = _font(42)
    label_font = _font(24, bold=True)

    y_shift = int(42 * (1 - _ease(t)))
    if scene_index == 0:
        hook = scene.get("hook") or title
        hook_lines = _wrap(draw, hook, title_font, width - 144, max_lines=4)
        center_y = 500 + y_shift
        draw.text((72, 238 + y_shift), "LIVE REPO TRAILER", font=label_font, fill=style["accent2"])
        draw.text((72, 292 + y_shift), "Kimi directs. Hermes ships.", font=_font(38, bold=True), fill=style["muted"])
        for line in hook_lines:
            _draw_centered_text_with_shadow(draw, (width // 2, center_y), line.upper(), title_font, style["fg"])
            center_y += 108
        draw.rounded_rectangle((86, 1010, width - 86, 1186), radius=42, fill=(255, 255, 255, 18), outline=(*_hex_to_rgb(style["accent2"]), 190), width=2)
        draw.text((width // 2, 1070), "REPO IN", font=_font(30, bold=True), fill=style["muted"], anchor="mm")
        draw.text((width // 2, 1132), "VERTICAL SHORT OUT", font=_font(54, bold=True), fill=style["accent2"], anchor="mm")
        return

    draw.text((72, 250 + y_shift), "KIMI CREATIVE BRIEF", font=label_font, fill=style["accent2"])
    draw.text((72, 316 + y_shift), repo_name, font=_font(48, bold=True), fill=style["muted"])

    lines = _wrap(draw, title, title_font, width - 144, max_lines=4)
    y = 430 + y_shift
    for line in lines:
        draw.text((72, y), line, font=title_font, fill=style["fg"])
        y += 92

    if description:
        desc_lines = _wrap(draw, description, body_font, width - 180, max_lines=3)
        panel_y = 990
        draw.rounded_rectangle((64, panel_y, width - 64, panel_y + 250), radius=34, fill=(255, 255, 255, 18), outline=(*_hex_to_rgb(style["line"]), 220), width=2)
        draw.text((96, panel_y + 48), "Repo signal", font=label_font, fill=style["accent"])
        for idx, line in enumerate(desc_lines):
            draw.text((96, panel_y + 98 + idx * 48), line, font=body_font, fill=style["soft"])


def _draw_system_map(image: Image.Image, t: float, style: dict[str, str], repo_name: str, components: list[str], scene_index: int, scene_count: int) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    width, _ = image.size
    title_font = _font(64, bold=True)
    card_font = _font(34, bold=True)
    small_font = _font(22)
    draw.text((72, 246), "Architecture in motion", font=title_font, fill=style["fg"])
    draw.text((72, 320), repo_name, font=_font(32), fill=style["muted"])

    visible = max(1, int(math.ceil(len(components[:6]) * _ease(t))))
    nodes = components[:6]
    positions = [(120, 500), (560, 500), (120, 760), (560, 760), (120, 1020), (560, 1020)]
    centers: list[tuple[int, int]] = []
    for idx, (component, (x, y)) in enumerate(zip(nodes, positions, strict=False)):
        if idx >= visible:
            continue
        alpha = int(255 * _ease(min(1, (t - idx * 0.08) / 0.24)))
        fill = (*_hex_to_rgb(style["panel"]), max(80, int(alpha * 0.78)))
        outline = style["accent"] if idx in {0, len(nodes) - 1} else style["line"]
        draw.rounded_rectangle((x, y, x + 400, y + 170), radius=34, fill=fill, outline=outline, width=3)
        draw.text((x + 32, y + 58), _slug_label(component), font=card_font, fill=style["fg"])
        draw.text((x + 32, y + 112), f"module.{idx + 1:02d}", font=small_font, fill=style["muted"])
        centers.append((x + 200, y + 85))
    for a, b in zip(centers, centers[1:], strict=False):
        draw.line((a[0], a[1], b[0], b[1]), fill=style["accent2"], width=5)
        draw.ellipse((b[0] - 8, b[1] - 8, b[0] + 8, b[1] + 8), fill=style["accent2"])


def _draw_code_evidence(image: Image.Image, t: float, style: dict[str, str], repo_name: str, key_files: list[str], language: str) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    width, _ = image.size
    title_font = _font(62, bold=True)
    mono = _font(30)
    draw.text((72, 246), "Evidence, not vibes", font=title_font, fill=style["fg"])
    draw.text((72, 320), f"{repo_name} · {language or 'codebase'}", font=_font(32), fill=style["muted"])

    x0, y0, x1, y1 = 64, 440, width - 64, 1250
    draw.rounded_rectangle((x0, y0, x1, y1), radius=34, fill=(0, 0, 0, 150), outline=(*_hex_to_rgb(style["line"]), 230), width=2)
    draw.ellipse((x0 + 34, y0 + 38, x0 + 54, y0 + 58), fill="#ff5f57")
    draw.ellipse((x0 + 66, y0 + 38, x0 + 86, y0 + 58), fill="#ffbd2e")
    draw.ellipse((x0 + 98, y0 + 38, x0 + 118, y0 + 58), fill="#28c840")
    files = key_files[:13] or ["src/pipeline.py", "src/creative_director.py", "src/manim_render.py", "tests/test_web.py"]
    visible = int(len(files) * min(1, t * 1.25))
    for idx, file_name in enumerate(files[:visible]):
        y = y0 + 112 + idx * 48
        prefix = "→" if idx == visible - 1 else " "
        color = style["accent2"] if idx % 3 == 0 else style["soft"]
        draw.text((x0 + 42, y), f"{prefix} {file_name}", font=mono, fill=color)


def _encode_frames_to_mp4(frames_dir: Path, total_frames: int, fps: int, width: int, height: int, output_path: Path) -> None:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is required for MP4 rendering.")
    if total_frames <= 0:
        raise RuntimeError("No frames rendered.")
    command = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(fps),
        "-i",
        str(frames_dir / "frame_%06d.png"),
        "-s",
        f"{width}x{height}",
        "-pix_fmt",
        "yuv420p",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-movflags",
        "+faststart",
        "-an",
        str(output_path),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
