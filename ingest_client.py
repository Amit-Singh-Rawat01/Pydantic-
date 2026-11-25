import json
import random
import time
from datetime import datetime, timezone

import requests
from requests.adapters import HTTPAdapter


URL = "http://localhost:8002/v1/ingest"
session = requests.Session()
session.mount("http://", HTTPAdapter(pool_maxsize=100))


def send_event(event: dict, max_tries: int = 8) -> bool:
    payload = dict(event)
    payload.setdefault(
        "occurred_at",
        datetime.now(timezone.utc).isoformat(),
    )
    body = json.dumps(payload, default=str)
    for attempt in range(1, max_tries + 1):
        try:
            response = session.post(
                URL,
                data=body,
                headers={"Content-Type": "application/json"},
                timeout=2,
            )
        except requests.RequestException as error:
            print(f"darwaza nahi mila (koshish {attempt}): {error}")
            wait = 1.0
        else:
            if response.status_code == 202:
                return True
            if response.status_code not in (429, 503):
                print(
                    f"darwaze ne mana kiya: {response.status_code} "
                    f"{response.text}"
                )
                return False
            wait = float(response.headers.get("Retry-After", 1))
        if attempt < max_tries:
            time.sleep(wait * random.uniform(0.5, 1.5))
    return False
