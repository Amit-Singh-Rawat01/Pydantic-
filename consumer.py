import json
import logging
import os
import random
import sys
import threading
import time

from kafka import KafkaConsumer
from kafka.errors import KafkaError
from pydantic import ValidationError
from prometheus_client import Counter, Gauge, Histogram, start_http_server
from redis_counters import count_error
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import OperationalError

from database import SessionLocal
import models
from schemas import ErrorEventSchema
from fingerprint import generate_fingerprint

from incident_detector import check_and_create_incident


MAX_PAYLOAD_LENGTH = 2000
MAX_REASON_LENGTH = 500
CRASH_AFTER = int(sys.argv[1]) if len(sys.argv) > 1 else 0

EVENTS = Counter(
    "consumer_events_total",
    "Consumer events by processing result",
    ["result"],
)
LAG = Gauge(
    "consumer_lag",
    "Kafka events queued but not yet fetched by this consumer",
)
EVENT_SECONDS = Histogram(
    "consumer_event_seconds",
    "Ek event ko process karne mein kitna time laga",
    buckets=(0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

for result in ("saved", "duplicate", "rejected", "db_error"):
    EVENTS.labels(result=result)


def update_lag(consumer):
    try:
        partitions = list(consumer.assignment())
        if not partitions:
            return
        end_offsets = consumer.end_offsets(partitions)
        lag = sum(
            end_offsets[partition] - consumer.position(partition)
            for partition in partitions
        )
        LAG.set(max(lag, 0))
    except Exception as error:
        print(f"lag naapna fail: {error}")


def run_lag_updates(consumer):
    last_lag = 0.0
    while not getattr(consumer, "closed", False):
        now = time.time()
        if now - last_lag >= 5:
            update_lag(consumer)
            last_lag = now
        time.sleep(1)


class BatchCommitter:
    """Commit Kafka offsets after a batch of processed events or elapsed time."""

    def __init__(self, consumer, every=100, interval=5):
        self.consumer = consumer
        self.every = every
        self.interval = interval
        self.pending = 0
        self.last_commit = time.monotonic()

    def event_done(self):
        self.pending += 1
        if (
            self.pending >= self.every
            or time.monotonic() - self.last_commit >= self.interval
        ):
            self.consumer.commit()
            self.pending = 0
            self.last_commit = time.monotonic()


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
        return True
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

    return False



KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:29092",
)


def create_consumer_with_retry():
    wait = 2
    while True:
        try:
            consumer = KafkaConsumer(
                "errors-topic",
                bootstrap_servers=[KAFKA_BOOTSTRAP_SERVERS],
                bootstrap_timeout_ms=2000,
                value_deserializer=lambda m: m,
                auto_offset_reset="earliest",
                enable_auto_commit=False,
                group_id="error-consumer",
            )
            print("[KAFKA OK] consumer connected")
            return consumer
        except KafkaError as error:
            print(
                f"[KAFKA WAIT] Kafka unavailable - "
                f"{type(error).__name__}; retrying in {wait}s"
            )
            time.sleep(wait)
            wait = min(wait * 2, 30)


start_http_server(8001)

while True:
    consumer = create_consumer_with_retry()
    committer = BatchCommitter(consumer)
    lag_thread = threading.Thread(
        target=run_lag_updates,
        args=(consumer,),
        daemon=True,
        name="consumer-lag",
    )
    lag_thread.start()

    print(
        f"Consumer started. Kafka: {KAFKA_BOOTSTRAP_SERVERS}"
    )

    try:
        saved_this_run = 0
        for message in consumer:
            commit_event = False
            with EVENT_SECONDS.time():
                if os.path.exists("slow.on") and random.random() < 0.02:
                    time.sleep(0.2)

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

                        stmt = pg_insert(models.Error).values(
                            service_name=validated_event.service_name,
                            error_type=validated_event.error_type,
                            message=validated_event.message,
                            severity=validated_event.severity.value,
                            stack_trace=validated_event.stack_trace,
                            occurred_at=validated_event.occurred_at,
                            fingerprint=fp,
                            kafka_partition=message.partition,
                            kafka_offset=message.offset,
                            event_id=validated_event.event_id,
                        )
                        stmt = stmt.on_conflict_do_nothing()

                        insert_result = db.execute(stmt)

                        if insert_result.rowcount:
                            check_and_create_incident(
                                db,
                                validated_event.service_name,
                                validated_event.error_type,
                                validated_event.severity.value,
                            )

                            print(
                                f"Saved to DB successfully. "
                                f"Fingerprint: {fp}"
                            )
                        else:
                            print(
                                "[SKIP] duplicate event ignored: "
                                f"partition={message.partition}, "
                                f"offset={message.offset}, "
                                f"event_id={validated_event.event_id}"
                            )

                        db.commit()
                        if not insert_result.rowcount:
                            EVENTS.labels(result="duplicate").inc()
                    except OperationalError as e:
                        print(
                            f"[DB WRITE FAILED] Database unreachable — "
                            f"'{validated_event.service_name}' ka event save nahi hua."
                        )
                        if db:
                            db.rollback()
                        EVENTS.labels(result="db_error").inc()
                        raise
                    except Exception as e:
                        print(
                            f"[DB WRITE FAILED] Unexpected error saving "
                            f"'{validated_event.service_name}': {e}"
                        )
                        if db:
                            db.rollback()
                        EVENTS.labels(result="db_error").inc()
                        raise

                    if insert_result.rowcount:
                        count_error(
                            validated_event.service_name,
                            validated_event.occurred_at,
                        )

                        saved_this_run += 1
                        EVENTS.labels(result="saved").inc()
                        if CRASH_AFTER and saved_this_run == CRASH_AFTER:
                            print(
                                f"[CRASH] event #{saved_this_run} save hua, commit nahi hua",
                                flush=True,
                            )
                            os._exit(1)

                    commit_event = True

                except (
                    UnicodeDecodeError,
                    json.JSONDecodeError,
                    ValidationError,
                    ValueError,
                ) as e:
                    print(f"[REJECTED] Invalid event skipped. Reason: {e}")
                    rejected_saved = save_rejected_event(
                        raw_message,
                        f"{type(e).__name__}: {e}",
                    )
                    if not rejected_saved:
                        raise RuntimeError(
                            "Rejected event could not be persisted; offset not committed"
                        )
                    EVENTS.labels(result="rejected").inc()
                    commit_event = True

                except Exception as e:
                    if db:
                        db.rollback()

                    print(f"Consumer error: {e}")
                    raise

                finally:
                    if db:
                        db.close()

            if commit_event:
                committer.event_done()
    except KafkaError as error:
        print(
            f"[KAFKA RETRY] connection lost - "
            f"{type(error).__name__}; reconnecting"
        )
        consumer.close()