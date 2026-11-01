import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from anomaly_incidents import handle_anomaly_event
from models import AnomalyIncident


class AnomalyIncidentTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
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
