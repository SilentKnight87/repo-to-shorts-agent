# Submission copy

## Discord-ready version

Built **Repo-to-Shorts Agent** for the Nous Research Hermes Agent Creative Hackathon.

It turns a GitHub repo or local repo into a launch-ready technical short-video package:

- repo brief
- story arc + storyboard
- architecture SVG
- narration script
- captions SRT
- X-ready launch copy
- Discord submission copy
- Kimi critic/script-editor pass
- browser-presentable `demo.html` for screen recording

Run it with:

```bash
repo-shorts analyze . \
  --audience "hackathon judges" \
  --out runs \
  --kimi-model moonshotai/kimi-k2.6
```

With `OPENROUTER_API_KEY` set, the Kimi critic stage calls OpenRouter's `moonshotai/kimi-k2.6` model and records `live-api` proof in `metadata.json`. Without credentials, it fails safely into an honest deterministic fallback.

## Short X-ready version

Built Repo-to-Shorts Agent for the Hermes Creative Hackathon.

Paste a repo → get a repo brief, storyboard, architecture diagram, narration, captions, launch copy, Kimi critic notes, and a browser demo artifact ready to screen-record.

One polished golden path for turning working code into a clear launch story.

## Longer project description

Most hackathon repos die in the gap between “it works” and “people understand why it matters.” Repo-to-Shorts Agent closes that gap. It ingests a local repo or GitHub URL, extracts concrete repo facts, creates a deterministic technical short-video narrative, runs a Kimi critic/script-editor stage, and writes all launch artifacts into a timestamped run folder.

The demo artifact is intentionally browser-first: open `demo.html`, record the polished cards, use `narration.md` and `captions.srt`, then post with the generated X and Discord copy.
