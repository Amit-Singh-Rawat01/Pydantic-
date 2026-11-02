import csv
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests


API = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")
TARGET_SERVICE = "payment-service"
SWITCH_FILE = Path(__file__).with_name(f"fail_{TARGET_SERVICE}.flag")
ROUNDS = 3
HOLD_SECONDS = 30
COOLDOWN_SECONDS = 60
TIMEOUT = 180
REQUEST_TIMEOUT = 5
RESULTS_FILE = Path(__file__).with_name("chain_test_results.csv")


def set_switch(on: bool) -> None:
    """Control the simulator's file-existence failure switch."""
    if on:
        SWITCH_FILE.touch()
    elif SWITCH_FILE.exists():
        SWITCH_FILE.unlink()


def get_incidents():
    response = requests.get(f"{API}/anomaly-incidents", timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def open_incident():
    """Return the target service's OPEN incident, if one exists."""
    for incident in get_incidents():
        if (
            incident["service_name"] == TARGET_SERVICE
            and incident["status"] == "OPEN"
        ):
            return incident
    return None


def wait_until(check, timeout):
    """Return elapsed seconds and the first truthy check result, or (None, None)."""
    started = time.monotonic()
    while time.monotonic() - started < timeout:
        answer = check()
        if answer:
            return time.monotonic() - started, answer
        time.sleep(1)
    return None, None


def run_round(number):
    print(f"\n--- Round {number} ---")

    set_switch(False)
    waited, _ = wait_until(lambda: open_incident() is None, TIMEOUT)
    if waited is None:
        print("Pehle se OPEN incident pada hai aur band nahi ho raha. Round skip.")
        return None

    set_switch(True)
    detect, incident = wait_until(open_incident, TIMEOUT)
    if detect is None:
        set_switch(False)
        print(f"FAIL: {TIMEOUT}s mein incident nahi khula.")
        return None, None
    print(f"Incident {detect:.0f}s mein khula")

    time.sleep(HOLD_SECONDS)
    set_switch(False)

    incident_id = incident["id"]
    recover, _ = wait_until(
        lambda: next(
            (
                row
                for row in get_incidents()
                if row["id"] == incident_id and row["status"] == "RESOLVED"
            ),
            None,
        ),
        TIMEOUT,
    )
    if recover is None:
        print(f"FAIL: spike band hone ke {TIMEOUT}s baad bhi RESOLVED nahi hua.")
        return detect, None
    print(f"Spike band hone ke {recover:.0f}s baad RESOLVED")
    return detect, recover


def summary(values):
    if not values:
        return "koi number nahi"
    return (
        f"avg {sum(values) / len(values):.0f}s, "
        f"min {min(values):.0f}s, max {max(values):.0f}s"
    )


def save_results(results):
    new_file = not RESULTS_FILE.exists() or RESULTS_FILE.stat().st_size == 0
    with RESULTS_FILE.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        if new_file:
            writer.writerow(
                [
                    "timestamp",
                    "round",
                    "detection_seconds",
                    "recovery_seconds",
                    "status",
                ]
            )
        timestamp = datetime.now().isoformat(timespec="seconds")
        for number, result in enumerate(results, start=1):
            if result is None:
                detection, recovery, status = "", "", "SKIPPED"
            elif result == "ERROR":
                detection, recovery, status = "", "", "ERROR"
            else:
                detect_time, recover_time = result
                detection = "" if detect_time is None else round(detect_time)
                recovery = "" if recover_time is None else round(recover_time)
                if detect_time is None:
                    status = "FAIL_DETECTION"
                elif recover_time is None:
                    status = "FAIL_RECOVERY"
                else:
                    status = "PASS"
            writer.writerow([timestamp, number, detection, recovery, status])


def main():
    results = []
    try:
        try:
            response = requests.get(f"{API}/health", timeout=3)
            response.raise_for_status()
        except requests.RequestException as error:
            print(
                f"Backend nahi mil raha ({error}). Pehle backend chalao.",
                file=sys.stderr,
            )
            return False

        for number in range(1, ROUNDS + 1):
            try:
                result = run_round(number)
            except requests.RequestException as error:
                print(
                    f"Round {number} mein API request fail hui: {error}",
                    file=sys.stderr,
                )
                results.append("ERROR")
                break
            results.append(result)
            if result is None:
                print(f"Round {number} skip hua; agle round se pehle state check karein.")
            if number < ROUNDS:
                print(f"{COOLDOWN_SECONDS}s aaram...")
                time.sleep(COOLDOWN_SECONDS)
    finally:
        set_switch(False)

    save_results(results)

    round_results = [result for result in results if isinstance(result, tuple)]
    detects = [result[0] for result in round_results if result[0] is not None]
    recovers = [result[1] for result in round_results if result[1] is not None]
    print("\n=== Nateeja ===")
    print(
        f"Detection (spike ON -> incident OPEN):  "
        f"{summary(detects)}  [{len(detects)}/{ROUNDS} round]"
    )
    print(
        f"Recovery  (spike OFF -> RESOLVED):      "
        f"{summary(recovers)}  [{len(recovers)}/{ROUNDS} round]"
    )
    print(f"CSV: {RESULTS_FILE}")
    return len(results) == ROUNDS and all(
        isinstance(result, tuple)
        and result[0] is not None
        and result[1] is not None
        for result in results
    )


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
