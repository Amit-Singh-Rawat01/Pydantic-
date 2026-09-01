from datetime import datetime, timedelta
from typing import Optional

from database import Base, engine, get_db
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

import models
import redis
import schemas
import os
from producer import send_error_to_kafka

from fastapi.middleware.cors import CORSMiddleware
from models import Error, Incident



# Create database tables
Base.metadata.create_all(bind=engine)


app = FastAPI(title="Error Intelligence Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Redis Connection Setup
r = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=6379,
    decode_responses=True,
)


VALID_SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


@app.get("/health")
def health_check():
    return {
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/errors")
def collect_error(error: schemas.ErrorCreate):
    if error.severity.upper() not in VALID_SEVERITIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid severity. Must be one of: {VALID_SEVERITIES}",
        )

    error_dict = error.model_dump()
    error_dict["severity"] = error.severity.upper()

    success = send_error_to_kafka(error_dict)

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to queue error to Kafka",
        )

    return {
        "status": "queued",
        "message": "Error queued successfully",
    }


@app.get("/errors")
def get_errors(
    service_name: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(models.Error)

    if service_name:
        query = query.filter(
            models.Error.service_name == service_name
        )

    if severity:
        query = query.filter(
            models.Error.severity == severity.upper()
        )

    query = query.order_by(
        models.Error.occurred_at.desc()
    )

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
                "occurred_at": e.occurred_at.isoformat(),
                "fingerprint": e.fingerprint,
            }
            for e in errors
        ],
    }


@app.get("/errors/stats", response_model=schemas.ErrorStats)
def get_error_stats(
    db: Session = Depends(get_db),
):
    total = db.query(models.Error).count()

    severity_rows = (
        db.query(
            models.Error.severity,
            func.count(models.Error.id),
        )
        .group_by(models.Error.severity)
        .all()
    )

    by_severity = {
        severity: count
        for severity, count in severity_rows
    }

    service_rows = (
        db.query(
            models.Error.service_name,
            func.count(models.Error.id),
        )
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
        .filter(
            models.Error.occurred_at >= one_hour_ago
        )
        .count()
    )

    return schemas.ErrorStats(
        total_errors=total,
        by_severity=by_severity,
        by_service=by_service,
        last_hour_count=last_hour_count,
    )


@app.get("/stats")
def get_stats():
    total = r.get("errors:total") or 0

    minute_key = (
        f"errors:minute:"
        f"{datetime.utcnow().strftime('%Y%m%d%H%M')}"
    )

    last_minute = r.get(minute_key) or 0

    return {
        "total_errors": int(total),
        "errors_last_minute": int(last_minute),
    }


# Day 15: Group errors by fingerprint
@app.get("/errors/groups")
def get_error_groups(
    db: Session = Depends(get_db),
):
    results = (
        db.query(
            models.Error.fingerprint,
            models.Error.service_name,
            models.Error.error_type,
            func.count(models.Error.id).label("count"),
            func.max(
                models.Error.occurred_at
            ).label("last_seen"),
        )
        .group_by(
            models.Error.fingerprint,
            models.Error.service_name,
            models.Error.error_type,
        )
        .order_by(
            func.count(models.Error.id).desc()
        )
        .all()
    )

    return [
        {
            "fingerprint": r.fingerprint,
            "service_name": r.service_name,
            "error_type": r.error_type,
            "count": r.count,
            "last_seen": (
                r.last_seen.isoformat()
                if r.last_seen
                else None
            ),
        }
        for r in results
    ]

@app.get("/incidents")
def get_incidents(
    status: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(Incident)

    if status:
        query = query.filter(
            Incident.status == status
        )

    return query.order_by(
        Incident.last_occurred_at.desc()
    ).all()


@app.get("/incidents/{incident_id}")
def get_incident(
    incident_id: int,
    db: Session = Depends(get_db)
):
    incident = db.query(Incident).filter(
        Incident.id == incident_id
    ).first()

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    return incident


