from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    HEAD = "HEAD"


class HttpRequestLog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: HttpMethod
    url: str
    params: Optional[Dict[str, str]] = None
    headers: Optional[Dict[str, str]] = None
    content_type: Optional[str] = None
    body_excerpt: Optional[str] = Field(default=None, description="First 512 characters of request body")


class HttpResponseLog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status_code: int
    elapsed_ms: float
    headers: Dict[str, str]
    body_excerpt: Optional[str] = Field(default=None, description="First 2k characters of response body")


class HttpInteraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request: HttpRequestLog
    response: HttpResponseLog
    analysis: Optional[Dict[str, Any]] = None
