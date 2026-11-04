from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from models import AnomalyIncident


def find_top_error(db: Session, service_name: str) -> str | None:
    """Find the most common recent error relative to this service's latest event."""
    if db.bind is not None and db.bind.dialect.name == "sqlite":
        query = text("""
            SELECT error_type, COUNT(*) AS n
            FROM errors
            WHERE service_name = :service
              AND occurred_at >= datetime(
                    (SELECT MAX(occurred_at) FROM errors WHERE service_name = :service),
                    '-5 minutes'
                  )
            GROUP BY error_type
            ORDER BY n DESC
            LIMIT 1
        """)
    else:
        query = text("""
            SELECT error_type, COUNT(*) AS n
            FROM errors
            WHERE service_name = :service
              AND occurred_at >= (
                    SELECT MAX(occurred_at) FROM errors WHERE service_name = :service
                  ) - INTERVAL '5 minutes'
            GROUP BY error_type
            ORDER BY n DESC
            LIMIT 1
        """)

    try:
        row = db.execute(query, {"service": service_name}).first()
    except Exception as e:
        db.rollback()
        print(f"[incident] top error nahi mila: {e}")
        return None

    if row is None:
        return None
    return f"{row.error_type} ({row.n} errors, last 5 min)"


def handle_anomaly_event(
    db: Session,
    service_name: str,
    new_status: str,
) -> None:
    """Open or resolve the active anomaly incident for a service."""
    open_incident = (
        db.query(AnomalyIncident)
        .filter(
            AnomalyIncident.service_name == service_name,
            AnomalyIncident.status == "OPEN",
        )
        .first()
    )

    if new_status == "ANOMALY":
        if open_incident is None:
            db.add(
                AnomalyIncident(
                    service_name=service_name,
                    status="OPEN",
                    top_error=find_top_error(db, service_name),
                )
            )
            db.commit()
    elif new_status == "NORMAL" and open_incident is not None:
        open_incident.status = "RESOLVED"
        open_incident.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
