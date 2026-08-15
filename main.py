from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import engine, get_db, Base
from models import Error
from schemas import ErrorCreate, ErrorResponse
import models

# Database mein tables create karo automatically
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Error Intelligence Platform", version="1.0")

@app.get("/")
def read_root():
    return {"message": "Error Intelligence Platform is running!", "status": "ok"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "error-intel-backend"}

# Error receive karo aur DATABASE mein save karo
@app.post("/api/errors", response_model=ErrorResponse)
def receive_error(error: ErrorCreate, db: Session = Depends(get_db)):
    # Database object banao
    db_error = Error(
        service_name=error.service_name,
        error_message=error.error_message,
        severity=error.severity
    )
    # Database mein save karo
    db.add(db_error)
    db.commit()
    db.refresh(db_error)
    return db_error

# Saare errors fetch karo
@app.get("/api/errors")
def get_errors(db: Session = Depends(get_db)):
    errors = db.query(Error).all()
    return errors