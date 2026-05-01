# Repo-to-Shorts Agent

Turn a GitHub repo, diff, or build log into a launch-ready technical demo video.

Built for the Nous Research Hermes Agent Creative Hackathon.

## Concept

Most technical projects die in the gap between "it works" and "people understand why it matters."

Repo-to-Shorts Agent is a Hermes-powered creative workflow that ingests a repository and produces:

- a narrative arc
- a storyboard
- an architecture diagram
- captioned visual frames
- narration script
- X-ready launch copy
- a rendered short demo video

## Hackathon angle

The demo shows Hermes acting as a creative production agent, not a chatbot:

1. Reads a repo.
2. Extracts the story.
3. Plans the video.
4. Creates the visual assets.
5. Uses Kimi as a critic/script editor pass.
6. Renders the final launch artifact.

## MVP pipeline

```text
repo/readme/diff
  -> repo brief
  -> story arc
  -> storyboard
  -> visual assets
  -> narration
  -> render plan
  -> short video + X post
```

## Current status

Groundwork scaffold. The first goal is one polished end-to-end path, not a generic platform.

## Deadline

Submission due EOD Sunday, May 3, 2026.
