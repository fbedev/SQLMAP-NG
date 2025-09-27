from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, EmailStr

from app.models.domain import ConsentFile, ProjectCreateData, ProjectStatus
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("/")
async def list_projects():
    projects = project_service.list_projects()
    return {"projects": [project.model_dump(mode="json") for project in projects]}


@router.get("/{project_id}")
async def get_project(project_id: str):
    project = project_service.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": project.model_dump(mode="json")}


@router.post("/", status_code=201)
async def create_project(
    name: str = Form(...),
    target_url: str = Form(...),
    attestor_name: str = Form(...),
    attestor_email: EmailStr = Form(...),
    attestation_statement: str = Form(...),
    description: str | None = Form(default=None),
    consent_file: UploadFile | None = File(default=None),
):
    file_payload: ConsentFile | None = None
    if consent_file is not None:
        content = await consent_file.read()
        file_payload = ConsentFile(original_name=consent_file.filename or "consent.pdf", content=content)

    project_data = ProjectCreateData(
        name=name,
        target_url=target_url,
        attestor_name=attestor_name,
        attestor_email=attestor_email,
        attestation_statement=attestation_statement,
        description=description,
        consent_file=file_payload,
    )

    project, consent = project_service.create_project_with_consent(project_data)
    return {
        "project": project.model_dump(mode="json"),
        "consent": consent.model_dump(mode="json"),
    }


class StatusUpdatePayload(BaseModel):
    status: ProjectStatus


@router.patch("/{project_id}/status")
async def update_project_status(project_id: str, payload: StatusUpdatePayload):
    project = project_service.update_project_status(project_id, payload.status)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": project.model_dump(mode="json")}
