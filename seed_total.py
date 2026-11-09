from database import SessionLocal
from models import Error
from redis_client import redis_client as r


def seed_total():
    db = SessionLocal()
    try:
        total = db.query(Error).count()
    finally:
        db.close()

    r.set("total_errors", total)
    r.set("total_errors_ready", 1)
    print("Seed ho gaya: total_errors =", total)


if __name__ == "__main__":
    seed_total()
