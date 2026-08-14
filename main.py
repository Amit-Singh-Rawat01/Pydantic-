from datetime import datetime
from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel

# 1. Initialize FastAPI App
app = FastAPI(
    title="Distributed Error Intelligence Platform",
    description="Collector Service API for receiving real-time application errors",
    version="0.1.0",
)


# 2. Define Data Schema using Pydantic
# Yeh define karta hai ki error log ka format kaisa hona chahiye
class ErrorLog(BaseModel):
    service_name: str  # Konse service se error aaya (e.g., 'auth-service')
    error_message: str  # Error ka description
    severity: str  # 'CRITICAL', 'ERROR', ya 'WARNING'
    timestamp: Optional[str] = None  # Optional timestamp


# 3. Basic Root Endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to Error Intelligence Platform Collector API"}


# 4. Health Check Endpoint
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "collector-service",
        "timestamp": datetime.utcnow().isoformat(),
    }


# 5. POST Endpoint to Receive Error Logs (Mock Ingestion)
@app.post("/api/v1/errors")
def receive_error(error: ErrorLog):
    # Agar timestamp na mile toh current time set kar do
    if not error.timestamp:
        error.timestamp = datetime.utcnow().isoformat()

    # Terminal par log print karo (Temporary verification)
    print(
        f"🚨 [RECEIVED ERROR] Service: {error.service_name} | Severity: {error.severity} | Message: {error.error_message}"
    )

    # Client ko response bhejo
    return {
        "status": "success",
        "message": "Error payload received successfully",
        "received_data": error,
    }