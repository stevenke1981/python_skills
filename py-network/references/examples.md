# py-network 完整範例集

## 範例 1：TCP 長度前綴協議 — 伺服器 + 客戶端

```python
"""TCP 長度前綴協議：4-byte header + payload"""
import socket
import struct
import json


def send_msg(sock: socket.socket, data: dict) -> None:
    """發送帶長度前綴的 JSON 訊息"""
    payload = json.dumps(data).encode("utf-8")
    header = struct.pack("!I", len(payload))  # 4 bytes 大端序
    sock.sendall(header + payload)


def recv_msg(sock: socket.socket) -> dict:
    """接收帶長度前綴的 JSON 訊息"""
    raw_header = recv_exact(sock, 4)
    (msg_len,) = struct.unpack("!I", raw_header)
    payload = recv_exact(sock, msg_len)
    return json.loads(payload.decode("utf-8"))


def recv_exact(sock: socket.socket, n: int) -> bytes:
    """確保接收到 n bytes"""
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("連線中斷")
        buf.extend(chunk)
    return bytes(buf)


# --- 伺服器端 ---
def run_server() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", 9000))
        srv.listen(5)
        print("伺服器啟動 :9000")
        conn, addr = srv.accept()
        with conn:
            msg = recv_msg(conn)
            print(f"收到: {msg}")
            send_msg(conn, {"status": "ok", "echo": msg})


# --- 客戶端 ---
def run_client() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect(("127.0.0.1", 9000))
        send_msg(sock, {"action": "hello", "name": "Python"})
        response = recv_msg(sock)
        print(f"回應: {response}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "client":
        run_client()
    else:
        run_server()
```

## 範例 2：asyncio 多人聊天伺服器

```python
"""asyncio 聊天伺服器 — 廣播模式"""
import asyncio

clients: dict[asyncio.StreamWriter, str] = {}


async def broadcast(sender: asyncio.StreamWriter, message: str) -> None:
    """廣播訊息給其他所有 client"""
    for writer in list(clients):
        if writer is not sender and not writer.is_closing():
            writer.write(message.encode("utf-8"))
            await writer.drain()


async def handle_client(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    addr = writer.get_extra_info("peername")
    nickname = f"{addr[0]}:{addr[1]}"
    clients[writer] = nickname
    await broadcast(writer, f"[{nickname}] 加入了聊天室\n")

    try:
        while True:
            data = await reader.readline()
            if not data:
                break
            msg = data.decode("utf-8").strip()
            if msg:
                await broadcast(writer, f"[{nickname}] {msg}\n")
    except (ConnectionResetError, asyncio.IncompleteReadError):
        pass
    finally:
        clients.pop(writer, None)
        await broadcast(writer, f"[{nickname}] 離開了聊天室\n")
        writer.close()
        await writer.wait_closed()


async def main() -> None:
    server = await asyncio.start_server(handle_client, "0.0.0.0", 8888)
    addrs = ", ".join(str(s.getsockname()) for s in server.sockets)
    print(f"聊天伺服器啟動: {addrs}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
```

## 範例 3：httpx 非同步並行請求

```python
"""httpx 並行 HTTP 請求 + 錯誤處理"""
import asyncio
import httpx


async def fetch_url(client: httpx.AsyncClient, url: str) -> dict:
    """安全擷取 URL"""
    try:
        resp = await client.get(url, timeout=10.0)
        resp.raise_for_status()
        return {"url": url, "status": resp.status_code, "size": len(resp.content)}
    except httpx.HTTPStatusError as e:
        return {"url": url, "error": f"HTTP {e.response.status_code}"}
    except httpx.RequestError as e:
        return {"url": url, "error": str(e)}


async def main() -> None:
    urls = [
        "https://httpbin.org/get",
        "https://httpbin.org/status/404",
        "https://httpbin.org/delay/2",
    ]

    async with httpx.AsyncClient() as client:
        # 並行執行所有請求
        results = await asyncio.gather(
            *(fetch_url(client, url) for url in urls)
        )

    for result in results:
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
```

## 範例 4：WebSocket 即時通訊

```python
"""websockets 聊天室（伺服器端）"""
import asyncio
import websockets
from websockets.server import ServerConnection

connected: set[ServerConnection] = set()


async def handler(ws: ServerConnection) -> None:
    connected.add(ws)
    try:
        async for message in ws:
            # 廣播給所有已連線 client
            futures = [
                w.send(f"[匿名] {message}")
                for w in connected
                if w is not ws
            ]
            if futures:
                await asyncio.gather(*futures)
    finally:
        connected.discard(ws)


async def main() -> None:
    async with websockets.serve(handler, "localhost", 8765):
        print("WebSocket 伺服器 ws://localhost:8765")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
```

## 範例 5：DNS 查詢 + 解析

```python
"""使用 dnspython 進行 DNS 查詢"""
import dns.resolver  # pip install dnspython


def lookup(domain: str) -> None:
    """查詢 A、MX、TXT 記錄"""
    # A 記錄
    answers = dns.resolver.resolve(domain, "A")
    for rdata in answers:
        print(f"A:  {rdata.address}")

    # MX 記錄
    try:
        mx_answers = dns.resolver.resolve(domain, "MX")
        for rdata in mx_answers:
            print(f"MX: {rdata.preference} {rdata.exchange}")
    except dns.resolver.NoAnswer:
        print("MX: 無記錄")

    # TXT 記錄
    try:
        txt_answers = dns.resolver.resolve(domain, "TXT")
        for rdata in txt_answers:
            print(f"TXT: {rdata.to_text()}")
    except dns.resolver.NoAnswer:
        print("TXT: 無記錄")


if __name__ == "__main__":
    lookup("google.com")
```
