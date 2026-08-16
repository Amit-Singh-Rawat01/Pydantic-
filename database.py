import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "error_intel",
    "user": "postgres",
    "password": "54321"
}

def get_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    return conn