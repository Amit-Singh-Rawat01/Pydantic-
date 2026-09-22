import json
import logging
import os

from kafka import KafkaConsumer
from pydantic import ValidationError
from redis_client import redis_client
from sqlalchemy.exc import OperationalError

from database import SessionLocal
import models
from schemas import ErrorEventSchema
from fingerprint import generate_fingerprint

import time
from incident_detector import check_and_create_incident


MAX_PAYLOAD_LENGTH = 2000
MAX_REASON_LENGTH = 500


def save_rejected_event(raw_payload, reason):
    if isinstance(raw_payload, bytes):
        raw_payload = raw_payload.decode("utf-8", errors="replace")
    elif not isinstance(raw_payload, str):
        raw_payload = str(raw_payload)

    db = None
    try:
        db = SessionLocal()
        db.add(
            models.RejectedEvent(
                raw_payload=raw_payload[:MAX_PAYLOAD_LENGTH],
                reason=str(reason)[:MAX_REASON_LENGTH],
            )
        )
        db.commit()
    except OperationalError as e:
        logging.error(
            "[DB WRITE FAILED] Database unreachable; rejected event was not saved: %s",
            e,
        )
        if db:
            db.rollback()
    except Exception as e:
        logging.error(
            "[DB WRITE FAILED] Unexpected error saving rejected event: %s | payload: %s",
            e,
            raw_payload[:200],
        )
        if db:
            db.rollback()
    finally:
        if db:
            db.close()



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
    value_deserializer=lambda m: m,
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    group_id="error-consumer",
)

print(
    f"Consumer started. Kafka: {KAFKA_BOOTSTRAP_SERVERS}"
)

for message in consumer:
    db = None
    raw_message = message.value

    try:
        error_data = json.loads(raw_message.decode("utf-8"))

        print(f"Received from Kafka: {error_data}")

        if not isinstance(error_data, dict):
            raise ValueError("Kafka message must contain a JSON object")

        validated_event = ErrorEventSchema(**error_data)

        fp = generate_fingerprint(
            service_name=validated_event.service_name,
            error_type=validated_event.error_type,
        )

        try:
            db = SessionLocal()

            new_error = models.Error(
                service_name=validated_event.service_name,
                error_type=validated_event.error_type,
                message=validated_event.message,
                severity=validated_event.severity.value,
                stack_trace=validated_event.stack_trace,
                occurred_at=validated_event.occurred_at,
                fingerprint=fp,
            )

            db.add(new_error)
            db.commit()

            check_and_create_incident(
                db,
                new_error.service_name,
                new_error.error_type,
                new_error.severity,
            )

            print(
                f"Saved to DB successfully. "
                f"Fingerprint: {fp}"
            )
        except OperationalError as e:
            print(
                f"[DB WRITE FAILED] Database unreachable — "
                f"'{validated_event.service_name}' ka event save nahi hua."
            )
            if db:
                db.rollback()
        except Exception as e:
            print(
                f"[DB WRITE FAILED] Unexpected error saving "
                f"'{validated_event.service_name}': {e}"
            )
            if db:
                db.rollback()

        update_realtime_counters(
        validated_event.service_name
        )
        

        print("Redis counters updated.")

    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValidationError,
        ValueError,
    ) as e:
        print(f"[REJECTED] Invalid event skipped. Reason: {e}")
        save_rejected_event(raw_message, f"{type(e).__name__}: {e}")

    except Exception as e:
        if db:
            db.rollback()

        print(f"Consumer error: {e}")

    finally:
        if db:
            db.close()