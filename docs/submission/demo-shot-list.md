# Demo Shot List — 60s, 9:16

## Pre-record setup

- Terminal: zsh in `/Users/operator/Documents/Code/repo-to-shorts-agent`, font size XL, dark background.
- Browser: `http://127.0.0.1:8765` open, dark theme matched to terminal, VHS broadcast aesthetic active.
- Recording: 1080x1920 vertical, 30fps, screen capture both panes side-by-side. Terminal on left (60% width), browser on right (40% width).
- Audio: capture system audio only (no mic). The generated MP4 provides its own TTS + music audio track.

## Beats

| Time | Terminal track | Browser track | On-screen text |
|------|----------------|---------------|----------------|
| 0:00–0:05 | Black. No content. | Black. No content. | "This video was made by the repo it's about." White on black, centered, fades out at 0:03. |
| 0:05–0:10 | `hermes` starts. User prompt visible: `hermes` launches, the REPL opens. User types `/repo-shorts-creative https://github.com/SilentKnight87/repo-to-shorts-agent` and presses enter. | VHS home page at `127.0.0.1:8765`. Visible: "REPO TO SHORTS" glitch-headline, the lede paragraph, the SKILL badge ("repo-shorts-creative" chip), and the broadcast control deck with the URL input field and REC button. | None. |
| 0:10–0:15 | Hermes begins processing. Terminal shows the agent's initial thinking output: reading the target repo, confirming the skill is loaded, beginning the creative pipeline. | Browser channel rows enter STBY state. The channel labels ("ingest", "analyze", "kimi_brief", "render_frames", "compose", "finalize") are visible with low amber fills and "STBY" status text. | None. |
| 0:15–0:20 | Terminal shows agent loop output: "Reading repo-to-shorts-agent", "Building repo analysis", key files being enumerated. Agent is visibly working through the ingest and analyze stages. | Channel rows transition: "ingest" goes LIVE (orange fill, LIVE status blinking). "analyze" goes LIVE shortly after. Progress bars fill on the channel rows. | None. |
| 0:20–0:25 | Terminal shows agent output: "Calling creative director", Kimi API request sent. The agent continues the pipeline, showing stage transitions. | Channel rows continue lighting up: "kimi_brief" goes LIVE (orange). "render_frames" enters LIVE state as ingest and analyze complete (DONE, green). | None. |
| 0:25–0:30 | Terminal transitions to post-pipeline inspection. Agent is reading the output directory, listing generated artifacts. The agent opens and reads `metadata.json`. | Channel rows progress: "render_frames" completes (DONE, green). "compose" goes LIVE. "finalize" transitions to DONE. All channels show green fills or final states. | None. |
| 0:30–0:35 | Terminal highlights metadata fields from the agent's output: `kimi.mode: live-api`, `kimi.provider: openrouter`. The agent is explicitly surfacing Kimi proof to the user. | Browser shows the success/result page: 9:16 video preview viewport with the generated MP4 loaded, artifact tiles (demo.mp4, metadata.json, captions.srt, submission_pack.md) as tape-label chips, and a cue sheet with scene breakdown. | None. |
| 0:35–0:40 | Terminal highlights `kimi.model: moonshotai/kimi-k2.6` and `render.validation.ok: true`. Agent reports: "Kimi proof confirmed. All checks passed." | Browser shows the `kimi · live-api` status pill next to the video preview. Final artifact listing visible. The scope strip at the bottom shows diagnostic readout: frame count, resolution, duration. | None. |
| 0:40–0:45 | Agent reports success summary in terminal: run directory path, MP4 path, duration, resolution. The terminal remains visible but is no longer the focus. | MP4 begins playing in the browser video viewport. The ColdOpen beat: "This repo made the video you're watching." overlay on the generated frames. The VHS UI chrome (scanlines, vignette) frames the video. | None. |
| 0:45–0:50 | Terminal sits static with the final success report visible. The command prompt returns. | MP4 plays the PipelineMap and mechanism sequences within the browser viewport. Generated captions appear. The `kimi · live-api` status pill remains visible in the VHS UI chrome. | None. |
| 0:50–0:55 | Terminal fades slightly or remains static. | MP4 plays the ArtifactStack and proof sequence. Generated captions: "...generated artifacts, metadata.json, submission copy." The scope strip updates. Terminal shows empty prompt, work complete. | None. |
| 0:55–1:00 | Black screen. | Black screen. | "github.com/SilentKnight87/repo-to-shorts-agent" on top line. "@NousResearch @Kimi_Moonshot" on bottom line. White text on black, centered. Held to end. |

## Recording notes

- Record the full 60 seconds in one take. No cuts, no post-production editing.
- The first 3 seconds are the hook title card. After that, both tracks are live and moving.
- Do not include any `.env` contents, API keys, or generated `runs/` paths in the visible terminal scrollback. Clear scrollback and history before recording.
- Ensure the VHS UI has the SKILL badge (`repo-shorts-creative` chip) visible on the home page at the start.
- The browser viewport should show the generated MP4 playing inline with scanlines and CRT vignette effects active.
- If the generated MP4 audio plays during the recording, let it be the only audio in the capture. No voiceover.
- Verify before recording: `metadata.json` shows `kimi.mode: live-api`, the MP4 is at least 8 MB and plays, and the VHS UI is running at `http://127.0.0.1:8765`.
