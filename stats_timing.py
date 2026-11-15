import statistics
import time

import requests


URL = "http://localhost:8000/stats"


def main():
    times_ms = []
    for _ in range(30):
        start = time.perf_counter()
        response = requests.get(URL, timeout=5)
        response.raise_for_status()
        times_ms.append((time.perf_counter() - start) * 1000)
        time.sleep(0.5)

    p95_ms = statistics.quantiles(times_ms, n=20)[-1]
    print(f"average: {statistics.mean(times_ms):.0f} ms")
    print(f"p95:     {p95_ms:.0f} ms")
    print(f"max:     {max(times_ms):.0f} ms")


if __name__ == "__main__":
    main()
