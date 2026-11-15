import asyncio
import os
import sys

import redis
import websockets


URL = "ws://localhost:8000/ws/live"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 1


async def one_client(received):
    async with websockets.connect(URL) as ws:
        async for _ in ws:
            received[0] += 1


async def main():
    if N <= 0:
        raise ValueError("The number of WebSocket clients must be greater than zero")

    received = [0]
    clients = [asyncio.create_task(one_client(received)) for _ in range(N)]
    r = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
    )
    try:
        await asyncio.sleep(3)
        for client in clients:
            if client.done():
                client.result()
                raise RuntimeError("A WebSocket client disconnected before measurement")

        cmds_before = r.info("stats")["total_commands_processed"]
        msgs_before = received[0]
        await asyncio.sleep(10)
        for client in clients:
            if client.done():
                client.result()
                raise RuntimeError("A WebSocket client disconnected during measurement")
        cmds_after = r.info("stats")["total_commands_processed"]
        msgs_after = received[0]

        print(f"clients: {N}")
        print(f"Redis commands/sec: {(cmds_after - cmds_before) / 10:.1f}")
        print(f"messages/sec (sab clients ke): {(msgs_after - msgs_before) / 10:.1f}")
    finally:
        for client in clients:
            client.cancel()
        await asyncio.gather(*clients, return_exceptions=True)
        r.close()


if __name__ == "__main__":
    asyncio.run(main())
