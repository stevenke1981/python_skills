# py-async 完整範例集

## 範例 1：TaskGroup + 錯誤處理

```python
"""TaskGroup 結構化並行 + ExceptionGroup 處理"""
import asyncio

class FetchError(Exception):
    """自定義取得資料錯誤"""

async def fetch_data(source: str, should_fail: bool = False) -> str:
    """模擬從不同來源取得資料"""
    await asyncio.sleep(0.5)
    if should_fail:
        raise FetchError(f"{source} 回應錯誤")
    return f"{source}: 資料取得成功"

async def main() -> None:
    try:
        async with asyncio.TaskGroup() as tg:
            t1 = tg.create_task(fetch_data("API-A"))
            t2 = tg.create_task(fetch_data("API-B", should_fail=True))
            t3 = tg.create_task(fetch_data("API-C"))
    except* FetchError as eg:
        # except* 捕獲 ExceptionGroup 中的特定例外類型
        for exc in eg.exceptions:
            print(f"捕獲錯誤: {exc}")
    except* Exception as eg:
        for exc in eg.exceptions:
            print(f"其他錯誤: {exc}")
    else:
        print(t1.result(), t3.result())

asyncio.run(main())
```

## 範例 2：aiohttp 並行抓取 + 重試

```python
"""使用 aiohttp 並行抓取多個 URL，含指數退避重試"""
import asyncio
from typing import Any
import aiohttp

async def fetch_with_retry(
    session: aiohttp.ClientSession,
    url: str,
    max_retries: int = 3,
) -> dict[str, Any]:
    """帶重試機制的非同步 HTTP GET"""
    for attempt in range(max_retries):
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {"url": url, "data": data, "attempts": attempt + 1}
                # 伺服器錯誤，等待後重試
                if resp.status >= 500:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return {"url": url, "error": f"HTTP {resp.status}", "attempts": attempt + 1}
        except (aiohttp.ClientError, asyncio.TimeoutError):
            if attempt == max_retries - 1:
                return {"url": url, "error": "所有重試失敗", "attempts": max_retries}
            await asyncio.sleep(2 ** attempt)
    return {"url": url, "error": "不應到達此處", "attempts": max_retries}

async def fetch_all(urls: list[str]) -> list[dict[str, Any]]:
    """並行取得所有 URL"""
    async with aiohttp.ClientSession() as session:
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(fetch_with_retry(session, u)) for u in urls]
        return [t.result() for t in tasks]

async def main() -> None:
    urls = [
        "https://httpbin.org/json",
        "https://httpbin.org/get",
        "https://httpbin.org/uuid",
    ]
    results = await fetch_all(urls)
    for r in results:
        print(f"  {r['url']} → 嘗試 {r['attempts']} 次")

asyncio.run(main())
```

## 範例 3：Async Context Manager 資源管理

```python
"""自定義 async context manager 管理連線池"""
import asyncio
from types import TracebackType

class AsyncConnectionPool:
    """模擬非同步連線池"""

    def __init__(self, pool_size: int = 5) -> None:
        self._pool_size = pool_size
        self._semaphore: asyncio.Semaphore | None = None
        self._connections: list[int] = []

    async def __aenter__(self) -> "AsyncConnectionPool":
        self._semaphore = asyncio.Semaphore(self._pool_size)
        self._connections = list(range(self._pool_size))
        print(f"連線池已建立（上限 {self._pool_size}）")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._connections.clear()
        print("連線池已關閉")

    async def execute(self, query: str) -> str:
        assert self._semaphore is not None
        async with self._semaphore:
            conn_id = self._connections[0]  # 簡化：取第一個
            await asyncio.sleep(0.1)  # 模擬查詢
            return f"連線 {conn_id} 執行: {query}"

async def main() -> None:
    async with AsyncConnectionPool(pool_size=3) as pool:
        async with asyncio.TaskGroup() as tg:
            tasks = [
                tg.create_task(pool.execute(f"SELECT {i}"))
                for i in range(6)
            ]
        for t in tasks:
            print(t.result())

asyncio.run(main())
```

## 範例 4：Async Iterator 串流處理

```python
"""使用 async iterator 串流處理大量資料"""
import asyncio
from collections.abc import AsyncIterator

class AsyncChunkReader:
    """模擬非同步逐塊讀取資料"""

    def __init__(self, data: list[str], chunk_delay: float = 0.2) -> None:
        self._data = data
        self._index = 0
        self._delay = chunk_delay

    def __aiter__(self) -> "AsyncChunkReader":
        return self

    async def __anext__(self) -> str:
        if self._index >= len(self._data):
            raise StopAsyncIteration
        chunk = self._data[self._index]
        self._index += 1
        await asyncio.sleep(self._delay)  # 模擬 IO 延遲
        return chunk

async def process_stream(reader: AsyncIterator[str]) -> list[str]:
    """處理非同步串流"""
    results: list[str] = []
    async for chunk in reader:
        processed = chunk.upper()
        results.append(processed)
        print(f"處理: {chunk} → {processed}")
    return results

async def main() -> None:
    data = ["alpha", "bravo", "charlie", "delta", "echo"]
    reader = AsyncChunkReader(data)
    results = await process_stream(reader)
    print(f"共處理 {len(results)} 個區塊")

asyncio.run(main())
```

## 範例 5：eager_task_factory（Python 3.12+）

```python
"""eager_task_factory 讓 coroutine 同步開始執行"""
import asyncio

_cache: dict[str, str] = {}

async def cached_fetch(key: str) -> str:
    """帶記憶體快取的取得函式"""
    if key in _cache:
        return _cache[key]  # 同步返回，不需切換到 event loop
    await asyncio.sleep(0.5)  # 模擬 IO
    result = f"值_{key}"
    _cache[key] = result
    return result

async def main() -> None:
    # 設定 eager task factory：coroutine 在建立 Task 時就開始執行
    loop = asyncio.get_running_loop()
    loop.set_task_factory(asyncio.eager_task_factory)

    # 第一次呼叫：需要等待 IO
    result1 = await cached_fetch("foo")
    print(f"第一次: {result1}")

    # 第二次呼叫：快取命中，eager factory 讓 Task 同步完成
    result2 = await cached_fetch("foo")
    print(f"第二次（快取）: {result2}")

asyncio.run(main())
```
