# SQLMap Pro (Python Scaffold)

FastAPI-powered backend for an ethical-but-capable SQL auditing platform. The current milestone ships consent-gated projects, a real HTTP executor with live SQLi payloads, JSON persistence, and both CLI/UI front ends so you can run everything locally without a database.

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

## Available Endpoints (v0.1)

- `GET  /health` — basic health probe.
- `GET  /api/projects` — list projects with their consent metadata.
- `GET  /api/projects/{project_id}` — fetch a single project.
- `POST /api/projects` — create a project plus consent attestation (multipart form with optional file upload).
- `PATCH /api/projects/{project_id}/status` — update project status (`draft`, `approved`, or `revoked`).
- `GET  /api/scans/modules` — list available educational scanner modules.
- `POST /api/scans/projects/{project_id}` — create and execute a scan session for a project.
- `GET  /api/scans/projects/{project_id}` — view all scan sessions tied to a project.
- `GET  /api/scans/{scan_id}` — fetch a specific scan session.
- Static consent files are served from `/static/authorizations/{consent_id}/<file>`.

## Scanner Modules

- `simulated_sqli` — inspects the project URL's query string for classic SQL injection training patterns without sending payloads.
- `live_sqli` — replays boolean, union-select, comment truncation, and timing payloads via the HTTP executor, comparing status/length/timing with baseline requests while capturing request/response evidence. Requires `safe_mode=false` and explicit authorization.
- Every module declares whether it requires safe mode; interactions (requests + responses) are recorded per scan session for reporting and replay.

### Quick Demo

```bash
# 1. Create a consent-backed project (multipart form data)
curl -X POST http://localhost:8000/api/projects \
  -F "name=DVWA Training" \
  -F "target_url=https://dvwa.local/login.php?username=admin&password=' OR '1'='1" \
  -F "attestor_name=Jane Tester" \
  -F "attestor_email=jane@example.com" \
  -F "attestation_statement=Authorized for lab-only testing"

# 2. Trigger the simulated SQLi module (safe heuristics)
project_id=<copy-id-from-step-1>
curl -X POST http://localhost:8000/api/scans/projects/$project_id \
  -H "Content-Type: application/json" \
  -d '{"module_id": "simulated_sqli", "safe_mode": true}'

# 3. Run the live SQLi module (requires explicit authorization)
curl -X POST http://localhost:8000/api/scans/projects/$project_id \
  -H "Content-Type: application/json" \
  -d '{"module_id": "live_sqli", "safe_mode": false}'
```

## Local Interfaces

### Web UI
- Visit http://localhost:8000/ for the built-in dashboard.
- Create projects, toggle safe mode, and launch scans directly in the browser.
- Results stream back into the page with summary tables plus raw JSON output.

### CLI
- Defaults to http://127.0.0.1:8000; override via the `SQLMAP_PRO_API` environment variable if needed.
- Example usage:
  ```bash
  python cli/main.py modules
  python cli/main.py create-project --name "Lab" --target-url "https://target/?id=1" \
    --attestor-name "Tester" --attestor-email tester@example.com
  python cli/main.py run-scan <project-id> --module live_sqli --unsafe
  ```


## Development Notes

- Storage uses simple JSON files. Swap `JsonFileStore` in `app/storage/file_store.py` when you are ready for a real database.
- `python -m compileall app` succeeds (verifies the modules import cleanly).
- The global `Exception` handler returns a 500 with a generic payload; extend it once you introduce structured logging.
- `cli/main.py` exposes a Typer CLI; `app/templates/index.html` powers the built-in dashboard via FastAPI's templating.

## Next Steps

- Flesh out workflow builder, request explorer, and reporting APIs.
- Add authentication/RBAC scaffolding and multi-tenant project separation.
- Record audit trails (who approved, when scans ran) alongside replay-ready session data.
- Integrate with the ChatGPT API to power learning-mode explanations in future iterations.
