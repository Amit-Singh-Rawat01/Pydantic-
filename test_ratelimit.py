import asyncio
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.responses import JSONResponse

import collector
from ratelimit import ServiceLimiter, check_rate_limit


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class TokenBucketTests(unittest.TestCase):
    def test_burst_refill_and_service_isolation(self):
        clock = FakeClock()
        with patch("ratelimit.time.monotonic", clock):
            limiter = ServiceLimiter(rate=5, burst=10)

            payment = [limiter.check("payment")[1] for _ in range(15)]
            self.assertEqual(payment.count(0), 10)
            self.assertAlmostEqual(payment[-1], 0.2)
            self.assertTrue(all(limiter.check("auth")[1] == 0 for _ in range(3)))

            clock.advance(1.1)
            replenished = [limiter.check("payment")[1] for _ in range(15)]
            self.assertEqual(replenished.count(0), 5)

    def test_new_service_names_share_the_fallback_bucket_at_capacity(self):
        with patch("ratelimit.time.monotonic", return_value=0):
            limiter = ServiceLimiter(rate=1, burst=1, max_services=2)

            self.assertEqual(limiter.check("one")[0], "one")
            self.assertEqual(limiter.check("two")[0], "two")
            self.assertEqual(limiter.check("three")[0], "_other")
            self.assertEqual(limiter.check("four")[0], "_other")
            self.assertLessEqual(len(limiter.buckets), 3)

    def test_rate_limit_response_has_retry_after_and_increments_metric(self):
        with (
            patch("ratelimit.limiter.check", return_value=("payments", 0.2)),
            patch("ratelimit.RATE_LIMITED.labels") as labels,
        ):
            response = check_rate_limit("payments")

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers["Retry-After"], "1")
        labels.assert_called_once_with(service="payments")
        labels.return_value.inc.assert_called_once_with()

    def test_collector_checks_service_limit_before_shared_slots(self):
        event = collector.IngestEvent(
            event_id=uuid4(),
            service_name="payments",
            error_type="RateLimitTest",
            message="test",
            severity="LOW",
            occurred_at="2026-01-01T00:00:00Z",
        )
        limited = JSONResponse(status_code=429, content={"detail": "rate limit"})

        async def call_ingest():
            with (
                patch("collector.check_rate_limit", return_value=limited) as check,
                patch.object(
                    collector.SLOTS,
                    "locked",
                    side_effect=AssertionError("shared slots checked too early"),
                ),
            ):
                response = await collector.ingest(event)
            check.assert_called_once_with("payments")
            return response

        self.assertIs(asyncio.run(call_ingest()), limited)

    def test_collector_still_accepts_valid_events(self):
        event = collector.IngestEvent(
            event_id=uuid4(),
            service_name="normal-test",
            error_type="RateLimitTest",
            message="test",
            severity="LOW",
            occurred_at="2026-01-01T00:00:00Z",
        )

        async def call_ingest():
            with (
                patch("collector.publish") as publish,
                patch("collector.os.path.exists", return_value=False),
            ):
                response = await collector.ingest(event)
            publish.assert_called_once()
            return response

        self.assertEqual(asyncio.run(call_ingest()), {
            "status": "accepted",
            "event_id": str(event.event_id),
        })


if __name__ == "__main__":
    unittest.main()
