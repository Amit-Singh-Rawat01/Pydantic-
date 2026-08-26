import json
from kafka import KafkaConsumer
from database import SessionLocal
import models


consumer = KafkaConsumer(
    "errors-topic",
    bootstrap_servers=["localhost:9092"],
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    auto_offset_reset="earliest",
    enable_auto_commit=False,
   group_id=None
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
            stack_trace=error_data.get("stack_trace")

        )

        db.add(db_error)
        db.commit()

        print("Successfully saved to DB!")

    except Exception as e:
        if db:
            db.rollback()

        print(f"Skipping bad message or DB failure: {e}")

    finally:
        if db:
            db.close()