# CLI Final-Cut Pass Design

## Status

Approved direction: final-cut CLI pass.

This spec covers the next shippable increment for the hackathon MVP. The website is intentionally out of scope until the CLI can produce an artifact worth showing.

## Context

Repo-to-Shorts currently has a working creative pipeline:

```text
repo-shorts creative <target>
  -> ingest repo
  -> build repo analysis
  -> ask Kimi for a creative brief
  -> render vertical MP4 frames with Pillow/ffmpeg
  -> generate narration/audio
  -> write metadata and demo.mp4
```

The pipeline runs end-to-end, but the output is not yet submission-grade. The current failure mode is not missing machinery; it is weak final-mile craft: generic scene direction, uneven proof, brittle audio, basic captions, and limited validation.

The hackathon priority is to produce one credible artifact quickly:

- a 45-60 second 9:16 MP4
- live Kimi proof in `metadata.json`
- a clean narration track
- captions that read well on mobile
- visible repo evidence without leaking secrets
- copy and instructions a user can use for X and Discord

## Goal

Make `repo-shorts creative` the reliable golden path for the submission video package.

The target final command is:

```bash
repo-shorts creative . \
  --audience "Nous Research Hermes Agent Creative Hackathon judges" \
  --kimi-model moonshotai/kimi-k2.6 \
  --tts-provider xai \
  --fallback-tts-provider openai \
  --out runs \
  --final
```

This command should create a timestamped run directory containing:

- `demo.mp4`
- `metadata.json`
- `captions.srt`
- `submission_pack.md`
- existing useful creative artifacts where already available

## Non-Goals

- Build or polish the website.
- Add Suno, ElevenLabs, or another paid music API.
- Add external posting or Discord/X publishing.
- Fake Kimi usage when the API call fails.
- Rewrite the renderer around a new animation framework.
- Turn the project into a full video editor.

## User-Facing CLI Design

### Command

Keep `repo-shorts creative` as the primary command. Add final-mode and provider controls:

```text
repo-shorts creative TARGET
  --audience TEXT
  --out PATH
  --kimi-model TEXT
  --music PATH
  --preview / --no-preview
  --skip-audio
  --final
  --tts-provider xai|openai|edge|none
  --fallback-tts-provider xai|openai|edge|none
  --voice TEXT
  --no-generated-music
```

### Behavior

`--final` is the submission-grade preset:

- disables preview slicing
- requires 45-60 seconds total duration
- requires at least 5 scenes
- requires audio unless `--tts-provider none` is explicit
- runs ffprobe validation after render
- writes `submission_pack.md`
- fails clearly if the output is not postable

`--preview` remains the fast smoke path:

- may use shorter scene durations
- may skip audio
- does not enforce final duration
- still writes honest metadata

Provider defaults:

- final mode default TTS provider chain: `xai` -> `openai` -> `edge`
- if `--fallback-tts-provider` is provided, use only the requested fallback after the primary provider
- if `--tts-provider edge` is provided, use the existing Edge path without xAI/OpenAI
- explicit no-audio path: `--tts-provider none`

## Component Design

### `cli.py`

Owns user-facing flags and maps them into pipeline options.

Responsibilities:

- expose the new provider/final options
- keep current command names stable
- print the run directory, MP4 path, and proof file path
- avoid printing API keys or environment values

### `hermes_skill.py`

Remains the orchestration layer for creative runs.

New or tightened responsibilities:

- accept a `final` boolean and TTS/music options
- choose preview vs final scene handling
- write expanded metadata
- call media validation before returning success in final mode
- call submission pack generation

The public function should remain callable from the future web UI. The web UI can pass the same options later instead of forking logic.

### `creative_director.py`

Keeps Kimi as the creative director.

Prompt changes:

- ask for concrete repo evidence, not generic marketing
- require a hook, 5 scenes, scene durations, visual evidence, narration, and CTA
- require the story to mention Kimi/Hermes only where it helps the submission
- forbid secret-like filenames and environment files in visual evidence
- keep total duration in the 45-60 second range for final mode

Fallback behavior:

- no key remains deterministic fallback
- API error remains honest fallback
- live success records `mode=live-api`, provider, and model

### `tts.py` or `compositor.py`

Add provider-based TTS behind a small interface.

Recommended shape:

```text
generate_tts(text, output_path, provider, voice=None, fallback_provider=None)
```

Provider behavior:

- `xai`: direct xAI TTS API using `XAI_API_KEY`
- `openai`: OpenAI TTS using `OPENAI_API_KEY`
- `edge`: existing `edge-tts` path
- `none`: skip narration, only valid when explicitly requested

Each provider should return a local WAV suitable for the existing ffmpeg flow.

Metadata should record:

- selected provider
- actual provider used
- voice
- fallback reason if fallback is used
- whether narration was skipped

Secrets must stay in environment variables only.

### `manim_render.py`

Do a focused polish pass without changing the renderer architecture.

Required changes:

- filter `.env`, `.env.*`, private keys, token-looking names, and generated run outputs from visual file evidence
- prefer real product evidence: `src/`, `tests/`, `docs/`, `README`, `pyproject.toml`
- improve typography hierarchy and line wrapping for mobile
- keep captions and proof labels inside safe 9:16 bounds
- render final mode at 30fps

The output can still be Pillow + ffmpeg. The goal is cleaner taste and reliability, not a new engine.

### `submissions.py`

Add a small final-mile package writer.

Input:

- target
- run directory
- metadata
- creative brief
- render validation result

Output:

- `submission_pack.md`

Contents:

- exact command used, with secrets omitted
- Kimi proof checklist
- MP4 validation summary
- X post draft
- Discord submission draft
- recording beats
- known limitations phrased honestly

### `media_validation.py`

Add a small ffprobe wrapper.

Final mode should validate:

- `demo.mp4` exists and is non-empty
- video stream exists
- audio stream exists unless audio was explicitly disabled
- duration is 45-60 seconds, with a small tolerance such as 43-62 seconds
- resolution is 1080x1920
- audio duration differs from video duration by no more than 1.5 seconds

Validation result is written to `metadata.json`.

In final mode, validation failures should make the CLI exit non-zero with a useful message. In preview mode, validation can be best-effort metadata.

## Data Flow

```text
CLI flags
  -> run_creative_pipeline(options)
  -> ingest_target(target)
  -> _build_repo_analysis(snapshot)
  -> direct(repo_analysis, final=True, model=...)
  -> generate_manim_script(...)
  -> render_scene(...)
  -> generate_tts(... provider/fallback ...)
  -> generate_ambient_music(...) or supplied music path
  -> mix_audio(...)
  -> burn captions
  -> write captions.srt
  -> validate_media(...)
  -> write metadata.json
  -> write submission_pack.md
```

## Error Handling

Kimi errors:

- never fake live usage
- write fallback mode and reason
- final mode may still succeed if fallback is acceptable, but the metadata must be honest

TTS errors:

- try configured fallback provider if available
- record fallback reason
- fail final mode if all configured audio providers fail
- allow explicit `--tts-provider none` for silent videos

Render errors:

- fail fast with the underlying ffmpeg/Pillow error
- do not leave metadata claiming success

Validation errors:

- fail final mode
- write validation details when possible
- preview mode can warn instead of fail

## Testing Strategy

Add focused tests without live network calls.

Unit tests:

- CLI exposes new options.
- Final-mode options pass into `run_creative_pipeline`.
- secret-like files are filtered from repo analysis/render descriptors.
- xAI provider builds the correct request shape with mocked HTTP.
- OpenAI provider builds the correct request shape with mocked client or HTTP.
- provider fallback is recorded when primary fails.
- `--tts-provider none` skips audio intentionally.
- media validation parses mocked ffprobe output.
- final mode fails on missing audio or bad duration.
- submission pack includes command, Kimi proof, and copy.

Integration tests:

- deterministic preview run still works without keys.
- final run can be exercised with mocked Kimi/TTS/ffprobe and no network.

Manual smoke after implementation:

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/repo-shorts creative . \
  --audience "Nous Research Hermes Agent Creative Hackathon judges" \
  --out runs \
  --final
```

Live smoke when keys are present:

```bash
OPENROUTER_API_KEY="$OPENROUTER_API_KEY" \
XAI_API_KEY="$XAI_API_KEY" \
OPENAI_API_KEY="$OPENAI_API_KEY" \
.venv/bin/repo-shorts creative . \
  --audience "Nous Research Hermes Agent Creative Hackathon judges" \
  --kimi-model moonshotai/kimi-k2.6 \
  --tts-provider xai \
  --fallback-tts-provider openai \
  --out runs \
  --final
```

## Acceptance Criteria

- `repo-shorts creative --help` documents final mode and provider options.
- `repo-shorts creative . --final` creates a timestamped run directory.
- Final mode writes `demo.mp4`, `metadata.json`, `captions.srt`, and `submission_pack.md`.
- `metadata.json` records Kimi mode, model, provider, TTS provider, render settings, and media validation.
- If Kimi succeeds live, metadata shows `mode=live-api`, `provider=openrouter`, and `model=moonshotai/kimi-k2.6`.
- If Kimi falls back, metadata says so plainly.
- Final mode does not include `.env` or secret-like paths in rendered evidence.
- Final mode fails if MP4 duration, resolution, or audio validation is bad.
- Tests pass and Ruff is clean.

## Implementation Order

1. Add tests for final CLI options, media validation, submission pack, secret filtering, and TTS provider selection.
2. Add option plumbing from `cli.py` into `hermes_skill.py`.
3. Add TTS provider abstraction for xAI/OpenAI/Edge/none.
4. Tighten Kimi final-mode prompt and fallback metadata.
5. Add media validation.
6. Add `submission_pack.md`.
7. Apply focused render polish and file evidence filtering.
8. Run deterministic and live smoke tests.

This order protects the working path while improving the parts that matter most for the submission.
