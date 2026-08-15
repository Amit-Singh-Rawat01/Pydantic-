from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database ka address — yahan tumhara PostgreSQL connect hoga
DATABASE_URL = "postgresql://postgres:54321@localhost:5432/error_intel"

# Engine — Python aur Database ke beech connection
engine = create_engine(DATABASE_URL)

# Session — har request ke liye ek temporary connection
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base — saare database models isse inherit karenge
Base = declarative_base()

# Helper function — har API request ko ek DB session deta hai
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()