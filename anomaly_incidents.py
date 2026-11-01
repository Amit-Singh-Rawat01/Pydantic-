from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models import AnomalyIncident


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
            db.add(AnomalyIncident(service_name=service_name, status="OPEN"))
            db.commit()
    elif new_status == "NORMAL" and open_incident is not None:
        open_incident.status = "RESOLVED"
        open_incident.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
