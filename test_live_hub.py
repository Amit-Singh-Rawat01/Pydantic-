import asyncio
import unittest
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
    def test_reads_total_once_and_broadcasts_to_every_client(self):
        first = FakeWebSocket()
        second = FakeWebSocket()
        hub = LiveHub(read_total=lambda: 23)
        hub.clients.extend([first, second])

        async def run_one_tick():
            async def stop_after_tick(_delay):
                hub.clients.clear()

            with (
                patch(
                    "live_hub.asyncio.to_thread",
                    new=AsyncMock(return_value=23),
                ) as read_total,
                patch(
                    "live_hub.asyncio.sleep",
                    new=AsyncMock(side_effect=stop_after_tick),
                ),
            ):
                await hub._loop()

            read_total.assert_awaited_once_with(hub.read_total)

        asyncio.run(run_one_tick())

        self.assertEqual(len(first.messages), 1)
        self.assertEqual(first.messages, second.messages)
        self.assertEqual(first.messages[0]["total_errors"], 23)
        self.assertEqual(first.messages[0]["total_source"], "redis")
        self.assertTrue(first.messages[0]["sent_at"])

    def test_read_failure_is_logged_and_null_is_broadcast(self):
        client = FakeWebSocket()
        hub = LiveHub(read_total=lambda: 23)
        hub.clients.append(client)

        async def run_one_tick():
            async def stop_after_tick(_delay):
                hub.clients.clear()

            with (
                patch(
                    "live_hub.asyncio.to_thread",
                    new=AsyncMock(side_effect=RuntimeError("Redis unavailable")),
                ),
                patch(
                    "live_hub.asyncio.sleep",
                    new=AsyncMock(side_effect=stop_after_tick),
                ),
                patch("builtins.print") as print_error,
            ):
                await hub._loop()

            print_error.assert_called_once_with(
                "[hub] total padhne mein error: Redis unavailable"
            )

        asyncio.run(run_one_tick())

        self.assertIsNone(client.messages[0]["total_errors"])
        self.assertEqual(client.messages[0]["total_source"], "unavailable")

    def test_connect_starts_loop_and_disconnect_removes_client(self):
        client = FakeWebSocket()
        hub = LiveHub(read_total=lambda: 23)

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
