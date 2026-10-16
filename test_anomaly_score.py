import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from baseline import calculate_anomaly_scores


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


class FakeDatabase:
    def __init__(self, rows):
        self.rows = rows
        self.statement = None
        self.parameters = None

    def execute(self, statement, parameters):
        self.statement = str(statement)
        self.parameters = parameters
        return FakeResult(self.rows)


class AnomalyScoreTests(unittest.TestCase):
    @patch("baseline.datetime")
    def test_detects_spike_and_includes_quiet_baseline_minutes(
        self, mocked_datetime
    ):
        mocked_datetime.utcnow.return_value = datetime(2026, 10, 13, 17, 24, 56)
        current_minute = datetime(2026, 10, 13, 17, 23)
        history_start = current_minute - timedelta(minutes=30)
        rows = [
            ("payment", history_start + timedelta(minutes=i), 20)
            for i in range(5)
        ]
        rows.append(("payment", current_minute, 60))
        db = FakeDatabase(rows)

        result = calculate_anomaly_scores(db)

        self.assertEqual(
            result,
            [
                {
                    "service": "payment",
                    "current": 60,
                    "mean": 3.33,
                    "std_dev": 7.58,
                    "z_score": 7.47,
                    "status": "ANOMALY",
                }
            ],
        )
        self.assertEqual(
            db.parameters,
            {
                "baseline_start": history_start,
                "window_end": datetime(2026, 10, 13, 17, 24),
            },
        )
        self.assertIn("date_trunc('minute', occurred_at)", db.statement)

    @patch("baseline.datetime")
    def test_returns_not_enough_data_for_new_service(self, mocked_datetime):
        mocked_datetime.utcnow.return_value = datetime(2026, 10, 13, 17, 24)
        current_minute = datetime(2026, 10, 13, 17, 23)
        four_minutes_of_history = [
            ("auth", current_minute - timedelta(minutes=offset), 2)
            for offset in range(1, 5)
        ]
        db = FakeDatabase(four_minutes_of_history + [("auth", current_minute, 10)])

        result = calculate_anomaly_scores(db)

        self.assertEqual(
            result,
            [{"service": "auth", "current": 10, "status": "NOT_ENOUGH_DATA"}],
        )

    def test_empty_window_returns_no_services(self):
        db = FakeDatabase([])

        self.assertEqual(calculate_anomaly_scores(db), [])


if __name__ == "__main__":
    unittest.main()
