from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from database import Base

class Error(Base):
    __tablename__ = "errors"

    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String, nullable=False)
    error_message = Column(Text, nullable=False)
    severity = Column(String, default="medium")
    timestamp = Column(DateTime, default=func.now())
    