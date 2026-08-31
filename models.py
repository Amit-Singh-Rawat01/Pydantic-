from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from database import Base
from datetime import datetime

class Error(Base):
    __tablename__ = "errors"

    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String, nullable=False)
    error_type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String, nullable=False)
    stack_trace = Column(Text, nullable=True)
    occurred_at = Column(DateTime, default=func.now())
    fingerprint = Column(String, index=True)  


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String, nullable=False)
    error_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    status = Column(String, default="OPEN")
    occurrence_count = Column(Integer, default=1)
    first_occurred_at = Column(DateTime, default=func.now())
    last_occurred_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())