import json
from datetime import datetime
from kafka import KafkaConsumer
import redis
from database import SessionLocal
import models

# 1. Redis Connection Setup
r = redis.Redis(host="localhost", port=6379, decode_responses=True)


# 2. Redis Counter Function
def update_realtime_counters():
    r.incr("errors:total")
    minute_key = f"errors:minute:{datetime.utcnow().strftime('%Y%m%d%H%M')}"
    r.incr(minute_key)
    r.expire(minute_key, 120)


consumer = KafkaConsumer(
    "errors-topic",
    bootstrap_servers=["localhost:9092"],
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    auto_offset_reset="earliest",
    enable_auto_commit=False,
    group_id=None,
)

print("Consumer started. Waiting for messages...")

for message in consumer:
    db = None

    try:
        error_data = message.value

        print(f"Received from Kafka: {error_data}")

        if not isinstance(error_data, dict):
            raise ValueError("Kafka message is not a valid dictionary")

        db = SessionLocal()
        db_error = models.Error(
            service_name=error_data.get("service_name"),
            error_type=error_data.get("error_type"),
            message=error_data.get("message"),
            severity=error_data.get("severity"),
            stack_trace=error_data.get("stack_trace"),
        )

        db.add(db_error)
        db.commit()

        print("Successfully saved to DB!")

        # 3. YAHAN CALL KARNA HAI (DB commit successful hone ke baad)
        update_realtime_counters()

    except Exception as e:
        if db:
            db.rollback()

        print(f"Skipping bad message or DB failure: {e}")

    finally:
        if db:
            db.close()