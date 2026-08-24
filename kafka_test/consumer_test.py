from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    "python-error-events",
    bootstrap_servers=["localhost:9092"],
    auto_offset_reset="earliest",
    group_id="python-test-group",
    enable_auto_commit=True,
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    consumer_timeout_ms=10000
)

print("Listening...")

try:
    for message in consumer:
        print(f"Received: {message.value}")
finally:
    consumer.close()