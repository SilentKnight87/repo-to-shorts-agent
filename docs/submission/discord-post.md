# Discord Submission Post

**Repo-to-Shorts Agent** turns a GitHub repo or local codebase into a launch-ready short-video package for hackathon demos and product launches.

Demo video: <X POST URL HERE>

How it works:

- Hermes Agent skill (`.hermes/skill/SKILL.md`) — judges can run `hermes` and invoke `/repo-shorts-creative <target>` directly. Hermes orchestrates ingest, rendering, and artifact packaging.
- Kimi K2.6 directs the storyboard via OpenRouter — `metadata.json` records `kimi.mode: live-api`, `kimi.provider: openrouter`, and `kimi.model: moonshotai/kimi-k2.6` as proof.
- Honest proof — Hermes validates the Kimi field before declaring success. If the live call fails, the deterministic fallback is recorded transparently in the metadata.

Try it in Hermes:

```
hermes
> /repo-shorts-creative https://github.com/<owner>/<repo>
```

Or directly via CLI:

```
repo-shorts creative <target> --kimi-model moonshotai/kimi-k2.6 --final
```

Output includes MP4, captions (SRT), metadata proof, and submission copy — everything a judge needs to verify the run.

Submitted for the Hermes Agent Creative Hackathon. Built with Hermes Agent and Kimi K2.6.

<GITHUB URL>
