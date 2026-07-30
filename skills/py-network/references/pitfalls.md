# py-network 常見陷阱與解法

## 陷阱 1：recv() 不保證接收完整訊息

**問題**：TCP 是位元組流，`recv(1024)` 可能只收到部分資料。

```python
# ❌ 假設 recv 一次收完
data = sock.recv(4096)
msg = json.loads(data)  # 可能只收到半段 JSON → 解析失敗
```

**解法**：使用訊息邊界協議（長度前綴、分隔符或固定長度）。

```python
# ✅ 長度前綴 + recv_exact
import struct

def recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("連線中斷")
        buf.extend(chunk)
    return bytes(buf)

# 讀取 4-byte header，取得 payload 長度
raw = recv_exact(sock, 4)
(length,) = struct.unpack("!I", raw)
payload = recv_exact(sock, length)
```

---

## 陷阱 2：忘記 SO_REUSEADDR

**問題**：重啟伺服器時出現 `OSError: [Errno 98] Address already in use`。

```python
# ❌ 上次連線 TIME_WAIT 尚未結束
srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.bind(("0.0.0.0", 8000))  # OSError!
```

**解法**：在 `bind()` 之前設定 `SO_REUSEADDR`。

```python
# ✅ 允許重用 TIME_WAIT 中的地址
srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("0.0.0.0", 8000))
```

---

## 陷阱 3：忘記 drain() 導致背壓失控

**問題**：asyncio `writer.write()` 只是寫入 buffer，不等待實際發送。高速寫入時記憶體暴漲。

```python
# ❌ 沒有 drain，buffer 無限增長
for msg in huge_list:
    writer.write(msg.encode())
# 記憶體可能暴漲到 GB
```

**解法**：定期呼叫 `await writer.drain()` 處理背壓。

```python
# ✅ 每次寫入後 drain
for msg in huge_list:
    writer.write(msg.encode())
    await writer.drain()  # 等待 buffer 清空
```

---

## 陷阱 4：blocking socket 無超時

**問題**：`recv()` 永久阻塞，若對方不回應程式會卡死。

```python
# ❌ 永遠等待
data = sock.recv(4096)  # 如果對方當機，永遠不會返回
```

**解法**：設定超時。

```python
# ✅ 設定超時
sock.settimeout(30.0)  # 30 秒後 raise socket.timeout
try:
    data = sock.recv(4096)
except socket.timeout:
    print("接收超時")
```

---

## 陷阱 5：send() vs sendall()

**問題**：`send()` 不保證發送完整資料，可能只發送了一部分。

```python
# ❌ send() 可能只發送部分
sock.send(large_data)  # 回傳值可能 < len(large_data)

# ✅ sendall() 保證全部發送
sock.sendall(large_data)
```

---

## 陷阱 6：SSL 憑證驗證被關閉

**問題**：開發時為了方便關閉 SSL 驗證，忘了恢復。

```python
# ❌ ⚠️ 極度不安全！中間人攻擊風險
ctx = ssl.SSLContext()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# ✅ 使用 create_default_context()（自動驗證）
ctx = ssl.create_default_context()
# 如需自訂 CA
ctx = ssl.create_default_context(cafile="/path/to/ca-bundle.pem")
```

---

## 陷阱 7：asyncio server 沒有 graceful shutdown

**問題**：直接 Ctrl+C 終止伺服器，已建立的連線被強制斷開。

```python
# ❌ 粗暴關閉
server = await asyncio.start_server(handle, "0.0.0.0", 8888)
await server.serve_forever()  # Ctrl+C → 所有連線立即斷開

# ✅ 優雅關閉
import signal

async def main() -> None:
    server = await asyncio.start_server(handle, "0.0.0.0", 8888)
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)

    async with server:
        await stop  # 等待關閉信號
    # server.__aexit__ 會等待現有連線完成
```

---

## 陷阱 8：DNS 解析在阻塞模式

**問題**：`socket.getaddrinfo()` 是阻塞呼叫，在 asyncio 中會阻塞事件迴圈。

```python
# ❌ 阻塞事件迴圈
result = socket.getaddrinfo("example.com", 80)

# ✅ 使用 asyncio 的非阻塞版本
loop = asyncio.get_running_loop()
result = await loop.getaddrinfo("example.com", 80)
```

---

## 陷阱 9：httpx 忘記設定 timeout

**問題**：`httpx` 預設的 timeout 是 5 秒，某些 API 需要更長時間。

```python
# ❌ 預設 timeout 可能不夠
resp = httpx.get("https://slow-api.example.com/data")

# ✅ 明確設定 timeout
resp = httpx.get(
    "https://slow-api.example.com/data",
    timeout=httpx.Timeout(30.0, connect=5.0)
)

# 非同步也一樣
async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
    resp = await client.get(url)
```

---

## 陷阱 10：socket 資源洩漏

**問題**：連線異常時忘記關閉 socket，導致 fd 耗盡。

```python
# ❌ 異常時 socket 未關閉
sock = socket.socket()
sock.connect(("example.com", 80))
data = sock.recv(4096)  # 可能拋出異常
sock.close()             # 不會執行

# ✅ 使用 context manager
with socket.socket() as sock:
    sock.connect(("example.com", 80))
    data = sock.recv(4096)
# 自動關閉，即使有異常

# asyncio 也一樣
reader, writer = await asyncio.open_connection("host", 8888)
try:
    data = await reader.read(4096)
finally:
    writer.close()
    await writer.wait_closed()
```
