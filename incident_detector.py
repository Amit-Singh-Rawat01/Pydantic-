from datetime import datetime, timedelta

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

    count = db.query(Error).filter(
        Error.service_name == service_name,
        Error.error_type == error_type,
        Error.occurred_at >= window_start
    ).count()

    if count < ERROR_THRESHOLD:
        return

    existing = db.query(Incident).filter(
        Incident.service_name == service_name,
        Incident.error_type == error_type,
        Incident.status == "OPEN"
    ).first()

    if existing:
        existing.occurrence_count = count
        existing.last_occurred_at = datetime.utcnow()

    else:
        db.add(Incident(
            service_name=service_name,
            error_type=error_type,
            severity=severity,
            occurrence_count=count,
            first_occurred_at=window_start,
            last_occurred_at=datetime.utcnow()
        ))

    db.commit()