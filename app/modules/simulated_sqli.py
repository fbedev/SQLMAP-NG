from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse, parse_qs
from uuid import uuid4

from app.models.http import HttpInteraction
from app.models.scan import Finding, FindingSeverity
from app.modules.base import ExecutionResult, ModuleMetadata, ScannerModule


class SimulatedSQLiModule(ScannerModule):
    metadata = ModuleMetadata(
        id="simulated_sqli",
        name="Simulated SQL Injection Detector",
        description=(
            "Educational module that inspects query parameters for patterns often associated "
            "with SQL injection. It never sends payloads—results are illustrative only."
        ),
        safe_mode_only=True,
    )

    suspicious_tokens = {
        "' or '1'='1": "Classic tautology pattern often used to bypass authentication.",
        "' --": "Inline comment token frequently appended to truncate legitimate queries.",
        "or 1=1": "Boolean bypass expression observed in many SQLi payloads.",
    }

    def execute(self, target: str, safe_mode: bool = True) -> ExecutionResult:
        findings: list[Finding] = []
        parsed = urlparse(target)
        params = parse_qs(parsed.query)

        evidence_params: list[str] = []
        recommendations: set[str] = set()

        for key, values in params.items():
            for value in values:
                normalized = value.lower()
                for token, explanation in self.suspicious_tokens.items():
                    if token in normalized:
                        evidence_params.append(f"{key}={value}")
                        recommendations.add("Apply parameterized queries and strict input validation.")

        if evidence_params:
            findings.append(
                Finding(
                    id=str(uuid4()),
                    module_id=self.metadata.id,
                    title="Potential SQL injection indicators in query string",
                    description=(
                        "Parameters on the provided URL contain patterns frequently referenced in SQL injection "
                        "training. Review the inputs and confirm the application enforces parameterized queries."
                    ),
                    severity=FindingSeverity.MEDIUM,
                    recommendation=" ".join(sorted(recommendations)) or "Ensure ORM or prepared statements are used for all database calls.",
                    evidence={
                        "observed_parameters": evidence_params,
                        "checked_at": datetime.utcnow().isoformat(),
                        "notes": "Detection is heuristic and educational—no live payloads executed.",
                    },
                )
            )
        else:
            findings.append(
                Finding(
                    id=str(uuid4()),
                    module_id=self.metadata.id,
                    title="No SQL injection signatures detected",
                    description=(
                        "No known SQL injection training patterns were observed in the query string. Manual validation "
                        "and additional testing are still recommended."
                    ),
                    severity=FindingSeverity.INFO,
                    recommendation="Continue with safe-mode recon or escalate to manual validation workflows.",
                    evidence={
                        "checked_at": datetime.utcnow().isoformat(),
                        "parameters_analyzed": list(params.keys()),
                    },
                )
            )
        return ExecutionResult(findings=findings, interactions=[])


MODULE = SimulatedSQLiModule()
