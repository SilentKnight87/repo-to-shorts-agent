# Taste QA Feedback Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the permissive taste heuristic with a real QA feedback loop that blocks hallucinated claims, catches weak creative metadata, retries Kimi with actionable feedback, and preserves QA artifacts on failure.

**Architecture:** Keep `repo-shorts creative` as the production path. Add a deterministic evidence manifest and strict pre-render QA in Python, then add a bounded Kimi revision loop before rendering. After render, run artifact QA over metadata, media validation, Remotion input, and sampled frame/contact-sheet artifacts. Hermes can orchestrate this as a dedicated Taste QA agent, but the CLI must enforce the same gates locally so it is reliable without manual review.

**Tech Stack:** Python 3.13, Typer, stdlib JSON/path handling, existing OpenRouter/Kimi adapter, existing Remotion/Pillow/ffmpeg paths, pytest, Ruff.

---

## Why This Plan Exists

The live Kimi taste test produced a technically valid video package, but QA incorrectly passed it with score `1.0` even though:

- `creative_brief.title` was `"Untitled"`.
- `creative_brief.hook` was empty.
- The CTA headline was `NPM RUN BUILD-SHORT`, which is not this repo's public CLI.
- The CTA evidence claimed `output folder: ./dist/shorts/`, which is not this pipeline's output path.

The current `taste_qa.py` judges the shape of a plan. The next build must judge truth and taste against source evidence.

## Ground Rules For OpenCode

- Do not remove live Kimi proof or media validation behavior.
- Do not fake `live-api`; Kimi metadata must remain honest.
- Do not make tests call the network.
- Do not commit `runs/`, `.env`, caches, audio files, or generated media.
- Do not rely on a single LLM judge for factual truth. Deterministic checks must catch invalid commands, invalid artifact names, empty titles, and empty hooks.
- Always write `production/qa_report.json` and `production/revision_history.json` when a run directory exists.
- If final QA fails after all retries, fail loudly and preserve the run directory.
- Keep retry count small: default `max_revisions=2`.

## File Structure

- Modify `src/repo_to_shorts/taste_qa.py`
  - Replace loose proof-term matching with a structured evidence-aware QA contract.
  - Add pre-render brief QA and post-render artifact QA.
- Modify `src/repo_to_shorts/hermes_skill.py`
  - Build a stronger evidence manifest.
  - Run Kimi in a bounded generate -> QA -> revise loop.
  - Write failure QA artifacts before raising.
- Modify `src/repo_to_shorts/creative_director.py`
  - Add a revision prompt path that sends QA feedback and allowed evidence back to Kimi.
- Modify `src/repo_to_shorts/production.py`
  - Add `revision_history.json` to production manifests.
- Modify `src/repo_to_shorts/cli.py`
  - Add `--max-revisions` and pass it into the creative pipeline.
  - Ensure command provenance records taste/QA flags.
- Add/modify tests:
  - `tests/test_taste_qa.py`
  - `tests/test_hermes_skill.py`
  - `tests/test_creative_director.py`
  - `tests/test_production.py`
  - `tests/test_cli.py`

---

### Task 1: Build A Deterministic Evidence Manifest

**Files:**
- Modify: `src/repo_to_shorts/hermes_skill.py`
- Modify: `tests/test_hermes_skill.py`

- [ ] **Step 1: Write failing tests for truth-source evidence**

Add these tests to `tests/test_hermes_skill.py`:

```python
def test_build_evidence_manifest_includes_allowed_commands_and_artifacts():
    from repo_to_shorts.hermes_skill import _build_evidence_manifest

    repo_analysis = {
        "repo_name": "repo-to-shorts-agent",
        "description": "Turns repos into short-video packages.",
        "key_files": ["README.md", "src/repo_to_shorts/cli.py", "tests/test_cli.py"],
        "components": ["Cli", "Pipeline", "Render"],
    }

    manifest = _build_evidence_manifest(repo_analysis)

    assert manifest["schema_version"] == 2
    assert "repo-shorts creative . --final" in manifest["allowed_commands"]
    assert "repo-shorts analyze . --out runs" in manifest["allowed_commands"]
    assert "demo.mp4" in manifest["allowed_artifacts"]
    assert "metadata.json" in manifest["allowed_artifacts"]
    assert "captions.srt" in manifest["allowed_artifacts"]
    assert "submission_pack.md" in manifest["allowed_artifacts"]
    assert "README.md" in manifest["allowed_files"]
    assert "src/repo_to_shorts/cli.py" in manifest["allowed_files"]
    assert "./dist/shorts/" not in manifest["allowed_output_paths"]
    assert "runs/<timestamp>-repo-to-shorts-agent/" in manifest["allowed_output_paths"]
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_hermes_skill.py::test_build_evidence_manifest_includes_allowed_commands_and_artifacts -q
```

Expected: FAIL because `_build_evidence_manifest()` currently emits schema version `1` and lacks allowed command/artifact/output path fields.

- [ ] **Step 3: Implement evidence manifest version 2**

Replace `_build_evidence_manifest()` in `src/repo_to_shorts/hermes_skill.py` with:

```python
def _build_evidence_manifest(repo_analysis: dict) -> dict:
    repo_name = str(repo_analysis.get("repo_name") or "repo").strip() or "repo"
    safe_files = list(repo_analysis.get("key_files") or [])
    components = list(repo_analysis.get("components") or [])
    return {
        "schema_version": 2,
        "repo_name": repo_name,
        "description": repo_analysis.get("description"),
        "allowed_files": safe_files,
        "allowed_components": components,
        "allowed_artifacts": [
            "demo.mp4",
            "metadata.json",
            "captions.srt",
            "submission_pack.md",
            "production/design_profile.json",
            "production/reference_pack.json",
            "production/evidence_manifest.json",
            "production/creative_brief.json",
            "production/scene_plan.json",
            "production/asset_manifest.json",
            "production/audio_plan.json",
            "production/qa_report.json",
            "production/revision_history.json",
        ],
        "allowed_commands": [
            "repo-shorts creative . --final",
            "repo-shorts creative . --preview --skip-audio",
            "repo-shorts creative . --preview --compare-previews",
            "repo-shorts analyze . --out runs",
        ],
        "allowed_output_paths": [
            f"runs/<timestamp>-{_slug(repo_name)}/",
            "runs/<timestamp>-<repo>/",
        ],
        "forbidden_claims": [
            "npm run build-short",
            "./dist/shorts/",
            "external publishing",
            "auto-posted to X",
            "uploaded to Discord",
        ],
    }
```

- [ ] **Step 4: Run test to verify pass**

Run:

```bash
.venv/bin/python -m pytest tests/test_hermes_skill.py::test_build_evidence_manifest_includes_allowed_commands_and_artifacts -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/repo_to_shorts/hermes_skill.py tests/test_hermes_skill.py
git commit -m "feat: build strict creative evidence manifest"
```

---

### Task 2: Replace Loose Taste QA With Evidence-Aware Brief QA

**Files:**
- Modify: `src/repo_to_shorts/taste_qa.py`
- Modify: `tests/test_taste_qa.py`

- [ ] **Step 1: Write failing tests for title, hook, and hallucinated CTA**

Add these tests to `tests/test_taste_qa.py`:

```python
def _evidence_manifest() -> dict:
    return {
        "schema_version": 2,
        "repo_name": "repo-to-shorts-agent",
        "allowed_files": ["README.md", "src/repo_to_shorts/cli.py"],
        "allowed_artifacts": ["demo.mp4", "metadata.json", "captions.srt", "submission_pack.md"],
        "allowed_commands": ["repo-shorts creative . --final", "repo-shorts analyze . --out runs"],
        "allowed_output_paths": ["runs/<timestamp>-repo-to-shorts-agent/"],
        "forbidden_claims": ["npm run build-short", "./dist/shorts/"],
    }


def test_score_creative_plan_blocks_untitled_empty_hook_and_fake_cta():
    brief = {
        "title": "Untitled",
        "hook": "",
        "scenes": [
            {"type": "ColdOpen", "headline": "THIS REPO MADE THIS VIDEO", "duration_seconds": 5, "evidence": ["README.md"]},
            {"type": "PipelineMap", "headline": "REPO BRIEF SCENES RENDER SHIP", "duration_seconds": 10, "evidence": ["src/repo_to_shorts/cli.py"]},
            {"type": "LiveProof", "headline": "PROOF IS IN METADATA.JSON", "duration_seconds": 7.5, "evidence": ["metadata.json"]},
            {"type": "ArtifactStack", "headline": "MP4 CAPTIONS SUBMISSION COPY", "duration_seconds": 10, "evidence": ["demo.mp4", "captions.srt"]},
            {"type": "CTAEndCard", "headline": "NPM RUN BUILD-SHORT", "duration_seconds": 5, "evidence": ["output folder: ./dist/shorts/"]},
        ],
    }

    report = score_creative_plan(brief, evidence_manifest=_evidence_manifest(), mode="final")

    assert report["allowed_to_publish"] is False
    defects = {issue["defect"] for issue in report["blocking_issues"]}
    assert "missing_title" in defects
    assert "missing_hook" in defects
    assert "invalid_cta_command" in defects
    assert "unsupported_evidence" in defects
    assert report["revision_prompt"]


def test_score_creative_plan_accepts_real_cli_cta_and_evidence():
    brief = {
        "title": "Repo-to-Shorts Turns Code Into Launch Video",
        "hook": "A repo becomes a validated short-video package.",
        "scenes": [
            {"type": "ColdOpen", "headline": "THIS REPO MADE THIS VIDEO", "duration_seconds": 5, "evidence": ["README.md"]},
            {"type": "PipelineMap", "headline": "KIMI READS THE REPO", "duration_seconds": 10, "evidence": ["src/repo_to_shorts/cli.py"]},
            {"type": "LiveProof", "headline": "PROOF IS IN METADATA.JSON", "duration_seconds": 7.5, "evidence": ["metadata.json"]},
            {"type": "ArtifactStack", "headline": "MP4 CAPTIONS SUBMISSION COPY", "duration_seconds": 10, "evidence": ["demo.mp4", "captions.srt"]},
            {"type": "CTAEndCard", "headline": "REPO-SHORTS CREATIVE DOT FINAL", "duration_seconds": 5, "evidence": ["repo-shorts creative . --final"]},
        ],
    }

    report = score_creative_plan(brief, evidence_manifest=_evidence_manifest(), mode="final")

    assert report["overall"] == "pass"
    assert report["allowed_to_publish"] is True
    assert report["blocking_issues"] == []
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_taste_qa.py -q
```

Expected: FAIL because `score_creative_plan()` does not accept `evidence_manifest`, does not check title/hook, and allows `"repo"` as specificity.

- [ ] **Step 3: Replace `score_creative_plan()` signature and report shape**

In `src/repo_to_shorts/taste_qa.py`, change the signature to:

```python
def score_creative_plan(
    brief: dict[str, Any],
    *,
    design_profile: dict[str, Any] | None = None,
    evidence_manifest: dict[str, Any] | None = None,
    mode: str = "final",
) -> dict[str, Any]:
```

Return this shape:

```python
return {
    "schema_version": 2,
    "mode": mode,
    "overall": "pass" if not blocking and weighted >= 0.8 else "fail",
    "score": weighted,
    "blocking_issues": blocking,
    "taste_issues": taste,
    "factual_issues": factual,
    "visual_issues": visual,
    "revision_prompt": _revision_prompt(blocking + factual + taste + visual),
    "allowed_to_publish": not blocking and not factual and weighted >= 0.8,
}
```

- [ ] **Step 4: Implement deterministic title and hook checks**

Add:

```python
def _valid_text(value: object, *, min_words: int = 3) -> bool:
    text = str(value or "").strip()
    if not text or text.lower() in {"untitled", "title", "draft"}:
        return False
    return len(text.split()) >= min_words
```

Inside `score_creative_plan()`:

```python
if mode == "final" and not _valid_text(brief.get("title"), min_words=4):
    blocking.append(_issue("missing_title", "Creative brief title is empty, generic, or still Untitled", "Write a repo-specific title with the product name and transformation."))
if mode == "final" and not _valid_text(brief.get("hook"), min_words=5):
    blocking.append(_issue("missing_hook", "Creative brief hook is empty or too thin", "Write a concrete one-sentence hook that explains the repo transformation."))
```

- [ ] **Step 5: Implement evidence normalization and exact evidence checks**

Add:

```python
def _allowed_evidence(evidence_manifest: dict[str, Any] | None) -> set[str]:
    if not evidence_manifest:
        return set()
    values: set[str] = set()
    for key in ("allowed_files", "allowed_artifacts", "allowed_commands", "allowed_output_paths", "allowed_components"):
        for item in evidence_manifest.get(key, []) or []:
            values.add(str(item).lower())
    repo_name = evidence_manifest.get("repo_name")
    if repo_name:
        values.add(f"repo_name: {repo_name}".lower())
        values.add(str(repo_name).lower())
    return values


def _scene_evidence_values(scene: dict[str, Any]) -> list[str]:
    raw = scene.get("evidence") or []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(item) for item in raw if str(item).strip()]
    return []


def _evidence_supported(value: str, allowed: set[str]) -> bool:
    lowered = value.lower().strip()
    if lowered in allowed:
        return True
    return any(token in lowered for token in allowed if token and token in {"metadata.json", "demo.mp4", "captions.srt", "submission_pack.md"})
```

Inside `score_creative_plan()`:

```python
allowed = _allowed_evidence(evidence_manifest)
if mode == "final":
    unsupported = []
    for index, scene in enumerate(scenes, start=1):
        evidence = _scene_evidence_values(scene)
        if not evidence:
            unsupported.append(f"scene {index}: no evidence")
            continue
        for value in evidence:
            if allowed and not _evidence_supported(value, allowed):
                unsupported.append(f"scene {index}: {value}")
    if unsupported:
        factual.append(_issue("unsupported_evidence", "; ".join(unsupported[:5]), "Use only evidence from production/evidence_manifest.json."))
```

- [ ] **Step 6: Implement CTA command validation**

Add:

```python
def _cta_scene(scenes: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((scene for scene in scenes if str(scene.get("type", "")).lower() == "ctaendcard"), None)


def _contains_allowed_command(text: str, evidence_manifest: dict[str, Any] | None) -> bool:
    lowered = text.lower()
    commands = [str(cmd).lower() for cmd in (evidence_manifest or {}).get("allowed_commands", [])]
    return any(cmd in lowered for cmd in commands)


def _contains_forbidden_claim(text: str, evidence_manifest: dict[str, Any] | None) -> str | None:
    lowered = text.lower()
    for claim in (evidence_manifest or {}).get("forbidden_claims", []) or []:
        claim_text = str(claim).lower()
        if claim_text and claim_text in lowered:
            return str(claim)
    return None
```

Inside `score_creative_plan()`:

```python
cta = _cta_scene(scenes)
if mode == "final" and cta:
    cta_text = " ".join([str(cta.get("headline", "")), str(cta.get("narration", "")), " ".join(_scene_evidence_values(cta))])
    forbidden = _contains_forbidden_claim(cta_text, evidence_manifest)
    if forbidden:
        factual.append(_issue("invalid_cta_command", f"CTA contains forbidden claim: {forbidden}", "Use the real repo-shorts creative/analyze CLI command."))
    elif not _contains_allowed_command(cta_text, evidence_manifest):
        factual.append(_issue("invalid_cta_command", "CTA does not include an allowed command", "Use one command from evidence_manifest.allowed_commands."))
```

- [ ] **Step 7: Remove `"repo"` as a proof term**

Delete `PROOF_TERMS` or reduce it to exact artifact/file evidence only. Do not let the word `"repo"` satisfy specificity by itself.

- [ ] **Step 8: Implement revision prompt builder**

Add:

```python
def _revision_prompt(issues: list[dict[str, str]]) -> str:
    if not issues:
        return ""
    lines = ["Revise the creative brief. Fix these QA failures without adding unsupported claims:"]
    for issue in issues[:8]:
        lines.append(f"- {issue['defect']}: {issue['evidence']} Fix: {issue['fix']}")
    return "\n".join(lines)
```

- [ ] **Step 9: Run tests to verify pass**

Run:

```bash
.venv/bin/python -m pytest tests/test_taste_qa.py -q
```

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add src/repo_to_shorts/taste_qa.py tests/test_taste_qa.py
git commit -m "feat: enforce evidence-aware taste qa"
```

---

### Task 3: Add Kimi Revision Prompt Support

**Files:**
- Modify: `src/repo_to_shorts/creative_director.py`
- Modify: `tests/test_creative_director.py`

- [ ] **Step 1: Write failing test for revision prompt injection**

Add this test to `tests/test_creative_director.py`:

```python
def test_director_prompt_includes_revision_feedback_and_allowed_evidence():
    prompt = _build_director_prompt(
        {
            "repo_name": "repo-to-shorts-agent",
            "description": "Turns repos into videos.",
            "key_files": ["README.md"],
            "components": ["Cli"],
        },
        model="moonshotai/kimi-k2.6",
        final=True,
        design_profile={"schema_version": 1},
        reference_pack={"schema_version": 1},
        revision_feedback="invalid_cta_command: use repo-shorts creative . --final",
        evidence_manifest={
            "allowed_commands": ["repo-shorts creative . --final"],
            "allowed_artifacts": ["demo.mp4", "metadata.json"],
            "allowed_files": ["README.md"],
            "forbidden_claims": ["npm run build-short"],
        },
    )

    assert "REVISION FEEDBACK" in prompt
    assert "invalid_cta_command" in prompt
    assert "ALLOWED EVIDENCE" in prompt
    assert "repo-shorts creative . --final" in prompt
    assert "npm run build-short" in prompt
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_creative_director.py::test_director_prompt_includes_revision_feedback_and_allowed_evidence -q
```

Expected: FAIL because `_build_director_prompt()` has no revision/evidence parameters.

- [ ] **Step 3: Extend `direct()` and `_build_director_prompt()` signatures**

In `src/repo_to_shorts/creative_director.py`, update:

```python
def direct(
    repo_analysis: dict,
    *,
    model: str = "moonshotai/kimi-k2.6",
    final: bool = False,
    design_profile: dict | None = None,
    reference_pack: dict | None = None,
    revision_feedback: str | None = None,
    evidence_manifest: dict | None = None,
) -> CreativeBrief:
```

Update `_build_director_prompt()` with the same new keyword-only arguments.

- [ ] **Step 4: Pass new arguments from `direct()` into `_build_director_prompt()`**

Use:

```python
prompt = _build_director_prompt(
    repo_analysis,
    model=model,
    final=final,
    design_profile=design_profile,
    reference_pack=reference_pack,
    revision_feedback=revision_feedback,
    evidence_manifest=evidence_manifest,
)
```

- [ ] **Step 5: Append revision/evidence block to the prompt**

Near the existing design/reference block, add:

```python
    if evidence_manifest:
        evidence_context = json.dumps(evidence_manifest, indent=2)[:4000]
        prompt += f"""

ALLOWED EVIDENCE:
{evidence_context}

Factuality rules:
- Use only commands, artifacts, files, and output paths listed in ALLOWED EVIDENCE.
- Do not invent npm scripts, output folders, publishing steps, integrations, or files.
- CTAEndCard must cite one allowed command exactly.
"""
    if revision_feedback:
        prompt += f"""

REVISION FEEDBACK:
{revision_feedback}

Revise the JSON response to fix every QA failure. Do not remove source evidence. Do not add unsupported claims.
"""
```

- [ ] **Step 6: Run test to verify pass**

Run:

```bash
.venv/bin/python -m pytest tests/test_creative_director.py::test_director_prompt_includes_revision_feedback_and_allowed_evidence -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/repo_to_shorts/creative_director.py tests/test_creative_director.py
git commit -m "feat: add kimi qa revision prompt"
```

---

### Task 4: Add Bounded Pre-Render QA Revision Loop

**Files:**
- Modify: `src/repo_to_shorts/hermes_skill.py`
- Modify: `src/repo_to_shorts/cli.py`
- Modify: `tests/test_hermes_skill.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing pipeline test for Kimi retry on QA failure**

Add this test to `tests/test_hermes_skill.py`:

```python
@patch("repo_to_shorts.hermes_skill.validate_media")
@patch("repo_to_shorts.hermes_skill.ingest_target")
@patch("repo_to_shorts.hermes_skill.direct")
@patch("repo_to_shorts.hermes_skill.generate_manim_script")
@patch("repo_to_shorts.hermes_skill.render_scene")
@patch("repo_to_shorts.hermes_skill._merge_creative_video")
def test_run_creative_pipeline_revises_brief_after_qa_failure(
    mock_merge,
    mock_render,
    mock_script,
    mock_direct,
    mock_ingest,
    mock_validate,
    tmp_path: Path,
):
    bad = _final_brief(
        title="Untitled",
        hook="",
        scenes=[
            {"type": "ColdOpen", "headline": "THIS REPO MADE THIS VIDEO", "duration_seconds": 5, "evidence": ["README.md"]},
            {"type": "PipelineMap", "headline": "REPO BRIEF SCENES RENDER SHIP", "duration_seconds": 10, "evidence": ["src/repo_to_shorts/cli.py"]},
            {"type": "LiveProof", "headline": "PROOF IS IN METADATA.JSON", "duration_seconds": 7.5, "evidence": ["metadata.json"]},
            {"type": "ArtifactStack", "headline": "MP4 CAPTIONS SUBMISSION COPY", "duration_seconds": 10, "evidence": ["demo.mp4"]},
            {"type": "CTAEndCard", "headline": "NPM RUN BUILD-SHORT", "duration_seconds": 5, "evidence": ["output folder: ./dist/shorts/"]},
        ],
    )
    good = _final_brief(
        title="Repo-to-Shorts Turns Code Into Launch Video",
        hook="A repo becomes a validated short-video package.",
        scenes=[
            {"type": "ColdOpen", "headline": "THIS REPO MADE THIS VIDEO", "duration_seconds": 5, "evidence": ["README.md"]},
            {"type": "PipelineMap", "headline": "KIMI READS THE REPO", "duration_seconds": 10, "evidence": ["src/repo_to_shorts/cli.py"]},
            {"type": "LiveProof", "headline": "PROOF IS IN METADATA.JSON", "duration_seconds": 7.5, "evidence": ["metadata.json"]},
            {"type": "ArtifactStack", "headline": "MP4 CAPTIONS SUBMISSION COPY", "duration_seconds": 10, "evidence": ["demo.mp4", "captions.srt"]},
            {"type": "CTAEndCard", "headline": "REPO-SHORTS CREATIVE DOT FINAL", "duration_seconds": 5, "evidence": ["repo-shorts creative . --final"]},
        ],
    )
    mock_direct.side_effect = [bad, good]
    mock_ingest.return_value = FakeSnapshot()
    mock_script.return_value = tmp_path / "script.json"
    raw = tmp_path / "video.mp4"
    raw.write_bytes(b"raw")
    mock_render.return_value = raw
    mock_validate.return_value = {"ok": True, "duration_seconds": 45, "resolution": "1080x1920", "has_audio": True, "errors": []}

    result = run_creative_pipeline(".", out_dir=tmp_path, final=True, tts_provider="none", max_revisions=2)

    assert Path(result["run_dir"]).exists()
    assert mock_direct.call_count == 2
    assert "invalid_cta_command" in mock_direct.call_args_list[1].kwargs["revision_feedback"]
    revision_history = json.loads((Path(result["run_dir"]) / "production" / "revision_history.json").read_text(encoding="utf-8"))
    assert len(revision_history["attempts"]) == 2
    assert revision_history["attempts"][0]["qa"]["allowed_to_publish"] is False
    assert revision_history["attempts"][1]["qa"]["allowed_to_publish"] is True
```

- [ ] **Step 2: Write failing CLI test for `--max-revisions`**

Add this to `tests/test_cli.py`:

```python
def test_creative_passes_max_revisions(monkeypatch, tmp_path):
    seen = {}

    def fake_run_creative_pipeline(*args, **kwargs):
        seen.update(kwargs)
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        return {"output": str(run_dir / "demo.mp4"), "run_dir": str(run_dir)}

    monkeypatch.setattr("repo_to_shorts.hermes_skill.run_creative_pipeline", fake_run_creative_pipeline)

    result = runner.invoke(app, ["creative", ".", "--out", str(tmp_path), "--max-revisions", "1"])

    assert result.exit_code == 0
    assert seen["max_revisions"] == 1
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_hermes_skill.py::test_run_creative_pipeline_revises_brief_after_qa_failure tests/test_cli.py::test_creative_passes_max_revisions -q
```

Expected: FAIL because `run_creative_pipeline()` and CLI do not accept `max_revisions`.

- [ ] **Step 4: Add `max_revisions` to CLI and pipeline signatures**

In `src/repo_to_shorts/cli.py`, add option:

```python
max_revisions: int = typer.Option(2, "--max-revisions", min=0, max=5, help="Maximum Kimi QA revision attempts before final failure."),
```

Append to command provenance:

```python
if max_revisions != 2:
    command.extend(["--max-revisions", str(max_revisions)])
if compare_previews:
    command.append("--compare-previews")
```

Pass `max_revisions=max_revisions` to `run_creative_pipeline()`.

In `src/repo_to_shorts/hermes_skill.py`, update:

```python
def run_creative_pipeline(..., compare_previews: bool = False, max_revisions: int = 2) -> dict:
```

- [ ] **Step 5: Add revision loop helper**

Add this helper to `src/repo_to_shorts/hermes_skill.py`:

```python
def _direct_with_qa_revisions(
    repo_analysis: dict,
    *,
    kimi_model: str | None,
    final: bool,
    design_profile: dict,
    reference_pack: dict,
    evidence_manifest: dict,
    max_revisions: int,
) -> tuple[object, dict, list[dict]]:
    attempts: list[dict] = []
    revision_feedback: str | None = None
    total_attempts = max(1, max_revisions + 1)
    for attempt_number in range(1, total_attempts + 1):
        brief = direct(
            repo_analysis,
            model=kimi_model or "moonshotai/kimi-k2.6",
            final=final,
            design_profile=design_profile,
            reference_pack=reference_pack,
            revision_feedback=revision_feedback,
            evidence_manifest=evidence_manifest,
        )
        brief_manifest = _brief_to_manifest(brief)
        qa_report = score_creative_plan(
            brief_manifest,
            design_profile=design_profile,
            evidence_manifest=evidence_manifest,
            mode="final" if final else "preview",
        )
        attempts.append({
            "attempt": attempt_number,
            "title": brief_manifest.get("title"),
            "qa": qa_report,
        })
        if not final or qa_report["allowed_to_publish"]:
            return brief, qa_report, attempts
        revision_feedback = qa_report.get("revision_prompt") or "Revise the brief to satisfy QA."
    return brief, qa_report, attempts
```

- [ ] **Step 6: Use revision loop in `run_creative_pipeline()`**

Replace the direct call block with:

```python
evidence_manifest = _build_evidence_manifest(repo_analysis)
brief, qa_report, revision_history = _direct_with_qa_revisions(
    repo_analysis,
    kimi_model=kimi_model,
    final=final,
    design_profile=design_profile,
    reference_pack=reference_pack,
    evidence_manifest=evidence_manifest,
    max_revisions=max_revisions,
)
```

Keep preview truncation after this block, then recompute preview QA if needed:

```python
if preview:
    brief.scenes = _preview_scenes(brief.scenes)
    brief.total_duration = int(sum(float(scene.get("duration_seconds", 4)) for scene in brief.scenes))
    brief_manifest = _brief_to_manifest(brief)
    qa_report = score_creative_plan(brief_manifest, design_profile=design_profile, evidence_manifest=evidence_manifest, mode="preview")
else:
    brief_manifest = _brief_to_manifest(brief)
```

Remove the old standalone `brief_manifest = ...; qa_report = ...` block.

- [ ] **Step 7: Write revision history manifest**

When calling `write_production_manifests()`, pass:

```python
revision_history={"schema_version": 1, "attempts": revision_history},
```

- [ ] **Step 8: Ensure final failure preserves artifacts**

Move `run_dir` creation before the final QA raise. If final QA fails after all retries, write production manifests first:

```python
if final and not qa_report["allowed_to_publish"]:
    write_production_manifests(
        run_dir,
        design_profile=design_profile,
        reference_pack=reference_pack,
        evidence_manifest=evidence_manifest,
        creative_brief=brief_manifest,
        scene_plan={"schema_version": 1, "scenes": brief.scenes},
        asset_manifest={"schema_version": 1, "assets": []},
        audio_plan={"schema_version": 1, "mode": "not_rendered"},
        qa_report=_final_qa_report(qa_report, comparison_report),
        revision_history={"schema_version": 1, "attempts": revision_history},
    )
    defects = ", ".join(issue["defect"] for issue in qa_report["blocking_issues"] + qa_report.get("factual_issues", []))
    raise RuntimeError(f"Taste QA failed before render: {defects}")
```

- [ ] **Step 9: Run targeted tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_hermes_skill.py::test_run_creative_pipeline_revises_brief_after_qa_failure tests/test_cli.py::test_creative_passes_max_revisions -q
```

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add src/repo_to_shorts/hermes_skill.py src/repo_to_shorts/cli.py tests/test_hermes_skill.py tests/test_cli.py
git commit -m "feat: add kimi taste qa revision loop"
```

---

### Task 5: Add Post-Render Artifact QA

**Files:**
- Modify: `src/repo_to_shorts/taste_qa.py`
- Modify: `src/repo_to_shorts/hermes_skill.py`
- Modify: `tests/test_taste_qa.py`
- Modify: `tests/test_hermes_skill.py`

- [ ] **Step 1: Write failing tests for post-render QA**

Add this test to `tests/test_taste_qa.py`:

```python
def test_score_rendered_artifact_blocks_bad_validation_and_missing_metadata():
    from repo_to_shorts.taste_qa import score_rendered_artifact

    report = score_rendered_artifact(
        metadata={
            "creative_brief": {"title": "Untitled", "hook": "", "scenes": []},
            "kimi": {"mode": "live-api"},
            "render": {"validation": {"ok": False, "errors": ["duration must be 43-62 seconds"]}},
            "artifacts": ["demo.mp4"],
        },
        evidence_manifest=_evidence_manifest(),
    )

    assert report["allowed_to_publish"] is False
    defects = {issue["defect"] for issue in report["blocking_issues"]}
    assert "media_validation_failed" in defects
    assert "missing_required_artifact" in defects
    assert "missing_title" in defects
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_taste_qa.py::test_score_rendered_artifact_blocks_bad_validation_and_missing_metadata -q
```

Expected: FAIL because `score_rendered_artifact()` does not exist.

- [ ] **Step 3: Implement `score_rendered_artifact()`**

Add to `src/repo_to_shorts/taste_qa.py`:

```python
def score_rendered_artifact(*, metadata: dict[str, Any], evidence_manifest: dict[str, Any]) -> dict[str, Any]:
    brief = metadata.get("creative_brief") or {}
    brief_report = score_creative_plan(
        brief,
        evidence_manifest=evidence_manifest,
        mode="final",
    )
    blocking = list(brief_report["blocking_issues"])
    factual = list(brief_report.get("factual_issues", []))
    taste = list(brief_report.get("taste_issues", []))
    visual = list(brief_report.get("visual_issues", []))

    validation = ((metadata.get("render") or {}).get("validation") or {})
    if not validation.get("ok"):
        blocking.append(_issue("media_validation_failed", "; ".join(validation.get("errors") or ["media validation failed"]), "Fix render duration, resolution, audio, or file output."))

    artifacts = set(metadata.get("artifacts") or [])
    for required in ("demo.mp4", "metadata.json", "captions.srt", "submission_pack.md", "production/qa_report.json"):
        if required not in artifacts:
            blocking.append(_issue("missing_required_artifact", required, "Add required artifact to metadata.artifacts and write it to the run directory."))

    weighted = _score(blocking + factual, taste + visual)
    return {
        "schema_version": 2,
        "mode": "rendered_artifact",
        "overall": "pass" if not blocking and not factual and weighted >= 0.8 else "fail",
        "score": weighted,
        "blocking_issues": blocking,
        "factual_issues": factual,
        "taste_issues": taste,
        "visual_issues": visual,
        "revision_prompt": _revision_prompt(blocking + factual + taste + visual),
        "allowed_to_publish": not blocking and not factual and weighted >= 0.8,
    }
```

- [ ] **Step 4: Merge post-render QA into final QA report**

In `src/repo_to_shorts/hermes_skill.py`, after `metadata` is built but before `write_production_manifests()`, add:

```python
artifact_qa_report = score_rendered_artifact(metadata=metadata, evidence_manifest=evidence_manifest) if final else qa_report
combined_qa_report = _merge_qa_reports(qa_report, artifact_qa_report)
```

Add helper:

```python
def _merge_qa_reports(pre_render: dict, post_render: dict) -> dict:
    if pre_render is post_render:
        return pre_render
    blocking = list(pre_render.get("blocking_issues", [])) + list(post_render.get("blocking_issues", []))
    factual = list(pre_render.get("factual_issues", [])) + list(post_render.get("factual_issues", []))
    taste = list(pre_render.get("taste_issues", [])) + list(post_render.get("taste_issues", []))
    visual = list(pre_render.get("visual_issues", [])) + list(post_render.get("visual_issues", []))
    score = min(float(pre_render.get("score", 0)), float(post_render.get("score", 0)))
    return {
        "schema_version": 2,
        "mode": "combined",
        "overall": "pass" if not blocking and not factual and score >= 0.8 else "fail",
        "score": score,
        "blocking_issues": blocking,
        "factual_issues": factual,
        "taste_issues": taste,
        "visual_issues": visual,
        "revision_prompt": _revision_prompt(blocking + factual + taste + visual),
        "allowed_to_publish": not blocking and not factual and score >= 0.8,
        "pre_render": pre_render,
        "post_render": post_render,
    }
```

Use `combined_qa_report` in `write_production_manifests(... qa_report=...)`.

- [ ] **Step 5: Block final success if post-render QA fails**

After writing manifests and `metadata.json`, add:

```python
if final and not combined_qa_report["allowed_to_publish"]:
    defects = ", ".join(issue["defect"] for issue in combined_qa_report["blocking_issues"] + combined_qa_report.get("factual_issues", []))
    raise RuntimeError(f"Post-render QA failed: {defects}")
```

- [ ] **Step 6: Run targeted tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_taste_qa.py::test_score_rendered_artifact_blocks_bad_validation_and_missing_metadata tests/test_hermes_skill.py::test_run_creative_pipeline_writes_production_manifests -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/repo_to_shorts/taste_qa.py src/repo_to_shorts/hermes_skill.py tests/test_taste_qa.py tests/test_hermes_skill.py
git commit -m "feat: add post-render artifact qa"
```

---

### Task 6: Add Revision History Production Manifest

**Files:**
- Modify: `src/repo_to_shorts/production.py`
- Modify: `tests/test_production.py`

- [ ] **Step 1: Write failing production manifest test**

Add this assertion to the existing production manifest test:

```python
assert (run_dir / "production" / "revision_history.json").exists()
```

Also assert it is returned:

```python
assert "revision_history.json" in {path.name for path in paths}
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_production.py -q
```

Expected: FAIL because `revision_history.json` is not in `MANIFEST_NAMES`.

- [ ] **Step 3: Add manifest name**

In `src/repo_to_shorts/production.py`, add:

```python
"revision_history": "revision_history.json",
```

to `MANIFEST_NAMES`.

- [ ] **Step 4: Run test to verify pass**

Run:

```bash
.venv/bin/python -m pytest tests/test_production.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/repo_to_shorts/production.py tests/test_production.py
git commit -m "feat: persist creative revision history"
```

---

### Task 7: Add Regression Test For The Exact Live Failure

**Files:**
- Modify: `tests/test_taste_qa.py`

- [ ] **Step 1: Add regression test using the bad live brief**

Add:

```python
def test_score_creative_plan_rejects_live_run_with_untitled_and_fake_npm_cta():
    bad_live_brief = {
        "title": "Untitled",
        "hook": "",
        "scenes": [
            {"type": "ColdOpen", "headline": "THIS REPO MADE THIS VIDEO", "duration_seconds": 5, "evidence": ["repo_name: repo-to-shorts-agent", "README.md exists", "live render pipeline active"]},
            {"type": "PainPoint", "headline": "DEMO VIDEOS EAT SIX HOURS", "duration_seconds": 7.5, "evidence": ["docs/PRD.md"]},
            {"type": "PipelineMap", "headline": "REPO BRIEF SCENES RENDER SHIP", "duration_seconds": 10, "evidence": ["COMPONENTS: Core, CLI, Pipeline, Render"]},
            {"type": "LiveProof", "headline": "PROOF IS IN METADATA.JSON", "duration_seconds": 7.5, "evidence": ["kimi.mode=live-api in metadata.json"]},
            {"type": "ArtifactStack", "headline": "MP4 CAPTIONS NARRATION SUBMISSION COPY", "duration_seconds": 10, "evidence": ["generated artifacts: storyboard, narration, captions, MP4, metadata"]},
            {"type": "CTAEndCard", "headline": "NPM RUN BUILD-SHORT", "duration_seconds": 5, "evidence": ["output folder: ./dist/shorts/"]},
        ],
    }

    report = score_creative_plan(bad_live_brief, evidence_manifest=_evidence_manifest(), mode="final")

    assert report["allowed_to_publish"] is False
    defects = {issue["defect"] for issue in report["blocking_issues"] + report["factual_issues"]}
    assert {"missing_title", "missing_hook", "invalid_cta_command", "unsupported_evidence"} <= defects
```

- [ ] **Step 2: Run regression test**

Run:

```bash
.venv/bin/python -m pytest tests/test_taste_qa.py::test_score_creative_plan_rejects_live_run_with_untitled_and_fake_npm_cta -q
```

Expected: PASS after Tasks 2 and 6.

- [ ] **Step 3: Commit**

```bash
git add tests/test_taste_qa.py
git commit -m "test: cover fake cta taste qa regression"
```

---

### Task 8: Full Verification And Manual Taste Smoke

**Files:**
- No code files unless tests reveal necessary fixes.

- [ ] **Step 1: Run static checks**

Run:

```bash
.venv/bin/ruff check .
```

Expected: `All checks passed!`

- [ ] **Step 2: Run full tests**

Run:

```bash
.venv/bin/python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 3: Run no-key final to verify deterministic fallback behavior is explicit**

Run:

```bash
env -u OPENROUTER_API_KEY -u KIMI_API_KEY .venv/bin/repo-shorts creative . --final --tts-provider none --out /tmp/repo-shorts-no-key-qa
```

Expected: one of these acceptable outcomes:

- PASS if deterministic fallback has been updated to satisfy evidence-aware final QA.
- FAIL with `Taste QA failed before render: ...`, while preserving a run directory with `production/qa_report.json`, `production/evidence_manifest.json`, and `production/revision_history.json`.

Do not accept a failure that leaves no QA artifacts.

- [ ] **Step 4: Run live Kimi final taste smoke**

Use an ignored local `.env` only if it exists. Do not print key values.

```bash
set -a; source .env; set +a; .venv/bin/repo-shorts creative . \
  --audience "Nous Research Hermes Agent Creative Hackathon judges" \
  --final \
  --tts-provider none \
  --out runs
```

Expected:

- `metadata.json` shows `kimi.mode=live-api`.
- `production/qa_report.json` has `allowed_to_publish=true`.
- `creative_brief.title` is not `Untitled`.
- `creative_brief.hook` is not empty.
- CTA scene cites `repo-shorts creative . --final` or another allowed command.
- CTA scene does not cite `NPM RUN BUILD-SHORT` or `./dist/shorts/`.
- `render.validation.ok=true`.

- [ ] **Step 5: Inspect generated QA artifacts**

Run:

```bash
LATEST="$(ls -td runs/*-repo-to-shorts-agent | head -1)"
jq '{title: .creative_brief.title, hook: .creative_brief.hook, cta: .creative_brief.scenes[-1], validation: .render.validation}' "$LATEST/metadata.json"
jq . "$LATEST/production/qa_report.json"
jq . "$LATEST/production/revision_history.json"
```

Expected: QA report explains pass/fail clearly, and revision history shows each Kimi attempt.

- [ ] **Step 6: Commit verification fixes if needed**

If verification revealed fixes, commit them:

```bash
git add src tests
git commit -m "fix: tighten creative qa verification"
```

If no fixes were needed, do not create an empty commit.

---

## Self-Review Checklist

- Spec coverage: This plan covers deterministic evidence, pre-render QA, Kimi retry, post-render QA, revision history, exact live-failure regression, and full verification.
- Placeholder scan: No placeholder markers, deferred validation, or generic "add tests" steps remain.
- Type consistency: `score_creative_plan(... evidence_manifest=..., mode=...)`, `score_rendered_artifact(...)`, `_direct_with_qa_revisions(...)`, and `max_revisions` are consistently named across tests and implementation steps.
- Scope check: This is one vertical slice. It does not attempt full VLM video watching yet; it creates the deterministic and artifact-level QA loop that a future Hermes/VLM judge can plug into.
