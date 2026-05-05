# Taste-Directed Remotion Renderer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the final MP4 look meaningfully better by having Remotion execute the taste/creative brief instead of rendering every run through the same VHS template.

**Architecture:** Keep Python as the orchestrator and Remotion as the final renderer. Expand the Remotion manifest so Kimi's `visual_world`, `motion_principles`, `shot_list`, `continuity_rules`, `quality_bar`, and scene type decisions reach the renderer, then give each scene type a distinct composition and add a visual repetition QA gate that rejects "same video with different words."

**Tech Stack:** Python 3.13, pytest, Remotion 4, React/TypeScript, Node/NPM, ffmpeg/ffprobe, existing `repo-shorts creative --final` workflow.

---

## Why This Plan Exists

The current taste work improved workflow correctness: Kimi runs live, evidence is checked, fake claims are blocked, QA artifacts are written, and the UI final path works.

It did not sufficiently improve the video because the Remotion renderer still applies one dominant VHS visual system to every scene. Kimi can write a better brief, but the renderer flattens `ColdOpen`, `PainPoint`, `PipelineMap`, `LiveProof`, `ArtifactStack`, and `CTAEndCard` into similar compositions.

Tomorrow's implementation should treat this as a renderer/product-quality problem, not a prompt-only problem.

## Files

- Modify: `src/repo_to_shorts/remotion_render.py`
- Modify: `src/repo_to_shorts/hermes_skill.py`
- Modify: `src/repo_to_shorts/taste_qa.py`
- Modify: `remotion/src/RepoShortsVideo.tsx`
- Modify: `remotion/src/styles.ts`
- Create: `remotion/src/sceneTypes.tsx`
- Create: `remotion/src/visualLanguage.ts`
- Create: `src/repo_to_shorts/visual_qa.py`
- Test: `tests/test_remotion_render.py`
- Test: `tests/test_taste_qa.py`
- Test: `tests/test_visual_qa.py`
- Optional docs update after implementation: `README.md`

---

## Task 1: Pass Taste Fields Into Remotion

**Files:**
- Modify: `src/repo_to_shorts/remotion_render.py`
- Modify: `src/repo_to_shorts/hermes_skill.py`
- Test: `tests/test_remotion_render.py`

- [ ] **Step 1: Write failing manifest test**

Add this test to `tests/test_remotion_render.py`:

```python
def test_build_remotion_input_carries_taste_contract():
    data = build_remotion_input(
        repo_name="repo-to-shorts-agent",
        description="Turns repos into short-video packages.",
        key_files=["README.md", "src/repo_to_shorts/cli.py"],
        scenes=[
            {
                "type": "ColdOpen",
                "duration_seconds": 5,
                "headline": "THIS REPO MADE THIS VIDEO",
                "evidence": ["README.md"],
                "visual_role": "kinetic_title",
                "layout": "full_bleed_type",
            }
        ],
        proof={"kimi_mode": "live-api"},
        creative_direction={
            "visual_world": "retro VHS broadcast deck with editorial proof inserts",
            "motion_principles": ["motion reveals hierarchy", "evidence is a visual object"],
            "shot_list": ["full-screen kinetic title", "metadata macro insert"],
            "continuity_rules": ["one REC motif, no repeated bottom captions"],
            "quality_bar": {"avoid": ["same card layout twice"]},
        },
    )

    assert data["creative_direction"]["visual_world"].startswith("retro VHS")
    assert data["creative_direction"]["motion_principles"] == [
        "motion reveals hierarchy",
        "evidence is a visual object",
    ]
    assert data["scenes"][0]["visual_role"] == "kinetic_title"
    assert data["scenes"][0]["layout"] == "full_bleed_type"
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
.venv/bin/python -m pytest tests/test_remotion_render.py::test_build_remotion_input_carries_taste_contract -q
```

Expected: FAIL because `build_remotion_input()` does not accept or emit `creative_direction`.

- [ ] **Step 3: Extend Python manifest builder**

Change `src/repo_to_shorts/remotion_render.py`:

```python
def build_remotion_input(
    *,
    repo_name: str,
    description: str,
    key_files: list[str],
    scenes: list[dict[str, Any]],
    proof: dict[str, Any],
    artifacts: list[str] | None = None,
    creative_direction: dict[str, Any] | None = None,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    duration_seconds: int = 45,
) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "repo": {
            "name": repo_name,
            "description": description,
            "key_files": key_files[:8],
        },
        "video": {
            "width": width,
            "height": height,
            "fps": fps,
            "duration_seconds": duration_seconds,
        },
        "creative_direction": _normalize_creative_direction(creative_direction),
        "proof": proof,
        "scenes": [_normalize_scene(scene, index) for index, scene in enumerate(scenes)],
        "artifacts": list(DEFAULT_ARTIFACTS) if artifacts is None else list(artifacts),
    }
```

Add:

```python
def _normalize_creative_direction(value: dict[str, Any] | None) -> dict[str, Any]:
    value = value or {}
    return {
        "visual_world": str(value.get("visual_world") or "taste-directed technical film"),
        "motion_principles": _string_list(value.get("motion_principles"), limit=8),
        "shot_list": _string_list(value.get("shot_list"), limit=12),
        "continuity_rules": _string_list(value.get("continuity_rules"), limit=8),
        "negative_prompts": _string_list(value.get("negative_prompts"), limit=10),
        "quality_bar": value.get("quality_bar") if isinstance(value.get("quality_bar"), dict) else {},
    }
```

Update `_normalize_scene()` to preserve renderer hints:

```python
def _normalize_scene(scene: dict[str, Any], index: int) -> dict[str, Any]:
    narration = str(scene.get("narration") or "")
    scene_type = str(scene.get("type") or _default_scene_type(index))
    return {
        "type": scene_type,
        "duration_seconds": float(scene.get("duration_seconds", 6)),
        "headline": str(scene.get("headline") or scene.get("hook") or _headline_from_narration(narration)),
        "narration": narration,
        "evidence": _string_list(scene.get("evidence"), limit=5),
        "caption_emphasis": _string_list(scene.get("caption_emphasis"), limit=6),
        "visual_role": str(scene.get("visual_role") or _default_visual_role(scene_type)),
        "layout": str(scene.get("layout") or _default_layout(scene_type)),
    }
```

Add:

```python
def _default_visual_role(scene_type: str) -> str:
    roles = {
        "ColdOpen": "kinetic_title",
        "PainPoint": "problem_counter",
        "RepoEvidence": "repo_evidence_wall",
        "PipelineMap": "animated_pipeline",
        "LiveProof": "metadata_macro",
        "ArtifactStack": "artifact_inventory",
        "DemoPreview": "device_preview",
        "CTAEndCard": "command_endcard",
    }
    return roles.get(scene_type, "editorial_scene")


def _default_layout(scene_type: str) -> str:
    layouts = {
        "ColdOpen": "full_bleed_type",
        "PainPoint": "split_alarm_counter",
        "RepoEvidence": "evidence_wall",
        "PipelineMap": "left_to_right_system_map",
        "LiveProof": "metadata_zoom",
        "ArtifactStack": "stacked_artifacts",
        "DemoPreview": "phone_monitor",
        "CTAEndCard": "command_console",
    }
    return layouts.get(scene_type, "editorial_panel")
```

- [ ] **Step 4: Pass creative fields from pipeline**

In `src/repo_to_shorts/hermes_skill.py`, update the `render_remotion_video()` call:

```python
remotion_result = render_remotion_video(
    run_dir,
    brief.scenes,
    repo_name=repo_analysis["repo_name"],
    description=repo_analysis["description"],
    key_files=repo_analysis["key_files"],
    proof=_build_remotion_proof(kimi_metadata),
    creative_direction={
        "visual_world": brief.visual_world,
        "motion_principles": brief.motion_principles,
        "shot_list": brief.shot_list,
        "continuity_rules": brief.continuity_rules,
        "negative_prompts": brief.negative_prompts,
        "quality_bar": brief.quality_bar,
    },
    config=RenderConfig(output_name=raw_video.name),
)
```

Update `render_remotion_video()` signature to accept and forward `creative_direction`.

- [ ] **Step 5: Run tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_remotion_render.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/repo_to_shorts/remotion_render.py src/repo_to_shorts/hermes_skill.py tests/test_remotion_render.py
git commit -m "feat: pass taste contract to remotion"
```

---

## Task 2: Split Remotion Scene Types Into Real Layouts

**Files:**
- Create: `remotion/src/sceneTypes.tsx`
- Create: `remotion/src/visualLanguage.ts`
- Modify: `remotion/src/RepoShortsVideo.tsx`
- Modify: `remotion/src/styles.ts`

- [ ] **Step 1: Create visual language resolver**

Create `remotion/src/visualLanguage.ts`:

```typescript
import type {CSSProperties} from 'react';
import {colors, type} from './styles';

export type CreativeDirection = {
  visual_world?: string;
  motion_principles?: string[];
  shot_list?: string[];
  continuity_rules?: string[];
  negative_prompts?: string[];
  quality_bar?: Record<string, unknown>;
};

export type VisualLanguage = {
  palette: {
    background: string;
    primary: string;
    secondary: string;
    accent: string;
    danger: string;
    paper: string;
  };
  typography: {
    display: CSSProperties;
    label: CSSProperties;
    mono: CSSProperties;
  };
  motifs: string[];
};

export const resolveVisualLanguage = (direction: CreativeDirection = {}): VisualLanguage => {
  const world = String(direction.visual_world || '').toLowerCase();
  const isBroadcast = world.includes('vhs') || world.includes('broadcast') || world.includes('tape');
  return {
    palette: {
      background: isBroadcast ? colors.carbon : '#07090d',
      primary: colors.paper,
      secondary: colors.paperDim,
      accent: isBroadcast ? colors.amber : colors.cyan,
      danger: colors.red,
      paper: colors.labelCream,
    },
    typography: {
      display: {
        fontFamily: type.display,
        textTransform: 'uppercase',
        letterSpacing: 0,
        lineHeight: 0.86,
      },
      label: {
        fontFamily: type.mono,
        textTransform: 'uppercase',
        letterSpacing: 0,
      },
      mono: {
        fontFamily: type.mono,
        letterSpacing: 0,
      },
    },
    motifs: isBroadcast ? ['rec', 'scanline', 'timecode'] : ['grid', 'cursor', 'proof'],
  };
};
```

- [ ] **Step 2: Create distinct scene components**

Create `remotion/src/sceneTypes.tsx` with one exported component per scene type. Use this shape:

```typescript
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {colors, hairline, monoLabel, safeArea, shadows, type} from './styles';
import type {RepoShortsScene} from './RepoShortsVideo';
import type {VisualLanguage} from './visualLanguage';

type SceneProps = {
  scene: Required<RepoShortsScene>;
  repoName: string;
  proof: Record<string, unknown>;
  artifacts: string[];
  visual: VisualLanguage;
};

const entry = (frame: number) => interpolate(frame, [0, 18], [0, 1], {extrapolateRight: 'clamp'});

export const ColdOpenScene: React.FC<SceneProps> = ({scene, repoName, visual}) => {
  const frame = useCurrentFrame();
  const opacity = entry(frame);
  return (
    <AbsoluteFill style={{...safeArea, justifyContent: 'center'}}>
      <div style={{...visual.typography.label, color: colors.green, fontSize: 30}}>
        REC // {repoName}
      </div>
      <h1 style={{...visual.typography.display, margin: '42px 0 0', fontSize: 142, color: visual.palette.primary, opacity}}>
        {scene.headline}
      </h1>
      <div style={{...hairline, marginTop: 42}} />
    </AbsoluteFill>
  );
};

export const PainPointScene: React.FC<SceneProps> = ({scene}) => {
  const frame = useCurrentFrame();
  const pulse = interpolate(frame % 30, [0, 15, 30], [0.2, 1, 0.2]);
  return (
    <AbsoluteFill style={{...safeArea, justifyContent: 'center'}}>
      <div style={{fontFamily: type.mono, color: colors.red, fontSize: 42}}>TRACKING ERROR</div>
      <div style={{fontFamily: type.display, color: colors.paper, fontSize: 116, lineHeight: 0.9, marginTop: 26}}>
        {scene.headline}
      </div>
      <div style={{height: 18, marginTop: 44, background: `rgba(255, 94, 94, ${pulse})`, boxShadow: shadows.glowAmber}} />
    </AbsoluteFill>
  );
};

export const RepoEvidenceScene: React.FC<SceneProps> = ({scene, repoName}) => (
  <AbsoluteFill style={{...safeArea}}>
    <div style={{...monoLabel}}>SOURCE VERIFIED</div>
    <h2 style={{fontFamily: type.display, fontSize: 86, lineHeight: 0.92, margin: '28px 0 36px'}}>{scene.headline}</h2>
    <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18}}>
      {[repoName, ...scene.evidence].slice(0, 6).map((item, index) => (
        <div key={`${item}-${index}`} style={{padding: 22, border: `1px solid ${colors.line}`, background: colors.panel}}>
          <div style={{fontFamily: type.mono, color: colors.amber, fontSize: 20}}>EVIDENCE {String(index + 1).padStart(2, '0')}</div>
          <div style={{fontFamily: type.mono, color: colors.paper, fontSize: 30, marginTop: 16}}>{item}</div>
        </div>
      ))}
    </div>
  </AbsoluteFill>
);

export const PipelineMapScene: React.FC<SceneProps> = ({scene}) => {
  const steps = ['INGEST', 'KIMI', 'QA', 'REMOTION', 'MP4'];
  return (
    <AbsoluteFill style={{...safeArea, justifyContent: 'center'}}>
      <h2 style={{fontFamily: type.display, fontSize: 92, lineHeight: 0.9, margin: 0}}>{scene.headline}</h2>
      <div style={{display: 'grid', gridTemplateColumns: `repeat(${steps.length}, 1fr)`, gap: 12, marginTop: 56}}>
        {steps.map((step) => (
          <div key={step} style={{height: 180, border: `1px solid ${colors.cyan}`, display: 'grid', placeItems: 'center', fontFamily: type.mono, fontSize: 28}}>
            {step}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

export const LiveProofScene: React.FC<SceneProps> = ({scene, proof}) => (
  <AbsoluteFill style={{...safeArea, justifyContent: 'center'}}>
    <div style={{...monoLabel}}>LIVE MODEL PROOF</div>
    <h2 style={{fontFamily: type.display, fontSize: 92, margin: '28px 0'}}>{scene.headline}</h2>
    <pre style={{fontFamily: type.mono, fontSize: 30, color: colors.green, background: colors.panel, padding: 34, whiteSpace: 'pre-wrap'}}>
      {JSON.stringify(proof, null, 2)}
    </pre>
  </AbsoluteFill>
);

export const ArtifactStackScene: React.FC<SceneProps> = ({scene, artifacts}) => (
  <AbsoluteFill style={{...safeArea}}>
    <h2 style={{fontFamily: type.display, fontSize: 86, lineHeight: 0.9}}>{scene.headline}</h2>
    {[...new Set([...scene.evidence, ...artifacts])].slice(0, 7).map((item, index) => (
      <div key={`${item}-${index}`} style={{marginTop: 16, transform: `translateX(${index * 18}px)`, padding: 20, background: colors.labelCream, color: colors.labelInk, fontFamily: type.mono, fontSize: 30}}>
        {item}
      </div>
    ))}
  </AbsoluteFill>
);

export const CTAEndCardScene: React.FC<SceneProps> = ({scene}) => (
  <AbsoluteFill style={{...safeArea, justifyContent: 'center'}}>
    <div style={{fontFamily: type.mono, color: colors.green, fontSize: 28}}>RUN COMMAND</div>
    <h2 style={{fontFamily: type.display, fontSize: 102, lineHeight: 0.9, margin: '30px 0'}}>{scene.headline}</h2>
    <div style={{fontFamily: type.mono, color: colors.amber, fontSize: 34}}>
      {scene.evidence[0] || 'repo-shorts creative . --final'}
    </div>
  </AbsoluteFill>
);

export const DefaultScene: React.FC<SceneProps> = ({scene}) => (
  <AbsoluteFill style={{...safeArea, justifyContent: 'center'}}>
    <h2 style={{fontFamily: type.display, fontSize: 92, lineHeight: 0.9}}>{scene.headline}</h2>
  </AbsoluteFill>
);
```

- [ ] **Step 3: Wire scene router**

In `remotion/src/RepoShortsVideo.tsx`, import the new components and replace the generic scene body with a router:

```typescript
import {
  ArtifactStackScene,
  CTAEndCardScene,
  ColdOpenScene,
  DefaultScene,
  LiveProofScene,
  PainPointScene,
  PipelineMapScene,
  RepoEvidenceScene,
} from './sceneTypes';
import {resolveVisualLanguage, type CreativeDirection} from './visualLanguage';
```

Extend `RepoShortsManifest`:

```typescript
creative_direction?: CreativeDirection;
```

Extend `NormalizedManifest`:

```typescript
creative_direction: CreativeDirection;
```

Normalize:

```typescript
creative_direction: input.creative_direction ?? {},
```

Replace scene rendering with:

```typescript
const visual = resolveVisualLanguage(manifest.creative_direction);
const common = {
  scene,
  repoName: manifest.repo.name,
  proof: manifest.proof,
  artifacts: manifest.artifacts,
  visual,
};

if (scene.type === 'ColdOpen') return <ColdOpenScene {...common} />;
if (scene.type === 'PainPoint') return <PainPointScene {...common} />;
if (scene.type === 'RepoEvidence') return <RepoEvidenceScene {...common} />;
if (scene.type === 'PipelineMap') return <PipelineMapScene {...common} />;
if (scene.type === 'LiveProof') return <LiveProofScene {...common} />;
if (scene.type === 'ArtifactStack') return <ArtifactStackScene {...common} />;
if (scene.type === 'CTAEndCard') return <CTAEndCardScene {...common} />;
return <DefaultScene {...common} />;
```

- [ ] **Step 4: Run TypeScript/Remotion smoke**

Run:

```bash
npm run render:remotion -- --input runs/20260504-225645-repo-to-shorts-agent/render/remotion_input.json --output /tmp/repo-shorts-taste-renderer-smoke.mp4
```

Expected: command exits 0 and writes `/tmp/repo-shorts-taste-renderer-smoke.mp4`.

- [ ] **Step 5: Commit**

```bash
git add remotion/src/RepoShortsVideo.tsx remotion/src/sceneTypes.tsx remotion/src/visualLanguage.ts remotion/src/styles.ts
git commit -m "feat: add distinct remotion scene layouts"
```

---

## Task 3: Add Rendered-Frame Visual QA

**Files:**
- Create: `src/repo_to_shorts/visual_qa.py`
- Modify: `src/repo_to_shorts/hermes_skill.py`
- Modify: `src/repo_to_shorts/taste_qa.py`
- Test: `tests/test_visual_qa.py`
- Test: `tests/test_taste_qa.py`

- [ ] **Step 1: Write visual QA tests**

Create `tests/test_visual_qa.py`:

```python
from pathlib import Path

from repo_to_shorts.visual_qa import score_scene_variety


def test_score_scene_variety_rejects_repeated_layouts():
    report = score_scene_variety(
        [
            {"type": "ColdOpen", "layout": "editorial_panel"},
            {"type": "PainPoint", "layout": "editorial_panel"},
            {"type": "PipelineMap", "layout": "editorial_panel"},
            {"type": "LiveProof", "layout": "editorial_panel"},
            {"type": "CTAEndCard", "layout": "editorial_panel"},
        ],
        frame_probes=[],
    )

    assert report["overall"] == "fail"
    assert report["allowed_to_publish"] is False
    assert any(issue["defect"] == "visual_repetition" for issue in report["visual_issues"])


def test_score_scene_variety_accepts_distinct_scene_design():
    report = score_scene_variety(
        [
            {"type": "ColdOpen", "layout": "full_bleed_type"},
            {"type": "PainPoint", "layout": "split_alarm_counter"},
            {"type": "PipelineMap", "layout": "left_to_right_system_map"},
            {"type": "LiveProof", "layout": "metadata_zoom"},
            {"type": "ArtifactStack", "layout": "stacked_artifacts"},
            {"type": "CTAEndCard", "layout": "command_console"},
        ],
        frame_probes=[Path("frame-001.png"), Path("frame-002.png")],
    )

    assert report["overall"] == "pass"
    assert report["allowed_to_publish"] is True
    assert report["visual_issues"] == []
```

- [ ] **Step 2: Implement deterministic visual QA**

Create `src/repo_to_shorts/visual_qa.py`:

```python
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any


def score_scene_variety(scenes: list[dict[str, Any]], *, frame_probes: list[Path]) -> dict[str, Any]:
    visual_issues: list[dict[str, str]] = []
    layouts = [str(scene.get("layout") or scene.get("type") or "unknown") for scene in scenes]
    scene_types = [str(scene.get("type") or "unknown") for scene in scenes]
    layout_counts = Counter(layouts)
    type_counts = Counter(scene_types)

    repeated_layouts = [layout for layout, count in layout_counts.items() if layout and count > 2]
    repeated_types = [scene_type for scene_type, count in type_counts.items() if scene_type and count > 2]

    if repeated_layouts:
        visual_issues.append(_issue("visual_repetition", f"Repeated layouts: {', '.join(repeated_layouts)}", "Give scene types distinct layouts."))
    if repeated_types:
        visual_issues.append(_issue("scene_type_repetition", f"Repeated scene types: {', '.join(repeated_types)}", "Vary scene type rhythm."))
    if len(set(layouts)) < min(4, len(layouts)):
        visual_issues.append(_issue("low_layout_variety", f"{len(set(layouts))} unique layouts across {len(layouts)} scenes", "Use at least four distinct layouts for a final short."))
    if not frame_probes:
        visual_issues.append(_issue("missing_frame_probes", "No rendered frame probes available", "Export representative frames or contact sheet before final publish."))

    return {
        "schema_version": 1,
        "mode": "visual_variety",
        "overall": "pass" if not visual_issues else "fail",
        "score": 1.0 if not visual_issues else max(0.0, round(1.0 - 0.2 * len(visual_issues), 2)),
        "visual_issues": visual_issues,
        "allowed_to_publish": not visual_issues,
    }


def _issue(defect: str, evidence: str, fix: str) -> dict[str, str]:
    return {"defect": defect, "evidence": evidence, "fix": fix}
```

- [ ] **Step 3: Merge visual QA into rendered artifact QA**

In `src/repo_to_shorts/taste_qa.py`, add an optional `visual_report` parameter:

```python
def score_rendered_artifact(
    *,
    metadata: dict[str, Any],
    evidence_manifest: dict[str, Any] | None = None,
    visual_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
```

Before scoring:

```python
if visual_report:
    visual.extend(visual_report.get("visual_issues", []))
```

- [ ] **Step 4: Wire into final pipeline**

In `src/repo_to_shorts/hermes_skill.py`, after metadata is assembled and before `score_rendered_artifact()`:

```python
from repo_to_shorts.visual_qa import score_scene_variety
```

Then:

```python
visual_report = score_scene_variety(
    brief.scenes,
    frame_probes=[run_dir / "demo.mp4"] if final_video.exists() else [],
) if final else None
artifact_qa_report = score_rendered_artifact(
    metadata=metadata,
    evidence_manifest=evidence_manifest,
    visual_report=visual_report,
) if final else qa_report
```

- [ ] **Step 5: Run tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_visual_qa.py tests/test_taste_qa.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/repo_to_shorts/visual_qa.py src/repo_to_shorts/taste_qa.py src/repo_to_shorts/hermes_skill.py tests/test_visual_qa.py tests/test_taste_qa.py
git commit -m "feat: gate final renders on visual variety"
```

---

## Task 4: Prove The New Renderer Is Visually Different

**Files:**
- Modify: `tests/test_remotion_render.py`
- Optional create: `tests/test_rendered_similarity.py`

- [ ] **Step 1: Add manifest-level similarity regression**

Add this test to `tests/test_remotion_render.py`:

```python
def test_normalized_scene_layouts_are_distinct_for_final_scene_arc():
    data = build_remotion_input(
        repo_name="repo-to-shorts-agent",
        description="Turns repos into short-video packages.",
        key_files=["README.md"],
        proof={"kimi_mode": "live-api"},
        scenes=[
            {"type": "ColdOpen", "duration_seconds": 5, "headline": "THIS REPO MADE THIS VIDEO"},
            {"type": "PainPoint", "duration_seconds": 10, "headline": "DEMO VIDEOS EAT 6 HOURS"},
            {"type": "PipelineMap", "duration_seconds": 10, "headline": "KIMI READS THE REPO"},
            {"type": "LiveProof", "duration_seconds": 7.5, "headline": "PROOF IS IN METADATA"},
            {"type": "ArtifactStack", "duration_seconds": 7.5, "headline": "MP4 SRT SUBMISSION PACK"},
            {"type": "CTAEndCard", "duration_seconds": 5, "headline": "RUN THE COMMAND"},
        ],
    )

    layouts = [scene["layout"] for scene in data["scenes"]]
    assert len(set(layouts)) >= 5
    assert layouts == [
        "full_bleed_type",
        "split_alarm_counter",
        "left_to_right_system_map",
        "metadata_zoom",
        "stacked_artifacts",
        "command_console",
    ]
```

- [ ] **Step 2: Run targeted tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_remotion_render.py::test_normalized_scene_layouts_are_distinct_for_final_scene_arc -q
```

Expected: PASS.

- [ ] **Step 3: Generate before/after evidence**

Run a fresh final UI or CLI path:

```bash
set -a; source .env; set +a
.venv/bin/repo-shorts creative . \
  --audience "Nous Research Hermes Agent Creative Hackathon judges" \
  --final \
  --tts-provider none \
  --out runs
```

Expected: generated `metadata.json` shows:

```json
{
  "kimi": {"mode": "live-api"},
  "render": {"renderer": "remotion", "final": true},
  "creative_brief": {"scenes": ["distinct scene layouts in remotion_input.json"]}
}
```

Inspect:

```bash
jq '[.scenes[] | {type, layout, visual_role, headline}]' runs/<latest>/render/remotion_input.json
```

Expected: at least 5 unique `layout` values.

- [ ] **Step 4: Commit**

```bash
git add tests/test_remotion_render.py
git commit -m "test: require distinct final scene layouts"
```

---

## Task 5: Full Product E2E Acceptance

**Files:**
- No required code changes unless this task reveals a bug.

- [ ] **Step 1: Run full tests**

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
```

Expected:

```text
170+ passed
All checks passed!
```

- [ ] **Step 2: Run UI final workflow**

Start UI:

```bash
set -a; source .env; set +a
.venv/bin/repo-shorts web --host 127.0.0.1 --port 8765
```

In browser:

```text
Target: .
Audience: Nous Research Hermes Agent Creative Hackathon judges
Mode: EP
Audio: OFF
Click: ROLL TAPE
```

Expected:

```text
Tape Archive shows newest run as MASTER
Generated demo.mp4 opens from /runs/<latest>/demo.mp4
```

- [ ] **Step 3: Verify artifacts**

```bash
latest="$(find runs -maxdepth 1 -type d -name '*repo-to-shorts-agent' -print | sort | tail -1)"
jq '{title: .creative_brief.title, kimi: .kimi, render: .render, tts: .tts}' "$latest/metadata.json"
jq '{overall, score, allowed_to_publish, visual_issues}' "$latest/production/qa_report.json"
jq '[.scenes[] | {type, layout, visual_role, headline}]' "$latest/render/remotion_input.json"
```

Expected:

```text
kimi.mode == live-api
render.renderer == remotion
render.validation.ok == true
tts.provider == none
qa.allowed_to_publish == true
at least 5 unique layouts in remotion_input.json
```

- [ ] **Step 4: Human taste check**

Open the MP4 and compare it to `runs/20260504-225645-repo-to-shorts-agent/demo.mp4`.

The new MP4 must pass this human check:

```text
Cold open no longer reads as the same card template.
Pipeline scene has a real map treatment.
LiveProof scene visibly shows metadata/proof, not just text.
ArtifactStack scene looks like a stack/inventory, not another headline card.
CTAEndCard has a command-focused ending.
The whole video is not just VHS captions with new copy.
```

- [ ] **Step 5: Commit final docs if needed**

Only update docs after the implementation is real:

```bash
git add README.md
git commit -m "docs: describe taste-directed final renderer"
```

---

## Completion Criteria

The implementation is not complete just because QA passes. It is complete only when:

- Final Remotion manifest includes creative direction and per-scene layout fields.
- Remotion renders different visual compositions for the main scene types.
- Visual QA rejects repeated layouts.
- UI `EP` final workflow generates and presents a final MP4.
- New MP4 is visibly different from the current `runs/20260504-225645-repo-to-shorts-agent/demo.mp4`.
- Full pytest and ruff pass.
- Secret/PII scan is clean before push.

## Commit And Push Checklist

Run before pushing:

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
git status --short
git diff --cached
```

Run the repository secret/PII scan from `AGENTS.md` against the staged diff and current tree. Exit code `1` from a targeted `rg` scan means no matches and is the desired result.
