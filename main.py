from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import database  # Day 3 ki file

app = FastAPI(title="Error Intelligence Platform")


# ---- PYDANTIC MODEL ----
# Yeh blueprint hai incoming error data ka
class ErrorEvent(BaseModel):
    service_name: str
    error_type: str
    message: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    stack_trace: Optional[str] = None  # optional field


# ---- HEALTH CHECK (Day 2 se) ----
@app.get("/health")
def health_check():
    return {"status": "running", "timestamp": datetime.utcnow().isoformat()}


# ---- POST /errors — Error receive karo aur save karo ----
@app.post("/errors")
def collect_error(error: ErrorEvent):
    # Step 1: Database connection lo
    conn = database.get_connection()
    cursor = conn.cursor()

    # Step 2: Validate severity
    valid_severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    if error.severity.upper() not in valid_severities:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid severity. Must be one of: {valid_severities}"
        )

    # Step 3: Database mein insert karo
    cursor.execute("""
        INSERT INTO errors (service_name, error_type, message, severity, stack_trace)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, occurred_at
    """, (
        error.service_name,
        error.error_type,
        error.message,
        error.severity.upper(),
        error.stack_trace
    ))

    # Step 4: Naya record ka data lo (id aur timestamp)
    result = cursor.fetchone()
    conn.commit()  # changes save karo
    cursor.close()
    conn.close()

    # Step 5: Response bhejo
    return {
        "success": True,
        "message": "Error recorded successfully",
        "error_id": result[0],
        "occurred_at": result[1].isoformat()
    }


# ---- GET /errors — Saved errors dekho ----
@app.get("/errors")
def get_errors():
    conn = database.get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, service_name, error_type, message, severity, occurred_at
        FROM errors
        ORDER BY occurred_at DESC
        LIMIT 50
    """)

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    # Rows ko readable format mein convert karo
    errors = []
    for row in rows:
        errors.append({
            "id": row[0],
            "service_name": row[1],
            "error_type": row[2],
            "message": row[3],
            "severity": row[4],
            "occurred_at": row[5].isoformat()
        })

    return {"total": len(errors), "errors": errors}