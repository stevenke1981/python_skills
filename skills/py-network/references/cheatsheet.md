# py-network 速查表

## socket 建立

```python
import socket

# TCP (串流)
tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# UDP (資料報)
udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# IPv6 TCP
tcp6 = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)

# Unix Domain Socket
unix = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

# 便捷函式（自動解析 host、支援 Happy Eyeballs）
sock = socket.create_connection(("example.com", 80), timeout=10)
```

## socket 生命週期

| 角色 | 流程 |
|------|------|
| **伺服器** | `socket()` → `setsockopt()` → `bind()` → `listen()` → `accept()` → `recv()`/`send()` → `close()` |
| **客戶端** | `socket()` → `connect()` → `send()`/`recv()` → `close()` |
| **UDP** | `socket()` → `bind()` → `recvfrom()`/`sendto()` → `close()` |

## 常用 socket 選項

```python
# 允許位址重用（避免 TIME_WAIT）
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# TCP Keepalive
sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

# TCP_NODELAY（停用 Nagle 演算法，低延遲）
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

# 接收緩衝區大小
sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)

# 設定超時
sock.settimeout(30.0)           # 30 秒超時
sock.setblocking(False)         # 非阻塞
sock.setblocking(True)          # 阻塞（預設）
```

## asyncio Stream API

```python
import asyncio

# TCP 客戶端
reader, writer = await asyncio.open_connection("host", 8888)
# 含 SSL
reader, writer = await asyncio.open_connection("host", 443, ssl=True)

# TCP 伺服器
server = await asyncio.start_server(callback, "0.0.0.0", 8888)

# Unix Socket
reader, writer = await asyncio.open_unix_connection("/tmp/my.sock")
server = await asyncio.start_unix_server(callback, "/tmp/my.sock")
```

### StreamReader 方法

| 方法 | 說明 |
|------|------|
| `await read(n)` | 讀取最多 n bytes |
| `await readline()` | 讀到 `\n` |
| `await readexactly(n)` | 精確讀取 n bytes（不足則 IncompleteReadError） |
| `await readuntil(sep)` | 讀到分隔符 |
| `at_eof()` | 是否到達 EOF |

### StreamWriter 方法

| 方法 | 說明 |
|------|------|
| `write(data)` | 寫入 buffer |
| `writelines(list)` | 寫入多段 |
| `await drain()` | flush buffer |
| `close()` | 開始關閉 |
| `await wait_closed()` | 等待關閉完成 |
| `await start_tls(ctx)` | 升級為 TLS |
| `get_extra_info("peername")` | 取得對方地址 |
| `is_closing()` | 是否正在關閉 |

## struct 封包格式碼

| 碼 | C 類型 | Python 類型 | 大小 |
|----|--------|-------------|------|
| `b` / `B` | signed/unsigned char | int | 1 |
| `h` / `H` | short / unsigned short | int | 2 |
| `i` / `I` | int / unsigned int | int | 4 |
| `q` / `Q` | long long / unsigned | int | 8 |
| `f` | float | float | 4 |
| `d` | double | float | 8 |
| `s` | char[] | bytes | 字串 |

**位元組序前綴**：

| 前綴 | 說明 |
|------|------|
| `!` | 網路序（Big-Endian）**推薦** |
| `>` | Big-Endian |
| `<` | Little-Endian |
| `@` | 原生 (預設) |

```python
import struct
# 封裝：4-byte 大端序整數
header = struct.pack("!I", 1024)  # b'\x00\x00\x04\x00'
# 解析
(value,) = struct.unpack("!I", header)  # 1024
```

## httpx 速查

```python
import httpx

# GET
resp = httpx.get("https://api.example.com/data", params={"key": "val"}, timeout=10)

# POST JSON
resp = httpx.post("https://api.example.com/data", json={"name": "test"}, timeout=10)

# POST 表單
resp = httpx.post("https://api.example.com/form", data={"field": "value"}, timeout=10)

# 上傳檔案
with open("file.pdf", "rb") as f:
    resp = httpx.post("https://api.example.com/upload", files={"file": f}, timeout=30)

# 認證
resp = httpx.get(url, headers={"Authorization": "Bearer TOKEN"}, timeout=10)

# 連線池設定
limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)
async with httpx.AsyncClient(limits=limits, timeout=10.0) as client:
    resp = await client.get(url)
```

## 常見 port 對照

| Port | 協定 | 說明 |
|------|------|------|
| 22 | SSH | 安全遠端登入 |
| 53 | DNS | 域名解析 |
| 80 | HTTP | 網頁 |
| 443 | HTTPS | 加密網頁 |
| 3306 | MySQL | 資料庫 |
| 5432 | PostgreSQL | 資料庫 |
| 6379 | Redis | 快取 |
| 8080 | HTTP Alt | 開發常用 |
| 8443 | HTTPS Alt | 開發常用 |
| 8888 | - | 自訂服務 |

## SSL/TLS 速查

```python
import ssl

# 客戶端：驗證伺服器憑證（預設即安全）
ctx = ssl.create_default_context()

# 客戶端：自訂 CA
ctx = ssl.create_default_context(cafile="/path/to/ca.pem")

# 伺服器端
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain("server.pem", "server.key")

# ⚠️ 不要在生產環境禁用驗證
# ctx.check_hostname = False           # 不安全！
# ctx.verify_mode = ssl.CERT_NONE      # 不安全！
```
