import asyncio
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from live_hub import LiveHub


class FakeWebSocket:
    def __init__(self):
        self.accepted = False
        self.messages = []

    async def accept(self):
        self.accepted = True

    async def send_json(self, message):
        self.messages.append(message)


class LiveHubTests(unittest.TestCase):
    def test_reads_snapshot_once_and_broadcasts_json_safe_payload(self):
        first = FakeWebSocket()
        second = FakeWebSocket()
        snapshot = {
            "total_errors": 23,
            "errors_per_minute": 4,
            "updated_at": datetime(2026, 11, 15, tzinfo=timezone.utc),
        }
        hub = LiveHub(read_snapshot=lambda: snapshot, every_sec=2)
        hub.clients.extend([first, second])

        async def run_one_tick():
            async def stop_after_tick(_delay):
                hub.clients.clear()

            with (
                patch(
                    "live_hub.asyncio.to_thread",
                    new=AsyncMock(return_value=snapshot),
                ) as read_snapshot,
                patch(
                    "live_hub.asyncio.sleep",
                    new=AsyncMock(side_effect=stop_after_tick),
                ),
            ):
                await hub._loop()

            read_snapshot.assert_awaited_once_with(hub.read_snapshot)
            self.assertEqual(hub.every_sec, 2)

        asyncio.run(run_one_tick())

        self.assertEqual(len(first.messages), 1)
        self.assertEqual(first.messages, second.messages)
        self.assertEqual(first.messages[0]["total_errors"], 23)
        self.assertEqual(
            first.messages[0]["updated_at"],
            "2026-11-15T00:00:00+00:00",
        )

    def test_snapshot_failure_is_logged_and_null_total_is_broadcast(self):
        client = FakeWebSocket()
        hub = LiveHub(read_snapshot=lambda: {"total_errors": 23})
        hub.clients.append(client)

        async def run_one_tick():
            async def stop_after_tick(_delay):
                hub.clients.clear()

            with (
                patch(
                    "live_hub.asyncio.to_thread",
                    new=AsyncMock(side_effect=RuntimeError("Postgres unavailable")),
                ),
                patch(
                    "live_hub.asyncio.sleep",
                    new=AsyncMock(side_effect=stop_after_tick),
                ),
                patch("builtins.print") as print_error,
            ):
                await hub._loop()

            print_error.assert_called_once_with(
                "[hub] snapshot padhne mein error: Postgres unavailable"
            )

        asyncio.run(run_one_tick())

        self.assertEqual(client.messages[0], {"total_errors": None})

    def test_connect_starts_loop_and_disconnect_removes_client(self):
        client = FakeWebSocket()
        hub = LiveHub(read_snapshot=lambda: {"total_errors": 23})

        async def connect_then_disconnect():
            await hub.connect(client)
            task = hub._task
            hub.disconnect(client)
            await task

        asyncio.run(connect_then_disconnect())

        self.assertEqual(hub.clients, [])
        self.assertTrue(client.accepted)
        self.assertTrue(hub._task.done())


if __name__ == "__main__":
    unittest.main()
