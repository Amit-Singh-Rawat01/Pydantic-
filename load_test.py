import csv
import json
import os
import sys
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")
LABEL = "commit-100"
TIMEOUT_SECONDS = 300
REQUEST_TIMEOUT_SECONDS = 5
RESULTS_FILE = Path(__file__).with_name("load_test_results.csv")


def send_one_event():
    event_id = uuid.uuid4().hex
    event = {
        "service_name": "load-test",
        "error_type": "LoadTestEvent",
        "message": f"Load-test event {event_id}",
        "severity": "LOW",
        "stack_trace": f"Load-test event ID: {event_id}",
    }
    request = Request(
        f"{API_URL}/errors",
        data=json.dumps(event).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS):
        pass


def flush_sender():
    pass


def get_total():
    metrics_url = (
        f"{API_URL}/metrics/total-errors?"
        f"{urlencode({'service_name': 'load-test'})}"
    )
    try:
        with urlopen(metrics_url, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.load(response)["total"]
    except HTTPError as error:
        if error.code != 404:
            raise
        errors_url = (
            f"{API_URL}/errors?"
            f"{urlencode({'service_name': 'load-test', 'limit': 1})}"
        )

    with urlopen(errors_url, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.load(response)["total"]


def run(n):
    if n <= 0:
        raise ValueError("The number of events must be greater than zero")

    start_total = get_total()

    t0 = time.monotonic()
    for _ in range(n):
        send_one_event()
    flush_sender()
    send_time = max(time.monotonic() - t0, 0.001)

    while get_total() < start_total + n:
        if time.monotonic() - t0 > TIMEOUT_SECONDS:
            print(f"Timeout: {n} events mein se sab DB tak nahi pahunche")
            return False
        time.sleep(0.5)
    drain_time = time.monotonic() - t0

    print(f"events            : {n}")
    print(f"bhejne ki speed   : {n / send_time:.1f} events/sec ({send_time:.1f}s)")
    print(f"poori pipeline    : {n / drain_time:.1f} events/sec ({drain_time:.1f}s)")
    print(f"consumer ko extra : {drain_time - send_time:.1f}s")

    new_file = not RESULTS_FILE.exists() or RESULTS_FILE.stat().st_size == 0
    with RESULTS_FILE.open("a", newline="", encoding="utf-8") as results:
        writer = csv.writer(results)
        if new_file:
            writer.writerow(
                [
                    "label",
                    "events",
                    "send_seconds",
                    "pipeline_seconds",
                    "events_per_sec",
                ]
            )
        writer.writerow(
            [
                LABEL,
                n,
                round(send_time, 2),
                round(drain_time, 2),
                round(n / drain_time, 2),
            ]
        )
    return True


def run_drain(n):
    """Queue events while the consumer is stopped, then measure its drain speed."""
    if n <= 0:
        raise ValueError("The number of events must be greater than zero")

    start_total = get_total()

    for _ in range(n):
        send_one_event()
    flush_sender()
    print(f"{n} events jama ho gaye. Ab consumer chalu karo.")

    wait_started = time.monotonic()
    while get_total() == start_total:
        if time.monotonic() - wait_started > TIMEOUT_SECONDS:
            print("Timeout: sab events DB tak nahi pahunche")
            return False
        time.sleep(0.1)
    t0 = time.monotonic()

    while get_total() < start_total + n:
        if time.monotonic() - t0 > TIMEOUT_SECONDS:
            print("Timeout: sab events DB tak nahi pahunche")
            return False
        time.sleep(0.5)
    drain_time = max(time.monotonic() - t0, 0.001)

    time.sleep(2)
    extra = get_total() - (start_total + n)

    print(f"consumer ki speed : {n / drain_time:.0f} events/sec ({drain_time:.1f}s)")
    print(f"extra/duplicate   : {extra}")

    new_file = not RESULTS_FILE.exists() or RESULTS_FILE.stat().st_size == 0
    with RESULTS_FILE.open("a", newline="", encoding="utf-8") as results:
        writer = csv.writer(results)
        if new_file:
            writer.writerow(
                [
                    "label",
                    "events",
                    "send_seconds",
                    "pipeline_seconds",
                    "events_per_sec",
                ]
            )
        writer.writerow(
            [
                f"{LABEL}-drain",
                n,
                "",
                round(drain_time, 2),
                round(n / drain_time),
            ]
        )
    return True


if __name__ == "__main__":
    try:
        event_count = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
        mode = sys.argv[2] if len(sys.argv) > 2 else "end-to-end"
        if mode == "drain":
            succeeded = run_drain(event_count)
        else:
            succeeded = run(event_count)
    except ValueError as error:
        print(f"Invalid event count: {error}", file=sys.stderr)
        sys.exit(2)
    sys.exit(0 if succeeded else 1)
