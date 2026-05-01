from __future__ import annotations

from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(help="Turn a repository into a technical short video package.")
console = Console()


def _slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")[:60]


@app.command()
def analyze(target: str = typer.Argument(..., help="Local repo path or GitHub URL.")) -> None:
    """Create a visible run folder for the repo-to-shorts pipeline."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target_slug = _slug(Path(target).name or target)
    run_dir = Path("runs") / f"{timestamp}-{target_slug}"
    run_dir.mkdir(parents=True, exist_ok=True)

    metadata = run_dir / "metadata.md"
    metadata.write_text(
        f"# Repo-to-Shorts Run\n\n- Target: `{target}`\n- Created: {datetime.now().isoformat()}\n\n",
        encoding="utf-8",
    )

    console.print(f"[green]Created run:[/green] {run_dir}")
    console.print(f"[cyan]Next:[/cyan] ingest repo facts, create storyboard, generate visuals.")


if __name__ == "__main__":
    app()
