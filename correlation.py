from datetime import timedelta

from sqlalchemy.orm import Session

from models import AnomalyIncident


CORRELATION_WINDOW = timedelta(minutes=5)


def find_correlation(db: Session) -> dict:
    """Return a probable root cause and nearby open incidents, if any."""
    open_incidents = (
        db.query(AnomalyIncident)
        .filter(AnomalyIncident.status == "OPEN")
        .order_by(AnomalyIncident.started_at.asc())
        .all()
    )

    for index, root in enumerate(open_incidents):
        followers = [
            incident
            for incident in open_incidents[index + 1 :]
            if incident.started_at - root.started_at <= CORRELATION_WINDOW
        ]
        if followers:
            return {
                "root_cause": {
                    "service_name": root.service_name,
                    "started_at": root.started_at,
                    "top_error": root.top_error,
                },
                "affected": [
                    {
                        "service_name": incident.service_name,
                        "lag_seconds": round(
                            (incident.started_at - root.started_at).total_seconds()
                        ),
                        "top_error": incident.top_error,
                    }
                    for incident in followers
                ],
            }

    return {"root_cause": None, "affected": []}
