---
name: py-async
description: >
  Python asyncio patterns, structured concurrency, and async best practices.
  Trigger when user mentions asyncio, async/await, TaskGroup, aiohttp,
  structured concurrency, event loop, coroutine, non-blocking IO,
  async generators, async context manager, concurrent tasks.
  Also trigger when user asks about parallel IO, async HTTP requests,
  or converting synchronous code to asynchronous.
---

# Python 非同步程式設計

## Quick Start（30 秒上手）

```python
import asyncio

async def fetch(name: str, delay: float) -> str:
    """模擬非同步 IO 操作"""
    await asyncio.sleep(delay)
    return f"{name} 完成（耗時 {delay}s）"

async def main() -> None:
    async with asyncio.TaskGroup() as tg:
        task_a = tg.create_task(fetch("A", 2.0))
        task_b = tg.create_task(fetch("B", 1.0))
    # 離開 context manager 後，所有任務已完成
    print(task_a.result())  # A 完成（耗時 2.0s）
    print(task_b.result())  # B 完成（耗時 1.0s）

asyncio.run(main())
# 總耗時約 2 秒（並行執行），而非 3 秒（串行執行）
```

## 核心概念

### 1. Coroutine 與 Event Loop

`async def` 定義的函式是 **coroutine function**，呼叫後回傳 coroutine object。
必須透過 `await` 或排程到 event loop 才會執行。

```python
import asyncio

async def greet(name: str) -> str:
    await asyncio.sleep(0.1)  # 讓出控制權給 event loop
    return f"Hello, {name}!"

# asyncio.run() 建立 event loop → 執行 coroutine → 關閉 loop
result = asyncio.run(greet("World"))
```

**關鍵概念**：`await` 是主動的 context switch，讓 event loop 可以去執行其他已就緒的任務。

### 2. TaskGroup（結構化並行，Python 3.11+）

`TaskGroup` 是取代 `asyncio.gather()` 的現代做法，提供更安全的錯誤處理機制。

```python
import asyncio

async def worker(task_id: int) -> int:
    await asyncio.sleep(task_id * 0.1)
    return task_id * 10

async def main() -> None:
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(worker(i)) for i in range(5)]
    # 所有任務完成，或其中一個失敗時自動取消其餘任務
    results = [t.result() for t in tasks]
    print(results)  # [0, 10, 20, 30, 40]

asyncio.run(main())
```

**TaskGroup vs gather**：
- TaskGroup 在任一子任務拋出例外時，自動取消所有其他子任務
- `gather(return_exceptions=False)` 不會自動取消其他任務
- TaskGroup 使用 `except*` 處理 `ExceptionGroup`

### 3. Timeout 控制（Python 3.11+）

```python
import asyncio

async def slow_operation() -> str:
    await asyncio.sleep(10)
    return "完成"

async def main() -> None:
    try:
        async with asyncio.timeout(2.0):
            result = await slow_operation()
    except TimeoutError:
        print("操作逾時！")

asyncio.run(main())
```

`asyncio.timeout()` 回傳一個 async context manager，超時時自動取消內部任務並拋出 `TimeoutError`。

### 4. Async Generator 與 Async Iterator

```python
import asyncio
from collections.abc import AsyncIterator

async def countdown(n: int) -> AsyncIterator[int]:
    """非同步產生器：每秒倒數"""
    while n > 0:
        yield n
        n -= 1
        await asyncio.sleep(1.0)

async def main() -> None:
    async for count in countdown(3):
        print(count)  # 3, 2, 1（每秒一個）

asyncio.run(main())
```

### 5. 同步轉非同步：to_thread

```python
import asyncio
import time

def blocking_io() -> str:
    """模擬阻塞式 IO（如檔案操作、同步 HTTP）"""
    time.sleep(2)
    return "資料讀取完畢"

async def main() -> None:
    # 將阻塞函式放到執行緒池，不阻塞 event loop
    result = await asyncio.to_thread(blocking_io)
    print(result)

asyncio.run(main())
```

## 實戰 Patterns

### Pattern 1: 並行 HTTP 請求（aiohttp）

**場景**：同時對多個 API 端點發送請求

```python
import asyncio
import aiohttp

async def fetch_url(
    session: aiohttp.ClientSession,
    url: str,
) -> dict[str, str | int]:
    """取得單一 URL 的回應"""
    async with session.get(url) as response:
        text = await response.text()
        return {"url": url, "status": response.status, "length": len(text)}

async def fetch_all(urls: list[str]) -> list[dict[str, str | int]]:
    """並行取得所有 URL"""
    async with aiohttp.ClientSession() as session:
        async with asyncio.TaskGroup() as tg:
            tasks = [
                tg.create_task(fetch_url(session, url))
                for url in urls
            ]
        return [t.result() for t in tasks]

async def main() -> None:
    urls = [
        "https://httpbin.org/get",
        "https://httpbin.org/delay/1",
        "https://httpbin.org/status/200",
    ]
    results = await fetch_all(urls)
    for r in results:
        print(f"{r['url']} → {r['status']}")

asyncio.run(main())
```

**注意**：使用 `aiohttp.ClientSession` 作為 async context manager，確保連線池正確釋放。

### Pattern 2: 限流並行（Semaphore）

**場景**：並行任務過多時需要限制同時執行數量

```python
import asyncio

async def limited_fetch(
    sem: asyncio.Semaphore,
    task_id: int,
) -> str:
    async with sem:  # 最多允許 N 個任務同時進入
        print(f"任務 {task_id} 開始")
        await asyncio.sleep(1.0)
        return f"任務 {task_id} 完成"

async def main() -> None:
    sem = asyncio.Semaphore(3)  # 同時最多 3 個
    async with asyncio.TaskGroup() as tg:
        tasks = [
            tg.create_task(limited_fetch(sem, i))
            for i in range(10)
        ]
    for t in tasks:
        print(t.result())

asyncio.run(main())
```

### Pattern 3: 生產者-消費者模式

**場景**：持續產生資料、多個消費者並行處理

```python
import asyncio
import random

async def producer(queue: asyncio.Queue[int], n: int) -> None:
    for i in range(n):
        await asyncio.sleep(random.uniform(0.1, 0.5))
        await queue.put(i)
        print(f"生產: {i}")
    # 放入哨兵值通知消費者結束
    await queue.put(-1)

async def consumer(name: str, queue: asyncio.Queue[int]) -> None:
    while True:
        item = await queue.get()
        if item == -1:
            await queue.put(-1)  # 傳遞哨兵給下一個消費者
            break
        await asyncio.sleep(random.uniform(0.2, 0.6))
        print(f"消費者 {name} 處理: {item}")
        queue.task_done()

async def main() -> None:
    queue: asyncio.Queue[int] = asyncio.Queue(maxsize=5)
    async with asyncio.TaskGroup() as tg:
        tg.create_task(producer(queue, 10))
        tg.create_task(consumer("A", queue))
        tg.create_task(consumer("B", queue))

asyncio.run(main())
```

## 工具鏈推薦

| 工具 | 用途 | 安裝 | 備註 |
|------|------|------|------|
| aiohttp | 非同步 HTTP client/server | `pip install aiohttp` | 最成熟的 async HTTP 庫 |
| httpx | 同步/非同步雙模式 HTTP | `pip install httpx` | API 類似 requests |
| uvloop | 高效能 event loop（Linux/macOS） | `pip install uvloop` | 替代預設 event loop，效能提升 2-4x |
| anyio | 跨框架 async 抽象層 | `pip install anyio` | 支援 asyncio + Trio |
| aiocache | 非同步快取 | `pip install aiocache` | 支援 Redis、Memcached |
| aiofiles | 非同步檔案 IO | `pip install aiofiles` | 包裝 `open()` 為 async |
| asyncpg | 非同步 PostgreSQL driver | `pip install asyncpg` | 高效能 native driver |

## 延伸閱讀

讀取 `references/` 目錄下的對應檔案：
- `references/examples.md` — 完整可運行範例
- `references/cheatsheet.md` — 速查表
- `references/pitfalls.md` — 常見錯誤與解法

## 版本相容性

| Python 版本 | 支援狀態 | 備註 |
|-------------|----------|------|
| 3.13+ | ✅ 完整支援 | `as_completed` 支援 async iteration |
| 3.12 | ✅ 完整支援 | `eager_task_factory`、Task `eager_start` 參數 |
| 3.11 | ✅ 完整支援 | `TaskGroup`、`asyncio.timeout()`、`ExceptionGroup` |
| 3.10 | ⚠️ 部分 | 移除 `loop` 參數、無 TaskGroup |
| 3.9 | ⚠️ 部分 | 新增 `asyncio.to_thread()` |
