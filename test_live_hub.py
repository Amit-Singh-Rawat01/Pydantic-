import asyncio
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, call, patch

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

    def test_snapshot_failure_is_logged_without_broadcasting_a_fake_snapshot(self):
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
                patch("live_hub.logger.exception") as log_error,
            ):
                await hub._loop()

            log_error.assert_called_once_with("hub cycle failed (%d in a row)", 1)

        asyncio.run(run_one_tick())

        self.assertEqual(client.messages, [])
        self.assertEqual(hub.fail_streak, 1)

    def test_loop_recovers_after_a_failed_cycle(self):
        client = FakeWebSocket()
        snapshot = {"total_errors": 23}
        hub = LiveHub(read_snapshot=lambda: snapshot)
        hub.clients.append(client)

        async def run_two_ticks():
            async def stop_after_second_tick(_delay):
                if sleep.await_count == 2:
                    hub.clients.clear()

            with (
                patch(
                    "live_hub.asyncio.to_thread",
                    new=AsyncMock(
                        side_effect=[RuntimeError("Postgres unavailable"), snapshot]
                    ),
                ),
                patch(
                    "live_hub.asyncio.sleep",
                    new=AsyncMock(side_effect=stop_after_second_tick),
                ) as sleep,
                patch("live_hub.logger.exception") as log_error,
                patch("live_hub.logger.warning") as log_recovery,
                patch("live_hub.time.monotonic", return_value=15.0),
            ):
                await hub._loop()

            log_error.assert_called_once_with("hub cycle failed (%d in a row)", 1)
            log_recovery.assert_called_once_with(
                "hub recovered after %d failed cycles", 1
            )

        asyncio.run(run_two_ticks())

        self.assertEqual(client.messages, [snapshot])
        self.assertEqual(hub.fail_streak, 0)
        self.assertEqual(hub.last_ok, 15.0)

    def test_repeated_failures_are_logged_on_first_and_tenth_cycles(self):
        hub = LiveHub(read_snapshot=lambda: {"total_errors": 23})
        hub.clients.append(FakeWebSocket())

        async def run_ten_failed_ticks():
            async def stop_after_tenth_tick(_delay):
                if sleep.await_count == 10:
                    hub.clients.clear()

            with (
                patch(
                    "live_hub.asyncio.to_thread",
                    new=AsyncMock(
                        side_effect=[
                            RuntimeError("Postgres unavailable") for _ in range(10)
                        ]
                    ),
                ),
                patch(
                    "live_hub.asyncio.sleep",
                    new=AsyncMock(side_effect=stop_after_tenth_tick),
                ) as sleep,
                patch("live_hub.logger.exception") as log_error,
            ):
                await hub._loop()

            self.assertEqual(
                log_error.call_args_list,
                [
                    call("hub cycle failed (%d in a row)", 1),
                    call("hub cycle failed (%d in a row)", 10),
                ],
            )

        asyncio.run(run_ten_failed_ticks())

        self.assertEqual(hub.fail_streak, 10)

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
