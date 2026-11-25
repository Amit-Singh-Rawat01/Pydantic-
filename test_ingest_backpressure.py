import ast
import unittest
from unittest.mock import Mock, patch

import ingest_client


COLLECTOR_PATH = ingest_client.__file__.rsplit("ingest_client.py", 1)[0] + "collector.py"


class IngestBackpressureTests(unittest.TestCase):
    def test_collector_declares_capacity_gauge_and_throttled_label(self):
        with open(COLLECTOR_PATH, encoding="utf-8") as source_file:
            source = source_file.read()
        tree = ast.parse(source)

        self.assertIn("MAX_IN_FLIGHT = 8", source)
        self.assertIn('Gauge(\n    "ingest_in_flight"', source)
        self.assertIn('("accepted", "invalid", "kafka_error", "throttled")', source)
        self.assertIn("slow_kafka.on", source)
        self.assertIn('headers={"Retry-After": "1"}', source)

    @patch("ingest_client.time.sleep")
    @patch("ingest_client.random.uniform", return_value=1.0)
    def test_client_retries_429_with_retry_after(self, mocked_uniform, mocked_sleep):
        first = Mock(status_code=429, headers={"Retry-After": "2"})
        second = Mock(status_code=202, headers={}, text="")

        with patch.object(ingest_client.session, "post", side_effect=[first, second]):
            self.assertTrue(
                ingest_client.send_event(
                    {
                        "service_name": "load-test",
                        "error_type": "LoadTestError",
                        "message": "test",
                        "severity": "LOW",
                    }
                )
            )

        mocked_sleep.assert_called_once_with(2.0)
        mocked_uniform.assert_called_once_with(0.5, 1.5)

    @patch("ingest_client.time.sleep")
    def test_client_does_not_retry_other_4xx(self, mocked_sleep):
        response = Mock(status_code=422, headers={}, text="invalid")

        with patch.object(ingest_client.session, "post", return_value=response):
            self.assertFalse(
                ingest_client.send_event(
                    {
                        "service_name": "load-test",
                        "error_type": "LoadTestError",
                        "message": "test",
                        "severity": "LOW",
                    }
                )
            )

        mocked_sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
