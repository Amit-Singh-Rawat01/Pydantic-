import requests
import random
import time

API_URL = "http://127.0.0.1:8000/errors"

SERVICES = [
    "auth-service",
    "payment-service",
    "inventory-service",
    "notification-service",
    "search-service"
]

ERROR_TYPES = [
    "ConnectionTimeout",
    "NullPointerException",
    "ValidationError",
    "DatabaseError",
    "RateLimitExceeded"
]

SEVERITIES = [
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL"
]

MESSAGES = {
    "ConnectionTimeout": "Connection to downstream service timed out",
    "NullPointerException": "Attempted to access a null object reference",
    "ValidationError": "Request payload failed schema validation",
    "DatabaseError": "Database query execution failed",
    "RateLimitExceeded": "Too many requests received in short window",
}


def generate_fake_error():
    error_type = random.choice(ERROR_TYPES)

    return {
        "service_name": random.choice(SERVICES),
        "error_type": error_type,
        "message": MESSAGES[error_type],
        "severity": random.choice(SEVERITIES),
        "stack_trace": (
            f"Traceback (most recent call last):\n"
            f'  File "app.py", line {random.randint(10, 300)}, in handler\n'
            f"{error_type}: {MESSAGES[error_type]}"
        ),
    }


def send_error(error):
    try:
        response = requests.post(API_URL, json=error, timeout=3)

        if response.status_code in (200, 201):
            print(
                f"[SENT] {error['service_name']} -> "
                f"{error['error_type']} ({error['severity']})"
            )
        else:
            print(f"[FAILED] Status {response.status_code}: {response.text}")

    except requests.exceptions.ConnectionError:
        print("[ERROR] FastAPI server se connect nahi ho paya.")


def run_simulator(num_errors=20, delay_seconds=1):
    print(f"Simulator start... {num_errors} fake errors bhejenge\n")

    for _ in range(num_errors):
        error = generate_fake_error()
        send_error(error)
        time.sleep(delay_seconds)

    print("\nSimulator finished.")


if __name__ == "__main__":
    run_simulator(num_errors=20, delay_seconds=1)

def send_error(error):
    try:
        response = requests.post(API_URL, json=error, timeout=3)
        if response.status_code == 200:
            print("[SENT] Error queued successfully")
        else:
            print(f"[FAILED] Status {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"[TIMEOUT] Backend took too long to respond")