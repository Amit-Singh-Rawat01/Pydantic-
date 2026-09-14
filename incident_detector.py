from datetime import datetime, timedelta

from models import Error, Incident
from sqlalchemy.orm import Session

ERROR_THRESHOLD = 5
TIME_WINDOW_MINUTES = 5

def check_and_create_incident(db, service_name=None, error_type=None, severity=None):
    window_start = datetime.utcnow() - timedelta(minutes=TIME_WINDOW_MINUTES)
    recent_errors = (
        db.query(Error)
        .filter(
            Error.fingerprint.isnot(None),
            Error.occurred_at >= window_start,
        )
        .order_by(Error.occurred_at)
        .all()
    )

    groups = {}
    for error in recent_errors:
        groups.setdefault(error.fingerprint, []).append(error)

    for fingerprint, errors in groups.items():
        if len(errors) < ERROR_THRESHOLD:
            continue

        latest = errors[-1]
        existing = (
            db.query(Incident)
            .filter(
                Incident.fingerprint == fingerprint,
            )
            .first()
        )

        if existing:
            existing.occurrence_count = len(errors)
            existing.last_seen = latest.occurred_at
            existing.status = "OPEN"
        else:
            db.add(Incident(
                fingerprint=fingerprint,
                service_name=latest.service_name,
                error_type=latest.error_type,
                sample_message=latest.message,
                severity=latest.severity,
                occurrence_count=len(errors),
                first_seen=errors[0].occurred_at,
                last_seen=latest.occurred_at,
                status="OPEN",
            ))

    db.commit()


def resolve_stale_incidents(db: Session):
    cutoff = datetime.utcnow() - timedelta(minutes=5)
    stale_incidents = (
        db.query(Incident)
        .filter(
            Incident.status == "OPEN",
            Incident.last_seen < cutoff,
        )
        .all()
    )

    for incident in stale_incidents:
        incident.status = "RESOLVED"

    if stale_incidents:
        db.commit()