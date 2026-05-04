from __future__ import annotations

from repo_to_shorts.progress import ProgressTracker, Stage


def test_create_and_get_session():
    ProgressTracker.create_session("test-1")
    session = ProgressTracker.get_session("test-1")
    assert session is not None
    data = session.to_dict()
    assert data["percent"] == 0
    assert data["error"] is None
    assert len(data["stages"]) == 7


def test_stage_progression():
    ProgressTracker.create_session("test-2")
    ProgressTracker.start_stage("test-2", "ingest", "Reading repo")
    session = ProgressTracker.get_session("test-2")
    data = session.to_dict()
    assert data["active_stage"] == "ingest"
    assert data["percent"] == 0

    ProgressTracker.complete_stage("test-2", "ingest", "Done")
    session = ProgressTracker.get_session("test-2")
    data = session.to_dict()
    assert data["active_stage"] is None
    assert data["percent"] > 0


def test_error_and_unknown_session():
    ProgressTracker.create_session("test-3")
    ProgressTracker.set_error("test-3", "Something broke")
    session = ProgressTracker.get_session("test-3")
    data = session.to_dict()
    assert data["error"] == "Something broke"
    ingest_stage = next(s for s in data["stages"] if s["name"] == "ingest")
    assert ingest_stage["status"] in ("pending", "error")

    assert ProgressTracker.get_session("nonexistent") is None


def test_stage_dataclass():
    s = Stage(name="ingest", label="Ingesting repo")
    assert s.name == "ingest"
    assert s.status == "pending"
