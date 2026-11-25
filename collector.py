import asyncio
import os
import time
import uuid
from datetime import datetime
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Response
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, ConfigDict, Field

from safe_producer import send_event as send_to_kafka


app = FastAPI(title="Collector")

INGEST = Counter(
    "ingest_events_total",
    "Darwaze par kitne events kis nateeje ke saath aaye",
    ["result"],
)
INGEST_SECONDS = Histogram(
    "ingest_seconds",
    "Darwaze par ek request mein kitna time laga",
    buckets=(0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

MAX_IN_FLIGHT = 8
SLOTS = asyncio.Semaphore(MAX_IN_FLIGHT)
IN_FLIGHT = Gauge(
    "ingest_in_flight",
    "Abhi kitne events line mein daale ja rahe hain",
)

for result in ("accepted", "invalid", "kafka_error", "throttled"):
    INGEST.labels(result=result)


def publish(payload):
    if os.path.exists("slow_kafka.on"):
        time.sleep(0.2)
    return send_to_kafka(payload)


class IngestEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    service_name: str = Field(min_length=1, max_length=100)
    error_type: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=2000)
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    stack_trace: Optional[str] = Field(default=None, max_length=20000)
    occurred_at: datetime


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.exception_handler(RequestValidationError)
async def count_invalid(request, exc):
    if request.url.path == "/v1/ingest":
        INGEST.labels(result="invalid").inc()
    return await request_validation_exception_handler(request, exc)


@app.post("/v1/ingest", status_code=202)
async def ingest(event: IngestEvent):
    if SLOTS.locked():
        INGEST.labels(result="throttled").inc()
        raise HTTPException(
            status_code=429,
            detail="Bheed zyada hai, thodi der baad aana",
            headers={"Retry-After": "1"},
        )

    async with SLOTS:
        with IN_FLIGHT.track_inprogress():
            with INGEST_SECONDS.time():
                payload = event.model_dump(mode="json")
                payload["event_id"] = str(uuid.uuid4())
                try:
                    await asyncio.to_thread(publish, payload)
                except Exception as error:
                    INGEST.labels(result="kafka_error").inc()
                    print(f"ingest: Kafka tak nahi pahunch paaye: {error}")
                    raise HTTPException(
                        status_code=503,
                        detail="Kafka tak nahi pahunch paaye",
                    )
    INGEST.labels(result="accepted").inc()
    return {"status": "accepted"}
