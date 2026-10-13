import unittest
from datetime import datetime
from unittest.mock import patch

from baseline import calculate_baseline


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


class BaselineTests(unittest.TestCase):
    @patch("baseline.datetime")
    def test_calculates_stats_with_quiet_minutes_and_skips_recent_data(
        self, mocked_datetime
    ):
        mocked_datetime.utcnow.return_value = datetime(
            2026, 10, 13, 17, 24, 56
        )
        db = FakeDatabase(
            [
                ("payment", 10),
                ("payment", 12),
                ("auth", 3),
            ]
        )

        result = calculate_baseline(db, lookback_minutes=4)

        self.assertEqual(
            result,
            {
                "window_start": "2026-10-13T17:15:00",
                "window_end": "2026-10-13T17:19:00",
                "lookback_minutes": 4,
                "services": [
                    {"service": "auth", "mean": 0.75, "std_dev": 1.3},
                    {"service": "payment", "mean": 5.5, "std_dev": 5.55},
                ],
            },
        )
        self.assertEqual(
            db.parameters,
            {
                "window_start": datetime(2026, 10, 13, 17, 15),
                "window_end": datetime(2026, 10, 13, 17, 19),
            },
        )
        self.assertIn("date_trunc('minute', occurred_at)", db.statement)

    def test_empty_window_returns_no_services(self):
        db = FakeDatabase([])

        result = calculate_baseline(db, lookback_minutes=10)

        self.assertEqual(result["services"], [])
        self.assertEqual(result["lookback_minutes"], 10)


if __name__ == "__main__":
    unittest.main()
