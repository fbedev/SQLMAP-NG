from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.models.scan import Finding
from app.models.http import HttpInteraction


@dataclass(slots=True)
class ModuleMetadata:
    id: str
    name: str
    description: str
    safe_mode_only: bool = True


@dataclass(slots=True)
class ExecutionResult:
    findings: List[Finding]
    interactions: List[HttpInteraction]


class ScannerModule:
    metadata: ModuleMetadata

    def execute(self, target: str, safe_mode: bool = True) -> ExecutionResult:
        raise NotImplementedError
