from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from repo_to_shorts.pipeline import run_analysis
from repo_to_shorts.web import run_web_server

DEFAULT_OUT = Path("runs")

app = typer.Typer(help="Turn a repository into a technical short-video package.")
console = Console()


@app.callback()
def main() -> None:
    """Repo-to-Shorts command group."""


def _slug(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug[:60] or "repo"


@app.command()
def analyze(
    target: str = typer.Argument(..., help="Local repo path or GitHub URL."),
    audience: str = typer.Option("technical builders", "--audience", "-a", help="Audience for the short."),
    out: Path = typer.Option(DEFAULT_OUT, "--out", "-o", help="Directory where run folders are written."),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing timestamped run directory if needed."),
    kimi_model: str | None = typer.Option(None, "--kimi-model", help="OpenRouter/Moonshot Kimi model name."),
    render: str = typer.Option("none", "--render", help="Optional renderer: none or mp4."),
) -> None:
    """Analyze TARGET and create a launch-ready short-video package."""
    try:
        run_dir = run_analysis(target, audience=audience, out_dir=out, force=force, kimi_model=kimi_model, render=render)
    except Exception as exc:  # noqa: BLE001 - Typer should print concise CLI failures.
        raise typer.BadParameter(str(exc)) from exc

    console.print(f"[green]Created run:[/green] {run_dir}")
    console.print(f"[cyan]Open:[/cyan] {run_dir / 'demo.html'}")
    if (run_dir / "demo.mp4").exists():
        console.print(f"[cyan]MP4:[/cyan] {run_dir / 'demo.mp4'}")
    console.print("[cyan]Artifacts:[/cyan] repo brief, storyboard, SVG architecture, narration, captions, launch copy, Kimi critique")


@app.command()
def web(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Run the local web UI."""
    run_web_server(host=host, port=port)


@app.command()
def creative(
    target: str = typer.Argument(..., help="Local repo path or GitHub URL."),
    audience: str = typer.Option("technical builders", "--audience", "-a", help="Audience for the short."),
    out: Path = typer.Option(DEFAULT_OUT, "--out", "-o", help="Directory where run folders are written."),
    kimi_model: str | None = typer.Option(None, "--kimi-model", help="OpenRouter/Moonshot Kimi model name."),
    music: Path | None = typer.Option(None, "--music", help="Optional background music MP3 file."),
    preview: bool = typer.Option(False, "--preview", help="Fast 12-15s preview render for iteration."),
    skip_audio: bool = typer.Option(False, "--skip-audio", help="Skip TTS/music composition for fastest visual iteration."),
) -> None:
    """Generate a creative short video with Kimi 2.6 creative direction."""
    from repo_to_shorts.hermes_skill import run_creative_pipeline

    try:
        result = run_creative_pipeline(
            target,
            audience=audience,
            out_dir=out,
            kimi_model=kimi_model,
            music_path=music,
            preview=preview,
            skip_audio=skip_audio,
        )
    except Exception as exc:  # noqa: BLE001
        raise typer.BadParameter(str(exc)) from exc

    console.print(f"[green]Creative short generated:[/green] {result['output']}")
    console.print(f"[cyan]Run dir:[/cyan] {result['run_dir']}")
    console.print("[cyan]Proof:[/cyan] metadata.json shows kimi.mode and creative brief")


if __name__ == "__main__":
    app()
