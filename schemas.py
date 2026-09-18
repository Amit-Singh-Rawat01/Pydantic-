from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
from enum import Enum


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ErrorEventSchema(BaseModel):
    service_name: str
    error_type: str
    message: str
    severity: Severity
    stack_trace: Optional[str] = None
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

class ErrorCreate(BaseModel):
    service_name: str
    error_type: str
    message: str
    severity: str
    stack_trace: Optional[str] = None

class ErrorOut(ErrorCreate):
    id: int
    occurred_at: datetime

    class Config:
        from_attributes = True

class ErrorStats(BaseModel):
    total_errors: int
    by_severity: dict[str, int]
    by_service: dict[str, int]
    last_hour_count: int


class IncidentResponse(BaseModel):
    id: int
    fingerprint: str
    service_name: str
    error_type: str
    sample_message: str | None
    occurrence_count: int
    first_seen: datetime
    last_seen: datetime
    status: str
    severity: str

    class Config:
        from_attributes = True