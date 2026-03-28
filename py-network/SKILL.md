---
name: py-network
description: >
  Python networking from L2 to L7 — socket programming, asyncio streams, HTTP clients,
  WebSocket, DNS, SSL/TLS, raw packets, and protocol implementation.
  Trigger when user mentions socket, TCP, UDP, HTTP client, networking, asyncio streams,
  aiohttp, httpx, websocket, SSL, TLS, DNS, raw socket, packet, scapy, paramiko, SSH,
  server, client, port, bind, listen, connect, send, recv, protocol, network programming,
  select, poll, epoll, non-blocking, multiplexing, proxy, tunnel.
  Also trigger when user asks about building a chat server, port scanner, file transfer,
  reverse proxy, or any network communication in Python.
---

# Python 網路程式設計（L2 ~ L7）

## Quick Start（30 秒上手）

```python
"""asyncio TCP echo server + client"""
import asyncio

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    data = await reader.read(1024)
    writer.write(data)                 # Echo 回去
    await writer.drain()
    writer.close()
    await writer.wait_closed()

async def main() -> None:
    server = await asyncio.start_server(handle_client, "127.0.0.1", 8888)
    async with server:
        print("Echo server listening on :8888")
        await server.serve_forever()

# asyncio.run(main())
```

## OSI 層對照 Python 工具

| OSI 層 | 功能 | Python 工具 |
|--------|------|-------------|
| L2 資料鏈結 | 原始 Ethernet 封包 | `socket(AF_PACKET, SOCK_RAW)` (Linux), scapy |
| L3 網路 | IP / ICMP | `socket(SOCK_RAW)`, scapy |
| L4 傳輸 | TCP / UDP | `socket`, `asyncio` streams |
| L5 會話 | 連線管理 | `ssl`, `asyncio.open_connection` |
| L6 表示 | 加密 / 編碼 | `ssl`, `struct`, `json` |
| L7 應用 | HTTP / WebSocket / DNS | `httpx`, `aiohttp`, `websockets`, `dnspython` |

## 核心概念

### 1. Socket 基礎（L3-L4）

```python
"""TCP 伺服器基本生命週期"""
import socket

# 建立 → 繫結 → 監聽 → 接受 → 收送 → 關閉
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", 9000))
    srv.settimeout(60)      # 超時機制（避免無限阻塞）
    srv.listen(5)
    print("TCP 伺服器啟動 :9000")
    conn, addr = srv.accept()
    with conn:
        print(f"連線來自 {addr}")
        data = conn.recv(4096)         # 接收
        conn.sendall(data.upper())     # 回送
```

**Address Family 總覽**：

| Family | 說明 | 範例 |
|--------|------|------|
| `AF_INET` | IPv4 | `("127.0.0.1", 8080)` |
| `AF_INET6` | IPv6 | `("::1", 8080, 0, 0)` |
| `AF_UNIX` | Unix Domain Socket | `"/tmp/my.sock"` |

### 2. 訊息邊界（Message Framing）

TCP 是 **位元組流**，不保證訊息邊界。三種常見做法：

```python
import struct

# 方法 A：固定長度
msg = b"Hello World!".ljust(64, b'\x00')  # 補到 64 bytes

# 方法 B：分隔符
msg = b"Hello World!\n"  # 以換行分隔

# 方法 C：長度前綴（推薦）
payload = b"Hello World!"
header = struct.pack("!I", len(payload))  # 4 bytes 大端序長度
msg = header + payload

def recv_exact(sock: socket.socket, n: int) -> bytes:
    """確保接收到 n bytes"""
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("連線中斷")
        buf.extend(chunk)
    return bytes(buf)
```

### 3. asyncio 高階 Stream API（L4-L7）

```python
"""非同步 TCP 聊天伺服器"""
import asyncio
from collections.abc import Set

clients: set[asyncio.StreamWriter] = set()

async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    clients.add(writer)
    addr = writer.get_extra_info("peername")
    print(f"{addr} 已連線")
    try:
        while True:
            data = await reader.readline()
            if not data:
                break
            # 廣播給所有其他 client
            for w in clients:
                if w is not writer:
                    w.write(data)
                    await w.drain()
    finally:
        clients.discard(writer)
        writer.close()
        await writer.wait_closed()
        print(f"{addr} 已離線")

async def main() -> None:
    server = await asyncio.start_server(handle, "0.0.0.0", 8888)
    async with server:
        await server.serve_forever()
```

### 4. SSL/TLS 安全連線（L5-L6）

```python
import ssl
import asyncio

async def secure_client() -> None:
    # 建立 SSL context（驗證憑證）
    ctx = ssl.create_default_context()

    reader, writer = await asyncio.open_connection(
        "example.com", 443, ssl=ctx
    )
    writer.write(b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
    await writer.drain()

    response = await reader.read(4096)
    print(response[:200].decode())

    writer.close()
    await writer.wait_closed()
```

### 5. HTTP 用戶端（L7）

```python
"""httpx — 同步 + 非同步 HTTP 客戶端"""
import httpx

# 同步
resp = httpx.get("https://httpbin.org/get", timeout=10.0)
print(resp.status_code, resp.json())

# 非同步
async def fetch() -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get("https://httpbin.org/get")
        return resp.json()
```

## 實戰 Patterns

### Pattern 1: 非阻塞多工（select / selectors）

**場景**：單執行緒同時處理多個連線

```python
import selectors
import socket

sel = selectors.DefaultSelector()  # 自動選用 epoll/kqueue/select

def accept(srv: socket.socket) -> None:
    conn, addr = srv.accept()
    conn.setblocking(False)
    sel.register(conn, selectors.EVENT_READ, data=addr)

def read(conn: socket.socket) -> None:
    data = conn.recv(1024)
    if data:
        conn.sendall(data)
    else:
        sel.unregister(conn)
        conn.close()

srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("0.0.0.0", 9000))
srv.listen(100)
srv.setblocking(False)
sel.register(srv, selectors.EVENT_READ, data=None)

while True:
    events = sel.select(timeout=1)
    for key, mask in events:
        if key.data is None:
            accept(key.fileobj)
        else:
            read(key.fileobj)
```

### Pattern 2: UDP 伺服器

**場景**：無連線、低延遲通訊（DNS、遊戲、IoT）

```python
import socket

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
    sock.bind(("0.0.0.0", 5353))
    print("UDP 伺服器 :5353")
    while True:
        data, addr = sock.recvfrom(1024)
        print(f"從 {addr} 收到: {data.decode()}")
        sock.sendto(data.upper(), addr)  # 回送
```

### Pattern 3: WebSocket（L7）

**場景**：即時雙向通訊

```python
"""websockets 簡易 echo server"""
import asyncio
import websockets

async def echo(ws: websockets.WebSocketServerProtocol) -> None:
    async for message in ws:
        await ws.send(f"Echo: {message}")

async def main() -> None:
    async with websockets.serve(echo, "localhost", 8765):
        await asyncio.Future()  # 永久運行

# asyncio.run(main())
```

### Pattern 4: 連線池與重試

**場景**：高可靠性 HTTP 請求

```python
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def fetch_with_retry(client: httpx.AsyncClient, url: str) -> dict:
    resp = await client.get(url, timeout=10.0)
    resp.raise_for_status()
    return resp.json()

async def main() -> None:
    # 連線池自動管理
    async with httpx.AsyncClient(
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
    ) as client:
        data = await fetch_with_retry(client, "https://api.example.com/data")
```

## 工具鏈推薦

| 工具 | 用途 | 安裝 | OSI 層 |
|------|------|------|--------|
| socket | TCP/UDP/Raw | 標準庫 | L2-L4 |
| asyncio | 非同步 I/O | 標準庫 | L4-L7 |
| selectors | I/O 多工 | 標準庫 | L4 |
| ssl | TLS 加密 | 標準庫 | L5-L6 |
| struct | 二進位封包 | 標準庫 | L3-L4 |
| httpx | HTTP Client | `pip install httpx` | L7 |
| aiohttp | HTTP Server/Client | `pip install aiohttp` | L7 |
| websockets | WebSocket | `pip install websockets` | L7 |
| scapy | 封包操作 | `pip install scapy` | L2-L7 |
| paramiko | SSH | `pip install paramiko` | L7 |
| asyncssh | Async SSH | `pip install asyncssh` | L7 |
| dnspython | DNS 查詢 | `pip install dnspython` | L7 |
| uvloop | 高效能事件迴圈 | `pip install uvloop` | L4 |
| tenacity | 重試邏輯 | `pip install tenacity` | - |

## 延伸閱讀

讀取 `references/` 目錄下的對應檔案：
- `references/examples.md` — 完整可運行範例
- `references/cheatsheet.md` — 速查表
- `references/pitfalls.md` — 常見錯誤與解法

## 版本相容性

| Python 版本 | 支援狀態 | 備註 |
|-------------|----------|------|
| 3.13+ | ✅ 完整支援 | ssl 改進、socket 新功能 |
| 3.12 | ✅ | asyncio TaskGroup 穩定 |
| 3.11 | ✅ | asyncio.TaskGroup 首次加入 |
| 3.10 | ⚠️ 部分 | 缺少 TaskGroup |
