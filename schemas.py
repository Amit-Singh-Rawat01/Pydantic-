from pydantic import BaseModel
from typing import Optional
from datetime import datetime

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