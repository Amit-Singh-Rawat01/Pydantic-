import time

import requests


URL = "http://localhost:8000/stats"
REQUEST_TIMEOUT_SECONDS = 5


def main():
    times = []

    for _ in range(100):
        start = time.perf_counter()
        response = requests.get(URL, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        times.append((time.perf_counter() - start) * 1000)

    print(f"average: {sum(times) / len(times):.1f} ms")
    print(f"slowest: {max(times):.1f} ms")


if __name__ == "__main__":
    main()
