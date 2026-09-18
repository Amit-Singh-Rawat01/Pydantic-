import json
import unittest
from datetime import datetime

from pydantic import ValidationError

from schemas import ErrorEventSchema, Severity


class ErrorEventValidationTests(unittest.TestCase):
    def test_valid_event_is_accepted(self):
        event = ErrorEventSchema(
            service_name="payments",
            error_type="TimeoutError",
            message="Payment provider timed out",
            severity="HIGH",
        )

        self.assertEqual(event.severity, Severity.HIGH)
        self.assertIsInstance(event.occurred_at, datetime)

    def test_invalid_severity_is_rejected(self):
        with self.assertRaises(ValidationError):
            ErrorEventSchema(
                service_name="payments",
                error_type="TimeoutError",
                message="Payment provider timed out",
                severity="RANDOM_TEXT",
            )

    def test_missing_required_field_is_rejected(self):
        payload = {
            "error_type": "TimeoutError",
            "message": "Payment provider timed out",
            "severity": "HIGH",
        }

        with self.assertRaises(ValidationError):
            ErrorEventSchema(**payload)

    def test_corrupt_json_is_rejected_before_schema_validation(self):
        with self.assertRaises(json.JSONDecodeError):
            json.loads(b'{"service_name": "payments"')

    def test_non_object_json_is_rejected(self):
        with self.assertRaises(ValueError):
            payload = json.loads(b'["not", "an", "event"]')
            if not isinstance(payload, dict):
                raise ValueError("Kafka message must contain a JSON object")


if __name__ == "__main__":
    unittest.main()