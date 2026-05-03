# Minimal Local Web UI Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add a tiny local browser UI so Peter can paste a GitHub URL or local path, click Generate, and open the generated short-video package without needing to remember CLI commands.

**Architecture:** Keep `run_analysis(...)` as the single generation engine. Add a thin local web server that renders one HTML page, accepts form posts, calls the existing pipeline, and serves generated artifacts. No database, no auth, no hosted deployment, no front-end framework.

**Tech Stack:** Python 3.13, stdlib `http.server` or a tiny optional FastAPI/Uvicorn stack, existing Typer CLI, existing `repo_to_shorts.pipeline.run_analysis`, pytest. Prefer stdlib unless FastAPI materially improves speed.

---

## Current vs target capability

| Area | Current | Target |
| --- | --- | --- |
| Generation engine | CLI `repo-shorts analyze` | Same engine reused by web UI |
| User input | terminal args | browser form |
| Output viewing | static server over `runs/` | generated links on success page plus static serving |
| Kimi | env-key live mode or fallback | same behavior, no key entry in browser |
| MP4 | `--render mp4` | checkbox maps to `render="mp4"` |
| Run history | file system only | latest runs list on home page |
| Job model | synchronous CLI run | synchronous local request for MVP |
| Network exposure | ad hoc server | safe localhost default, explicit LAN flag |

## Non-negotiables

- Do not rewrite the pipeline.
- Do not store API keys in form fields, files, cookies, local storage, or logs.
- Do not post publicly.
- Do not add a database.
- Do not make a complex frontend. One server-rendered page is enough.
- Default host must be `127.0.0.1`; LAN access requires explicit `--host 0.0.0.0`.
- Generation failures must return a useful error page, not a traceback dump.

## Proposed UX

Home page at `/`:

```text
Repo-to-Shorts Agent

[ Target repo or GitHub URL __________________________ ]
[ Audience ___________________________________________ ]
[ Kimi model moonshotai/kimi-k2.6 ____________________ ]
[ ] Render MP4

[ Generate short package ]

Latest runs:
- 20260503-092819-repo-to-shorts-agent
  demo.html | demo.mp4 | metadata.json | kimi_critique.md
```

After submit:

```text
Generation complete

Run: runs/<timestamp>-<repo>
Kimi: live-api / deterministic-fallback / api-error-fallback
Render: success / skipped / failed

Open demo.html
Open demo.mp4, if present
Open metadata.json
Open kimi_critique.md
Back to home
```

## Route contract

### `GET /`

Renders:
- form
- latest runs list
- server/network hint
- reminder that API keys come from environment only

### `POST /generate`

Reads form fields:
- `target`, required
- `audience`, optional, default `technical builders`
- `kimi_model`, optional, default `moonshotai/kimi-k2.6`
- `render_mp4`, optional checkbox

Calls:

```python
run_analysis(
    target,
    audience=audience,
    out_dir=Path("runs"),
    kimi_model=kimi_model,
    render="mp4" if render_mp4 else "none",
)
```

Returns a success page with artifact links.

### `GET /runs/<path>`

Serves generated files from the `runs/` directory only.
Must prevent path traversal.

### `GET /healthz`

Returns simple JSON:

```json
{"ok": true}
```

Useful for local readiness checks.

## File plan

Create:
- `src/repo_to_shorts/web.py`
- `tests/test_web.py`

Modify:
- `src/repo_to_shorts/cli.py`
- `README.md`
- `docs/PRD.md`, if implementation deviates from this plan
- `AGENTS.md`, if new commands matter for future agents

Avoid new template files unless the HTML becomes too large. A string-rendered page is fine for MVP.

## Task 1: Add web module skeleton

**Objective:** Provide a local HTTP app entry point without generation logic yet.

**Files:**
- Create: `src/repo_to_shorts/web.py`
- Test: `tests/test_web.py`

**Step 1: Write failing test**

Test that a request to `/healthz` returns `200` and `{"ok": true}`.

If using stdlib server, test the handler helpers directly rather than spinning a real socket unless necessary.

**Step 2: Implement minimal app/server helper**

Add:

```python
def run_web_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    ...
```

Add a request handler with `/healthz` support.

**Step 3: Verify**

```bash
.venv/bin/python -m pytest tests/test_web.py -q
```

Expected: pass.

## Task 2: Add CLI command `repo-shorts web`

**Objective:** Let Peter launch the UI with one command.

**Files:**
- Modify: `src/repo_to_shorts/cli.py`
- Test: `tests/test_cli.py` or `tests/test_web.py`

**Step 1: Write failing CLI test**

Use Typer's runner to verify `repo-shorts web --help` includes:
- `--host`
- `--port`
- default `127.0.0.1`

Do not start a long-running server in tests. Monkeypatch `run_web_server`.

**Step 2: Implement CLI command**

Add:

```python
@app.command()
def web(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Run the local web UI."""
    run_web_server(host=host, port=port)
```

**Step 3: Verify**

```bash
.venv/bin/python -m pytest tests/test_cli.py tests/test_web.py -q
```

Expected: pass.

## Task 3: Render home page and latest runs list

**Objective:** Show the product UI shell and existing generated runs.

**Files:**
- Modify: `src/repo_to_shorts/web.py`
- Test: `tests/test_web.py`

**Step 1: Write failing tests**

Test that `render_home_page(...)` includes:
- `Repo-to-Shorts Agent`
- form field `target`
- form field `audience`
- checkbox `render_mp4`
- latest run links when run folders exist

**Step 2: Implement helper functions**

Suggested helpers:

```python
def list_runs(runs_dir: Path, limit: int = 10) -> list[Path]:
    ...

def render_home_page(runs: list[Path], message: str | None = None) -> str:
    ...
```

Escape all dynamic content with `html.escape`.

**Step 3: Verify**

```bash
.venv/bin/python -m pytest tests/test_web.py -q
```

Expected: pass.

## Task 4: Implement generation form handling

**Objective:** POST `/generate` calls the existing pipeline and returns artifact links.

**Files:**
- Modify: `src/repo_to_shorts/web.py`
- Test: `tests/test_web.py`

**Step 1: Write failing unit test**

Monkeypatch `repo_to_shorts.web.run_analysis` to capture args and return a fake run directory.

Assert:
- target and audience are passed through
- checkbox maps to `render="mp4"`
- Kimi model defaults correctly
- response contains `demo.html`, `metadata.json`, `kimi_critique.md`

**Step 2: Implement form parser**

Use `urllib.parse.parse_qs` for stdlib HTTP handling.

Validation:
- empty `target` returns 400 with a friendly error
- blank audience becomes `technical builders`
- blank model becomes `moonshotai/kimi-k2.6`

**Step 3: Verify**

```bash
.venv/bin/python -m pytest tests/test_web.py -q
```

Expected: pass.

## Task 5: Serve artifacts safely

**Objective:** Let the browser open generated files from `runs/` without exposing the whole machine.

**Files:**
- Modify: `src/repo_to_shorts/web.py`
- Test: `tests/test_web.py`

**Step 1: Write failing tests**

Assert:
- `/runs/example/demo.html` maps inside the configured `runs/` directory
- `/runs/../secret` is rejected
- non-existent file returns 404
- common content types work for `.html`, `.json`, `.md`, `.svg`, `.srt`, `.mp4`

**Step 2: Implement safe resolver**

Suggested helper:

```python
def resolve_run_file(runs_dir: Path, request_path: str) -> Path:
    candidate = (runs_dir / request_path.removeprefix("/runs/")).resolve()
    if runs_dir.resolve() not in candidate.parents and candidate != runs_dir.resolve():
        raise ValueError("path escapes runs directory")
    return candidate
```

**Step 3: Verify**

```bash
.venv/bin/python -m pytest tests/test_web.py -q
```

Expected: pass.

## Task 6: Manual LAN demo check

**Objective:** Confirm Peter can open the UI from laptop when intentionally bound to LAN.

**Files:**
- No code changes unless bugs found

**Commands:**

```bash
.venv/bin/repo-shorts web --host 127.0.0.1 --port 8765
curl -I http://127.0.0.1:8765/healthz
```

For laptop access:

```bash
ipconfig getifaddr en0
.venv/bin/repo-shorts web --host 0.0.0.0 --port 8765
```

Open from laptop:

```text
http://<mac-mini-ip>:8765/
```

Expected:
- local UI loads
- form can generate a run
- links open generated artifacts

## Task 7: Update docs and final checks

**Objective:** Make docs match actual behavior.

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/PRD.md`, only if behavior changed from plan

Docs must state:
- web UI is local-only
- default host is `127.0.0.1`
- use `--host 0.0.0.0` only for LAN demo
- API keys come from environment variables only
- CLI remains canonical engine

Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
```

Expected:
- all tests pass
- ruff passes

Commit:

```bash
git add src/repo_to_shorts/web.py src/repo_to_shorts/cli.py tests/test_web.py README.md AGENTS.md docs/PRD.md docs/plans/2026-05-03-local-web-ui-plan.md
git commit -m "feat: add local web ui"
```

## Acceptance checklist

Before calling the web UI done:

- [ ] `repo-shorts web --help` documents host/port.
- [ ] `repo-shorts web --host 127.0.0.1 --port 8765` starts locally.
- [ ] Home page loads.
- [ ] Target/audience form appears.
- [ ] Generate works for a local repo.
- [ ] Generate works for a public GitHub URL.
- [ ] MP4 checkbox produces `demo.mp4` when ffmpeg/Pillow are available.
- [ ] Latest runs list shows artifact links.
- [ ] `/runs/...` cannot escape the runs directory.
- [ ] No API key appears in page source, logs, docs, or committed files.
- [ ] Tests/lint pass.

## Final-mile note

This web UI is for demo clarity, not product completeness. The win condition is making the workflow obvious: paste repo, generate package, show Kimi proof, open MP4/browser demo. Do not let the UI become a swamp.
