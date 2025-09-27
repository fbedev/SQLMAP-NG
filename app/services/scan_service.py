from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from app.models.domain import Project
from app.models.scan import ScanSession, ScanStatus
from app.modules import registry as module_registry
from app.services.project_service import get_project
from app.storage.file_store import JsonFileStore

SCANS_FILE = "scans.json"
_scan_store = JsonFileStore(SCANS_FILE)


def _session_from_record(record: dict) -> ScanSession:
    return ScanSession.model_validate(record)


def list_scan_sessions(project_id: Optional[str] = None) -> List[ScanSession]:
    sessions = [_session_from_record(raw) for raw in _scan_store.list()]
    if project_id is not None:
        return [session for session in sessions if session.project_id == project_id]
    return sessions


def get_scan_session(session_id: str) -> Optional[ScanSession]:
    record = _scan_store.find_one(lambda item: item.get("id") == session_id)
    return _session_from_record(record) if record else None


def create_scan_session(project_id: str, module_id: str, safe_mode: bool = True) -> ScanSession:
    project = get_project(project_id)
    if project is None:
        raise ValueError("Project does not exist")

    module = module_registry.get_module(module_id)
    if module is None:
        raise ValueError("Module not registered")

    if module.metadata.safe_mode_only and not safe_mode:
        raise ValueError("Module only supports safe mode")

    now = datetime.now(timezone.utc)
    session = ScanSession(
        id=str(uuid4()),
        project_id=project_id,
        module_id=module_id,
        status=ScanStatus.PENDING,
        created_at=now,
        findings=[],
        safe_mode=safe_mode,
    )
    _scan_store.append(session.model_dump(mode="json"))
    return session


def run_scan(session_id: str) -> ScanSession:
    session = get_scan_session(session_id)
    if session is None:
        raise ValueError("Scan session not found")

    if session.status == ScanStatus.RUNNING:
        return session

    module = module_registry.get_module(session.module_id)
    if module is None:
        raise ValueError("Module not registered")

    updated = session.model_copy(update={"status": ScanStatus.RUNNING})
    _scan_store.upsert("id", updated.model_dump(mode="json"))

    try:
        project: Project | None = get_project(session.project_id)
        target_url = project.target_url if project else ""
        result = module.execute(target_url, safe_mode=session.safe_mode)
        completed = updated.model_copy(
            update={
                "status": ScanStatus.COMPLETED,
                "completed_at": datetime.now(timezone.utc),
                "findings": result.findings,
                "interactions": result.interactions,
            }
        )
    except Exception as exc:  # pragma: no cover - placeholder for future logging
        completed = updated.model_copy(
            update={
                "status": ScanStatus.FAILED,
                "completed_at": datetime.now(timezone.utc),
                "notes": str(exc),
            }
        )

    _scan_store.upsert("id", completed.model_dump(mode="json"))
    return completed
