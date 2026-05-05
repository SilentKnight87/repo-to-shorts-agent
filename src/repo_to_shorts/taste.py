from __future__ import annotations

from pathlib import Path
from typing import Any

DEFAULT_DESIGN_PROFILE: dict[str, Any] = {
    "schema_version": 1,
    "source": None,
    "name": "Repo-to-Shorts Default Taste",
    "colors": {
        "neutral": "#080A0F",
        "primary": "#F6F2E8",
        "secondary": "#9BA3AF",
        "tertiary": "#6EE7F9",
        "accentWarm": "#F97316",
    },
    "rounded": {"sm": "4px", "md": "8px", "lg": "8px"},
    "notes": "terminal-native, premium, fast, credible",
}


def load_design_profile(path: Path | str = Path("DESIGN.md")) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return dict(DEFAULT_DESIGN_PROFILE)

    text = path.read_text(encoding="utf-8")
    frontmatter, notes = _split_frontmatter(text)
    profile = dict(DEFAULT_DESIGN_PROFILE)
    profile["source"] = str(path)
    profile["notes"] = notes.strip()
    profile.update(_parse_simple_yaml(frontmatter))
    profile["schema_version"] = 1
    return profile


def build_reference_pack(
    design_path: Path | str = Path("DESIGN.md"),
    taste_research_path: Path | str = Path("docs/taste-research.md"),
) -> dict[str, Any]:
    design_path = Path(design_path)
    taste_research_path = Path(taste_research_path)
    sources = []
    for source in (design_path, taste_research_path):
        if source.exists():
            sources.append({"path": str(source), "kind": source.stem})

    return {
        "schema_version": 1,
        "sources": sources,
        "references": [
            {
                "label": "premium console",
                "borrow": ["restrained palette", "repo proof chips", "kinetic code text"],
                "avoid": ["purple-blue gradient hero", "three generic cards"],
            },
            {
                "label": "cinematic kinetic typography",
                "borrow": ["3-7 word beats", "motion follows meaning", "proof holds"],
                "avoid": ["full sentences as overlays", "ambient motion without purpose"],
            },
        ],
        "avoid": [
            "generic AI SaaS soup",
            "default three-card grid",
            "abstract shapes before product context",
            "random colors outside DESIGN.md",
            "captions outside 9:16 safe area",
        ],
    }


def _split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---", 4)
    if end == -1:
        return "", text
    return text[4:end], text[end + 4 :]


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, result)]
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.strip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip().strip('"')
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value:
            parent[key] = value
        else:
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
    return result
