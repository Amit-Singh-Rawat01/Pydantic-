import json
import random
import sys
import time

from kafka import KafkaProducer


# -----------------------------------
# 1. Service name command line se lo
# -----------------------------------

if len(sys.argv) < 2:
    print("Usage: python producer.py <service_name>")
    sys.exit(1)

SERVICE_NAME = sys.argv[1]


# -----------------------------------
# 2. Har service ke typical errors
# -----------------------------------

ERROR_PROFILES = {
    "auth-service": [
        "InvalidCredentialsError",
        "TokenExpiredError",
        "SessionNotFoundError"
    ],

    "payment-service": [
        "PaymentGatewayTimeout",
        "InsufficientFundsError",
        "CardDeclinedError"
    ],

    "order-service": [
        "OrderValidationError",
        "InventoryMismatchError",
        "DuplicateOrderError"
    ]
}


# Service ke errors nikalo
error_types = ERROR_PROFILES.get(
    SERVICE_NAME,
    ["GenericError"]
)


# -----------------------------------
# 3. Kafka Producer
# -----------------------------------

try:
    producer = KafkaProducer(
        bootstrap_servers=["localhost:9092"],
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )

    print(f"{SERVICE_NAME} connected to Kafka.")

except Exception as e:
    print(f"Kafka connection setup failed: {e}")
    producer = None


# -----------------------------------
# 4. Existing main.py function
# -----------------------------------

def send_error_to_kafka(error_data: dict):

    if not producer:
        print("Kafka producer initialized nahi hai.")
        return False

    try:
        producer.send("errors-topic", error_data)
        producer.flush()

        return True

    except Exception as e:
        print(f"Kafka publish failed: {e}")
        return False


# -----------------------------------
# 5. Standalone service simulator
# -----------------------------------

if __name__ == "__main__":

    if producer is None:
        sys.exit(1)

    print(f"{SERVICE_NAME} started.")
    print(f"Possible errors: {error_types}")

    while True:

        error_type = random.choice(error_types)

        error_data = {
            "service_name": SERVICE_NAME,
            "error_type": error_type,
            "severity": random.choice(
                ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            ),
            "message": f"{error_type} occurred in {SERVICE_NAME}"
        }

        success = send_error_to_kafka(error_data)

        if success:
            print(f"Sent: {error_data}")

        time.sleep(random.randint(2, 5))