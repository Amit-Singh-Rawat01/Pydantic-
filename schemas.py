from pydantic import BaseModel
from datetime import datetime

# Yeh define karta hai ki API mein error data kaise aana chahiye
class ErrorCreate(BaseModel):
    service_name: str
    error_message: str
    severity: str = "medium"  # Default medium hai

# Yeh response mein kya bhejenge
class ErrorResponse(BaseModel):
    id: int
    service_name: str
    error_message: str
    severity: str
    timestamp: datetime

    class Config:
        from_attributes = True