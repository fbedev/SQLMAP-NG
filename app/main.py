from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import projects

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "app": settings.app_name,
    }


app.include_router(projects.router, prefix=settings.api_prefix)

authorization_path = settings.data_dir / settings.authorization_subdir
app.mount("/static/authorizations", StaticFiles(directory=authorization_path), name="authorizations")


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"message": "Internal server error"})
