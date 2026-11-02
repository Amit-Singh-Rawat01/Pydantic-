import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

import chain_test


class ChainTestTests(unittest.TestCase):
    def test_switch_uses_file_existence(self):
        with tempfile.TemporaryDirectory() as directory:
            switch_file = Path(directory) / "fail_payment-service.flag"
            with patch.object(chain_test, "SWITCH_FILE", switch_file):
                chain_test.set_switch(True)
                self.assertTrue(switch_file.exists())

                chain_test.set_switch(False)
                self.assertFalse(switch_file.exists())

    @patch("chain_test.requests.get")
    def test_get_incidents_reads_anomaly_incidents_endpoint(self, mocked_get):
        response = mocked_get.return_value
        response.json.return_value = [{"id": 7, "status": "OPEN"}]

        self.assertEqual(chain_test.get_incidents(), [{"id": 7, "status": "OPEN"}])

        mocked_get.assert_called_once_with(
            f"{chain_test.API}/anomaly-incidents",
            timeout=chain_test.REQUEST_TIMEOUT,
        )
        response.raise_for_status.assert_called_once_with()

    @patch("chain_test.time.sleep")
    @patch("chain_test.time.monotonic", side_effect=[10, 10, 12])
    def test_wait_until_returns_elapsed_time_and_result(
        self, mocked_monotonic, mocked_sleep
    ):
        elapsed, answer = chain_test.wait_until(lambda: {"id": 1}, timeout=5)

        self.assertEqual((elapsed, answer), (2, {"id": 1}))
        mocked_sleep.assert_not_called()

    @patch("chain_test.set_switch")
    @patch("chain_test.time.sleep")
    @patch(
        "chain_test.wait_until",
        side_effect=[(0, True), (2.4, {"id": 3}), (4.6, {})],
    )
    def test_round_measures_detection_and_recovery(
        self, mocked_wait, mocked_sleep, mocked_set_switch
    ):
        result = chain_test.run_round(1)

        self.assertEqual(result, (2.4, 4.6))
        self.assertEqual(
            mocked_set_switch.call_args_list,
            [call(False), call(True), call(False)],
        )
        self.assertEqual(mocked_sleep.call_args_list, [call(chain_test.HOLD_SECONDS)])
        self.assertEqual(mocked_wait.call_count, 3)

    def test_save_results_appends_header_and_round_status(self):
        with tempfile.TemporaryDirectory() as directory:
            results_file = Path(directory) / "chain_test_results.csv"
            with patch.object(chain_test, "RESULTS_FILE", results_file):
                chain_test.save_results([(1.2, 4.6), (None, None), None])
                chain_test.save_results([(2, 3)])

            with results_file.open(newline="", encoding="utf-8") as csv_file:
                rows = list(csv.reader(csv_file))

        self.assertEqual(
            rows[0],
            [
                "timestamp",
                "round",
                "detection_seconds",
                "recovery_seconds",
                "status",
            ],
        )
        self.assertEqual(rows[1][1:], ["1", "1", "5", "PASS"])
        self.assertEqual(rows[2][1:], ["2", "", "", "FAIL_DETECTION"])
        self.assertEqual(rows[3][1:], ["3", "", "", "SKIPPED"])
        self.assertEqual(rows[4][1:], ["1", "2", "3", "PASS"])

    def test_save_results_marks_api_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            results_file = Path(directory) / "chain_test_results.csv"
            with patch.object(chain_test, "RESULTS_FILE", results_file):
                chain_test.save_results(["ERROR"])

            with results_file.open(newline="", encoding="utf-8") as csv_file:
                rows = list(csv.reader(csv_file))

        self.assertEqual(rows[1][1:], ["1", "", "", "ERROR"])

    @patch("chain_test.set_switch")
    @patch(
        "chain_test.requests.get",
        side_effect=chain_test.requests.ConnectionError("backend unavailable"),
    )
    @patch("chain_test.print")
    def test_main_turns_switch_off_when_health_check_fails(
        self, mocked_print, mocked_get, mocked_set_switch
    ):
        self.assertFalse(chain_test.main())

        mocked_set_switch.assert_called_once_with(False)
        self.assertTrue(
            any("Backend nahi mil raha" in call.args[0]
                for call in mocked_print.call_args_list)
        )


if __name__ == "__main__":
    unittest.main()
