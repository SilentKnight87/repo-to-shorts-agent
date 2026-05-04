# Remotion Final Renderer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Remotion-based final MP4 renderer that produces a polished, evidence-rich hackathon short while preserving the existing Python CLI, live Kimi proof, and Pillow fallback.

**Architecture:** Python remains the orchestrator and writes a versioned Remotion manifest into each run directory. A Node/Remotion renderer reads that manifest and produces `demo.mp4`. If Remotion is unavailable or fails, Python falls back to the current Pillow renderer and records that honestly in metadata.

**Tech Stack:** Python 3.13, Typer CLI, pytest, Ruff, Node/npm, React, Remotion 4, ffmpeg.

---

## File Map

- Create `src/repo_to_shorts/remotion_render.py`
  - Builds `render/remotion_input.json`.
  - Detects Node/npm/Remotion availability.
  - Invokes `npm run render:remotion -- --input ... --output ...`.
  - Returns the existing `RenderResult` type.

- Modify `src/repo_to_shorts/hermes_skill.py`
  - Route final creative MP4 rendering through Remotion when available.
  - Preserve existing Pillow renderer fallback and metadata honesty.
  - Include Kimi proof and artifact proof in the Remotion manifest.

- Modify `src/repo_to_shorts/creative_director.py`
  - Upgrade Kimi prompt to output a storyboard object with scene `type`, `headline`, `narration`, `evidence`, and `caption_emphasis`.
  - Keep compatibility with existing `CreativeBrief.scenes`.

- Create `package.json`
  - Minimal Remotion scripts and dependencies.

- Create `remotion/render.mjs`
  - Reads manifest path and output path from CLI flags.
  - Uses `@remotion/renderer` to render the composition.

- Create `remotion/src/index.ts`
  - Registers the Remotion composition.

- Create `remotion/src/RepoShortsVideo.tsx`
  - React composition with polished scene components.

- Create `remotion/src/styles.ts`
  - Shared tokens: palette, spacing, type, shadows.

- Create `tests/test_remotion_render.py`
  - Unit tests for manifest shape, availability, command invocation, and fallback signaling.

- Modify `tests/test_hermes_skill.py`
  - Verify metadata records `renderer=remotion` when Remotion succeeds.
  - Verify fallback metadata when Remotion fails.

- Modify `tests/test_creative_director.py`
  - Verify final prompt requests scene `type`, evidence, Kimi proof beat, and object-shaped output.

- Modify `scripts/run-local-final.sh`
  - Keep live-Kimi guard.
  - Print Remotion/Pillow renderer metadata.
  - Generate a contact sheet when ffmpeg is available.

---

### Task 1: Python Remotion Manifest Builder

**Files:**
- Create: `src/repo_to_shorts/remotion_render.py`
- Test: `tests/test_remotion_render.py`

- [ ] **Step 1: Write failing manifest tests**

Add to `tests/test_remotion_render.py`:

```python
from pathlib import Path

from repo_to_shorts.remotion_render import build_remotion_input, write_remotion_input


def test_build_remotion_input_contains_repo_proof_scenes_and_artifacts():
    scenes = [
        {
            "type": "ColdOpen",
            "duration_seconds": 3,
            "headline": "This repo made the video you're watching.",
            "narration": "This repo made the video you're watching.",
            "evidence": ["repo-to-shorts-agent"],
        },
        {
            "type": "LiveProof",
            "duration_seconds": 6,
            "headline": "Kimi proof is in the metadata.",
            "narration": "The run records live Kimi usage.",
            "evidence": ["metadata.json"],
        },
    ]

    data = build_remotion_input(
        repo_name="repo-to-shorts-agent",
        description="Turns repos into launch-ready shorts.",
        key_files=["README.md", "src/repo_to_shorts/pipeline.py"],
        scenes=scenes,
        proof={
            "kimi_mode": "live-api",
            "kimi_provider": "openrouter",
            "kimi_model": "moonshotai/kimi-k2.6",
            "render_validation": "pass",
        },
        artifacts=["demo.mp4", "metadata.json", "captions.srt", "submission_pack.md"],
    )

    assert data["schema_version"] == 1
    assert data["repo"]["name"] == "repo-to-shorts-agent"
    assert data["video"] == {"width": 1080, "height": 1920, "fps": 30, "duration_seconds": 45}
    assert data["proof"]["kimi_mode"] == "live-api"
    assert data["scenes"][0]["type"] == "ColdOpen"
    assert data["artifacts"] == ["demo.mp4", "metadata.json", "captions.srt", "submission_pack.md"]


def test_write_remotion_input_writes_versioned_manifest(tmp_path: Path):
    path = write_remotion_input(
        tmp_path,
        {
            "schema_version": 1,
            "repo": {"name": "repo"},
            "video": {"width": 1080, "height": 1920, "fps": 30, "duration_seconds": 45},
            "proof": {},
            "scenes": [],
            "artifacts": [],
        },
    )

    assert path == tmp_path / "render" / "remotion_input.json"
    assert path.exists()
    assert '"schema_version": 1' in path.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_remotion_render.py -q
```

Expected: import failure because `repo_to_shorts.remotion_render` does not exist.

- [ ] **Step 3: Implement manifest builder**

Create `src/repo_to_shorts/remotion_render.py`:

```python
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from repo_to_shorts.render import RenderConfig, RenderResult, VideoScene


DEFAULT_ARTIFACTS = ["demo.mp4", "metadata.json", "captions.srt", "submission_pack.md"]


def build_remotion_input(
    *,
    repo_name: str,
    description: str,
    key_files: list[str],
    scenes: list[dict[str, Any]],
    proof: dict[str, Any],
    artifacts: list[str] | None = None,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    duration_seconds: int = 45,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
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
        "proof": proof,
        "scenes": [_normalize_scene(scene, index) for index, scene in enumerate(scenes)],
        "artifacts": artifacts or DEFAULT_ARTIFACTS,
    }


def write_remotion_input(run_dir: Path, data: dict[str, Any]) -> Path:
    render_dir = Path(run_dir) / "render"
    render_dir.mkdir(parents=True, exist_ok=True)
    path = render_dir / "remotion_input.json"
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def _normalize_scene(scene: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "type": str(scene.get("type") or _default_scene_type(index)),
        "duration_seconds": float(scene.get("duration_seconds", 6)),
        "headline": str(scene.get("headline") or scene.get("hook") or _headline_from_narration(scene.get("narration", ""))),
        "narration": str(scene.get("narration") or ""),
        "evidence": [str(item) for item in scene.get("evidence", [])][:4],
        "caption_emphasis": [str(item) for item in scene.get("caption_emphasis", [])][:5],
    }


def _default_scene_type(index: int) -> str:
    return ["ColdOpen", "RepoEvidence", "PipelineMap", "ArtifactStack", "LiveProof", "CTAEndCard"][min(index, 5)]


def _headline_from_narration(narration: str) -> str:
    first = str(narration).split(".")[0].strip()
    return first or "Repo to Shorts"
```

- [ ] **Step 4: Run manifest tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_remotion_render.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/repo_to_shorts/remotion_render.py tests/test_remotion_render.py
git commit -m "feat: add remotion render manifest"
```

---

### Task 2: Remotion Availability And Python Invocation

**Files:**
- Modify: `src/repo_to_shorts/remotion_render.py`
- Test: `tests/test_remotion_render.py`

- [ ] **Step 1: Write failing availability/invocation tests**

Append:

```python
import subprocess

from repo_to_shorts.render import RenderConfig
from repo_to_shorts.remotion_render import remotion_available, render_remotion_video


def test_remotion_available_requires_node_npm_and_render_script(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("repo_to_shorts.remotion_render.shutil.which", lambda name: f"/usr/bin/{name}" if name in {"node", "npm"} else None)

    assert remotion_available() is False

    (tmp_path / "package.json").write_text('{"scripts":{"render:remotion":"node remotion/render.mjs"}}', encoding="utf-8")
    assert remotion_available() is True


def test_render_remotion_video_invokes_npm_and_returns_result(monkeypatch, tmp_path: Path):
    commands = []

    def fake_run(command, cwd, check, capture_output, text):
        commands.append((command, cwd, check, capture_output, text))
        output = Path(command[-1])
        output.write_bytes(b"fake mp4")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("repo_to_shorts.remotion_render.subprocess.run", fake_run)
    monkeypatch.setattr("repo_to_shorts.remotion_render.remotion_available", lambda: True)

    result = render_remotion_video(
        tmp_path,
        [
            {"type": "ColdOpen", "headline": "Hook", "narration": "Hook.", "duration_seconds": 3},
            {"type": "CTAEndCard", "headline": "Ship", "narration": "Ship.", "duration_seconds": 4},
        ],
        repo_name="repo",
        description="Description",
        key_files=["README.md"],
        proof={"kimi_mode": "live-api"},
    )

    assert result.renderer == "remotion"
    assert result.path == tmp_path / "demo.mp4"
    assert result.path.exists()
    command = commands[0][0]
    assert command[:5] == ["npm", "run", "render:remotion", "--", "--input"]
    assert "--output" in command
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_remotion_render.py -q
```

Expected: fails because availability/render functions do not exist.

- [ ] **Step 3: Implement availability and invocation**

Add to `remotion_render.py`:

```python
def remotion_available(project_root: Path | None = None) -> bool:
    root = project_root or Path.cwd()
    package_json = root / "package.json"
    return bool(shutil.which("node") and shutil.which("npm") and package_json.exists() and "render:remotion" in package_json.read_text(encoding="utf-8"))


def render_remotion_video(
    run_dir: Path,
    scenes: list[dict[str, Any]],
    *,
    repo_name: str,
    description: str,
    key_files: list[str],
    proof: dict[str, Any],
    config: RenderConfig | None = None,
    project_root: Path | None = None,
) -> RenderResult:
    if not remotion_available(project_root):
        return RenderResult(path=None, status="skipped", renderer="remotion", error="Remotion unavailable: node/npm/package script missing")

    cfg = config or RenderConfig()
    manifest = build_remotion_input(
        repo_name=repo_name,
        description=description,
        key_files=key_files,
        scenes=scenes,
        proof=proof,
        width=cfg.width,
        height=cfg.height,
        fps=cfg.fps,
        duration_seconds=int(sum(float(scene.get("duration_seconds", 0)) for scene in scenes)) or 45,
    )
    input_path = write_remotion_input(run_dir, manifest)
    output_path = Path(run_dir) / "demo.mp4"
    command = [
        "npm",
        "run",
        "render:remotion",
        "--",
        "--input",
        str(input_path.resolve()),
        "--output",
        str(output_path.resolve()),
    ]
    try:
        subprocess.run(
            command,
            cwd=str((project_root or Path.cwd()).resolve()),
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        return RenderResult(path=None, status="error", renderer="remotion", error=f"Remotion render failed: {exc.__class__.__name__}")

    if not output_path.exists():
        return RenderResult(path=None, status="error", renderer="remotion", error="Remotion render did not create demo.mp4")
    return RenderResult(path=output_path, status="success", renderer="remotion", error=None)
```

- [ ] **Step 4: Run tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_remotion_render.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/repo_to_shorts/remotion_render.py tests/test_remotion_render.py
git commit -m "feat: invoke remotion renderer from python"
```

---

### Task 3: Remotion Project Scaffold

**Files:**
- Create: `package.json`
- Create: `remotion/render.mjs`
- Create: `remotion/src/index.ts`
- Create: `remotion/src/RepoShortsVideo.tsx`
- Create: `remotion/src/styles.ts`

- [ ] **Step 1: Create root package file**

Create `package.json`:

```json
{
  "private": true,
  "scripts": {
    "render:remotion": "node remotion/render.mjs"
  },
  "dependencies": {
    "@remotion/renderer": "^4.0.448",
    "remotion": "^4.0.448",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.23",
    "@types/react-dom": "^18.3.7",
    "typescript": "^5.8.3"
  }
}
```

- [ ] **Step 2: Create render entry**

Create `remotion/render.mjs`:

```javascript
import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';

const args = process.argv.slice(2);
const inputIndex = args.indexOf('--input');
const outputIndex = args.indexOf('--output');

if (inputIndex === -1 || outputIndex === -1 || !args[inputIndex + 1] || !args[outputIndex + 1]) {
  console.error('Usage: npm run render:remotion -- --input <manifest.json> --output <demo.mp4>');
  process.exit(2);
}

const inputPath = path.resolve(args[inputIndex + 1]);
const outputPath = path.resolve(args[outputIndex + 1]);
const inputProps = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
const entry = path.resolve('remotion/src/index.ts');
const bundleLocation = await bundle({entryPoint: entry});
const composition = await selectComposition({
  serveUrl: bundleLocation,
  id: 'RepoShortsVideo',
  inputProps,
});

await renderMedia({
  composition,
  serveUrl: bundleLocation,
  codec: 'h264',
  outputLocation: outputPath,
  inputProps,
});
```

- [ ] **Step 3: Register composition**

Create `remotion/src/index.ts`:

```typescript
import {registerRoot} from 'remotion';
import {RemotionRoot} from './RepoShortsVideo';

registerRoot(RemotionRoot);
```

- [ ] **Step 4: Create tokens**

Create `remotion/src/styles.ts`:

```typescript
export const tokens = {
  bg: '#050507',
  panel: '#10131b',
  panel2: '#171b26',
  text: '#f7f8ff',
  muted: '#9ca3af',
  cyan: '#16d9e3',
  violet: '#7c72ff',
  green: '#30d158',
  yellow: '#ffd60a',
  red: '#ff453a',
  shadow: '0 28px 80px rgba(0,0,0,0.42)',
};

export const font = {
  display: 'Arial, Helvetica, sans-serif',
  mono: 'SFMono-Regular, Menlo, Consolas, monospace',
};
```

- [ ] **Step 5: Create Remotion composition**

Create `remotion/src/RepoShortsVideo.tsx` with:

```tsx
import React from 'react';
import {AbsoluteFill, Composition, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {font, tokens} from './styles';

type Scene = {
  type: string;
  duration_seconds: number;
  headline: string;
  narration: string;
  evidence?: string[];
  caption_emphasis?: string[];
};

type InputProps = {
  repo: {name: string; description: string; key_files: string[]};
  video: {width: number; height: number; fps: number; duration_seconds: number};
  proof: Record<string, string>;
  scenes: Scene[];
  artifacts: string[];
};

const defaultProps: InputProps = {
  repo: {name: 'repo-to-shorts-agent', description: 'Turns repos into launch-ready shorts.', key_files: ['README.md']},
  video: {width: 1080, height: 1920, fps: 30, duration_seconds: 45},
  proof: {kimi_mode: 'live-api', kimi_provider: 'openrouter', kimi_model: 'moonshotai/kimi-k2.6'},
  scenes: [
    {type: 'ColdOpen', duration_seconds: 3, headline: "This repo made the video you're watching.", narration: "This repo made the video you're watching."},
    {type: 'PipelineMap', duration_seconds: 8, headline: 'From repo to reel.', narration: 'The pipeline turns source into story.'},
    {type: 'ArtifactStack', duration_seconds: 10, headline: 'Artifacts, not vibes.', narration: 'It writes the package judges can inspect.'},
    {type: 'LiveProof', duration_seconds: 8, headline: 'Kimi proof is visible.', narration: 'The metadata records live Kimi.'},
    {type: 'CTAEndCard', duration_seconds: 6, headline: 'Ship the demo.', narration: 'Run one command.'},
  ],
  artifacts: ['demo.mp4', 'metadata.json', 'captions.srt', 'submission_pack.md'],
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="RepoShortsVideo"
      component={RepoShortsVideo}
      durationInFrames={defaultProps.video.duration_seconds * defaultProps.video.fps}
      fps={defaultProps.video.fps}
      width={defaultProps.video.width}
      height={defaultProps.video.height}
      defaultProps={defaultProps}
      calculateMetadata={({props}) => ({
        durationInFrames: Math.max(1, Math.round(props.scenes.reduce((sum, scene) => sum + scene.duration_seconds, 0) * props.video.fps)),
        fps: props.video.fps,
        width: props.video.width,
        height: props.video.height,
      })}
    />
  );
};

export const RepoShortsVideo: React.FC<InputProps> = (props) => {
  let start = 0;
  return (
    <AbsoluteFill style={{backgroundColor: tokens.bg, color: tokens.text, fontFamily: font.display, overflow: 'hidden'}}>
      <Background />
      {props.scenes.map((scene, index) => {
        const duration = Math.max(1, Math.round(scene.duration_seconds * props.video.fps));
        const item = (
          <Sequence key={`${scene.type}-${index}`} from={start} durationInFrames={duration}>
            <SceneView scene={scene} index={index} total={props.scenes.length} propsData={props} />
          </Sequence>
        );
        start += duration;
        return item;
      })}
    </AbsoluteFill>
  );
};

const SceneView: React.FC<{scene: Scene; index: number; total: number; propsData: InputProps}> = ({scene, index, total, propsData}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame, fps, config: {damping: 18, stiffness: 120}});
  const y = interpolate(enter, [0, 1], [48, 0]);
  const opacity = interpolate(enter, [0, 1], [0, 1]);
  const style = {transform: `translateY(${y}px)`, opacity};

  return (
    <AbsoluteFill style={{padding: 72}}>
      <Chrome index={index} total={total} />
      {scene.type === 'ColdOpen' && <ColdOpen scene={scene} repo={propsData.repo} style={style} />}
      {scene.type === 'RepoEvidence' && <RepoEvidence scene={scene} repo={propsData.repo} style={style} />}
      {scene.type === 'PainPoint' && <PainPoint scene={scene} style={style} />}
      {scene.type === 'PipelineMap' && <PipelineMap scene={scene} style={style} />}
      {scene.type === 'ArtifactStack' && <ArtifactStack scene={scene} artifacts={propsData.artifacts} style={style} />}
      {scene.type === 'LiveProof' && <LiveProof scene={scene} proof={propsData.proof} style={style} />}
      {scene.type === 'DemoPreview' && <DemoPreview scene={scene} repo={propsData.repo} style={style} />}
      {scene.type === 'CTAEndCard' && <CTAEndCard scene={scene} proof={propsData.proof} style={style} />}
      {!['ColdOpen', 'RepoEvidence', 'PainPoint', 'PipelineMap', 'ArtifactStack', 'LiveProof', 'DemoPreview', 'CTAEndCard'].includes(scene.type) && (
        <PainPoint scene={scene} style={style} />
      )}
      <Caption text={scene.narration} />
    </AbsoluteFill>
  );
};
```

Then add simple component definitions in the same file for `Background`, `Chrome`, `ColdOpen`, `RepoEvidence`, `PainPoint`, `PipelineMap`, `ArtifactStack`, `LiveProof`, `DemoPreview`, `CTAEndCard`, and `Caption`. Keep them deterministic and CSS-only. Use the scene patterns in the spec.

- [ ] **Step 6: Install Node deps**

Run:

```bash
npm install
```

Expected: creates `package-lock.json` and `node_modules/`. Do not commit `node_modules/`.

- [ ] **Step 7: Smoke render default composition**

Run:

```bash
mkdir -p /tmp/repo-shorts-remotion-smoke
npm run render:remotion -- --input /tmp/repo-shorts-remotion-smoke/input.json --output /tmp/repo-shorts-remotion-smoke/demo.mp4
```

Before this command, write `/tmp/repo-shorts-remotion-smoke/input.json` with the default manifest from Task 1.

Expected: MP4 exists.

- [ ] **Step 8: Commit**

```bash
git add package.json package-lock.json remotion
git commit -m "feat: add remotion video project"
```

---

### Task 4: Route Final Creative Pipeline Through Remotion

**Files:**
- Modify: `src/repo_to_shorts/hermes_skill.py`
- Modify: `tests/test_hermes_skill.py`

- [ ] **Step 1: Write failing tests for Remotion success/fallback metadata**

Add tests:

```python
@patch("repo_to_shorts.hermes_skill.render_remotion_video")
@patch("repo_to_shorts.hermes_skill.render_scene")
@patch("repo_to_shorts.hermes_skill.generate_manim_script")
@patch("repo_to_shorts.hermes_skill.direct")
@patch("repo_to_shorts.hermes_skill.ingest_target")
def test_run_creative_pipeline_records_remotion_renderer_when_success(
    mock_ingest,
    mock_direct,
    mock_script,
    mock_render_scene,
    mock_remotion,
    tmp_path: Path,
):
    mock_ingest.return_value = FakeSnapshot()
    mock_direct.return_value = live_brief_with_five_scenes()
    mock_script.return_value = tmp_path / "descriptor.json"
    mock_render_scene.return_value = tmp_path / "video_raw.mp4"
    mock_render_scene.return_value.write_bytes(b"raw")
    remotion_mp4 = tmp_path / "remotion.mp4"
    remotion_mp4.write_bytes(b"mp4")
    mock_remotion.return_value = RenderResult(path=remotion_mp4, status="success", renderer="remotion")

    result = run_creative_pipeline(".", out_dir=tmp_path, final=True, tts_provider="none")

    metadata = json.loads((Path(result["run_dir"]) / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["render"]["renderer"] == "remotion"
    assert metadata["render"]["input"] == "render/remotion_input.json"
```

Add a second test where Remotion returns `RenderResult(path=None, status="error", renderer="remotion", error="boom")`; assert Pillow/raw path is used and metadata includes `fallback_renderer: remotion`.

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_hermes_skill.py -q
```

Expected: import/metadata failures.

- [ ] **Step 3: Implement route**

In `hermes_skill.py`:

```python
from repo_to_shorts.remotion_render import render_remotion_video
from repo_to_shorts.render import RenderResult
```

After Kimi brief validation and before Pillow rendering, call Remotion for final mode:

```python
remotion_result = None
if final:
    remotion_result = render_remotion_video(
        run_dir,
        brief.scenes,
        repo_name=snapshot.name,
        description=repo_analysis.get("description", ""),
        key_files=repo_analysis.get("key_files", []),
        proof={
            "kimi_mode": _brief_text_attr(brief, "mode", "deterministic-fallback"),
            "kimi_provider": _brief_text_attr(brief, "provider", "openrouter"),
            "kimi_model": _brief_text_attr(brief, "model", kimi_model or "moonshotai/kimi-k2.6"),
        },
    )
```

If Remotion succeeds, set `video_path` to `remotion_result.path` and skip `render_scene()`. If Remotion fails/skips, continue with existing Pillow path and preserve `remotion_result.error` for metadata.

Add metadata fields:

```python
"renderer": "remotion" if remotion_result and remotion_result.status == "success" else "pillow+ffmpeg-enhanced",
"input": "render/remotion_input.json" if remotion_result else None,
"fallback_renderer": "remotion" if remotion_result and remotion_result.status != "success" else None,
"fallback_reason": remotion_result.error if remotion_result and remotion_result.status != "success" else None,
```

- [ ] **Step 4: Run tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_hermes_skill.py tests/test_remotion_render.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/repo_to_shorts/hermes_skill.py tests/test_hermes_skill.py
git commit -m "feat: route final creative renders through remotion"
```

---

### Task 5: Kimi Storyboard Contract Upgrade

**Files:**
- Modify: `src/repo_to_shorts/creative_director.py`
- Modify: `tests/test_creative_director.py`

- [ ] **Step 1: Write failing prompt/parse tests**

Add:

```python
def test_final_director_prompt_requests_remotion_scene_contract():
    prompt = _build_director_prompt(
        {
            "repo_name": "repo-to-shorts",
            "description": "Turns repos into shorts",
            "key_files": ["README.md", "src/repo_to_shorts/pipeline.py"],
            "components": ["CLI", "Kimi", "Renderer"],
        },
        final=True,
    )

    assert "schema_version" in prompt
    assert "ColdOpen" in prompt
    assert "PipelineMap" in prompt
    assert "ArtifactStack" in prompt
    assert "LiveProof" in prompt
    assert "CTAEndCard" in prompt
    assert "evidence" in prompt
    assert "caption_emphasis" in prompt
    assert "Do not make generic architecture slides" in prompt
```

Add parse test:

```python
def test_parse_brief_accepts_storyboard_contract():
    raw = json.dumps({
        "schema_version": 1,
        "creative_direction": {"angle": "meta demo"},
        "storyboard": [
            {
                "type": "ColdOpen",
                "duration_seconds": 3,
                "headline": "This repo made the video.",
                "narration": "This repo made the video.",
                "evidence": ["repo_name"],
                "caption_emphasis": ["repo", "video"],
            }
        ],
        "music_mood": "electronic",
        "total_duration": 45,
    })
    result = _parse_brief(raw)
    assert result.scenes[0]["type"] == "ColdOpen"
    assert result.scenes[0]["headline"] == "This repo made the video."
    assert result.scenes[0]["evidence"] == ["repo_name"]
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_creative_director.py -q
```

Expected: prompt/parse failures.

- [ ] **Step 3: Update prompt and parser**

In `_build_director_prompt(final=True)`, include the object-shaped scene contract from the spec and the explicit taste constraints.

In `_parse_brief`, support both:

- old shape: `scenes`
- new shape: `storyboard`

Implementation:

```python
scenes = data.get("storyboard") or data.get("scenes", [])
```

Normalize each scene to preserve `type`, `headline`, `evidence`, and `caption_emphasis`.

- [ ] **Step 4: Run tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_creative_director.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/repo_to_shorts/creative_director.py tests/test_creative_director.py
git commit -m "feat: upgrade kimi remotion storyboard contract"
```

---

### Task 6: Runner QA Output

**Files:**
- Modify: `scripts/run-local-final.sh`
- Modify: `tests/test_local_runner.py`

- [ ] **Step 1: Write failing runner tests**

Extend test to assert:

```python
assert "contact_sheet.jpg" in text
assert "renderer" in text
assert "ffmpeg -y -i" in text
```

- [ ] **Step 2: Implement contact sheet generation**

After live Kimi validation, add:

```bash
if command -v ffmpeg >/dev/null 2>&1 && [[ -f "$run_dir/demo.mp4" ]]; then
  ffmpeg -y -i "$run_dir/demo.mp4" \
    -vf "fps=1/7,scale=270:-1,tile=3x3" \
    -frames:v 1 "$run_dir/contact_sheet.jpg" >/dev/null 2>&1 || true
  [[ -f "$run_dir/contact_sheet.jpg" ]] && echo "Contact sheet: $run_dir/contact_sheet.jpg"
fi
```

Also update the `jq` projection to print `.render.renderer`.

- [ ] **Step 3: Run tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_local_runner.py -q
bash -n scripts/run-local-final.sh
```

Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add scripts/run-local-final.sh tests/test_local_runner.py
git commit -m "chore: add final render qa contact sheet"
```

---

### Task 7: Full Verification And Live Smoke

**Files:**
- No code unless fixing issues.

- [ ] **Step 1: Run full Python checks**

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
git diff --check
```

Expected:

- all tests pass
- Ruff clean
- no whitespace errors

- [ ] **Step 2: Install Node dependencies if needed**

```bash
npm install
```

Expected: `package-lock.json` exists, `node_modules/` remains untracked.

- [ ] **Step 3: Run guarded final render**

```bash
OPEN_VIDEO=0 ./scripts/run-local-final.sh
```

Expected:

- exits 0
- metadata shows `kimi.mode=live-api`
- metadata shows `render.renderer=remotion` when Node deps are available
- MP4 validates 1080x1920 with audio
- contact sheet exists

- [ ] **Step 4: Inspect latest metadata**

```bash
jq '{kimi: .kimi, tts: .tts, render: .render}' runs/<latest>/metadata.json
```

Expected:

- `kimi.mode == "live-api"`
- `render.validation.ok == true`
- `render.renderer == "remotion"` or honest Pillow fallback reason

- [ ] **Step 5: Commit any final fixes**

```bash
git status --short
git log --oneline --decorate -5
```

If clean, stop. If fixes were needed, commit them.

---

## Plan Self-Review

- Spec coverage: Remotion renderer, Kimi contract, metadata honesty, fallback, runner QA, and tests are covered.
- Placeholder scan: No `TBD`, `TODO`, or unspecified “add tests” steps remain.
- Type consistency: Python uses existing `RenderResult`, `RenderConfig`, and list-of-dict scene contracts. Node receives JSON by file path.
- Scope: This plan stays focused on final MP4 quality and does not add website UI, publishing, or cloud rendering.
