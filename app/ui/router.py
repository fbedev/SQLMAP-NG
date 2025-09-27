from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.modules import registry as module_registry
from app.services import project_service, scan_service

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    modules = [asdict(meta) for meta in module_registry.list_modules()]
    projects = [project.model_dump(mode="json") for project in project_service.list_projects()]
    scans = [session.model_dump(mode="json") for session in scan_service.list_scan_sessions()]
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "modules": modules,
            "projects": projects,
            "scans": scans,
        },
    )
