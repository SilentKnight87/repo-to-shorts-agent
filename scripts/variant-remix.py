#!/usr/bin/env python3
"""Re-mix audio on an existing run dir with a different TTS voice/provider.

Avoids spending another Kimi + Remotion render. Uses the run's video_raw.mp4
and creative_brief scenes from metadata.json, then re-runs TTS + audio mix
with the requested voice. Saves to a new file in the same run dir.

Usage:
  variant-remix.py <run_dir> <out_filename> --tts-provider PROVIDER [--voice VOICE]
                                              [--fallback-tts-provider PROVIDER]
                                              [--no-music]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Import the existing audio remix function so we keep behavior identical.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from repo_to_shorts.hermes_skill import _merge_creative_video  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("out_filename")
    parser.add_argument("--tts-provider", required=True)
    parser.add_argument("--voice", default=None)
    parser.add_argument("--fallback-tts-provider", default=None)
    parser.add_argument("--no-music", action="store_true")
    parser.add_argument("--music-path", default=None, help="Path to music MP3 to mix under voice")
    args = parser.parse_args()

    run_dir: Path = args.run_dir.resolve()
    if not run_dir.is_dir():
        print(f"error: run_dir not found: {run_dir}", file=sys.stderr)
        return 2

    video_raw = run_dir / "video_raw.mp4"
    metadata_path = run_dir / "metadata.json"
    if not video_raw.exists() or not metadata_path.exists():
        print(f"error: missing video_raw.mp4 or metadata.json in {run_dir}", file=sys.stderr)
        return 2

    metadata = json.loads(metadata_path.read_text())
    scenes = metadata.get("creative_brief", {}).get("scenes", [])
    if not scenes:
        print("error: no scenes in metadata.json", file=sys.stderr)
        return 2

    out_path = run_dir / args.out_filename
    print(f"Remixing {video_raw.name} with provider={args.tts_provider}, voice={args.voice}")
    print(f"  -> {out_path}")

    music_path = Path(args.music_path).resolve() if args.music_path else None
    result = _merge_creative_video(
        video_raw,
        scenes,
        out_path,
        music_path=music_path,
        tts_provider=args.tts_provider,
        fallback_tts_provider=args.fallback_tts_provider,
        voice=args.voice,
        generated_music=not args.no_music,
    )
    print(f"Done. actual_provider={result.get('actual_tts_provider')}, output={result.get('output')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
