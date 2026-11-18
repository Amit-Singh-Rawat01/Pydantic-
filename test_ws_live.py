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
    async def receive_text(self):
        raise WebSocketDisconnect(code=1000)


class LiveWebSocketTests(unittest.TestCase):
    def test_endpoint_connects_and_disconnects_from_hub(self):
        websocket = FakeWebSocket()
        with (
            patch.object(main.hub, "connect", new=AsyncMock()) as connect,
            patch.object(main.hub, "disconnect") as disconnect,
        ):
            asyncio.run(main.ws_live(websocket))

        connect.assert_awaited_once_with(websocket)
        disconnect.assert_called_once_with(websocket)

    def test_health_reports_hub_client_count(self):
        clients = main.hub.clients
        main.hub.clients = [object(), object()]
        try:
            with (
                patch.object(main.redis_client, "ping"),
                patch("main.time.monotonic", return_value=123.45),
            ):
                main.hub.last_ok = 120.0
                result = main.health_check()
        finally:
            main.hub.clients = clients

        self.assertEqual(result["ws_clients"], 2)
        self.assertEqual(result["hub_last_ok_age_s"], 3.5)

    def test_metrics_exposes_prometheus_text_with_live_gauges_and_counters(self):
        clients = main.hub.clients
        main.hub.clients = [object(), object()]
        try:
            with patch("main.time.monotonic", return_value=123.45):
                result = asyncio.run(main.metrics())
        finally:
            main.hub.clients = clients

        body = result.body.decode()
        self.assertTrue(result.media_type.startswith("text/plain"))
        self.assertIn("ws_clients 2.0", body)
        self.assertRegex(body, r"hub_last_ok_age_seconds 3\.45\d*")
        self.assertIn('hub_cycles_total{result="ok"}', body)
        self.assertIn('hub_cycles_total{result="fail"}', body)


if __name__ == "__main__":
    unittest.main()
