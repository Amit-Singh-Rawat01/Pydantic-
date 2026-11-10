import argparse
import os
import time

import requests


API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
REQUEST_TIMEOUT_SECONDS = 5
REQUEST_COUNT = 200
REQUEST_INTERVAL_SECONDS = 0.02


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "source",
        choices=("redis", "postgres"),
        nargs="?",
        default="redis",
    )
    source = parser.parse_args(argv).source
    url = f"{API_URL}/stats?source={source}"
    times = []
    sources = {}

    with requests.Session() as session:
        for _ in range(REQUEST_COUNT):
            start = time.perf_counter()
            response = session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
            times.append((time.perf_counter() - start) * 1000)
            response.raise_for_status()
            used_source = response.json().get("total_source", "?")
            sources[used_source] = sources.get(used_source, 0) + 1
            time.sleep(REQUEST_INTERVAL_SECONDS)

    times.sort()
    print(f"maanga  : {source}")
    print(f"raasta  : {sources}")
    print(f"average : {sum(times) / len(times):.1f} ms")
    print(f"p95     : {times[int(len(times) * 0.95) - 1]:.1f} ms")
    print(f"slowest : {times[-1]:.1f} ms")


if __name__ == "__main__":
    main()
