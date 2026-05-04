#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TARGET="${1:-.}"
OUT_DIR="${OUT_DIR:-runs}"
AUDIENCE="${AUDIENCE:-Nous Research Hermes Agent Creative Hackathon judges}"
KIMI_MODEL="${KIMI_MODEL:-moonshotai/kimi-k2.6}"
TTS_PROVIDER="${TTS_PROVIDER:-xai}"
FALLBACK_TTS_PROVIDER="${FALLBACK_TTS_PROVIDER:-openai}"
REQUIRE_LIVE_KIMI="${REQUIRE_LIVE_KIMI:-1}"

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  . ".env"
  set +a
fi

if [[ ! -x ".venv/bin/repo-shorts" ]]; then
  echo "Missing .venv/bin/repo-shorts. Run: .venv/bin/python -m pip install -e '.[dev,render]'" >&2
  exit 1
fi

before_file="$(mktemp)"
after_file="$(mktemp)"
trap 'rm -f "$before_file" "$after_file"' EXIT

find "$OUT_DIR" -mindepth 1 -maxdepth 1 -type d -print 2>/dev/null | sort > "$before_file" || true

.venv/bin/repo-shorts creative "$TARGET" \
  --audience "$AUDIENCE" \
  --kimi-model "$KIMI_MODEL" \
  --tts-provider "$TTS_PROVIDER" \
  --fallback-tts-provider "$FALLBACK_TTS_PROVIDER" \
  --out "$OUT_DIR" \
  --final

find "$OUT_DIR" -mindepth 1 -maxdepth 1 -type d -print 2>/dev/null | sort > "$after_file" || true
run_dir="$(comm -13 "$before_file" "$after_file" | tail -n 1)"

if [[ -z "$run_dir" ]]; then
  run_dir="$(find "$OUT_DIR" -mindepth 1 -maxdepth 1 -type d -print 2>/dev/null | sort | tail -n 1)"
fi

if [[ -z "$run_dir" ]]; then
  echo "No run directory found under $OUT_DIR" >&2
  exit 1
fi

echo
echo "Run directory: $run_dir"
echo "MP4: $run_dir/demo.mp4"
echo "Metadata: $run_dir/metadata.json"
echo "Submission pack: $run_dir/submission_pack.md"

if command -v jq >/dev/null 2>&1 && [[ -f "$run_dir/metadata.json" ]]; then
  echo
  jq '{kimi: .kimi, tts: .tts, validation: .render.validation}' "$run_dir/metadata.json"

  kimi_mode="$(jq -r '.kimi.mode // ""' "$run_dir/metadata.json")"
  if [[ "$REQUIRE_LIVE_KIMI" == "1" && "$kimi_mode" != "live-api" ]]; then
    echo
    echo "This runner requires live Kimi, but metadata.json recorded kimi.mode=$kimi_mode." >&2
    echo "Run preserved for debugging: $run_dir" >&2
    exit 2
  fi
elif [[ "$REQUIRE_LIVE_KIMI" == "1" ]]; then
  echo "This runner requires live Kimi validation, but jq or metadata.json is unavailable." >&2
  echo "Run preserved for debugging: $run_dir" >&2
  exit 2
fi

if [[ "${OPEN_VIDEO:-1}" == "1" && -f "$run_dir/demo.mp4" ]]; then
  open "$run_dir/demo.mp4" >/dev/null 2>&1 || true
fi
