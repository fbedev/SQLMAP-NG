from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import httpx
import typer

app = typer.Typer(help="SQLMap Pro CLI")

API_BASE_ENV = "SQLMAP_PRO_API"
DEFAULT_API = "http://127.0.0.1:8000"


def _client() -> httpx.Client:
    base_url = os.getenv(API_BASE_ENV, DEFAULT_API)
    return httpx.Client(base_url=base_url, timeout=15.0)


@app.command()
def health() -> None:
    """Check server health."""
    with _client() as client:
        response = client.get("/health")
        typer.echo(response.text)


@app.command()
def modules() -> None:
    """List available scanning modules."""
    with _client() as client:
        response = client.get("/api/scans/modules")
        response.raise_for_status()
        payload = response.json()
        typer.echo(json.dumps(payload, indent=2))


@app.command()
def create_project(
    name: str = typer.Option(..., prompt=True),
    target_url: str = typer.Option(..., prompt=True),
    attestor_name: str = typer.Option(..., prompt=True),
    attestor_email: str = typer.Option(..., prompt=True),
    attestation_statement: str = typer.Option("Authorized for testing", prompt=True),
    consent_file: Optional[Path] = typer.Option(None, exists=True, dir_okay=False, help="Signed authorization document"),
) -> None:
    """Create a project with consent metadata."""
    with _client() as client:
        file_payload = None
        if consent_file:
            file_payload = {"consentFile": (consent_file.name, consent_file.read_bytes())}
        data = {
            "name": name,
            "target_url": target_url,
            "attestor_name": attestor_name,
            "attestor_email": attestor_email,
            "attestation_statement": attestation_statement,
        }
        try:
            response = client.post(
                "/api/projects",
                data=data,
                files=file_payload,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            typer.echo(f"Request failed: {exc}")
            raise typer.Exit(code=1)
        typer.echo(json.dumps(response.json(), indent=2))


@app.command()
def run_scan(
    project_id: str = typer.Argument(...),
    module_id: str = typer.Option("simulated_sqli", "--module", "-m"),
    unsafe: bool = typer.Option(False, help="Run without safe mode (required for live_sqli)")
) -> None:
    """Trigger a scan for the specified project."""
    with _client() as client:
        payload = {"module_id": module_id, "safe_mode": not unsafe}
        try:
            response = client.post(f"/api/scans/projects/{project_id}", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            typer.echo(f"Request failed: {exc}")
            raise typer.Exit(code=1)
        typer.echo(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    app()
