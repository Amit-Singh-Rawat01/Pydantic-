from datetime import datetime, timedelta
from statistics import mean, pstdev, stdev

from sqlalchemy import text
from sqlalchemy.orm import Session


BASELINE_MINUTES = 30
MIN_BASELINE_MINUTES = 5
WARNING_Z = 2.0
ANOMALY_Z = 3.0


def classify_z_score(z_score):
    if z_score is None:
        return "NO_DATA"
    if z_score >= ANOMALY_Z:
        return "ANOMALY"
    if z_score >= WARNING_Z:
        return "WARNING"
    return "NORMAL"


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


def calculate_anomaly_scores(db: Session):
    now_minute = datetime.utcnow().replace(second=0, microsecond=0)
    current_minute = now_minute - timedelta(minutes=1)
    baseline_start = now_minute - timedelta(minutes=BASELINE_MINUTES + 1)

    rows = db.execute(
        text(
            """
            SELECT service_name,
                   date_trunc('minute', occurred_at) AS error_minute,
                   COUNT(*) AS error_count
            FROM errors
            WHERE occurred_at >= :baseline_start
              AND occurred_at < :window_end
            GROUP BY service_name, error_minute
            """
        ),
        {"baseline_start": baseline_start, "window_end": now_minute},
    ).fetchall()

    counts_by_service = {}
    for service_name, error_minute, error_count in rows:
        counts_by_service.setdefault(service_name, {})[error_minute] = error_count

    results = []
    for service_name, minute_counts in sorted(counts_by_service.items()):
        history = [
            minute_counts.get(
                baseline_start + timedelta(minutes=offset),
                0,
            )
            for offset in range(BASELINE_MINUTES)
        ]
        observed_history_minutes = [
            minute for minute in minute_counts if minute < current_minute
        ]
        available_minutes = (
            min(
                BASELINE_MINUTES,
                int(
                    (current_minute - min(observed_history_minutes)).total_seconds()
                    // 60
                ),
            )
            if observed_history_minutes
            else 0
        )
        current_count = minute_counts.get(current_minute, 0)

        if available_minutes < MIN_BASELINE_MINUTES:
            results.append(
                {
                    "service": service_name,
                    "current": current_count,
                    "z_score": None,
                    "status": classify_z_score(None),
                }
            )
            continue

        baseline_counts = history[-available_minutes:]
        average = mean(baseline_counts)
        std_dev = stdev(baseline_counts)
        z_score = (current_count - average) / max(std_dev, 1)

        results.append(
            {
                "service": service_name,
                "current": current_count,
                "mean": round(average, 2),
                "std_dev": round(std_dev, 2),
                "z_score": round(z_score, 2),
                "status": classify_z_score(z_score),
            }
        )

    return results
