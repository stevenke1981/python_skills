# py-async 速查表

## 基本語法

```python
import asyncio

# 定義 coroutine
async def my_coro() -> str:
    await asyncio.sleep(1)
    return "done"

# 執行 coroutine
asyncio.run(my_coro())
```

## asyncio 常用 API

### 啟動與執行

| API | 用途 | 版本 |
|-----|------|------|
| `asyncio.run(coro)` | 建立 loop + 執行 + 關閉 | 3.7+ |
| `asyncio.create_task(coro)` | 在當前 loop 排程任務 | 3.7+ |
| `asyncio.sleep(delay)` | 非同步等待 | 3.4+ |
| `asyncio.to_thread(func, *args)` | 在執行緒池跑阻塞函式 | 3.9+ |

### 並行執行

| API | 用途 | 版本 |
|-----|------|------|
| `asyncio.TaskGroup()` | 結構化並行（推薦） | 3.11+ |
| `asyncio.gather(*coros)` | 並行執行多個 awaitable | 3.4+ |
| `asyncio.wait(tasks)` | 等待多個任務（可設條件） | 3.4+ |
| `asyncio.as_completed(coros)` | 按完成順序迭代結果 | 3.4+ |

### 超時與取消

| API | 用途 | 版本 |
|-----|------|------|
| `asyncio.timeout(delay)` | async context manager 超時 | 3.11+ |
| `asyncio.timeout_at(when)` | 指定絕對時間超時 | 3.11+ |
| `asyncio.shield(coro)` | 保護 awaitable 不被取消 | 3.4+ |
| `task.cancel()` | 取消任務 | 3.4+ |
| `task.uncancel()` | 減少取消計數 | 3.11+ |

### 同步原語

| API | 用途 | 版本 |
|-----|------|------|
| `asyncio.Lock()` | 互斥鎖 | 3.4+ |
| `asyncio.Semaphore(n)` | 信號量（限流） | 3.4+ |
| `asyncio.Event()` | 事件通知 | 3.4+ |
| `asyncio.Condition()` | 條件變數 | 3.4+ |
| `asyncio.Queue(maxsize)` | 非同步佇列 | 3.4+ |

### 跨執行緒

| API | 用途 | 版本 |
|-----|------|------|
| `asyncio.to_thread(func)` | 在 executor 跑同步函式 | 3.9+ |
| `asyncio.run_coroutine_threadsafe(coro, loop)` | 從其他執行緒提交 coro | 3.4+ |

## TaskGroup 模式

```python
# 基本用法
async with asyncio.TaskGroup() as tg:
    t1 = tg.create_task(coro1())
    t2 = tg.create_task(coro2())
# 離開後 t1.result() / t2.result() 可用

# 錯誤處理
try:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(may_fail())
        tg.create_task(also_may_fail())
except* ValueError as eg:
    for e in eg.exceptions:
        print(e)
except* TypeError as eg:
    for e in eg.exceptions:
        print(e)
```

## aiohttp 模式

```python
import aiohttp

# GET 請求
async with aiohttp.ClientSession() as session:
    async with session.get("https://api.example.com/data") as resp:
        data = await resp.json()

# POST 請求
async with aiohttp.ClientSession() as session:
    async with session.post(url, json={"key": "val"}) as resp:
        result = await resp.json()

# 設定 timeout
timeout = aiohttp.ClientTimeout(total=30, connect=10)
async with aiohttp.ClientSession(timeout=timeout) as session:
    ...
```

## httpx 模式（同步 / 非同步通用）

```python
import httpx

# 非同步
async with httpx.AsyncClient() as client:
    resp = await client.get("https://api.example.com/data")
    data = resp.json()

# 同步（相同 API）
with httpx.Client() as client:
    resp = client.get("https://api.example.com/data")
```

## 常用型別標註

```python
from collections.abc import (
    AsyncIterator,
    AsyncGenerator,
    Awaitable,
    Coroutine,
)

# Async generator 型別
async def gen() -> AsyncGenerator[int, None]:
    yield 1

# Async iterator 型別
async def iter_items() -> AsyncIterator[str]:
    yield "item"

# 接受任何 awaitable
async def run_it(aw: Awaitable[str]) -> str:
    return await aw
```

## 效能調校

```python
# 使用 uvloop 取代預設 event loop（Linux/macOS）
import uvloop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# 啟用 debug 模式
asyncio.run(main(), debug=True)

# eager task factory（3.12+）
loop = asyncio.get_running_loop()
loop.set_task_factory(asyncio.eager_task_factory)
```

## Async Context Manager 模板

```python
from types import TracebackType

class AsyncResource:
    async def __aenter__(self) -> "AsyncResource":
        # 取得資源
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        # 釋放資源
        pass
```

## 裝飾器：contextlib

```python
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

@asynccontextmanager
async def managed_resource() -> AsyncIterator[str]:
    resource = "opened"
    try:
        yield resource
    finally:
        print("closed")
```
