import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from anomaly_incidents import find_top_error, handle_anomaly_event
from models import AnomalyIncident, Error


class AnomalyIncidentTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Error.__table__.create(self.engine)
        AnomalyIncident.__table__.create(self.engine)
        self.session = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_anomaly_opens_one_incident_and_repeated_anomaly_does_not_duplicate(self):
        handle_anomaly_event(self.session, "test-service", "ANOMALY")
        handle_anomaly_event(self.session, "test-service", "ANOMALY")

        incidents = self.session.query(AnomalyIncident).all()
        self.assertEqual(len(incidents), 1)
        self.assertEqual(incidents[0].status, "OPEN")
        self.assertIsNone(incidents[0].resolved_at)

    def test_find_top_error_uses_five_minutes_from_latest_error(self):
        from datetime import datetime, timedelta

        latest = datetime(2026, 1, 1, 12, 0)
        self.session.add_all(
            [
                Error(
                    service_name="test-service",
                    error_type="DB timeout",
                    message="timeout",
                    severity="HIGH",
                    occurred_at=latest - timedelta(minutes=4),
                ),
                Error(
                    service_name="test-service",
                    error_type="DB timeout",
                    message="timeout",
                    severity="HIGH",
                    occurred_at=latest,
                ),
                Error(
                    service_name="test-service",
                    error_type="Connection refused",
                    message="refused",
                    severity="HIGH",
                    occurred_at=latest - timedelta(minutes=1),
                ),
                Error(
                    service_name="test-service",
                    error_type="Old failure",
                    message="old",
                    severity="HIGH",
                    occurred_at=latest - timedelta(minutes=6),
                ),
            ]
        )
        self.session.commit()

        self.assertEqual(
            find_top_error(self.session, "test-service"),
            "DB timeout (2 errors, last 5 min)",
        )

    def test_top_error_is_retained_after_incident_resolution(self):
        self.session.add(
            Error(
                service_name="test-service",
                error_type="DB timeout",
                message="timeout",
                severity="HIGH",
            )
        )
        self.session.commit()

        handle_anomaly_event(self.session, "test-service", "ANOMALY")
        handle_anomaly_event(self.session, "test-service", "NORMAL")

        incident = self.session.query(AnomalyIncident).one()
        self.assertEqual(incident.top_error, "DB timeout (1 errors, last 5 min)")
        self.assertEqual(incident.status, "RESOLVED")

    def test_normal_resolves_open_incident(self):
        handle_anomaly_event(self.session, "test-service", "ANOMALY")

        handle_anomaly_event(self.session, "test-service", "NORMAL")

        incident = self.session.query(AnomalyIncident).one()
        self.assertEqual(incident.status, "RESOLVED")
        self.assertIsNotNone(incident.resolved_at)

    def test_anomaly_after_resolution_opens_a_new_incident(self):
        handle_anomaly_event(self.session, "test-service", "ANOMALY")
        handle_anomaly_event(self.session, "test-service", "NORMAL")

        handle_anomaly_event(self.session, "test-service", "ANOMALY")

        incidents = (
            self.session.query(AnomalyIncident)
            .order_by(AnomalyIncident.id)
            .all()
        )
        self.assertEqual(
            [incident.status for incident in incidents],
            [
                "RESOLVED",
                "OPEN",
            ],
        )

    def test_warning_does_not_open_or_resolve_an_incident(self):
        handle_anomaly_event(self.session, "test-service", "WARNING")
        self.assertEqual(self.session.query(AnomalyIncident).count(), 0)

        handle_anomaly_event(self.session, "test-service", "ANOMALY")
        handle_anomaly_event(self.session, "test-service", "WARNING")

        incident = self.session.query(AnomalyIncident).one()
        self.assertEqual(incident.status, "OPEN")
        self.assertIsNone(incident.resolved_at)

    def test_normal_without_open_incident_does_nothing(self):
        handle_anomaly_event(self.session, "test-service", "NORMAL")

        self.assertEqual(self.session.query(AnomalyIncident).count(), 0)


if __name__ == "__main__":
    unittest.main()
