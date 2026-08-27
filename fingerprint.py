import hashlib
import re

def normalize_message(message: str) -> str:
    """
    Message ke andar ke numbers ko '#' se replace karta hai,
    taaki dynamic parameters ignore ho sakein.
    """
    normalized = re.sub(r'\d+', '#', message)
    return normalized.lower().strip()

def generate_fingerprint(service_name: str, error_type: str, message: str) -> str:
    """
    Service name, error type aur normalized message ko mila kar
    16-character ka unique sha256 fingerprint hash banata hai.
    """
    normalized_message = normalize_message(message)
    raw_string = f"{service_name}:{error_type}:{normalized_message}"
    return hashlib.sha256(raw_string.encode()).hexdigest()[:16]