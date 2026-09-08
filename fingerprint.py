import hashlib


def generate_fingerprint(service_name: str, error_type: str) -> str:
    raw = f"{service_name}:{error_type}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]