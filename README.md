# SQLMap Pro (Python Scaffold)

Early FastAPI backend scaffold for an ethical SQL auditing platform. This iteration focuses on the consent-gated project workflow and local JSON storage so you can prototype features without a database.

## Getting Started

1. **Create a virtual environment and install dependencies**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Run the API server**
   ```bash
   uvicorn app.main:app --reload
   ```
3. **Explore the interactive docs** (after the server starts)
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

The service stores data inside the `data/` directory:
- `data/projects.json` and `data/consents.json` are created automatically.
- Uploaded authorization artifacts land under `data/authorizations/<consent_id>/`.

## Available Endpoints (v0)

- `GET  /health` — basic health probe.
- `GET  /api/projects` — list projects with their consent metadata.
- `GET  /api/projects/{project_id}` — fetch a single project.
- `POST /api/projects` — create a project plus consent attestation (multipart form with optional file upload).
- `PATCH /api/projects/{project_id}/status` — update project status (`draft`, `approved`, or `revoked`).
- Static consent files are served from `/static/authorizations/{consent_id}/<file>`.

## Development Notes

- Storage uses simple JSON files. Swap `JsonFileStore` in `app/storage/file_store.py` when you are ready for a real database.
- `python -m compileall app` succeeds (verifies the modules import cleanly).
- The global `Exception` handler returns a 500 with a generic payload; extend it once you introduce structured logging.

## Next Steps

- Flesh out workflow builder, request explorer, and reporting APIs.
- Add authentication/RBAC scaffolding and multi-tenant project separation.
- Record audit trails (who approved, when scans ran) alongside replay-ready session data.
- Integrate with the ChatGPT API to power learning-mode explanations in future iterations.
