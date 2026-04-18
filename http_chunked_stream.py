import asyncio
import os
from datetime import datetime

PORT = int(os.environ.get("PORT", 8888))

async def handle_client(reader, writer):
    # 1. Read the incoming HTTP request (just enough to move past it).
    #    An HTTP request ends with a blank line: \r\n\r\n
    request = b""
    while b"\r\n\r\n" not in request:
        request += await reader.read(1024)
    print("Got request:\n", request.decode(errors="replace"))

    # 2. Write an HTTP response header.
    #    "Transfer-Encoding: chunked" tells the browser:
    #    "I don't know the total length; I'll send pieces as I go."
    headers = (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/plain\r\n"
        b"Transfer-Encoding: chunked\r\n"
        b"\r\n"
    )
    writer.write(headers)
    await writer.drain()

    # 3. Stream 10 chunks, one per second.
    #    In chunked encoding, each piece is: <size in hex>\r\n<data>\r\n
    for i in range(10):
        body = f"Line {i} at {datetime.now().strftime('%H:%M:%S')}\n".encode()
        chunk = f"{len(body):x}\r\n".encode() + body + b"\r\n"
        writer.write(chunk)
        await writer.drain()
        await asyncio.sleep(1)

    # 4. A zero-length chunk signals the end of the response.
    writer.write(b"0\r\n\r\n")
    await writer.drain()

    writer.close()
    await writer.wait_closed()

async def main():
    server = await asyncio.start_server(handle_client, "127.0.0.1", PORT)
    print(f"Listening on http://127.0.0.1:{PORT}")
    async with server:
        await server.serve_forever()

asyncio.run(main())
