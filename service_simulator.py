import os
import random
import sys
import time

import requests

API_URL = "http://127.0.0.1:8000/errors"
TICK = 0.5
NORMAL_CHANCE = 0.005
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

NORMAL_ERRORS = {
    "payment-service": [
        ("CardDeclined", "Card was declined by the bank", "LOW"),
        ("PaymentRetry", "Payment needed a retry", "MEDIUM"),
        ("InvalidCoupon", "Coupon code is invalid", "LOW"),
    ],
    "auth-service": [
        ("InvalidToken", "Token expired or invalid", "LOW"),
        ("LoginFailed", "Wrong password entered", "LOW"),
        ("SlowLogin", "Login took longer than 3 seconds", "MEDIUM"),
    ],
    "order-service": [
        ("OutOfStock", "Requested item is out of stock", "LOW"),
        ("AddressMissing", "Delivery address is missing", "MEDIUM"),
        ("SlowCheckout", "Checkout took longer than 4 seconds", "MEDIUM"),
    ],
}

FAILURE_ERRORS = {
    "payment-service": (
        "PaymentGatewayTimeout",
        "Payment gateway did not respond in 5 seconds",
        "CRITICAL",
    ),
    "auth-service": (
        "TokenServiceDown",
        "Token service is unreachable",
        "CRITICAL",
    ),
    "order-service": (
        "DatabaseConnectionError",
        "Could not connect to orders database",
        "CRITICAL",
    ),
}


def flag_path(service_name):
    return os.path.join(BASE_DIR, f"fail_{service_name}.flag")


def is_failing(service_name):
    return os.path.exists(flag_path(service_name))


def make_event(service_name, error):
    error_type, message, severity = error
    return {
        "service_name": service_name,
        "error_type": error_type,
        "message": message,
        "severity": severity,
        "stack_trace": f"{error_type} raised in {service_name}",
    }


def send_event(event):
    try:
        response = requests.post(API_URL, json=event, timeout=3)
        print(
            f"[{event['service_name']}] {event['severity']:<8} "
            f"{event['error_type']} -> {response.status_code}"
        )
    except requests.RequestException as error:
        print(f"[{event['service_name']}] bhejne me dikkat: {error}")


def run_service(service_name):
    print(f"{service_name} chalu. Rokne ke liye Ctrl+C dabao.")
    send_event(make_event(service_name, random.choice(NORMAL_ERRORS[service_name])))
    while True:
        if is_failing(service_name):
            send_event(make_event(service_name, FAILURE_ERRORS[service_name]))
        elif random.random() < NORMAL_CHANCE:
            send_event(make_event(service_name, random.choice(NORMAL_ERRORS[service_name])))
        time.sleep(TICK)


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in NORMAL_ERRORS:
        print("Use: python service_simulator.py <service-name>")
        print("Services:", ", ".join(NORMAL_ERRORS))
        sys.exit(1)

    service_name = sys.argv[1]
    try:
        run_service(service_name)
    except KeyboardInterrupt:
        print(f"\n{service_name} band ho gayi.")