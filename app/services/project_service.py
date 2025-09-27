from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import uuid4

from app.models.domain import (
    ConsentAttestation,
    ConsentFile,
    Project,
    ProjectCreateData,
    ProjectStatus,
)
from app.storage.file_store import JsonFileStore, resolve_authorization_path
from app.utils.file_utils import sanitize_file_name

PROJECTS_FILE = "projects.json"
CONSENTS_FILE = "consents.json"

_project_store = JsonFileStore(PROJECTS_FILE)
_consent_store = JsonFileStore(CONSENTS_FILE)


def list_projects() -> List[Project]:
    return [Project.model_validate(obj) for obj in _project_store.list()]


def get_project(project_id: str) -> Optional[Project]:
    record = _project_store.find_one(lambda item: item.get("id") == project_id)
    return Project.model_validate(record) if record else None


def _persist_consent_file(consent_id: str, consent_file: ConsentFile) -> str:
    safe_name = sanitize_file_name(consent_file.original_name, default="consent.pdf")
    stored_name = f"{consent_id}-{safe_name}"
    target_path = resolve_authorization_path(consent_id, stored_name)
    target_path.write_bytes(consent_file.content)
    return stored_name


def create_project_with_consent(data: ProjectCreateData) -> Tuple[Project, ConsentAttestation]:
    now = datetime.now(timezone.utc)
    project_id = str(uuid4())
    consent_id = str(uuid4())

    stored_file_name: Optional[str] = None
    if data.consent_file is not None:
        stored_file_name = _persist_consent_file(consent_id, data.consent_file)

    consent = ConsentAttestation(
        id=consent_id,
        project_id=project_id,
        attestor_name=data.attestor_name,
        attestor_email=data.attestor_email,
        attestation_statement=data.attestation_statement,
        timestamp=now,
        consent_file_name=stored_file_name,
    )

    project = Project(
        id=project_id,
        name=data.name,
        target_url=data.target_url,
        description=data.description,
        status=ProjectStatus.DRAFT,
        created_at=now,
        updated_at=now,
        consent_id=consent_id,
    )

    _consent_store.append(consent.model_dump(mode="json"))
    _project_store.append(project.model_dump(mode="json"))

    return project, consent


def update_project_status(project_id: str, status: ProjectStatus) -> Optional[Project]:
    existing = get_project(project_id)
    if existing is None:
        return None

    updated = existing.model_copy(
        update={
            "status": status,
            "updated_at": datetime.now(timezone.utc),
        }
    )

    _project_store.upsert("id", updated.model_dump(mode="json"))
    return updated
