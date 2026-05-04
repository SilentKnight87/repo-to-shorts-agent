---
name: repo-shorts-creative
description: Generate a launch-ready 9:16 short-form video for any GitHub repo or local repository. Hermes orchestrates the Repo-to-Shorts creative pipeline — Kimi K2.6 directs the storyboard, the renderer produces the MP4, and Hermes returns the run directory with submission-ready artifacts.
version: 0.1.0
platforms: [macos, linux]
metadata:
  hermes:
    tags: [video, repo-shorts, kimi, creative, hackathon]
    category: video
    requires_toolsets: [terminal]
    requires_tools: [run_terminal_cmd]
---

# Repo-to-Shorts Creative

## When to Use

Use this skill when the user asks to:
- Turn a GitHub repo into a short-form launch video
- Generate a hackathon demo / X video / Discord submission for a code project
- Produce a 45-60 second 9:16 MP4 with Kimi-directed storyboard, narration, captions, and submission copy

## Inputs

- `target` — GitHub URL (e.g. `https://github.com/owner/repo`) or a local repo path. Required.
- `audience` — short string describing who the video is for. Optional. Defaults to `"Nous Research Hermes Agent Creative Hackathon judges"`.

If the user didn't supply a target, ask once: "Which repo should I turn into a short?"

## Procedure

1. Confirm `target` is set. If not, ask the user.
2. Invoke the Repo-to-Shorts CLI in final mode. If the CLI is installed in a local checkout, run this from that repo root and use `.venv/bin/repo-shorts` instead of `repo-shorts`:

   ```bash
   repo-shorts creative "<target>" \
     --audience "<audience>" \
     --kimi-model moonshotai/kimi-k2.6 \
     --tts-provider xai \
     --fallback-tts-provider openai \
     --out runs \
     --final
   ```

3. The CLI prints the run directory (`runs/<timestamp>-<repo>/`) and the path to `demo.mp4`. Capture both from stdout.
4. Read `runs/<timestamp>-<repo>/metadata.json` and confirm:
   - `kimi.mode == "live-api"`
   - `kimi.provider == "openrouter"`
   - `kimi.model` starts with `moonshotai/kimi-k2.6`
   - `render.validation.ok == true`
5. Read `runs/<timestamp>-<repo>/submission_pack.md` and surface:
   - The exact command used
   - The Kimi proof checklist
   - The X/Discord post drafts

## Output

Tell the user, in this order:
1. `demo.mp4` absolute path
2. Run directory absolute path
3. Kimi mode/provider/model from metadata
4. Whether media validation passed
5. The X tweet draft and the Discord post draft from `submission_pack.md`

## Verification

Before claiming success:
- Confirm `demo.mp4` exists on disk and is non-empty.
- Confirm `metadata.json` shows `kimi.mode = live-api`. If it shows `deterministic-fallback`, surface the `fallback_reason` to the user — do NOT claim live Kimi was used.
- Confirm `render.validation.ok` is true. If false, surface the validation errors.

## Pitfalls

- If using a local editable checkout, run the CLI from the repo root, not from `~/.hermes`.
- The user must provide API keys via environment variables such as `OPENROUTER_API_KEY`, `XAI_API_KEY`, and `OPENAI_API_KEY`. Do not echo these values back to the user.
- Final mode requires 5+ scenes and 45-60s duration; the CLI will exit non-zero with a clear message if Kimi returns an out-of-bound brief.
- Do not fabricate Kimi proof. If the live call failed and the pipeline used deterministic fallback, say so plainly.
