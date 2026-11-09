import unittest
from datetime import datetime
from unittest.mock import patch

import redis_counters


class RedisCounterTests(unittest.TestCase):
    def setUp(self):
        redis_counters._pause_until = 0

    def test_minute_key_accepts_iso_utc_text_and_datetime(self):
        expected = "errors:payment:2026-11-08T23:10"

        self.assertEqual(
            redis_counters._minute_key(
                "payment", "2026-11-08T23:10:05Z"
            ),
            expected,
        )
        self.assertEqual(
            redis_counters._minute_key(
                "payment", datetime(2026, 11, 8, 23, 10, 5)
            ),
            expected,
        )

    @patch.object(redis_counters.r, "expire")
    @patch.object(redis_counters.r, "incr", side_effect=[1, 2])
    def test_new_counter_gets_ttl(self, incr, expire):
        redis_counters.count_error("payment", "2026-11-08T23:10:05")

        self.assertEqual(
            incr.call_args_list,
            [
                unittest.mock.call("errors:payment:2026-11-08T23:10"),
                unittest.mock.call("total_errors"),
            ],
        )
        expire.assert_called_once_with(
            "errors:payment:2026-11-08T23:10",
            redis_counters.COUNTER_TTL,
        )

    @patch.object(redis_counters.r, "expire")
    @patch.object(redis_counters.r, "incr", side_effect=[2, 3])
    def test_existing_counter_does_not_reset_ttl(self, incr, expire):
        redis_counters.count_error("payment", "2026-11-08T23:10:05")

        self.assertEqual(
            incr.call_args_list[-1],
            unittest.mock.call("total_errors"),
        )
        expire.assert_not_called()

    @patch.object(
        redis_counters.r,
        "incr",
        side_effect=redis_counters.redis.exceptions.ConnectionError("down"),
    )
    @patch.object(redis_counters.time, "time", return_value=100)
    def test_redis_failure_pauses_retries_for_ten_seconds(self, _current_time, incr):
        with patch("builtins.print") as print_error:
            redis_counters.count_error(
                "payment", "2026-11-08T23:10:05"
            )
            redis_counters.count_error(
                "payment", "2026-11-08T23:10:06"
            )

        self.assertEqual(redis_counters._pause_until, 110)
        _current_time.assert_called()
        incr.assert_called_once()
        print_error.assert_called_once()

    @patch.object(redis_counters.r, "incr", side_effect=[2, 10])
    def test_retries_after_pause_expires(self, incr):
        redis_counters._pause_until = 110
        with patch.object(redis_counters.time, "time", return_value=110):
            redis_counters.count_error(
                "payment", "2026-11-08T23:10:05"
            )

        self.assertEqual(incr.call_count, 2)

    @patch.object(redis_counters.r, "mget", return_value=("50377", "1"))
    def test_reads_seeded_total(self, mget):
        self.assertEqual(redis_counters.get_total_from_redis(), 50377)
        mget.assert_called_once_with("total_errors", "total_errors_ready")

    @patch.object(redis_counters.r, "mget", return_value=(None, None))
    def test_missing_redis_total_uses_fallback(self, _mget):
        self.assertIsNone(redis_counters.get_total_from_redis())

    @patch.object(
        redis_counters.r,
        "mget",
        side_effect=redis_counters.redis.exceptions.ConnectionError("down"),
    )
    def test_redis_read_failure_uses_fallback(self, _mget):
        with patch("builtins.print") as print_error:
            self.assertIsNone(redis_counters.get_total_from_redis())

        print_error.assert_called_once()

    @patch.object(redis_counters.r, "mget", return_value=("bad", "1"))
    def test_invalid_redis_total_uses_fallback(self, _mget):
        with patch("builtins.print") as print_error:
            self.assertIsNone(redis_counters.get_total_from_redis())

        print_error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
