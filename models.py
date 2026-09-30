from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from database import Base
from datetime import datetime, timezone

class Error(Base):
    __tablename__ = "errors"
    __table_args__ = (
        UniqueConstraint(
            "kafka_partition",
            "kafka_offset",
            name="uq_kafka_partition_offset",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String, nullable=False)
    error_type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String, nullable=False)
    stack_trace = Column(Text, nullable=True)
    occurred_at = Column(DateTime, default=func.now())
    fingerprint = Column(String, index=True)  
    kafka_partition = Column(Integer, nullable=True)
    kafka_offset = Column(BigInteger, nullable=True)


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    fingerprint = Column(String, index=True, nullable=False)
    service_name = Column(String, nullable=False)
    error_type = Column(String, nullable=False)
    sample_message = Column(Text, nullable=True)
    severity = Column(String, nullable=False)
    occurrence_count = Column(Integer, default=1)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="OPEN", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class RejectedEvent(Base):
    __tablename__ = "rejected_events"

    id = Column(Integer, primary_key=True, index=True)
    raw_payload = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    rejected_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )