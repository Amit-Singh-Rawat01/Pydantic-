"""Send concurrent traffic from one noisy service and one quiet service."""

import threading
import time
from collections import Counter
from datetime import datetime, timezone

import requests

try:
    from uuid import uuid7
except ImportError:
    from uuid6 import uuid7

URL = "http://127.0.0.1:8002/v1/ingest"
SECONDS = 20
NOISY = "noisy-test"
QUIET = "quiet-test"

results = {NOISY: Counter(), QUIET: Counter()}
lock = threading.Lock()


def make_event(service: str) -> dict[str, str]:
    return {
        "event_id": str(uuid7()),
        "service_name": service,
        "error_type": "RateLimitTest",
        "message": "noisy neighbor test",
        "severity": "LOW",
        "stack_trace": "test",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }


def worker(service: str, pause: float, stop_at: float) -> None:
    session = requests.Session()
    while time.time() < stop_at:
        try:
            code: int | str = session.post(
                URL,
                json=make_event(service),
                timeout=5,
            ).status_code
        except requests.RequestException:
            code = "no_reply"
        with lock:
            results[service][code] += 1
        time.sleep(pause)


def main() -> None:
    first = requests.post(URL, json=make_event(QUIET), timeout=5)
    if first.status_code != 202:
        raise SystemExit(
            f"Pehla hi parcel andar nahi gaya: {first.status_code} {first.text}"
        )

    stop_at = time.time() + SECONDS
    threads = [
        threading.Thread(target=worker, args=(NOISY, 0.05, stop_at))
        for _ in range(20)
    ]
    threads.append(threading.Thread(target=worker, args=(QUIET, 0.5, stop_at)))
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    for service, counts in results.items():
        total = sum(counts.values())
        accepted = counts[202]
        percentage = accepted / total if total else 0
        print(
            f"{service}: bheje={total} accepted={accepted} "
            f"({percentage:.0%}) jawab={dict(counts)}"
        )


if __name__ == "__main__":
    main()
