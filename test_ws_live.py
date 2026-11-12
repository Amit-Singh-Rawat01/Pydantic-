import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from starlette.websockets import WebSocketDisconnect

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


class FakeWebSocket:
    def __init__(self):
        self.accepted = False
        self.messages = []
        self.clients_when_sent = None

    async def accept(self):
        self.accepted = True

    async def send_json(self, message):
        self.messages.append(message)
        self.clients_when_sent = main.health_check()["ws_clients"]
        raise WebSocketDisconnect(code=1000)


class LiveWebSocketTests(unittest.TestCase):
    def _run_endpoint(self, total):
        main.ws_clients = 0
        websocket = FakeWebSocket()
        with (
            patch.object(
                main.asyncio, "to_thread", new=AsyncMock(return_value=total)
            ) as to_thread,
            patch.object(main.asyncio, "sleep", new=AsyncMock()),
            patch.object(main.redis_client, "ping"),
        ):
            asyncio.run(main.ws_live(websocket))

        self.assertTrue(websocket.accepted)
        self.assertEqual(len(websocket.messages), 1)
        self.assertEqual(websocket.clients_when_sent, 1)
        self.assertEqual(main.ws_clients, 0)
        to_thread.assert_awaited_once_with(main.get_total_from_redis)
        return websocket.messages[0]

    def test_sends_redis_total_and_tracks_connected_client(self):
        message = self._run_endpoint(total=23)

        self.assertEqual(message["total_errors"], 23)
        self.assertEqual(message["total_source"], "redis")
        self.assertTrue(message["sent_at"])

    def test_unavailable_redis_total_is_sent_as_null(self):
        message = self._run_endpoint(total=None)

        self.assertIsNone(message["total_errors"])
        self.assertEqual(message["total_source"], "unavailable")


if __name__ == "__main__":
    unittest.main()
