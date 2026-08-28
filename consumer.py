import json
import os
from datetime import datetime

from kafka import KafkaConsumer
from redis_client import redis_client

from database import SessionLocal
import models
from fingerprint import generate_fingerprint

import time



def update_realtime_counters(service_name):
    redis_client.incr("errors:total")

    minute_bucket = int(time.time() // 60)
    minute_key = f"errors:minute:{minute_bucket}"

    redis_client.incr(minute_key)
    redis_client.expire(minute_key, 120)

    redis_client.incr(f"errors:service:{service_name}")


KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:29092",
)


consumer = KafkaConsumer(
    "errors-topic",
    bootstrap_servers=[KAFKA_BOOTSTRAP_SERVERS],
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    group_id="error-consumer",
)

print(
    f"Consumer started. Kafka: {KAFKA_BOOTSTRAP_SERVERS}"
)

for message in consumer:
    db = None

    try:
        error_data = message.value

        print(f"Received from Kafka: {error_data}")

        if not isinstance(error_data, dict):
            raise ValueError(
                "Kafka message is not a valid dictionary"
            )

        fp = generate_fingerprint(
            service_name=error_data["service_name"],
            error_type=error_data["error_type"],
            message=error_data["message"],
        )

        db = SessionLocal()

        new_error = models.Error(
            service_name=error_data["service_name"],
            error_type=error_data["error_type"],
            message=error_data["message"],
            severity=error_data["severity"],
            stack_trace=error_data.get("stack_trace"),
            occurred_at=error_data.get("occurred_at"),
            fingerprint=fp,
        )

        db.add(new_error)
        db.commit()

        print(
            f"Saved to DB successfully. "
            f"Fingerprint: {fp}"
        )

        update_realtime_counters(
        error_data["service_name"]
        )
        

        print("Redis counters updated.")

    except Exception as e:
        if db:
            db.rollback()

        print(f"Consumer error: {e}")

    finally:
        if db:
            db.close()