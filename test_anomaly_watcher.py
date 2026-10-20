import unittest
from unittest.mock import Mock, call, patch

import requests

import anomaly_watcher


class AnomalyWatcherTests(unittest.TestCase):
    def setUp(self):
        anomaly_watcher.last_status.clear()

    @patch("anomaly_watcher.print")
    @patch("anomaly_watcher.now", return_value="12:00:00")
    @patch("anomaly_watcher.requests.get")
    def test_list_response_only_prints_when_status_changes(
        self, mock_get, mock_now, mock_print
    ):
        response = Mock()
        response.json.return_value = [
            {
                "service": "payment",
                "status": "NORMAL",
                "z_score": 0.4,
                "current": 12,
            }
        ]
        mock_get.return_value = response

        anomaly_watcher.check_once()
        anomaly_watcher.check_once()

        response.raise_for_status.assert_called()
        self.assertEqual(
            mock_print.call_args_list,
            [call("[12:00:00] [INFO] payment: START -> NORMAL (z=0.4, rate=12)")],
        )

        response.json.return_value[0]["status"] = "ANOMALY"
        anomaly_watcher.check_once()

        self.assertEqual(mock_print.call_count, 2)
        self.assertIn("[ALERT] payment: NORMAL -> ANOMALY", mock_print.call_args[0][0])

    @patch("anomaly_watcher.requests.get")
    def test_mapping_response_is_supported(self, mock_get):
        response = Mock()
        response.json.return_value = {
            "payment": {"status": "WARNING", "z_score": 2.5, "current_rate": 18}
        }
        mock_get.return_value = response

        with patch("anomaly_watcher.print") as mock_print:
            anomaly_watcher.check_once()

        self.assertIn(
            "[INFO] payment: START -> WARNING (z=2.5, rate=18)",
            mock_print.call_args[0][0],
        )

    @patch("anomaly_watcher.print")
    @patch("anomaly_watcher.time.sleep", side_effect=KeyboardInterrupt)
    @patch(
        "anomaly_watcher.requests.get",
        side_effect=requests.ConnectionError("backend unavailable"),
    )
    def test_main_warns_and_stops_cleanly_after_backend_error(
        self, mock_get, mock_sleep, mock_print
    ):
        anomaly_watcher.main()

        self.assertTrue(
            any("[WARN] backend se data nahi mila:" in call.args[0]
                for call in mock_print.call_args_list)
        )
        self.assertIn(call("\nWatcher band."), mock_print.call_args_list)


if __name__ == "__main__":
    unittest.main()
