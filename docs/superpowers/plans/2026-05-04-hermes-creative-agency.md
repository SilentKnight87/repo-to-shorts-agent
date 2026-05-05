# Hermes Creative Agency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Repo-to-Shorts taste system: truthful web states, persistent design/taste inputs, production manifests, Kimi creative-director contracts, deterministic taste QA, and preview comparison.

**Architecture:** Keep the existing pipeline and Remotion/Pillow render paths. Add small modules around the current coordinator: `taste.py` reads `DESIGN.md` and builds reference inputs, `production.py` writes run manifests, and `taste_qa.py` evaluates creative plans/output metadata before the project declares success. Kimi remains the director; deterministic Python code remains the gatekeeper.

**Tech Stack:** Python 3.13, Typer, stdlib `http.server`, JSON/YAML-ish frontmatter parsing with stdlib only, existing Remotion/Pillow/ffmpeg paths, pytest, Ruff.

---

## Ground Rules For DeepSeek/OpenCode

- Do not rewrite the whole pipeline.
- Do not remove existing final-mode, media validation, submission pack, Remotion, or Kimi proof behavior.
- Do not add real network calls to tests.
- Do not touch `.env`, credentials, `runs/`, `.venv/`, generated caches, or Mac Mini-only files.
- Do not claim final success when `metadata["render"]["validation"]["ok"]` is false.
- Keep all new generated run artifacts under `runs/<timestamp>/production/`.
- Keep `DESIGN.md` and `docs/taste-research.md` as source documents; do not hard-code their full contents into prompts.
- Commit after each task if working interactively.

## Source Documents

- `docs/superpowers/specs/2026-05-04-hermes-creative-agency-design.md`
- `DESIGN.md`
- `docs/taste-research.md`
- `AGENTS.md`

## File Structure

- Create `src/repo_to_shorts/taste.py`
  - Read `DESIGN.md`, parse frontmatter, build design profile and reference pack.
- Create `src/repo_to_shorts/production.py`
  - Write `production/*.json` manifests for each run.
- Create `src/repo_to_shorts/taste_qa.py`
  - Score creative plans and produce `qa_report.json`.
- Modify `src/repo_to_shorts/creative_director.py`
  - Extend `CreativeBrief` and prompt/parse logic with taste fields.
- Modify `src/repo_to_shorts/hermes_skill.py`
  - Load taste inputs, pass them to Kimi, write production manifests, run pre-render QA.
- Modify `src/repo_to_shorts/web.py`
  - Fix toggle markup, send final mode, and render preview/failure truthfully.
- Modify `src/repo_to_shorts/static/app.js`
  - Wire `final` hidden flag for EP/final mode.
- Modify tests under `tests/`
  - Add focused tests for new modules and update web/creative pipeline tests.

---

### Task 1: Truthful Web Mode And Validation Surface

**Files:**
- Modify: `src/repo_to_shorts/web.py`
- Modify: `src/repo_to_shorts/static/app.js`
- Modify: `tests/test_web.py`

- [ ] **Step 1: Write failing web tests**

Add tests to `tests/test_web.py`:

```python
def test_home_page_toggle_clusters_have_js_contract():
    html = render_home_page([])
    assert 'class="toggle-mode" data-toggle="tape-mode"' in html
    assert 'class="toggle-mode" data-toggle="audio-mode"' in html
    assert 'data-flag="final"' in html


def test_success_page_labels_validation_failed_preview(tmp_path: Path):
    run_dir = tmp_path / "20260504-failed-preview"
    run_dir.mkdir()
    metadata = {
        "artifacts": ["demo.mp4", "metadata.json"],
        "kimi": {"mode": "deterministic-fallback"},
        "render": {
            "mode": "mp4",
            "renderer": "pillow+ffmpeg-enhanced",
            "preview": True,
            "final": False,
            "validation": {"ok": False, "errors": ["duration must be 43-62 seconds"]},
        },
        "creative_brief": {"title": "Draft", "hook": "Draft hook", "scenes": []},
    }
    (run_dir / "demo.mp4").write_bytes(b"mp4")

    html = render_success_page(run_dir, metadata)

    assert "PREVIEW DRAFT" in html
    assert "VALIDATION FAILED" in html
    assert "duration must be 43-62 seconds" in html
    assert "BROADCAST COMPLETE" not in html


def test_generate_creative_final_mode_passes_final_flag(tmp_path: Path, monkeypatch):
    calls = []

    def fake_run_creative_pipeline(target, audience, out_dir, **kwargs):
        calls.append(kwargs)
        run_dir = tmp_path / "20260504-final"
        run_dir.mkdir(parents=True, exist_ok=True)
        metadata = {
            "artifacts": ["demo.mp4", "metadata.json"],
            "kimi": {"mode": "live-api"},
            "render": {"mode": "mp4", "final": True, "validation": {"ok": True, "errors": []}},
            "creative_brief": {"title": "Final", "hook": "Final hook", "scenes": []},
        }
        (run_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        (run_dir / "demo.mp4").write_bytes(b"mp4")
        return {"output": str(run_dir / "demo.mp4"), "run_dir": str(run_dir)}

    monkeypatch.setattr("repo_to_shorts.hermes_skill.run_creative_pipeline", fake_run_creative_pipeline)
    server, port = _start_server(tmp_path)
    try:
        data = urllib.parse.urlencode({
            "target": ".",
            "audience": "builders",
            "kimi_model": "moonshotai/kimi-k2.6",
            "creative_mode": "on",
            "final": "on",
        }).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{port}/generate", data=data, method="POST")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
    finally:
        _stop_server(server)

    assert calls[0]["final"] is True
    assert calls[0]["preview"] is False
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_web.py -q
```

Expected: the new tests fail because `data-toggle` and `final` are missing and the success page always says broadcast complete.

- [ ] **Step 3: Fix `render_home_page()` toggle markup**

In `src/repo_to_shorts/web.py`, update the two toggle clusters:

```html
<div class="toggle-mode" data-toggle="tape-mode" role="radiogroup" aria-label="Tape mode">
```

```html
<div class="toggle-mode" data-toggle="audio-mode" role="radiogroup" aria-label="Audio mode">
```

Add a hidden final flag:

```html
<input type="hidden" name="" value="" data-flag="final">
```

- [ ] **Step 4: Wire final flag in JS**

In `src/repo_to_shorts/static/app.js`, update `applyToggleState(form)`:

```js
let finalMode;

if (tape === "sp") {
  preview = true;
  finalMode = false;
  skipAudio = true;
} else if (tape === "lp") {
  preview = true;
  finalMode = false;
  skipAudio = audio === "off";
} else {
  preview = false;
  finalMode = true;
  skipAudio = audio === "off";
}

setFlag(form, "creative_mode", creative);
setFlag(form, "preview", preview);
setFlag(form, "final", finalMode);
setFlag(form, "skip_audio", skipAudio);
```

- [ ] **Step 5: Pass final mode through `/generate`**

In `do_POST`, parse:

```python
final = "final" in form
if final:
    preview = False
```

Pass to `run_creative_pipeline(..., final=final, preview=preview, skip_audio=skip_audio)`.

- [ ] **Step 6: Make success page truthful**

In `render_success_page`, derive:

```python
validation = render_info.get("validation") if isinstance(render_info, dict) else {}
validation_ok = bool(validation.get("ok")) if isinstance(validation, dict) else True
is_preview = bool(render_info.get("preview")) if isinstance(render_info, dict) else False
is_final = bool(render_info.get("final")) if isinstance(render_info, dict) else False

if not validation_ok:
    state_label = "VALIDATION FAILED"
elif is_preview:
    state_label = "PREVIEW DRAFT"
elif is_final:
    state_label = "BROADCAST COMPLETE"
else:
    state_label = "PACKAGE COMPLETE"
```

Use `state_label` in the kicker instead of hard-coded `// BROADCAST COMPLETE`. Render validation errors in a visible deck section.

- [ ] **Step 7: Run web tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_web.py -q
```

Expected: all web tests pass.

- [ ] **Step 8: Commit**

```bash
git add src/repo_to_shorts/web.py src/repo_to_shorts/static/app.js tests/test_web.py
git commit -m "fix: make web preview and final states truthful"
```

---

### Task 2: Taste Profile And Reference Pack Module

**Files:**
- Create: `src/repo_to_shorts/taste.py`
- Create: `tests/test_taste.py`

- [ ] **Step 1: Write failing tests**

Add `tests/test_taste.py`:

```python
from __future__ import annotations

from pathlib import Path

from repo_to_shorts.taste import build_reference_pack, load_design_profile


def test_load_design_profile_reads_frontmatter(tmp_path: Path):
    design = tmp_path / "DESIGN.md"
    design.write_text(
        """---
name: Repo-to-Shorts Cinematic Console
colors:
  neutral: "#080A0F"
  tertiary: "#6EE7F9"
rounded:
  md: 8px
---

## Overview
Terminal-native, premium, fast, and credible.
""",
        encoding="utf-8",
    )

    profile = load_design_profile(design)

    assert profile["name"] == "Repo-to-Shorts Cinematic Console"
    assert profile["colors"]["neutral"] == "#080A0F"
    assert profile["rounded"]["md"] == "8px"
    assert "Terminal-native" in profile["notes"]


def test_load_design_profile_fallback_when_missing(tmp_path: Path):
    profile = load_design_profile(tmp_path / "missing.md")

    assert profile["name"] == "Repo-to-Shorts Default Taste"
    assert profile["colors"]["neutral"] == "#080A0F"
    assert profile["source"] is None


def test_build_reference_pack_uses_design_and_taste_research(tmp_path: Path):
    design = tmp_path / "DESIGN.md"
    taste = tmp_path / "taste-research.md"
    design.write_text("---\nname: Console\n---\n## Do\nUse references before generating.", encoding="utf-8")
    taste.write_text(
        "# Taste\n\n## X signals gathered\n\n### 1. References beat vibes\n\nImplementation implication:\n- Add a `reference_pack` concept.\n",
        encoding="utf-8",
    )

    pack = build_reference_pack(design, taste)

    assert pack["schema_version"] == 1
    assert pack["sources"][0]["path"].endswith("DESIGN.md")
    assert pack["references"][0]["label"] == "premium console"
    assert "generic AI SaaS soup" in pack["avoid"]
```

- [ ] **Step 2: Run tests to verify failure**

```bash
.venv/bin/python -m pytest tests/test_taste.py -q
```

Expected: import failure because `repo_to_shorts.taste` does not exist.

- [ ] **Step 3: Implement `taste.py`**

Create `src/repo_to_shorts/taste.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any


DEFAULT_DESIGN_PROFILE: dict[str, Any] = {
    "schema_version": 1,
    "source": None,
    "name": "Repo-to-Shorts Default Taste",
    "colors": {
        "neutral": "#080A0F",
        "primary": "#F6F2E8",
        "secondary": "#9BA3AF",
        "tertiary": "#6EE7F9",
        "accentWarm": "#F97316",
    },
    "rounded": {"sm": "4px", "md": "8px", "lg": "8px"},
    "notes": "terminal-native, premium, fast, credible",
}


def load_design_profile(path: Path | str = Path("DESIGN.md")) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return dict(DEFAULT_DESIGN_PROFILE)

    text = path.read_text(encoding="utf-8")
    frontmatter, notes = _split_frontmatter(text)
    profile = dict(DEFAULT_DESIGN_PROFILE)
    profile["source"] = str(path)
    profile["notes"] = notes.strip()
    profile.update(_parse_simple_yaml(frontmatter))
    profile["schema_version"] = 1
    return profile


def build_reference_pack(
    design_path: Path | str = Path("DESIGN.md"),
    taste_research_path: Path | str = Path("docs/taste-research.md"),
) -> dict[str, Any]:
    design_path = Path(design_path)
    taste_research_path = Path(taste_research_path)
    sources = []
    for source in (design_path, taste_research_path):
        if source.exists():
            sources.append({"path": str(source), "kind": source.stem})

    return {
        "schema_version": 1,
        "sources": sources,
        "references": [
            {
                "label": "premium console",
                "borrow": ["restrained palette", "repo proof chips", "kinetic code text"],
                "avoid": ["purple-blue gradient hero", "three generic cards"],
            },
            {
                "label": "cinematic kinetic typography",
                "borrow": ["3-7 word beats", "motion follows meaning", "proof holds"],
                "avoid": ["full sentences as overlays", "ambient motion without purpose"],
            },
        ],
        "avoid": [
            "generic AI SaaS soup",
            "default three-card grid",
            "abstract shapes before product context",
            "random colors outside DESIGN.md",
            "captions outside 9:16 safe area",
        ],
    }
```

Then add the helper functions:

```python
def _split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---", 4)
    if end == -1:
        return "", text
    return text[4:end], text[end + 4 :]


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, result)]
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.strip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip().strip('"')
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value:
            parent[key] = value
        else:
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
    return result
```

- [ ] **Step 4: Run tests**

```bash
.venv/bin/python -m pytest tests/test_taste.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/repo_to_shorts/taste.py tests/test_taste.py
git commit -m "feat: add taste profile loader"
```

---

### Task 3: Production Manifest Writer

**Files:**
- Create: `src/repo_to_shorts/production.py`
- Create: `tests/test_production.py`

- [ ] **Step 1: Write failing tests**

Add `tests/test_production.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from repo_to_shorts.production import write_production_manifests


def test_write_production_manifests_creates_expected_files(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    data = {
        "design_profile": {"schema_version": 1, "name": "Console"},
        "reference_pack": {"schema_version": 1, "references": []},
        "evidence_manifest": {"repo_name": "repo", "safe_files": ["README.md"]},
        "creative_brief": {"title": "Title"},
        "scene_plan": {"scenes": [{"type": "ColdOpen"}]},
        "asset_manifest": {"assets": []},
        "audio_plan": {"mode": "voiceover_with_ducked_music"},
        "qa_report": {"overall": "pass"},
    }

    written = write_production_manifests(run_dir, **data)

    assert sorted(path.name for path in written) == [
        "asset_manifest.json",
        "audio_plan.json",
        "creative_brief.json",
        "design_profile.json",
        "evidence_manifest.json",
        "qa_report.json",
        "reference_pack.json",
        "scene_plan.json",
    ]
    assert json.loads((run_dir / "production" / "design_profile.json").read_text())["name"] == "Console"
```

- [ ] **Step 2: Run tests to verify failure**

```bash
.venv/bin/python -m pytest tests/test_production.py -q
```

Expected: import failure.

- [ ] **Step 3: Implement `production.py`**

Create `src/repo_to_shorts/production.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


MANIFEST_NAMES = {
    "design_profile": "design_profile.json",
    "reference_pack": "reference_pack.json",
    "evidence_manifest": "evidence_manifest.json",
    "creative_brief": "creative_brief.json",
    "scene_plan": "scene_plan.json",
    "asset_manifest": "asset_manifest.json",
    "audio_plan": "audio_plan.json",
    "qa_report": "qa_report.json",
}


def write_production_manifests(run_dir: Path, **manifests: dict[str, Any]) -> list[Path]:
    production_dir = run_dir / "production"
    production_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for key, filename in MANIFEST_NAMES.items():
        payload = manifests.get(key, {})
        path = production_dir / filename
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(path)
    return written
```

- [ ] **Step 4: Run tests**

```bash
.venv/bin/python -m pytest tests/test_production.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/repo_to_shorts/production.py tests/test_production.py
git commit -m "feat: write production manifests"
```

---

### Task 4: Extend Kimi Creative Brief Contract

**Files:**
- Modify: `src/repo_to_shorts/creative_director.py`
- Modify: `tests/test_creative_director.py`

- [ ] **Step 1: Add failing tests**

Add tests:

```python
def test_parse_brief_preserves_taste_fields():
    raw = json.dumps({
        "style": "cinematic",
        "title": "Taste Title",
        "hook": "Watch the repo become a reel.",
        "distribution_channel": "x_short",
        "reference_pack": [{"label": "premium console"}],
        "visual_world": "cinematic engineering console",
        "motion_principles": ["motion guides attention"],
        "shot_list": ["raw repo input", "proof metadata"],
        "continuity_rules": ["captions stay inside safe area"],
        "negative_prompts": ["generic AI SaaS soup"],
        "storyboard": [{"type": "ColdOpen", "duration_seconds": 5, "headline": "REPO BECOMES REEL"}],
        "total_duration": 50,
    })

    result = _parse_brief(raw)

    assert result.distribution_channel == "x_short"
    assert result.reference_pack == [{"label": "premium console"}]
    assert result.visual_world == "cinematic engineering console"
    assert result.motion_principles == ["motion guides attention"]
    assert result.shot_list == ["raw repo input", "proof metadata"]
    assert result.continuity_rules == ["captions stay inside safe area"]
    assert result.negative_prompts == ["generic AI SaaS soup"]


def test_director_prompt_includes_design_profile_and_reference_pack():
    prompt = _build_director_prompt(
        {"repo_name": "repo", "description": "desc", "key_files": ["README.md"]},
        final=True,
        design_profile={"name": "Console", "colors": {"neutral": "#080A0F"}},
        reference_pack={"references": [{"label": "premium console"}], "avoid": ["generic AI SaaS soup"]},
    )

    assert "DESIGN PROFILE" in prompt
    assert "Console" in prompt
    assert "REFERENCE PACK" in prompt
    assert "premium console" in prompt
    assert "generic AI SaaS soup" in prompt
    assert "visual_world" in prompt
    assert "negative_prompts" in prompt
```

- [ ] **Step 2: Run tests to verify failure**

```bash
.venv/bin/python -m pytest tests/test_creative_director.py -q
```

Expected: failures because dataclass/prompt signatures do not include these fields.

- [ ] **Step 3: Extend `CreativeBrief`**

Add fields:

```python
distribution_channel: str = "x_short"
reference_pack: list = field(default_factory=list)
visual_world: str = "cinematic engineering console"
motion_principles: list[str] = field(default_factory=list)
shot_list: list[str] = field(default_factory=list)
continuity_rules: list[str] = field(default_factory=list)
negative_prompts: list[str] = field(default_factory=list)
quality_bar: dict = field(default_factory=dict)
```

- [ ] **Step 4: Update `direct()` and `_build_director_prompt()` signatures**

Use:

```python
def direct(
    repo_analysis: dict,
    model: str = "moonshotai/kimi-k2.6",
    *,
    final: bool = False,
    design_profile: dict | None = None,
    reference_pack: dict | None = None,
) -> CreativeBrief:
```

And:

```python
def _build_director_prompt(
    analysis: dict,
    *,
    final: bool = False,
    design_profile: dict | None = None,
    reference_pack: dict | None = None,
) -> str:
```

Append compact JSON snippets to the final prompt:

```python
design_context = json.dumps(design_profile or {}, indent=2)[:4000]
reference_context = json.dumps(reference_pack or {}, indent=2)[:4000]
```

Require output fields `distribution_channel`, `reference_pack`, `visual_world`, `motion_principles`, `shot_list`, `continuity_rules`, and `negative_prompts`.

- [ ] **Step 5: Update `_parse_brief()`**

Map fields from parsed data into `CreativeBrief`.

- [ ] **Step 6: Run tests**

```bash
.venv/bin/python -m pytest tests/test_creative_director.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add src/repo_to_shorts/creative_director.py tests/test_creative_director.py
git commit -m "feat: extend creative brief taste contract"
```

---

### Task 5: Deterministic Taste QA

**Files:**
- Create: `src/repo_to_shorts/taste_qa.py`
- Create: `tests/test_taste_qa.py`

- [ ] **Step 1: Write failing tests**

Add `tests/test_taste_qa.py`:

```python
from __future__ import annotations

from repo_to_shorts.taste_qa import score_creative_plan


def test_score_creative_plan_passes_specific_postable_plan():
    brief = {
        "title": "Repo Becomes Reel",
        "distribution_channel": "x_short",
        "scenes": [
            {"type": "ColdOpen", "headline": "REPO BECOMES REEL", "duration_seconds": 5, "evidence": ["repo_name"]},
            {"type": "PipelineMap", "headline": "KIMI READS THE REPO", "duration_seconds": 10, "evidence": ["src/pipeline.py"]},
            {"type": "LiveProof", "headline": "PROOF IN METADATA", "duration_seconds": 7.5, "evidence": ["metadata.json"]},
            {"type": "ArtifactStack", "headline": "SHORT PACKAGE BUILT", "duration_seconds": 7.5, "evidence": ["demo.mp4"]},
            {"type": "CTAEndCard", "headline": "SHIP THE SHORT", "duration_seconds": 5, "evidence": ["repo-shorts creative"]},
        ],
    }

    report = score_creative_plan(brief, design_profile={"colors": {"neutral": "#080A0F"}})

    assert report["overall"] == "pass"
    assert report["allowed_to_publish"] is True
    assert report["score"] >= 0.8
    assert report["blocking_issues"] == []


def test_score_creative_plan_fails_generic_slop():
    brief = {
        "title": "Introducing an AI-powered workflow",
        "scenes": [
            {"type": "ColdOpen", "headline": "INTRODUCING SEAMLESS AI", "duration_seconds": 4, "evidence": []},
            {"type": "Card", "headline": "OPTIMIZE YOUR WORKFLOW WITH AI POWERED TOOLS", "duration_seconds": 4, "evidence": []},
            {"type": "Card", "headline": "LEVERAGE ROBUST AUTOMATION", "duration_seconds": 4, "evidence": []},
        ],
    }

    report = score_creative_plan(brief, design_profile={})

    assert report["overall"] == "fail"
    assert report["allowed_to_publish"] is False
    defects = {issue["defect"] for issue in report["blocking_issues"] + report["taste_issues"]}
    assert "missing_repo_specificity" in defects
    assert "caption_density_high" in defects
    assert "missing_final_cta" in defects
```

- [ ] **Step 2: Run tests to verify failure**

```bash
.venv/bin/python -m pytest tests/test_taste_qa.py -q
```

Expected: import failure.

- [ ] **Step 3: Implement `taste_qa.py`**

Create:

```python
from __future__ import annotations

from collections import Counter
from typing import Any

GENERIC_WORDS = {"seamless", "robust", "leverage", "optimize", "game-changing", "supercharge", "unleash"}
PROOF_TERMS = {"metadata", "demo.mp4", "repo", "file", "command", "artifact", "src/", "tests/"}


def score_creative_plan(brief: dict[str, Any], *, design_profile: dict[str, Any] | None = None) -> dict[str, Any]:
    scenes = [scene for scene in brief.get("scenes", []) if isinstance(scene, dict)]
    blocking: list[dict[str, str]] = []
    taste: list[dict[str, str]] = []

    if not scenes:
        blocking.append(_issue("missing_scenes", "No scenes in creative plan", "Generate at least 5 scenes for final mode."))
    if scenes and not _scene_reveals_purpose(scenes[0]):
        blocking.append(_issue("weak_hook", "First scene does not reveal project purpose or transformation", "Rewrite ColdOpen around repo transformation."))
    if not any(str(scene.get("type", "")).lower() == "ctaendcard" for scene in scenes):
        blocking.append(_issue("missing_final_cta", "No CTAEndCard scene found", "Add final scene with command, artifact, or repo link."))

    layout_counts = Counter(str(scene.get("type", "")).lower() for scene in scenes)
    for layout, count in layout_counts.items():
        if layout and count > 2:
            taste.append(_issue("layout_repetition", f"{count} scenes use layout {layout}", "Vary scene types or mark repetition as intentional."))

    for index, scene in enumerate(scenes, start=1):
        headline = str(scene.get("headline") or scene.get("narration") or "")
        word_count = len(headline.split())
        if word_count > 12:
            taste.append(_issue("caption_density_high", f"Scene {index} has {word_count} headline words", "Split into two beats or shorten to 3-7 words."))
        lowered = headline.lower()
        if any(word in lowered for word in GENERIC_WORDS):
            taste.append(_issue("generic_ai_copy", f"Scene {index} uses generic AI copy: {headline}", "Replace with repo-specific proof language."))

    if not _has_repo_specificity(brief, scenes):
        blocking.append(_issue("missing_repo_specificity", "Plan could describe any AI repo by swapping the name", "Add file, command, artifact, metadata, or architecture evidence."))

    weighted = _score(blocking, taste)
    return {
        "schema_version": 1,
        "overall": "pass" if not blocking and weighted >= 0.8 else "fail",
        "score": weighted,
        "blocking_issues": blocking,
        "taste_issues": taste,
        "allowed_to_publish": not blocking and weighted >= 0.8,
    }
```

Add helpers:

```python
def _issue(defect: str, evidence: str, fix: str) -> dict[str, str]:
    return {"defect": defect, "evidence": evidence, "fix": fix}


def _scene_reveals_purpose(scene: dict[str, Any]) -> bool:
    text = " ".join(str(scene.get(key, "")) for key in ("headline", "narration", "type")).lower()
    return any(term in text for term in ("repo", "reel", "short", "video", "trailer", "demo", "code"))


def _has_repo_specificity(brief: dict[str, Any], scenes: list[dict[str, Any]]) -> bool:
    haystack = str(brief).lower()
    if any(term in haystack for term in PROOF_TERMS):
        return True
    return any(scene.get("evidence") for scene in scenes)


def _score(blocking: list[dict[str, str]], taste: list[dict[str, str]]) -> float:
    score = 1.0
    score -= 0.25 * len(blocking)
    score -= 0.08 * len(taste)
    return max(0.0, round(score, 2))
```

- [ ] **Step 4: Run tests**

```bash
.venv/bin/python -m pytest tests/test_taste_qa.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/repo_to_shorts/taste_qa.py tests/test_taste_qa.py
git commit -m "feat: add deterministic taste qa"
```

---

### Task 6: Integrate Taste Inputs And Production Manifests

**Files:**
- Modify: `src/repo_to_shorts/hermes_skill.py`
- Modify: `tests/test_hermes_skill.py`

- [ ] **Step 1: Write failing integration test**

Add to `tests/test_hermes_skill.py`:

```python
@patch("repo_to_shorts.hermes_skill.validate_media")
@patch("repo_to_shorts.hermes_skill.ingest_target")
@patch("repo_to_shorts.hermes_skill.direct")
@patch("repo_to_shorts.hermes_skill.generate_manim_script")
@patch("repo_to_shorts.hermes_skill.render_scene")
@patch("repo_to_shorts.hermes_skill._merge_creative_video")
def test_run_creative_pipeline_writes_production_manifests(
    mock_merge,
    mock_render,
    mock_script,
    mock_direct,
    mock_ingest,
    mock_validate,
    tmp_path: Path,
):
    mock_ingest.return_value = FakeSnapshot()
    mock_direct.return_value = _final_brief()
    mock_script.return_value = tmp_path / "script.json"
    raw = tmp_path / "video.mp4"
    raw.write_bytes(b"raw")
    mock_render.return_value = raw
    mock_validate.return_value = {"ok": True, "duration_seconds": 50, "resolution": "1080x1920", "has_audio": True, "errors": []}

    result = run_creative_pipeline(".", out_dir=tmp_path, final=True)

    run_dir = Path(result["run_dir"])
    production = run_dir / "production"
    assert (production / "design_profile.json").exists()
    assert (production / "reference_pack.json").exists()
    assert (production / "evidence_manifest.json").exists()
    assert (production / "creative_brief.json").exists()
    assert (production / "scene_plan.json").exists()
    assert (production / "qa_report.json").exists()

    metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
    assert "production/design_profile.json" in metadata["artifacts"]
    assert "production/qa_report.json" in metadata["artifacts"]
    assert mock_direct.call_args.kwargs["design_profile"]["schema_version"] == 1
    assert mock_direct.call_args.kwargs["reference_pack"]["schema_version"] == 1
```

- [ ] **Step 2: Run test to verify failure**

```bash
.venv/bin/python -m pytest tests/test_hermes_skill.py::test_run_creative_pipeline_writes_production_manifests -q
```

Expected: failure because manifests are not written.

- [ ] **Step 3: Import helpers in `hermes_skill.py`**

Add:

```python
from repo_to_shorts.production import write_production_manifests
from repo_to_shorts.taste import build_reference_pack, load_design_profile
from repo_to_shorts.taste_qa import score_creative_plan
```

- [ ] **Step 4: Load taste inputs before Kimi call**

Before `direct(...)`:

```python
design_profile = load_design_profile(Path("DESIGN.md"))
reference_pack = build_reference_pack(Path("DESIGN.md"), Path("docs/taste-research.md"))
```

Pass:

```python
brief = direct(
    repo_analysis,
    model=kimi_model or "moonshotai/kimi-k2.6",
    final=final,
    design_profile=design_profile,
    reference_pack=reference_pack,
)
```

- [ ] **Step 5: Build manifest payloads after `run_dir` exists**

Add helper functions in `hermes_skill.py`:

```python
def _build_evidence_manifest(repo_analysis: dict) -> dict:
    return {
        "schema_version": 1,
        "repo_name": repo_analysis.get("repo_name"),
        "description": repo_analysis.get("description"),
        "safe_files": repo_analysis.get("key_files", []),
        "components": repo_analysis.get("components", []),
    }


def _brief_to_manifest(brief) -> dict:
    return {
        "schema_version": 1,
        "style": getattr(brief, "style", ""),
        "title": getattr(brief, "title", ""),
        "hook": getattr(brief, "hook", ""),
        "distribution_channel": getattr(brief, "distribution_channel", "x_short"),
        "reference_pack": getattr(brief, "reference_pack", []),
        "visual_world": getattr(brief, "visual_world", ""),
        "motion_principles": getattr(brief, "motion_principles", []),
        "shot_list": getattr(brief, "shot_list", []),
        "continuity_rules": getattr(brief, "continuity_rules", []),
        "negative_prompts": getattr(brief, "negative_prompts", []),
        "scenes": getattr(brief, "scenes", []),
        "music_mood": getattr(brief, "music_mood", ""),
        "total_duration": getattr(brief, "total_duration", 0),
    }
```

- [ ] **Step 6: Run QA before render**

After preview/final scene adjustments:

```python
brief_manifest = _brief_to_manifest(brief)
qa_report = score_creative_plan(brief_manifest, design_profile=design_profile)
if final and not qa_report["allowed_to_publish"]:
    defects = ", ".join(issue["defect"] for issue in qa_report["blocking_issues"])
    raise RuntimeError(f"Taste QA failed before render: {defects}")
```

For preview, write the report but do not raise.

- [ ] **Step 7: Write production manifests**

After `run_dir.mkdir(...)` and after `qa_report` exists:

```python
production_paths = write_production_manifests(
    run_dir,
    design_profile=design_profile,
    reference_pack=reference_pack,
    evidence_manifest=_build_evidence_manifest(repo_analysis),
    creative_brief=brief_manifest,
    scene_plan={"schema_version": 1, "scenes": brief.scenes},
    asset_manifest={"schema_version": 1, "assets": []},
    audio_plan={
        "schema_version": 1,
        "mode": "skipped" if skip_audio else "voiceover_with_ducked_music",
        "tts_provider": tts_provider,
        "fallback_tts_provider": fallback_tts_provider,
        "generated_music": generated_music,
    },
    qa_report=qa_report,
)
```

Include the relative production paths in `metadata["artifacts"]`.

- [ ] **Step 8: Run focused tests**

```bash
.venv/bin/python -m pytest tests/test_hermes_skill.py tests/test_taste.py tests/test_taste_qa.py tests/test_production.py -q
```

Expected: pass.

- [ ] **Step 9: Commit**

```bash
git add src/repo_to_shorts/hermes_skill.py tests/test_hermes_skill.py
git commit -m "feat: integrate taste manifests into creative pipeline"
```

---

### Task 7: Preview Comparison Mode

**Files:**
- Modify: `src/repo_to_shorts/hermes_skill.py`
- Modify: `src/repo_to_shorts/cli.py`
- Modify: `tests/test_hermes_skill.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add tests for candidate scoring**

Add to `tests/test_hermes_skill.py`:

```python
def test_select_best_preview_candidate_uses_qa_score():
    from repo_to_shorts.hermes_skill import _select_best_preview_candidate

    weak = _final_brief(title="Weak", scenes=[
        {"type": "Card", "headline": "INTRODUCING SEAMLESS AI POWERED WORKFLOW", "duration_seconds": 4, "evidence": []}
    ])
    strong = _final_brief(title="Strong")

    chosen, report = _select_best_preview_candidate([weak, strong], design_profile={})

    assert chosen.title == "Strong"
    assert report["candidate_count"] == 2
    assert report["selected_index"] == 1
```

- [ ] **Step 2: Add CLI test for flag**

In `tests/test_cli.py`, add a test matching the existing CLI runner style:

```python
def test_creative_accepts_compare_previews_flag(monkeypatch, tmp_path):
    calls = []

    def fake_run_creative_pipeline(target, **kwargs):
        calls.append({"target": target, **kwargs})
        return {"run_dir": str(tmp_path), "output": str(tmp_path / "demo.mp4")}

    monkeypatch.setattr("repo_to_shorts.cli.run_creative_pipeline", fake_run_creative_pipeline)
    result = runner.invoke(app, ["creative", ".", "--compare-previews"])

    assert result.exit_code == 0
    assert calls[0]["compare_previews"] is True
```

- [ ] **Step 3: Implement helper**

In `hermes_skill.py`:

```python
def _select_best_preview_candidate(candidates: list, design_profile: dict) -> tuple[object, dict]:
    scored = []
    for index, candidate in enumerate(candidates):
        report = score_creative_plan(_brief_to_manifest(candidate), design_profile=design_profile)
        scored.append((float(report["score"]), index, candidate, report))
    scored.sort(key=lambda item: item[0], reverse=True)
    score, index, candidate, report = scored[0]
    return candidate, {
        "schema_version": 1,
        "candidate_count": len(candidates),
        "selected_index": index,
        "selected_score": score,
        "candidates": [item[3] for item in scored],
    }
```

- [ ] **Step 4: Add `compare_previews` pipeline argument**

Add `compare_previews: bool = False` to `run_creative_pipeline(...)`.

MVP behavior: do not call Kimi multiple times yet. Create deterministic candidate variants from the first brief:

```python
if compare_previews and preview:
    candidates = [brief, _make_concise_candidate(brief), _make_proof_first_candidate(brief)]
    brief, comparison_report = _select_best_preview_candidate(candidates, design_profile)
else:
    comparison_report = None
```

Implement the two candidate helpers as shallow copies that adjust titles/headlines/evidence only.

- [ ] **Step 5: Add CLI flag**

In `src/repo_to_shorts/cli.py`, add:

```python
compare_previews: bool = typer.Option(False, "--compare-previews", help="Generate and score preview concept variants before rendering."),
```

Pass `compare_previews=compare_previews`.

- [ ] **Step 6: Include comparison report in production manifests**

If `comparison_report` exists, write it into `production/qa_report.json` under `preview_comparison`.

- [ ] **Step 7: Run tests**

```bash
.venv/bin/python -m pytest tests/test_hermes_skill.py tests/test_cli.py -q
```

Expected: pass.

- [ ] **Step 8: Commit**

```bash
git add src/repo_to_shorts/hermes_skill.py src/repo_to_shorts/cli.py tests/test_hermes_skill.py tests/test_cli.py
git commit -m "feat: add preview comparison scoring"
```

---

### Task 8: Documentation And Final Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-05-04-hermes-creative-agency-design.md` only if implementation discoveries require a correction.
- Keep: `DESIGN.md`
- Keep: `docs/taste-research.md`

- [ ] **Step 1: Update README mode language**

Add or update a section that distinguishes:

- deterministic package mode
- preview video mode
- final video mode
- taste QA / production manifest outputs

Mention:

```text
runs/<timestamp>/production/design_profile.json
runs/<timestamp>/production/reference_pack.json
runs/<timestamp>/production/qa_report.json
```

- [ ] **Step 2: Add usage examples**

Add:

```bash
repo-shorts creative . --preview --skip-audio
repo-shorts creative . --preview --compare-previews
repo-shorts creative . --final --tts-provider xai --fallback-tts-provider openai
```

- [ ] **Step 3: Run full verification**

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
rg -n "sk-or-v1|OPENROUTER_API_KEY=.*sk|KIMI_API_KEY=.*sk|OPENAI_API_KEY=.*sk|XAI_API_KEY=.*[A-Za-z0-9]|[A-Za-z0-9_\-]{40,}" . --glob '!runs/**' --glob '!.venv/**' --glob '!node_modules/**'
git status --short
```

Expected:

- pytest passes
- ruff passes
- secret scan has no real secrets; inspect any false positives manually
- only intended files are modified

- [ ] **Step 4: Commit**

```bash
git add README.md DESIGN.md docs/taste-research.md docs/superpowers/specs/2026-05-04-hermes-creative-agency-design.md
git commit -m "docs: document creative agency taste system"
```

---

## Recommended Execution Order

1. Task 1: truthful web states.
2. Task 2: taste profile loader.
3. Task 3: production manifests.
4. Task 4: Kimi brief contract.
5. Task 5: deterministic taste QA.
6. Task 6: integration into the creative pipeline.
7. Task 7: preview comparison.
8. Task 8: docs and full verification.

If time is tight, stop after Task 6. That gives the product the core "taste as a system" substrate without adding preview comparison UI/CLI polish yet.

## Acceptance Criteria

- Website no longer says "BROADCAST COMPLETE" for validation-failed previews.
- SP/LP/EP and DOLBY/OFF toggles actually control submitted hidden fields.
- Final web mode passes `final=True` into `run_creative_pipeline`.
- Creative runs write `production/design_profile.json`, `production/reference_pack.json`, `production/evidence_manifest.json`, `production/creative_brief.json`, `production/scene_plan.json`, `production/asset_manifest.json`, `production/audio_plan.json`, and `production/qa_report.json`.
- Kimi prompt and parsed `CreativeBrief` include reference/taste/pre-production fields.
- Taste QA report uses structured `defect`, `evidence`, `fix` issues.
- Final mode refuses publishable success when deterministic validation or taste QA fails.
- Preview mode may complete as a draft, but validation and QA failures are visible.
- README accurately distinguishes deterministic, preview, and final modes.
- Full test and ruff suite pass.
