"""Fixed-destination TLS passthrough. AgentControl terminates end-to-end mTLS.

No credentials, TLS keys, HTTP headers, request routing or arbitrary destinations
are accepted here. Enrollment still requires its one-time token and key proof.
"""

import asyncio
from contextlib import suppress

UPSTREAM = "agent-control-relay"
LIMIT = 64
active = 0


async def forward(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    while data := await asyncio.wait_for(reader.read(65536), timeout=120):
        writer.write(data)
        await writer.drain()


async def connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, port: int) -> None:
    global active
    if active >= LIMIT:
        writer.close()
        return
    active += 1
    upstream = None
    tasks = []
    try:
        remote, upstream = await asyncio.wait_for(asyncio.open_connection(UPSTREAM, port), 10)
        tasks = [
            asyncio.create_task(forward(reader, upstream)),
            asyncio.create_task(forward(remote, writer)),
        ]
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    except (OSError, TimeoutError):
        pass
    finally:
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        for stream in (writer, upstream):
            if stream:
                stream.close()
                with suppress(OSError):
                    await stream.wait_closed()
        active -= 1


async def main() -> None:
    control = await asyncio.start_server(lambda r, w: connection(r, w, 50053), "0.0.0.0", 50051)
    enrollment = await asyncio.start_server(lambda r, w: connection(r, w, 50054), "0.0.0.0", 50052)
    async with control, enrollment:
        await asyncio.gather(control.serve_forever(), enrollment.serve_forever())


if __name__ == "__main__":
    asyncio.run(main())
