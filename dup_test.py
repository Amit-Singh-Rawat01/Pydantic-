from datetime import datetime, timezone

from ingest_client import send_event


event = {
    "service_name": "dup-test",
    "error_type": "DuplicateTest",
    "message": "ek hi event, teen koshish",
    "severity": "LOW",
    "occurred_at": datetime.now(timezone.utc).isoformat(),
}
print("result:", send_event(event, max_tries=3))
