import csv
import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from unittest.mock import patch

import load_test


class LoadTestTests(unittest.TestCase):
    @patch("load_test.urlopen")
    def test_reads_total_for_load_test_service(self, mocked_urlopen):
        response = mocked_urlopen.return_value.__enter__.return_value
        response.read.return_value = b'{"total": 12}'
        response.__iter__.return_value = iter([b'{"total": 12}'])

        self.assertEqual(load_test.get_total(), 12)
        self.assertIn(
            "/metrics/total-errors?service_name=load-test",
            mocked_urlopen.call_args.args[0],
        )

    @patch("load_test.urlopen")
    def test_reads_total_from_errors_endpoint_when_metrics_route_is_missing(
        self, mocked_urlopen
    ):
        response = mocked_urlopen.return_value
        response.__enter__.return_value.read.return_value = b'{"total": 12}'
        response.__enter__.return_value.__iter__.return_value = iter(
            [b'{"total": 12}']
        )
        mocked_urlopen.side_effect = [
            HTTPError(
                "http://example.test/metrics/total-errors",
                404,
                "Not Found",
                {},
                None,
            ),
            response,
        ]

        self.assertEqual(load_test.get_total(), 12)
        self.assertEqual(mocked_urlopen.call_count, 2)
        self.assertIn(
            "/errors?service_name=load-test&limit=1",
            mocked_urlopen.call_args.args[0],
        )

    @patch("load_test.urlopen")
    def test_sends_unique_load_test_event_to_errors_endpoint(self, mocked_urlopen):
        load_test.send_one_event()

        request = mocked_urlopen.call_args.args[0]
        event = json.loads(request.data)
        self.assertEqual(request.full_url, f"{load_test.API_URL}/errors")
        self.assertEqual(event["service_name"], "load-test")
        self.assertEqual(event["error_type"], "LoadTestEvent")
        self.assertEqual(event["severity"], "LOW")
        self.assertTrue(event["message"].endswith(event["stack_trace"].split()[-1]))

    @patch("load_test.time.sleep")
    @patch("load_test.time.monotonic", side_effect=[100, 101, 102, 102])
    @patch("load_test.flush_sender")
    @patch("load_test.send_one_event")
    @patch("load_test.get_total", side_effect=[10, 10, 11])
    def test_records_successful_run(
        self,
        mocked_get_total,
        mocked_send,
        mocked_flush,
        mocked_monotonic,
        mocked_sleep,
    ):
        with tempfile.TemporaryDirectory() as directory:
            results_file = Path(directory) / "load_test_results.csv"
            with patch.object(load_test, "RESULTS_FILE", results_file):
                succeeded = load_test.run(1)

            with results_file.open(newline="", encoding="utf-8") as results:
                rows = list(csv.reader(results))

        self.assertTrue(succeeded)
        self.assertEqual(rows[0][0:2], ["label", "events"])
        self.assertEqual(rows[1][0:2], ["commit-100", "1"])
        self.assertEqual(rows[1][4], "0.5")
        mocked_send.assert_called_once_with()
        mocked_flush.assert_called_once_with()
        mocked_sleep.assert_called_once_with(0.5)

    @patch("load_test.time.monotonic", side_effect=[100, 101, 401])
    @patch("load_test.send_one_event")
    @patch("load_test.get_total", return_value=10)
    def test_timeout_does_not_record_successful_results(
        self,
        mocked_get_total,
        mocked_send,
        mocked_monotonic,
    ):
        with tempfile.TemporaryDirectory() as directory:
            results_file = Path(directory) / "load_test_results.csv"
            with patch.object(load_test, "RESULTS_FILE", results_file):
                succeeded = load_test.run(1)

            self.assertFalse(succeeded)
            self.assertFalse(results_file.exists())

    def test_rejects_non_positive_event_count(self):
        with self.assertRaises(ValueError):
            load_test.run(0)

        with self.assertRaises(ValueError):
            load_test.run_drain(0)

    @patch("load_test.time.sleep")
    @patch("load_test.time.monotonic", side_effect=[100, 101, 102, 103, 104])
    @patch("load_test.flush_sender")
    @patch("load_test.send_one_event")
    @patch("load_test.get_total", side_effect=[10, 10, 11, 11, 14, 14])
    def test_drain_records_consumer_only_throughput(
        self,
        mocked_get_total,
        mocked_send,
        mocked_flush,
        mocked_monotonic,
        mocked_sleep,
    ):
        with tempfile.TemporaryDirectory() as directory:
            results_file = Path(directory) / "load_test_results.csv"
            with patch.object(load_test, "RESULTS_FILE", results_file):
                with patch.object(load_test, "LABEL", "commit-100"):
                    succeeded = load_test.run_drain(4)

            with results_file.open(newline="", encoding="utf-8") as results:
                rows = list(csv.reader(results))

        self.assertTrue(succeeded)
        self.assertEqual(rows[0][0:2], ["label", "events"])
        self.assertEqual(rows[1], ["commit-100-drain", "4", "", "2", "2"])
        self.assertEqual(mocked_send.call_count, 4)
        mocked_flush.assert_called_once_with()
        mocked_sleep.assert_any_call(0.1)
        mocked_sleep.assert_any_call(2)

    @patch("load_test.time.monotonic", side_effect=[100, 401])
    @patch("load_test.flush_sender")
    @patch("load_test.send_one_event")
    @patch("load_test.get_total", return_value=10)
    def test_drain_times_out_before_consumer_starts(
        self,
        mocked_get_total,
        mocked_send,
        mocked_flush,
        mocked_monotonic,
    ):
        with patch("load_test.time.sleep"):
            self.assertFalse(load_test.run_drain(1))


if __name__ == "__main__":
    unittest.main()
