from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    REVOKED = "revoked"


class ConsentAttestation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    project_id: str
    attestor_name: str
    attestor_email: EmailStr
    attestation_statement: str
    timestamp: datetime
    consent_file_name: Optional[str] = None


class Project(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    id: str
    name: str
    target_url: str
    description: Optional[str] = None
    status: ProjectStatus = Field(default=ProjectStatus.DRAFT)
    created_at: datetime
    updated_at: datetime
    consent_id: Optional[str] = None


@dataclass(slots=True)
class ConsentFile:
    original_name: str
    content: bytes


@dataclass(slots=True)
class ProjectCreateData:
    name: str
    target_url: str
    attestor_name: str
    attestor_email: EmailStr
    attestation_statement: str
    description: Optional[str]
    consent_file: Optional[ConsentFile]
