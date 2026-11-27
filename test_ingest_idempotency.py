import asyncio
import json
import unittest
import uuid
from unittest.mock import AsyncMock, Mock, patch

from pydantic import ValidationError

import collector
import ingest_client
import models
from schemas import ErrorEventSchema


class IngestIdempotencyTests(unittest.TestCase):
    def test_client_reuses_one_uuid7_across_timeout_retry(self):
        accepted = Mock(status_code=202)
        with (
            patch.object(
                ingest_client.session,
                "post",
                side_effect=[ingest_client.requests.Timeout("late response"), accepted],
            ) as mocked_post,
            patch("ingest_client.time.sleep"),
            patch("ingest_client.random.uniform", return_value=1.0),
        ):
            result = ingest_client.send_event(
                {
                    "service_name": "payments",
                    "error_type": "TimeoutError",
                    "message": "request timed out",
                    "severity": "HIGH",
                },
                max_tries=2,
            )

        self.assertTrue(result)
        first_event = json.loads(mocked_post.call_args_list[0].kwargs["data"])
        second_event = json.loads(mocked_post.call_args_list[1].kwargs["data"])
        event_id = uuid.UUID(first_event["event_id"])
        self.assertEqual(event_id.version, 7)
        self.assertEqual(second_event["event_id"], first_event["event_id"])

    def test_client_preserves_an_existing_event_id(self):
        event_id = str(uuid.uuid4())
        response = Mock(status_code=202)

        with patch.object(ingest_client.session, "post", return_value=response) as post:
            self.assertTrue(
                ingest_client.send_event(
                    {
                        "service_name": "payments",
                        "error_type": "TimeoutError",
                        "message": "request timed out",
                        "severity": "HIGH",
                        "event_id": event_id,
                    }
                )
            )

        sent = json.loads(post.call_args.kwargs["data"])
        self.assertEqual(sent["event_id"], event_id)

    def test_legacy_consumer_event_can_omit_event_id(self):
        event = ErrorEventSchema(
            service_name="legacy",
            error_type="LegacyError",
            message="no id",
            severity="LOW",
        )

        self.assertIsNone(event.event_id)

    def test_database_event_id_is_nullable_and_uniquely_indexed(self):
        event_id_column = models.Error.__table__.c.event_id
        event_id_indexes = [
            index
            for index in models.Error.__table__.indexes
            if index.name == "uq_errors_event_id"
        ]

        self.assertTrue(event_id_column.nullable)
        self.assertEqual(len(event_id_indexes), 1)
        self.assertTrue(event_id_indexes[0].unique)

    def test_collector_requires_and_returns_event_id_receipt(self):
        payload = {
            "service_name": "payments",
            "error_type": "TimeoutError",
            "message": "request timed out",
            "severity": "HIGH",
            "occurred_at": "2026-11-27T12:00:00+00:00",
        }
        with self.assertRaises(ValidationError):
            collector.IngestEvent(**payload)

        event_id = uuid.UUID(ingest_client.new_event_id())
        event = collector.IngestEvent(**payload, event_id=event_id)

        with patch("collector.asyncio.to_thread", new=AsyncMock()):
            response = asyncio.run(collector.ingest(event))

        self.assertEqual(response, {"status": "accepted", "event_id": str(event_id)})


if __name__ == "__main__":
    unittest.main()
