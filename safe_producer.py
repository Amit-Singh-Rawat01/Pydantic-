import json
import os
import sys
import threading
import time
from collections import deque

from kafka import KafkaProducer
from kafka.errors import KafkaError


if sys.platform != "win32" and os.path.exists("/.dockerenv"):
    BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
else:
    BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

TOPIC = "errors-topic"
RETRY_EVERY_SECONDS = 10
BUFFER_LIMIT = 500

_producer = None
_buffer = deque()
_next_try_at = 0.0
_dropped = 0
_lock = threading.Lock()


def send_event(event: dict) -> str:
    """Send an event or retain it in memory until Kafka is available."""
    global _producer, _next_try_at, _dropped

    with _lock:
        _buffer.append(event)
        if len(_buffer) > BUFFER_LIMIT:
            _buffer.popleft()
            _dropped += 1
            print(
                f"[BUFFER FULL] oldest event dropped "
                f"(total dropped: {_dropped})"
            )

        if time.time() < _next_try_at:
            return "buffered"

        try:
            if _producer is None:
                _producer = KafkaProducer(
                    bootstrap_servers=[BOOTSTRAP_SERVERS],
                    api_version=(2, 0),
                    value_serializer=lambda value: json.dumps(
                        value, default=str
                    ).encode("utf-8"),
                    bootstrap_timeout_ms=2000,
                    max_block_ms=2000,
                )
                print("[KAFKA OK] connected")

            sent = 0
            while _buffer:
                _producer.send(TOPIC, value=_buffer[0]).get(timeout=2)
                _buffer.popleft()
                sent += 1

            if sent > 1:
                print(
                    f"[KAFKA OK] recovered - sent {sent} pending events"
                )
            _next_try_at = 0.0
            return "sent"

        except KafkaError as error:
            _next_try_at = time.time() + RETRY_EVERY_SECONDS
            print(
                f"[KAFKA DOWN] {type(error).__name__} - "
                f"{len(_buffer)} events buffered, retrying in "
                f"{RETRY_EVERY_SECONDS}s"
            )
            return "buffered"