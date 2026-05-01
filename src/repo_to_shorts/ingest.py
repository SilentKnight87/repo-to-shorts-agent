from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import tomllib


@dataclass(frozen=True)
class RepoSnapshot:
    target: str
    name: str
    source_type: str
    path: Path
    readme: str
    file_tree: list[str]
    package_metadata: dict[str, str] = field(default_factory=dict)
    git_log: str = "Git history unavailable."
    git_diff: str = "No git diff available."


def is_github_url(target: str) -> bool:
    parsed = urlparse(target)
    return parsed.scheme in {"http", "https"} and parsed.netloc.lower() == "github.com"


def ingest_target(target: str) -> RepoSnapshot:
    """Create a deterministic snapshot from a local repository or GitHub URL."""
    if is_github_url(target):
        temp_root = Path(tempfile.mkdtemp(prefix="repo-shorts-"))
        repo_path = temp_root / _repo_name_from_target(target)
        subprocess.run(
            ["git", "clone", "--depth", "1", target, str(repo_path)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        source_type = "github"
    else:
        repo_path = Path(target).expanduser().resolve()
        if not repo_path.exists() or not repo_path.is_dir():
            raise FileNotFoundError(f"Repository target does not exist or is not a directory: {target}")
        source_type = "local"

    return RepoSnapshot(
        target=target,
        name=_repo_name_from_path(repo_path),
        source_type=source_type,
        path=repo_path,
        readme=_read_readme(repo_path),
        file_tree=_file_tree(repo_path),
        package_metadata=_package_metadata(repo_path),
        git_log=_git_output(repo_path, ["git", "log", "--oneline", "-5"], "Git history unavailable."),
        git_diff=_git_output(repo_path, ["git", "diff", "--stat"], "No git diff available."),
    )


def _repo_name_from_target(target: str) -> str:
    parsed = urlparse(target)
    stem = Path(parsed.path).name if parsed.scheme else Path(target).name
    return stem.removesuffix(".git") or "repository"


def _repo_name_from_path(path: Path) -> str:
    metadata = _package_metadata(path)
    return metadata.get("name") or path.name


def _read_readme(path: Path) -> str:
    for name in ("README.md", "readme.md", "README.rst", "README.txt"):
        candidate = path / name
        if candidate.exists():
            return _safe_read(candidate, limit=12000)
    return "No README found."


def _file_tree(path: Path, limit: int = 80) -> list[str]:
    ignored_dirs = {
        ".git",
        ".venv",
        ".ruff_cache",
        ".pytest_cache",
        "node_modules",
        "__pycache__",
        "dist",
        "build",
        "runs",
    }
    entries: list[str] = []
    for candidate in sorted(path.rglob("*")):
        rel = candidate.relative_to(path)
        if any(part in ignored_dirs for part in rel.parts):
            continue
        if candidate.is_file():
            entries.append(str(rel))
        if len(entries) >= limit:
            entries.append("... truncated ...")
            break
    return entries


def _package_metadata(path: Path) -> dict[str, str]:
    pyproject = path / "pyproject.toml"
    if pyproject.exists():
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            project = data.get("project", {})
            return {k: str(v) for k, v in project.items() if k in {"name", "version", "description"}}
        except (tomllib.TOMLDecodeError, OSError):
            pass
    package_json = path / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
            return {k: str(v) for k, v in data.items() if k in {"name", "version", "description"}}
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _git_output(path: Path, command: list[str], fallback: str) -> str:
    if not shutil.which("git"):
        return fallback
    try:
        result = subprocess.run(command, cwd=path, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except (subprocess.CalledProcessError, OSError):
        return fallback
    output = result.stdout.strip()
    return output or fallback


def _safe_read(path: Path, limit: int) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:limit]
