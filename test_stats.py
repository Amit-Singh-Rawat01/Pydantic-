import unittest
from unittest.mock import Mock, patch

import database

with (
    patch.object(database.Base.metadata, "create_all"),
    patch.object(database, "ensure_error_fingerprint_column"),
    patch.object(database, "ensure_error_occurred_at_index"),
    patch.object(database, "ensure_incident_fingerprint_column"),
    patch.object(database, "ensure_incident_sample_message_column"),
    patch.object(database, "ensure_incident_status_column"),
    patch.object(database, "ensure_anomaly_incident_top_error_column"),
):
    import main


class StatsSourceTests(unittest.TestCase):
    def setUp(self):
        main.resolve_stale_incidents = Mock()
        self.db = Mock()
        query = self.db.query.return_value
        query.filter.return_value = query
        query.first.return_value = None

    def test_postgres_source_skips_redis(self):
        self.db.query.return_value.count.side_effect = [17, 0, 0]
        main.get_total_from_redis = Mock()

        result = main.get_stats(source="postgres", db=self.db)

        main.get_total_from_redis.assert_not_called()
        self.assertEqual(result["total_errors"], 17)
        self.assertEqual(result["total_source"], "postgres")

    def test_redis_source_reports_redis(self):
        self.db.query.return_value.count.side_effect = [0, 0]
        main.get_total_from_redis = Mock(return_value=23)

        result = main.get_stats(source="redis", db=self.db)

        main.get_total_from_redis.assert_called_once_with()
        self.assertEqual(result["total_errors"], 23)
        self.assertEqual(result["total_source"], "redis")

    def test_redis_fallback_reports_postgres(self):
        self.db.query.return_value.count.side_effect = [17, 0, 0]
        main.get_total_from_redis = Mock(return_value=None)

        result = main.get_stats(source="redis", db=self.db)

        self.assertEqual(result["total_errors"], 17)
        self.assertEqual(result["total_source"], "postgres")


if __name__ == "__main__":
    unittest.main()
