# Live Kimi + Render Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Upgrade Repo-to-Shorts from a deterministic browser-recordable package generator into an honest hackathon MVP with live Kimi critique support, Hermes harness positioning, and an optional MP4 render path.

**Architecture:** Keep the current deterministic golden path intact. Add Kimi as a small adapter behind `critique_story()`, with API/fallback metadata. Document and, if possible, demonstrate Hermes running the workflow with Kimi as the selected model. Add rendering as an optional layer that consumes generated run artifacts instead of entangling it with ingestion/story logic.

**Tech Stack:** Python 3.13, Typer, Jinja2, Rich, pytest, Ruff, Hermes Agent CLI/skills, optional OpenAI SDK or HTTP client for Moonshot/Kimi, optional MoviePy/ffmpeg for MP4.

---

## Task 0: Document Hermes harness + two-front Kimi strategy

**Objective:** Make the repo's strategy match Peter's intended positioning: Hermes is the harness, Kimi powers the harness, and Kimi also appears as a product-level critic/editor.

**Files:**
- Create: `docs/HACKATHON_STRATEGY.md`
- Modify: `docs/PRD.md`
- Modify: `README.md`

**Step 1: Write the strategy doc**

Document:
- What Repo-to-Shorts builds.
- Why it maps to creativity/usefulness/presentation.
- The two-front Kimi strategy.
- Hermes creative skills we can leverage.
- The 60-second winning demo structure.

**Step 2: Update PRD**

Add a P0 requirement for Hermes harness positioning.

**Step 3: Update README**

Add a short section linking to `docs/HACKATHON_STRATEGY.md` and explaining:

```text
Kimi reasons. Hermes acts. Repo-to-Shorts packages the output.
```

**Step 4: Verify docs only**

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
```

Expected: PASS.

**Step 5: Commit**

```bash
git add docs/HACKATHON_STRATEGY.md docs/PRD.md docs/plans/2026-05-01-live-kimi-render-plan.md README.md
git commit -m "docs: define hermes kimi hackathon strategy"
```

---

## Task 1: Make Kimi result metadata explicit

**Objective:** Extend `KimiCritique` so downstream metadata can distinguish fallback, configured placeholder, live API, and API failure.

**Files:**
- Modify: `src/repo_to_shorts/kimi.py`
- Modify: `src/repo_to_shorts/pipeline.py`
- Test: `tests/test_pipeline.py`

**Step 1: Write failing test**

Add a test asserting metadata includes `mode`, `model`, and `fallback_reason`.

```python
def test_run_analysis_records_structured_kimi_metadata(tmp_path: Path):
    repo = make_sample_repo(tmp_path)
    run_dir = run_analysis(str(repo), audience="Python builders", out_dir=tmp_path / "runs")

    metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))

    assert metadata["kimi"] == {
        "mode": "deterministic-fallback",
        "model": None,
        "fallback_reason": "KIMI_API_KEY not set",
    }
```

**Step 2: Run test to verify failure**

```bash
.venv/bin/python -m pytest tests/test_pipeline.py::test_run_analysis_records_structured_kimi_metadata -q
```

Expected: FAIL because metadata only has `mode`.

**Step 3: Implement minimal metadata**

Update dataclass:

```python
@dataclass(frozen=True)
class KimiCritique:
    mode: str
    text: str
    model: str | None = None
    fallback_reason: str | None = None
```

Fallback return:

```python
return KimiCritique(
    mode="deterministic-fallback",
    model=None,
    fallback_reason="KIMI_API_KEY not set",
    text=...,
)
```

Pipeline metadata:

```python
"kimi": {
    "mode": kimi.mode,
    "model": kimi.model,
    "fallback_reason": kimi.fallback_reason,
},
```

**Step 4: Run test**

```bash
.venv/bin/python -m pytest tests/test_pipeline.py::test_run_analysis_records_structured_kimi_metadata -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/repo_to_shorts/kimi.py src/repo_to_shorts/pipeline.py tests/test_pipeline.py
git commit -m "feat: record structured kimi metadata"
```

---

## Task 2: Add Kimi prompt builder

**Objective:** Create a deterministic prompt from repo brief, storyboard, and audience.

**Files:**
- Modify: `src/repo_to_shorts/kimi.py`
- Test: `tests/test_pipeline.py` or new `tests/test_kimi.py`

**Step 1: Write failing test**

```python
def test_build_kimi_prompt_includes_repo_audience_and_storyboard(tmp_path: Path):
    snapshot = RepoSnapshot(
        target=".",
        name="sample-repo",
        source_type="local",
        path=tmp_path,
        readme="README text",
        file_tree=["src/app.py"],
        package_metadata={"description": "Does useful things"},
    )

    prompt = build_kimi_prompt(snapshot, "hackathon judges", "# Storyboard\nProof")

    assert "sample-repo" in prompt
    assert "hackathon judges" in prompt
    assert "# Storyboard" in prompt
    assert "Return:" in prompt
```

**Step 2: Run test to verify failure**

Expected: FAIL because `build_kimi_prompt` does not exist.

**Step 3: Implement prompt builder**

```python
def build_kimi_prompt(snapshot: RepoSnapshot, audience: str, storyboard: str) -> str:
    metadata = "\n".join(f"- {k}: {v}" for k, v in snapshot.package_metadata.items()) or "- none"
    tree = "\n".join(f"- {entry}" for entry in snapshot.file_tree[:30]) or "- no files"
    return f"""You are Kimi acting as a creative critic and short-form technical video editor.

Repo: {snapshot.name}
Audience: {audience}

Package metadata:
{metadata}

File tree:
{tree}

README excerpt:
{snapshot.readme[:2000]}

Storyboard:
{storyboard}

Return:
1. Sharper 1-sentence hook.
2. Critique of the current story.
3. Revised 60-second narration.
4. Strong final CTA.
5. Any risky/unclear claims to avoid.
"""
```

**Step 4: Run tests**

Expected: PASS.

**Step 5: Commit**

```bash
git add src/repo_to_shorts/kimi.py tests/test_kimi.py
git commit -m "feat: build kimi editor prompt"
```

---

## Task 3: Wire live Kimi API behind an injectable client

**Objective:** Implement real API support while keeping tests network-free.

**Files:**
- Modify: `src/repo_to_shorts/kimi.py`
- Modify: `pyproject.toml`
- Test: `tests/test_kimi.py`

**Step 1: Choose dependency**

Preferred minimal dependency:

```toml
"openai>=1.0"
```

Reason: Moonshot/Kimi exposes an OpenAI-compatible API.

**Step 2: Write mocked live API test**

Use monkeypatch to replace the OpenAI client factory or a private `_call_kimi_api()` function.

```python
def test_critique_story_uses_live_kimi_when_key_present(monkeypatch, tmp_path: Path):
    snapshot = RepoSnapshot(...)

    def fake_call(prompt: str, model: str) -> str:
        assert "sample-repo" in prompt
        return "# Live Kimi critique\n\nSharper hook here."

    monkeypatch.setenv("KIMI_API_KEY", "test-key")
    monkeypatch.setattr("repo_to_shorts.kimi._call_kimi_api", fake_call)

    result = critique_story(snapshot, "hackathon judges", "storyboard")

    assert result.mode == "live-api"
    assert result.model
    assert result.fallback_reason is None
    assert "Live Kimi critique" in result.text
```

**Step 3: Implement `_call_kimi_api()`**

```python
DEFAULT_KIMI_MODEL = "kimi-k2-0905-preview"
DEFAULT_KIMI_BASE_URL = "https://api.moonshot.ai/v1"


def _call_kimi_api(prompt: str, model: str) -> str:
    from openai import OpenAI

    client = OpenAI(
        api_key=os.environ["KIMI_API_KEY"],
        base_url=os.environ.get("KIMI_BASE_URL", DEFAULT_KIMI_BASE_URL),
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a creative critic and technical short-video editor."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content or ""
```

**Step 4: Update `critique_story()`**

```python
if not os.environ.get("KIMI_API_KEY"):
    return fallback

model = os.environ.get("KIMI_MODEL", DEFAULT_KIMI_MODEL)
prompt = build_kimi_prompt(snapshot, audience, storyboard)
try:
    text = _call_kimi_api(prompt, model)
except Exception as exc:
    return KimiCritique(
        mode="deterministic-fallback",
        model=model,
        fallback_reason=f"Kimi API failed: {exc.__class__.__name__}",
        text=fallback_text(...),
    )

return KimiCritique(mode="live-api", model=model, fallback_reason=None, text=text)
```

**Step 5: Run tests**

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
```

Expected: PASS.

**Step 6: Commit**

```bash
git add pyproject.toml src/repo_to_shorts/kimi.py tests/test_kimi.py
git commit -m "feat: wire live kimi critic adapter"
```

---

## Task 4: Add CLI options for Kimi model

**Objective:** Let Peter override the model without editing code.

**Files:**
- Modify: `src/repo_to_shorts/cli.py`
- Modify: `src/repo_to_shorts/pipeline.py`
- Modify: `src/repo_to_shorts/kimi.py`
- Test: `tests/test_pipeline.py`

**Step 1: Add failing CLI test**

Assert `--kimi-model test-model` reaches metadata.

**Step 2: Update signatures**

```python
run_analysis(..., kimi_model: str | None = None)
critique_story(..., model: str | None = None)
```

**Step 3: Add Typer option**

```python
kimi_model: str | None = typer.Option(None, "--kimi-model", help="Kimi/Moonshot model name.")
```

**Step 4: Run tests**

Expected: PASS.

**Step 5: Commit**

```bash
git add src/repo_to_shorts/cli.py src/repo_to_shorts/pipeline.py src/repo_to_shorts/kimi.py tests/test_pipeline.py
git commit -m "feat: expose kimi model option"
```

---

## Task 5: Add optional MP4 render artifact

**Objective:** Generate `demo.mp4` from deterministic text scenes if time allows.

**Files:**
- Create: `src/repo_to_shorts/render.py`
- Modify: `src/repo_to_shorts/pipeline.py`
- Modify: `src/repo_to_shorts/cli.py`
- Test: `tests/test_render.py`

**Recommended lightweight implementation:** Use MoviePy `TextClip` if ImageMagick works. If it does not, avoid yak-shaving and use ffmpeg with generated SVG/PNG frames. The fallback is to keep the browser recording path.

**Step 1: Write test for render output path only**

Mock the actual renderer to avoid video dependency in tests.

**Step 2: Add `--render mp4|none` CLI option**

Default: `none` to preserve reliability.

**Step 3: Implement `render_mp4(run_dir)`**

Minimum contract:
- Reads `storyboard.md`, `narration.md`, `kimi_critique.md`.
- Writes `demo.mp4`.
- Updates metadata render block.

**Step 4: Verify locally**

```bash
.venv/bin/repo-shorts analyze . --audience "hackathon judges" --out runs --render mp4
open runs/<latest>/demo.mp4
```

**Step 5: Commit**

```bash
git add src/repo_to_shorts/render.py src/repo_to_shorts/cli.py src/repo_to_shorts/pipeline.py tests/test_render.py
git commit -m "feat: add optional mp4 render"
```

---

## Task 6: Update docs and final demo script

**Objective:** Make README, PRD, and demo script truthful after implementation.

**Files:**
- Modify: `README.md`
- Modify: `docs/PRD.md`
- Modify: `docs/demo-script.md`
- Modify: `docs/submission-copy.md`

**Step 1: Update README modes**

Document:
- No-key deterministic mode.
- Live Kimi mode.
- Optional render mode.

**Step 2: Update demo script**

The recorded demo should show:
1. CLI command.
2. `metadata.json` with live Kimi mode if available.
3. `kimi_critique.md` model output.
4. `demo.html` or `demo.mp4`.
5. Artifact checklist.

**Step 3: Run final checks**

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/repo-shorts analyze . --audience "Nous Research Hermes Agent Creative Hackathon judges" --out runs
```

If key available:

```bash
KIMI_API_KEY=$KIMI_API_KEY .venv/bin/repo-shorts analyze . --audience "Nous Research Hermes Agent Creative Hackathon judges" --out runs
```

**Step 4: Commit**

```bash
git add README.md docs/PRD.md docs/demo-script.md docs/submission-copy.md
git commit -m "docs: document live kimi demo flow"
```

---

## Final verification checklist

```bash
cd /Users/aiserver/projects/repo-to-shorts-agent
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/repo-shorts analyze . --audience "Nous Research Hermes Agent Creative Hackathon judges" --out runs
```

If Kimi key exists:

```bash
KIMI_API_KEY=... .venv/bin/repo-shorts analyze . --audience "Nous Research Hermes Agent Creative Hackathon judges" --out runs
```

Open latest:

```bash
open runs/<latest>/demo.html
```

Check:
- All core artifacts exist.
- `metadata.json` is honest.
- `kimi_critique.md` is live if key was set.
- Demo page is visually readable.
- No external posting happened.
