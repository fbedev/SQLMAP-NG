from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.modules import registry as module_registry
from app.services import scan_service

router = APIRouter(prefix="/scans", tags=["Scans"])


class ScanCreatePayload(BaseModel):
    module_id: str = Field(..., description="Registered module identifier")
    safe_mode: bool = Field(default=True, description="Keep true for non-destructive educational scans")


@router.get("/modules")
async def list_modules():
    modules = module_registry.list_modules()
    return {
        "modules": [asdict(module) for module in modules],
    }


@router.post("/projects/{project_id}", status_code=201)
async def create_and_run_scan(project_id: str, payload: ScanCreatePayload):
    module = module_registry.get_module(payload.module_id)
    if module is None:
        raise HTTPException(status_code=404, detail="Module not found")

    try:
        session = scan_service.create_scan_session(
            project_id=project_id,
            module_id=payload.module_id,
            safe_mode=payload.safe_mode,
        )
        result = scan_service.run_scan(session.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"scan_session": result.model_dump(mode="json")}


@router.get("/projects/{project_id}")
async def list_project_scans(project_id: str):
    sessions = scan_service.list_scan_sessions(project_id=project_id)
    return {"scan_sessions": [session.model_dump(mode="json") for session in sessions]}


@router.get("/{scan_id}")
async def get_scan(scan_id: str):
    session = scan_service.get_scan_session(scan_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Scan session not found")
    return {"scan_session": session.model_dump(mode="json")}
