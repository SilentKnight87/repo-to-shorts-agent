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
    final: bool = typer.Option(False, "--final", help="Run submission-grade final export with validation."),
    tts_provider: str = typer.Option("edge", "--tts-provider", help="TTS provider: xai, openai, elevenlabs, edge, or none."),
    fallback_tts_provider: str | None = typer.Option(
        None,
        "--fallback-tts-provider",
        help="Fallback TTS provider (--fallback-tts-provider).",
    ),
    voice: str | None = typer.Option(None, "--voice", help="Provider-specific voice id."),
    generated_music: bool = typer.Option(
        True,
        "--generated-music/--no-generated-music",
        help="Generate ambient music when no --music is supplied.",
    ),
    compare_previews: bool = typer.Option(False, "--compare-previews", help="Generate and score preview concept variants before rendering."),
    max_revisions: int = typer.Option(2, "--max-revisions", min=0, max=5, help="Maximum Kimi QA revision attempts before final failure."),
) -> None:
    """Generate a creative short video with Kimi 2.6 creative direction.

    Final export options include --final, --tts-provider, --fallback-tts-provider,
    --voice, and --no-generated-music.
    """
    from repo_to_shorts.hermes_skill import run_creative_pipeline

    command = ["repo-shorts", "creative", target, "--audience", audience, "--out", str(out)]
    if kimi_model:
        command.extend(["--kimi-model", kimi_model])
    if music is not None:
        command.extend(["--music", str(music)])
    if preview:
        command.append("--preview")
    if skip_audio:
        command.append("--skip-audio")
    if final:
        command.append("--final")
    command.extend(["--tts-provider", tts_provider])
    if fallback_tts_provider:
        command.extend(["--fallback-tts-provider", fallback_tts_provider])
    if voice:
        command.extend(["--voice", voice])
    if not generated_music:
        command.append("--no-generated-music")
    if max_revisions != 2:
        command.extend(["--max-revisions", str(max_revisions)])
    if compare_previews:
        command.append("--compare-previews")

    try:
        result = run_creative_pipeline(
            target,
            audience=audience,
            out_dir=out,
            kimi_model=kimi_model,
            music_path=music,
            preview=preview,
            skip_audio=skip_audio,
            final=final,
            tts_provider=tts_provider,
            fallback_tts_provider=fallback_tts_provider,
            voice=voice,
            generated_music=generated_music,
            command=command,
            compare_previews=compare_previews,
            max_revisions=max_revisions,
        )
    except Exception as exc:  # noqa: BLE001
        raise typer.BadParameter(str(exc)) from exc

    console.print(f"[green]Creative short generated:[/green] {result['output']}")
    console.print(f"[cyan]Run dir:[/cyan] {result['run_dir']}")
    console.print("[cyan]Proof:[/cyan] metadata.json shows kimi.mode and creative brief")


if __name__ == "__main__":
    app()
