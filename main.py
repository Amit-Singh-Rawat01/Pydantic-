from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from database import engine, Base, get_db
from typing import Optional
from fastapi import Query
from sqlalchemy import desc
from sqlalchemy import func
import models
import schemas

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Error Intelligence Platform")

VALID_SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

@app.get("/health")
def health_check():
    return {"status": "running", "timestamp": datetime.utcnow().isoformat()}

@app.post("/errors")
def collect_error(error: schemas.ErrorCreate, db: Session = Depends(get_db)):
    if error.severity.upper() not in VALID_SEVERITIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid severity. Must be one of: {VALID_SEVERITIES}"
        )

    db_error = models.Error(
        service_name=error.service_name,
        error_type=error.error_type,
        message=error.message,
        severity=error.severity.upper(),
        stack_trace=error.stack_trace
    )
    db.add(db_error)
    db.commit()
    db.refresh(db_error)

    return {
        "success": True,
        "message": "Error recorded successfully",
        "error_id": db_error.id,
        "occurred_at": db_error.occurred_at.isoformat()
    }

@app.get("/errors")
def get_errors(
    service_name: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(models.Error)

    if service_name:
        query = query.filter(models.Error.service_name == service_name)
    if severity:
        query = query.filter(models.Error.severity == severity.upper())

    query = query.order_by(models.Error.occurred_at.desc())

    total = query.count()
    errors = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "errors": [
            {
                "id": e.id,
                "service_name": e.service_name,
                "error_type": e.error_type,
                "message": e.message,
                "severity": e.severity,
                "occurred_at": e.occurred_at.isoformat()
            }
            for e in errors
        ]
    }
@app.get("/errors/stats", response_model=schemas.ErrorStats)
def get_error_stats(db: Session = Depends(get_db)):
    total = db.query(models.Error).count()

    severity_rows = (
        db.query(models.Error.severity, func.count(models.Error.id))
        .group_by(models.Error.severity)
        .all()
    )

    by_severity = {
        severity: count
        for severity, count in severity_rows
    }
    service_rows = (
        db.query(models.Error.service_name, func.count(models.Error.id))
        .group_by(models.Error.service_name)
        .all()
    )

    by_service = {
        service: count
        for service, count in service_rows
    }
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)

    last_hour_count = (
        db.query(models.Error)
        .filter(models.Error.occurred_at >= one_hour_ago)
        .count()
    )
    return schemas.ErrorStats(
        total_errors=total,
        by_severity=by_severity,
        by_service=by_service,
        last_hour_count=last_hour_count
    )