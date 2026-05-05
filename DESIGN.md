---
version: alpha
name: Repo-to-Shorts Cinematic Console
description: A premium, cinematic, developer-native motion identity for turning repos into short-form product trailers.
colors:
  primary: "#F6F2E8"
  secondary: "#9BA3AF"
  tertiary: "#6EE7F9"
  neutral: "#080A0F"
  surface: "#10131C"
  surfaceRaised: "#171B26"
  accentWarm: "#F97316"
  success: "#22C55E"
  danger: "#EF4444"
typography:
  display:
    fontFamily: "Space Grotesk"
    fontSize: "3.1rem"
    fontWeight: 700
    lineHeight: 0.95
    letterSpacing: "0"
  headline:
    fontFamily: "Space Grotesk"
    fontSize: "1.85rem"
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: "0"
  body:
    fontFamily: "Inter"
    fontSize: "1rem"
    fontWeight: 450
    lineHeight: 1.45
    letterSpacing: "0"
  mono:
    fontFamily: "JetBrains Mono"
    fontSize: "0.82rem"
    fontWeight: 500
    lineHeight: 1.35
    letterSpacing: "0"
  caption:
    fontFamily: "Inter"
    fontSize: "0.72rem"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "0.08em"
rounded:
  sm: 4px
  md: 8px
  lg: 8px
spacing:
  xs: 6px
  sm: 10px
  md: 18px
  lg: 32px
  xl: 54px
components:
  canvas:
    backgroundColor: "{colors.neutral}"
    textColor: "{colors.primary}"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary}"
    rounded: "{rounded.md}"
    padding: 18px
  button-primary:
    backgroundColor: "{colors.tertiary}"
    textColor: "{colors.neutral}"
    rounded: "{rounded.sm}"
    padding: 12px
  code-chip:
    backgroundColor: "{colors.surfaceRaised}"
    textColor: "{colors.tertiary}"
    rounded: "{rounded.sm}"
    padding: 8px
  metadata-label:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.secondary}"
    rounded: "{rounded.sm}"
    padding: 6px
  transformation-spark:
    backgroundColor: "{colors.accentWarm}"
    textColor: "{colors.neutral}"
    rounded: "{rounded.sm}"
    padding: 8px
  success-proof:
    backgroundColor: "{colors.success}"
    textColor: "{colors.neutral}"
    rounded: "{rounded.sm}"
    padding: 8px
  danger-warning:
    backgroundColor: "{colors.danger}"
    textColor: "{colors.neutral}"
    rounded: "{rounded.sm}"
    padding: 8px
---

## Overview

Repo-to-Shorts should feel like a cinematic engineering trailer, not a generic AI SaaS demo. The emotional target is: **terminal-native, premium, fast, and credible**. It should feel like a polished launch asset for a serious agent project, not a template with a repo URL pasted into it.

The core design thesis is: agents do not magically have taste. They need references, constraints, and review loops. This file is the persistent taste layer for the product.

## Colors

The palette is dark, high-contrast, and restrained. Use cyan as the primary technical accent, warm orange only for urgency or transformation, and never scatter random neon colors across scenes.

- **Neutral (#080A0F):** cinematic black canvas. Most frames should start from here.
- **Primary (#F6F2E8):** warm editorial white for headlines.
- **Secondary (#9BA3AF):** metadata, labels, muted supporting copy.
- **Tertiary (#6EE7F9):** agent intelligence, scanning, graph edges, highlights.
- **Surface (#10131C):** panels, code windows, repo cards.
- **Surface Raised (#171B26):** elevated UI objects and active states.
- **Accent Warm (#F97316):** reveal moments, warnings, transformation sparks. Use sparingly.

## Typography

Typography carries most of the brand. Use tight, confident display type for hooks and conclusions. Use mono only where it earns its place: repo paths, file names, metrics, CLI commands, commit IDs.

Rules:
- Headlines should be short enough to read in under 1.5 seconds.
- Avoid full sentences as giant captions unless the scene is intentionally quote-like.
- Prefer 3 to 7 words per major text beat.
- Never stack more than two competing text hierarchies in one frame.
- Kinetic text must follow meaning: slam for a hard claim, glide for flow, flicker for machine/process, hold for the point.

## Layout

Design for 9:16 first. The safe area matters more than clever composition.

- Keep primary captions inside a centered vertical band, roughly 10% to 86% screen height.
- Preserve breathing room around the top and bottom for platform UI overlays.
- Use one focal object per scene: repo card, graph, metric, timeline, generated short, final CTA.
- Use diagonal motion and parallax for cinematic depth, but not constant camera drift.
- Every frame should have a clear answer to: what should the viewer look at first?

## Elevation & Depth

Depth should come from contrast, blur, parallax, and motion timing, not heavy shadows. Panels can glow subtly when active. Avoid cheap cyberpunk bloom. This is “premium console,” not nightclub dashboard.

## Shapes

Use sharp geometry softened by small radii. Cards and code panels use 8px corners at most. CTA buttons and chips use tighter 4px corners. Avoid pill soup.

## Components

- **Repo card:** shows repo name, language mix, stars/files/commits, and one memorable insight.
- **Signal graph:** shows agent analysis moving from files to plan to scenes to video.
- **Scene strip:** a horizontal/vertical timeline of generated scenes.
- **CLI proof chip:** displays actual command or artifact path when credibility matters.
- **Before/after moment:** show raw repo input becoming a trailer output. This is the magic beat.

## Do's and Don'ts

Do:
- Start with the problem or transformation in the first second.
- Show real product/UI artifacts, not abstract shapes forever.
- Use references before generating final visual direction.
- Favor one strong idea per scene.
- Make captions readable without audio.
- Use audio/music to support pacing, not to hide weak visuals.

Don't:
- Use generic purple-blue gradients.
- Use default Inter everywhere with default spacing.
- Fill the screen with three rounded cards and call it design.
- Add motion that does not guide attention.
- Make the voiceover explain what the viewer can already see.
- Ship “functional” as if it means good.
