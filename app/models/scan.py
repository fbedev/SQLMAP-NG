from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.http import HttpInteraction


class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class FindingSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    module_id: str
    title: str
    description: str
    severity: FindingSeverity
    recommendation: str
    evidence: Optional[dict] = None


class ScanSession(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    project_id: str
    module_id: str
    status: ScanStatus = Field(default=ScanStatus.PENDING)
    created_at: datetime
    completed_at: Optional[datetime] = None
    findings: List[Finding] = Field(default_factory=list)
    notes: Optional[str] = None
    safe_mode: bool = True
    interactions: List[HttpInteraction] = Field(default_factory=list)
