import asyncio
import os

PORT = int(os.environ.get("PORT", 8888))

clients: set[asyncio.StreamWriter] = set()


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    request = b""
    while b"\r\n\r\n" not in request:
        request += await reader.read(1024)

    writer.write(
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/plain\r\n"
        b"Transfer-Encoding: chunked\r\n"
        b"X-Accel-Buffering: no\r\n"
        b"\r\n"
    )
    await writer.drain()

    # Browsers buffer text/plain until ~1KB arrives before rendering anything.
    # Sending a padding chunk immediately flushes that buffer so subsequent
    # messages appear the moment they're sent.
    padding = b" " * 1024
    writer.write(f"{len(padding):x}\r\n".encode() + padding + b"\r\n")
    await writer.drain()

    clients.add(writer)
    addr = writer.get_extra_info("peername")
    print(f"[+] {addr} connected ({len(clients)} total)")

    try:
        # Block here until the browser closes the tab (EOF = b"")
        while True:
            data = await reader.read(1024)
            if not data:
                break
    finally:
        clients.discard(writer)
        writer.close()
        print(f"[-] {addr} disconnected ({len(clients)} total)")


async def broadcast(message: str):
    body = (message + "\n").encode()
    chunk = f"{len(body):x}\r\n".encode() + body + b"\r\n"

    dead = set()
    for writer in clients:
        try:
            writer.write(chunk)
            await writer.drain()
        except Exception:
            dead.add(writer)

    for writer in dead:
        clients.discard(writer)


async def read_stdin():
    loop = asyncio.get_event_loop()
    while True:
        # run_in_executor lets blocking input() live on a thread
        # so it doesn't freeze the event loop
        line = await loop.run_in_executor(None, input, "> ")
        if clients:
            await broadcast(line)
            print(f"  -> sent to {len(clients)} client(s)")
        else:
            print("  (no clients connected)")


async def main():
    server = await asyncio.start_server(handle_client, "127.0.0.1", PORT)
    print(f"Listening on http://127.0.0.1:{PORT}")
    print("Type a message and press Enter to stream it to all connected browsers.\n")

    asyncio.create_task(read_stdin())

    async with server:
        await server.serve_forever()


asyncio.run(main())
