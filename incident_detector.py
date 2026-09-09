from datetime import datetime, timedelta

from sqlalchemy import func

from models import Error, Incident

ERROR_THRESHOLD = 5
TIME_WINDOW_MINUTES = 5

def check_and_create_incident(
    db,
    service_name: str,
    error_type: str,
    severity: str
):
    window_start = datetime.utcnow() - timedelta(
        minutes=TIME_WINDOW_MINUTES
    )

    fingerprint_groups = (
        db.query(
            Error.fingerprint,
            func.count(Error.id).label("error_count"),
        )
        .filter(
            Error.fingerprint.isnot(None),
            Error.occurred_at >= window_start,
        )
        .group_by(Error.fingerprint)
        .having(func.count(Error.id) >= ERROR_THRESHOLD)
        .all()
    )

    now = datetime.utcnow()
    for fingerprint, count in fingerprint_groups:
        latest_error = (
            db.query(Error)
            .filter(
                Error.fingerprint == fingerprint,
                Error.occurred_at >= window_start,
            )
            .order_by(Error.occurred_at.desc())
            .first()
        )

        existing = db.query(Incident).filter(
            Incident.fingerprint == fingerprint,
            Incident.status == "OPEN",
        ).first()

        if existing:
            existing.occurrence_count = count
            existing.last_occurred_at = now
        elif latest_error:
            db.add(Incident(
                fingerprint=fingerprint,
                service_name=latest_error.service_name,
                error_type=latest_error.error_type,
                severity=latest_error.severity,
                occurrence_count=count,
                first_occurred_at=window_start,
                last_occurred_at=now,
            ))

    db.commit()