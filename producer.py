import json
import random
import sys
import time
from kafka import KafkaProducer


# -----------------------------------
# 1. Kafka Producer Factory
# -----------------------------------

def create_kafka_producer():
    """
    Docker ke andar Kafka:
        kafka:9092

    Windows/host machine par Kafka:
        localhost:9092
    """

    # Docker container ke andar /.dockerenv file hoti hai
    if sys.platform != "win32" and __import__("os").path.exists("/.dockerenv"):
        bootstrap_server = "kafka:9092"
    else:
        bootstrap_server = "localhost:9092"

    return KafkaProducer(
        bootstrap_servers=[bootstrap_server],
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )


# -----------------------------------
# 2. Reusable Kafka send function
# -----------------------------------

def send_error_to_kafka(error_data: dict) -> bool:
    """
    FastAPI /errors endpoint is function ko use karega.
    """

    producer = None

    try:
        producer = create_kafka_producer()

        future = producer.send(
            "errors-topic",
            value=error_data,
        )

        # Kafka acknowledgement ka wait
        future.get(timeout=10)

        producer.flush()

        print(f"Sent to Kafka: {error_data}")

        return True

    except Exception as e:
        print(f"Kafka publish failed: {e}")
        return False

    finally:
        if producer:
            producer.close()


# -----------------------------------
# 3. Service error profiles
# -----------------------------------

ERROR_PROFILES = {
    "auth-service": [
        "InvalidCredentialsError",
        "TokenExpiredError",
        "SessionNotFoundError",
    ],

    "payment-service": [
        "PaymentGatewayTimeout",
        "InsufficientFundsError",
        "CardDeclinedError",
    ],

    "order-service": [
        "OrderValidationError",
        "InventoryMismatchError",
        "DuplicateOrderError",
    ],
}


# -----------------------------------
# 4. Standalone Service Simulator
# -----------------------------------

def run_simulator(service_name: str):

    error_types = ERROR_PROFILES.get(
        service_name,
        ["GenericError"],
    )

    print(f"{service_name} started.")
    print(f"Possible errors: {error_types}")

    while True:

        error_type = random.choice(error_types)

        error_data = {
            "service_name": service_name,
            "error_type": error_type,
            "severity": random.choice(
                ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            ),
            "message": f"{error_type} occurred in {service_name}",
        }

        success = send_error_to_kafka(error_data)

        if success:
            print(f"Sent: {error_data}")
        else:
            print("Failed to send error to Kafka.")

        time.sleep(random.randint(2, 5))


# -----------------------------------
# 5. Simulator entry point
# -----------------------------------

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: python producer.py <service_name>")
        sys.exit(1)

    service_name = sys.argv[1]

    run_simulator(service_name)