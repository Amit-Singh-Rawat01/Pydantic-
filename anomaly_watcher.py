import time
from datetime import datetime

import requests


API_URL = "http://localhost:8000/metrics/anomaly-score"
EVENTS_URL = "http://localhost:8000/anomaly-events"
POLL_SECONDS = 10

last_status = {}


def now():
    return datetime.now().strftime("%H:%M:%S")


def to_rows(data):
    """Convert list or mapping responses to (service_name, info) pairs."""
    if isinstance(data, list):
        return [
            (row.get("service") or row.get("service_name"), row)
            for row in data
        ]
    return list(data.items())


def send_event(name, old_status, new_status, info):
    payload = {
        "service_name": name,
        "old_status": old_status,
        "new_status": new_status,
        "z_score": info.get("z_score"),
        "current_rate": info.get("current_rate", info.get("current")),
    }
    response = requests.post(EVENTS_URL, json=payload, timeout=5)
    response.raise_for_status()


def check_once():
    response = requests.get(API_URL, timeout=5)
    response.raise_for_status()

    for name, info in to_rows(response.json()):
        new_status = info.get("status")
        old_status = last_status.get(name)

        if new_status != old_status:
            tag = "ALERT" if new_status == "ANOMALY" else "INFO"
            rate = info.get("current_rate", info.get("current"))
            print(
                f"[{now()}] [{tag}] {name}: {old_status or 'START'} -> {new_status} "
                f"(z={info.get('z_score')}, rate={rate})"
            )
            send_event(name, old_status, new_status, info)
            last_status[name] = new_status


def main():
    print(
        f"Watcher start: har {POLL_SECONDS} sec mein check karega. "
        "Band karne ke liye Ctrl+C."
    )
    try:
        while True:
            try:
                check_once()
            except requests.RequestException as error:
                print(f"[{now()}] [WARN] backend request fail hui: {error}")
            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        print("\nWatcher band.")


if __name__ == "__main__":
    main()
