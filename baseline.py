from datetime import datetime, timedelta
from statistics import mean, pstdev

from sqlalchemy import text
from sqlalchemy.orm import Session


def calculate_baseline(
    db: Session,
    lookback_minutes: int = 30,
    skip_recent_minutes: int = 5,
):
    now_minute = datetime.utcnow().replace(second=0, microsecond=0)
    window_end = now_minute - timedelta(minutes=skip_recent_minutes)
    window_start = window_end - timedelta(minutes=lookback_minutes)

    rows = db.execute(
        text(
            """
            SELECT service_name, COUNT(*) AS error_count
            FROM errors
            WHERE occurred_at >= :window_start AND occurred_at < :window_end
            GROUP BY service_name, date_trunc('minute', occurred_at)
            """
        ),
        {"window_start": window_start, "window_end": window_end},
    ).fetchall()

    counts_by_service = {}
    for service_name, error_count in rows:
        counts_by_service.setdefault(service_name, []).append(error_count)

    services = []
    for service_name, counts in sorted(counts_by_service.items()):
        quiet_minutes = lookback_minutes - len(counts)
        counts = counts + [0] * max(0, quiet_minutes)
        services.append(
            {
                "service": service_name,
                "mean": round(mean(counts), 2),
                "std_dev": round(pstdev(counts), 2),
            }
        )

    return {
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "lookback_minutes": lookback_minutes,
        "services": services,
    }
