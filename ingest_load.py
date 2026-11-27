# python ingest_load.py [seconds] [clients] [retry]
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests

from ingest_client import new_event_id, send_event


URL = "http://localhost:8002/v1/ingest"
SECONDS = float(sys.argv[1]) if len(sys.argv) > 1 else 10
CLIENTS = int(sys.argv[2]) if len(sys.argv) > 2 else 100
RETRY = len(sys.argv) > 3 and sys.argv[3] == "retry"
THINK = 0.05


def make_event(i):
    return {
        "service_name": "load-test",
        "error_type": "LoadTestError",
        "message": f"ingest load test {i}",
        "severity": "LOW",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "event_id": new_event_id(),
    }


def worker(_):
    session = requests.Session()
    results = []
    end = time.time() + SECONDS
    i = 0
    while time.time() < end:
        i += 1
        started = time.perf_counter()
        if RETRY:
            code = 202 if send_event(make_event(i)) else -1
        else:
            try:
                code = session.post(
                    URL,
                    json=make_event(i),
                    timeout=10,
                ).status_code
            except requests.RequestException:
                code = 0
        results.append((code, time.perf_counter() - started))
        time.sleep(THINK)
    return results


if __name__ == "__main__":
    started = time.time()
    with ThreadPoolExecutor(max_workers=CLIENTS) as pool:
        results = [
            result
            for part in pool.map(worker, range(CLIENTS))
            for result in part
        ]
    total = time.time() - started

    print(f"{len(results)} requests, {CLIENTS} clients, {total:.1f}s")
    for code in sorted({status for status, _ in results}):
        latencies = sorted(
            elapsed
            for status, elapsed in results
            if status == code
        )
        p50 = latencies[len(latencies) // 2] * 1000
        p99 = latencies[
            min(len(latencies) - 1, int(len(latencies) * 0.99))
        ] * 1000
        print(
            f"  {code}: {len(latencies)} requests, "
            f"p50={p50:.0f} ms, p99={p99:.0f} ms"
        )
