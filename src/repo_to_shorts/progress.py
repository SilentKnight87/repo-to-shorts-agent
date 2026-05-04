from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class Stage:
    name: str
    label: str
    status: str = "pending"  # pending | active | complete | error
    detail: str = ""
    started_at: float | None = None
    completed_at: float | None = None


@dataclass
class ProgressSession:
    session_id: str
    stages: list[Stage] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error: str | None = None

    def to_dict(self) -> dict:
        total = len(self.stages)
        complete = sum(1 for s in self.stages if s.status == "complete")
        active = next((s for s in self.stages if s.status == "active"), None)
        return {
            "session_id": self.session_id,
            "percent": int((complete / total * 100)) if total else 0,
            "complete": complete,
            "total": total,
            "active_stage": active.name if active else None,
            "active_label": active.label if active else None,
            "active_detail": active.detail if active else "",
            "error": self.error,
            "stages": [
                {
                    "name": s.name,
                    "label": s.label,
                    "status": s.status,
                    "detail": s.detail,
                }
                for s in self.stages
            ],
        }


class ProgressTracker:
    """Thread-safe in-memory progress tracker for generation sessions."""

    _store: ClassVar[dict[str, ProgressSession]] = {}
    _lock: ClassVar[threading.Lock] = threading.Lock()

    STAGES: ClassVar[list[tuple[str, str]]] = [
        ("ingest", "Ingesting repo"),
        ("analyze", "Analyzing structure"),
        ("kimi_brief", "Writing creative brief"),
        ("render_frames", "Rendering frames"),
        ("tts", "Generating voice"),
        ("compose", "Composing video"),
        ("finalize", "Packaging artifacts"),
    ]

    @classmethod
    def create_session(cls, session_id: str) -> ProgressSession:
        session = ProgressSession(
            session_id=session_id,
            stages=[Stage(name=name, label=label) for name, label in cls.STAGES],
        )
        with cls._lock:
            cls._store[session_id] = session
        return session

    @classmethod
    def start_stage(cls, session_id: str, stage_name: str, detail: str = "") -> None:
        with cls._lock:
            session = cls._store.get(session_id)
            if not session:
                return
            for stage in session.stages:
                if stage.name == stage_name:
                    stage.status = "active"
                    stage.detail = detail
                    stage.started_at = time.time()
                elif stage.status == "active":
                    stage.status = "complete"
                    stage.completed_at = time.time()
            session.updated_at = time.time()

    @classmethod
    def complete_stage(cls, session_id: str, stage_name: str, detail: str = "") -> None:
        with cls._lock:
            session = cls._store.get(session_id)
            if not session:
                return
            for stage in session.stages:
                if stage.name == stage_name:
                    stage.status = "complete"
                    stage.detail = detail
                    stage.completed_at = time.time()
            session.updated_at = time.time()

    @classmethod
    def set_error(cls, session_id: str, message: str) -> None:
        with cls._lock:
            session = cls._store.get(session_id)
            if session:
                session.error = message
                for stage in session.stages:
                    if stage.status == "active":
                        stage.status = "error"
                session.updated_at = time.time()

    @classmethod
    def get_session(cls, session_id: str) -> ProgressSession | None:
        with cls._lock:
            return cls._store.get(session_id)

    @classmethod
    def cleanup_old_sessions(cls, max_age_seconds: float = 3600) -> None:
        cutoff = time.time() - max_age_seconds
        with cls._lock:
            to_remove = [sid for sid, s in cls._store.items() if s.updated_at < cutoff]
            for sid in to_remove:
                del cls._store[sid]
