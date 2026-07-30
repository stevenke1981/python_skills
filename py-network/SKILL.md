---
name: py-network
description: >
  Build and review authorized Python networking software across TCP, UDP, TLS, HTTP clients, WebSocket, DNS, SSH, proxies, and custom protocols. Use for socket or asyncio streams, message framing, connection limits, timeouts, retries, backpressure, graceful shutdown, protocol parsing, current websockets asyncio APIs, and secure network automation within an explicitly permitted scope.
compatibility: Agent Skills-compatible. Raw sockets, packet capture, scanning, proxies, tunnels, and SSH automation require OS capabilities and explicit authorization.
metadata:
  author: stevenke1981
  version: "2.0.0"
  last-reviewed: "2026-07-30"
---

# Python 網路程式設計

## 目標與安全邊界

用此 skill 建立具訊息邊界、逾時、連線限制、背壓、TLS 與 graceful shutdown 的網路程式。

在執行掃描、封包擷取、raw socket、proxy、tunnel、SSH 批次操作或流量重放前，必須確認目標、時間、協議與權限範圍。未取得授權時，只能提供本機、模擬或防禦性範例。

若任務是一般 FastAPI/HTTP endpoint，以 `py-web` 為主；若核心問題是 asyncio cancellation，以 `py-async` 為支援。

## 執行流程

1. **定義協議契約**：transport、訊息格式、最大長度、編碼、版本、錯誤碼與順序語意。
2. **確認信任與授權邊界**：可連線來源、目的地、DNS、proxy、憑證與網路範圍。
3. **設定資源上限**：連線數、message size、queue、buffer、timeout、rate 與總工作時間。
4. **實作 framing 與 parser**：先檢查長度與型別，再配置記憶體或解析內容。
5. **加入 lifecycle**：連線建立、取消、半關閉、斷線、重連與 server shutdown。
6. **加入安全層**：TLS 驗證、認證、allowlist、SSRF 防護與敏感 log 遮蔽。
7. **故障測試**：partial read/write、slow peer、malformed frame、timeout、DNS/TLS 失敗與重試。
8. **觀測與交付**：記錄連線、延遲、流量、錯誤、拒絕原因與資源使用。

## 協議與工具選擇

| 情境 | 優先 API |
|---|---|
| 一般同步 TCP/UDP | `socket` |
| 大量並行 TCP | `asyncio` streams |
| HTTP client | `httpx` 或既有專案標準 client |
| WebSocket | `websockets.asyncio` 或 Web framework 內建 API |
| DNS | `dnspython` 或系統 resolver |
| SSH | `asyncssh` / `paramiko`，搭配 host-key 驗證 |
| 封包分析 | Scapy／pcap，只在授權環境 |
| 高效能既有協議 | 優先成熟 library，不自行重寫 TLS、HTTP 或 SSH |

## TCP 訊息邊界

TCP 是 byte stream，單次 `recv()` 不等於一個完整訊息。常用 framing：

- 固定長度
- 分隔符
- 長度前綴
- 成熟協議格式

### asyncio 長度前綴範例

```python
from __future__ import annotations

import asyncio
import struct


HEADER = struct.Struct("!I")
MAX_MESSAGE_BYTES = 1_048_576
READ_TIMEOUT_SECONDS = 10.0


async def read_frame(reader: asyncio.StreamReader) -> bytes:
    header = await asyncio.wait_for(
        reader.readexactly(HEADER.size),
        timeout=READ_TIMEOUT_SECONDS,
    )
    (length,) = HEADER.unpack(header)
    if length > MAX_MESSAGE_BYTES:
        raise ValueError(f"frame too large: {length} bytes")
    return await asyncio.wait_for(
        reader.readexactly(length),
        timeout=READ_TIMEOUT_SECONDS,
    )


async def write_frame(
    writer: asyncio.StreamWriter,
    payload: bytes,
) -> None:
    if len(payload) > MAX_MESSAGE_BYTES:
        raise ValueError("payload exceeds protocol limit")
    writer.write(HEADER.pack(len(payload)) + payload)
    await writer.drain()
```

規則：

- 先驗證長度，再配置或讀取 payload。
- 為 header 與 body 設定逾時。
- 使用 `readexactly()` 處理 partial read。
- `writer.drain()` 只提供 transport 層背壓，應用層仍需 bounded queue。
- 解析器要有 recursion、collection count、compression ratio 等額外上限。

## 安全的連線處理

```python
import asyncio


async def handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    peer = writer.get_extra_info("peername")
    try:
        while payload := await read_frame(reader):
            response = payload.upper()
            await write_frame(writer, response)
    except asyncio.IncompleteReadError:
        pass
    except (TimeoutError, ValueError) as exc:
        print(f"connection rejected for {peer}: {exc}")
    finally:
        writer.close()
        await writer.wait_closed()
```

正式服務不要用 `print()` 記錄敏感 payload；使用結構化 log，遮蔽 token、cookie、authorization 與個資。

## TLS

- client 使用 `ssl.create_default_context()`，預設驗證 hostname 與 CA。
- 不以 `CERT_NONE` 或關閉 hostname check 解決測試憑證問題。
- server 使用正式憑證、適當 protocol minimum 與安全 cipher policy。
- mTLS 必須驗證 client certificate chain 與應用身分映射。
- 測試環境建立自己的 CA/fixture，不修改全域安全設定。
- 憑證輪替、過期與 clock skew 要有監控。

## HTTP Client 規則

- 重用 client 取得 connection pooling；不要每次請求都新建 client。
- 分開設定 connect、read、write 與 pool timeout。
- 限制 redirects，並在 redirect 後重新驗證目的地。
- 對使用者提供 URL 的服務防範 SSRF：限制 scheme、host、port、解析後 IP 與 redirect。
- response body 設定最大大小，streaming download 寫入暫存檔後再 atomic rename。
- 僅對 transient failure 且可安全重試的操作重試。

### 重試政策

- GET/HEAD 等冪等操作通常較適合重試。
- POST/付款/建立資源需要 idempotency key 或 server-side 去重。
- 使用 bounded exponential backoff + jitter。
- 尊重 `Retry-After` 與 rate-limit header。
- 4xx 驗證錯誤通常不重試。
- 設定整體 deadline，不讓每次 retry 各自耗盡完整 timeout。

## WebSocket 現行 asyncio API

```python
import asyncio

from websockets.asyncio.server import ServerConnection, serve


async def echo(websocket: ServerConnection) -> None:
    async for message in websocket:
        await websocket.send(f"Echo: {message}")


async def main() -> None:
    async with serve(
        echo,
        "127.0.0.1",
        8765,
        max_size=1_048_576,
        max_queue=16,
        ping_interval=20,
        ping_timeout=20,
    ):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
```

現行 `websockets` asyncio server handler 接收 `ServerConnection`；不要再以舊 `WebSocketServerProtocol` 型別作新程式預設。

生產環境另需：

- browser client 的 `Origin` allowlist
- 認證與 session expiry
- per-connection send queue 與 slow-client 策略
- message、fragment、compression 與連線數限制
- server shutdown 時的 close code、deadline 與 task cancellation
- 不依序等待每個 client 廣播；使用有界並行並處理個別失敗

## UDP

- UDP 無連線、可能遺失、重複、亂序或截斷。
- protocol 必須自行處理 message ID、重放、防偽、fragment 與最大 datagram。
- 不把來源位址當作可靠身分。
- 避免建立可被利用的 amplification response。
- 需要可靠傳輸時優先 TCP、QUIC 或成熟協議。

## DNS、Proxy 與 SSH

### DNS

- DNS 名稱解析後重新檢查實際 IP 範圍，防止 SSRF 與 rebinding。
- 不假設一次解析結果永遠有效。
- 記錄 resolver、TTL 與失敗類型，但不洩漏敏感 query。

### Proxy / Tunnel

- 明確限制 listen address、allowed destination、protocol 與認證。
- 預設只綁 loopback，除非使用者要求並配置存取控制。
- 不建立 open proxy。
- 設定 idle timeout、bandwidth、connection 與 audit limits。

### SSH

- 驗證 host key，不使用無條件 auto-add。
- 金鑰從安全儲存取得，不寫入 repository。
- 指令與參數分離，避免 shell injection。
- 批次操作有 dry-run、主機 allowlist、並行限制與失敗彙整。

## 測試策略

- parser 使用 fuzz/property-based tests 測 malformed input。
- 使用 loopback 或 ephemeral port，不依賴固定外部服務。
- 測 partial reads、slowloris、斷線、half-close、timeout 與取消。
- 使用測試 CA 驗證 TLS 成功、過期、錯誤 hostname 與不可信鏈。
- 對 HTTP 重試測 idempotency、Retry-After 與總 deadline。
- 對 WebSocket 測 origin、message limit、slow client 與 graceful close。
- 壓力測試要設定明確授權範圍與安全上限。

## 交付標準

- 協議 framing、版本、最大訊息與錯誤行為已記錄。
- 所有讀寫、連線與整體工作都有 timeout/deadline。
- queue、buffer、連線、速率與並行均有上限。
- TLS 預設驗證憑證與 hostname，測試不降低全域安全。
- retry 僅套用於安全情境，非冪等操作有去重策略。
- 掃描、raw socket、proxy、tunnel 與 SSH 均有明確授權與 allowlist。
- shutdown 不留下 socket、task、thread 或未 flush 資料。
- malformed input、斷線與 slow peer 已測試。

## 延伸閱讀

- [完整範例](references/examples.md)
- [速查表](references/cheatsheet.md)
- [常見陷阱](references/pitfalls.md)
- [websockets asyncio server API](https://websockets.readthedocs.io/en/stable/reference/asyncio/server.html)

## 版本相容性

| 環境 | 建議 |
|---|---|
| Python 3.14 | 穩定維護基準；可用現行 asyncio 與 TLS 改進 |
| Python 3.10–3.13 | 支援；依最低版本調整 TaskGroup 等 API |
| websockets 16+ | 使用 `websockets.asyncio` 與 `ServerConnection` |
| 舊 websockets | 先讀 migration guide，不混用 legacy 與新 asyncio API |
| Raw/packet APIs | 依 OS、capability 與授權範圍驗證 |
