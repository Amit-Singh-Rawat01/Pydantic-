import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def ensure_error_fingerprint_column():
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE errors "
                "ADD COLUMN IF NOT EXISTS fingerprint VARCHAR"
            )
        )
        connection.execute(
            text(
                "UPDATE errors SET fingerprint = "
                "left(md5(service_name || ':' || error_type), 12)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_errors_fingerprint "
                "ON errors (fingerprint)"
            )
        )


def ensure_incident_fingerprint_column():
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE incidents "
                "ADD COLUMN IF NOT EXISTS fingerprint VARCHAR"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_incidents_fingerprint "
                "ON incidents (fingerprint)"
            )
        )


def ensure_incident_status_column():
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE incidents "
                "ADD COLUMN IF NOT EXISTS status VARCHAR"
            )
        )
        connection.execute(
            text(
                "UPDATE incidents SET status = 'OPEN' "
                "WHERE status IS NULL OR status = 'ACTIVE'"
            )
        )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()