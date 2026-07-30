---
name: py-async
description: >
  Design and debug Python asyncio systems with structured concurrency, TaskGroup, gather, cancellation, timeouts, bounded concurrency, queues, backpressure, streaming, graceful shutdown, blocking-call isolation, and async testing. Use for concurrent I/O, producer-consumer pipelines, task leaks, event-loop stalls, retry coordination, or choosing between async, threads, processes, and free-threaded execution.
compatibility: Agent Skills-compatible. TaskGroup and asyncio.timeout require Python 3.11+; respect the target project's minimum Python version.
metadata:
  author: stevenke1981
  version: "2.0.0"
  last-reviewed: "2026-07-30"
---

# Python 非同步與結構化並行

## 目標與邊界

用此 skill 建立可取消、有逾時、有背壓、會正確關閉資源的 asyncio 程式。非同步主要改善等待 I/O 時的併發，不會自動加速 CPU-bound 工作。

若主要交付物是網路協議，使用 `py-network` 為主；若只是同步程式的少量背景工作，不要為了「現代化」強行改成 async。

## 執行流程

1. **辨識工作型態**：區分 I/O-bound、CPU-bound、blocking library 與真正 async API。
2. **定義 ownership**：每個 task 由誰建立、等待、取消與收集錯誤。
3. **使用結構化並行**：parent scope 不結束，child task 就不能遺失。
4. **設定 deadline**：連線、單次操作與整體工作分別設 timeout。
5. **限制並行與緩衝**：Semaphore、Queue、connection pool 與 batch 都要有上限。
6. **設計取消安全**：`CancelledError` 必須向上傳播，資源在 `finally`/context manager 清理。
7. **測試故障與關閉**：timeout、partial failure、client disconnect、SIGTERM 與 task leak。
8. **加入觀測**：記錄 active tasks、queue depth、延遲、timeout、retry 與 cancellation。

## 選擇並行模型

| 工作 | 優先方案 |
|---|---|
| 大量 socket/HTTP/DB 等待 | asyncio |
| 少量 blocking I/O library | `asyncio.to_thread()` 或 thread pool |
| CPU-bound 純 Python | process pool；free-threaded 需實測且依賴相容 |
| 釋放 GIL 的 native 計算 | thread pool 或 library 自身平行能力，先 benchmark |
| 獨立服務／故障隔離 | 多 process 或工作佇列 |
| 單純依序工作 | 同步程式通常更清楚 |

不要在 event loop 內直接呼叫 `time.sleep()`、同步 HTTP、長時間檔案 I/O 或 CPU 密集迴圈。

## TaskGroup 與 gather

### 優先 TaskGroup 的情境

- child tasks 屬於同一 parent operation。
- 任一 child 失敗時，其他工作應取消。
- 需要收斂成明確的 `ExceptionGroup`。

```python
import asyncio


async def fetch_one(item_id: int) -> str:
    await asyncio.sleep(0.01)
    return f"item-{item_id}"


async def fetch_all(item_ids: list[int]) -> list[str]:
    tasks: list[asyncio.Task[str]] = []
    async with asyncio.TaskGroup() as group:
        for item_id in item_ids:
            tasks.append(group.create_task(fetch_one(item_id)))
    return [task.result() for task in tasks]
```

### gather 仍適合的情境

- 呼叫端刻意需要依輸入順序收集結果。
- 已清楚定義 partial failure 或 `return_exceptions=True` 的語意。
- 既有 API 契約就是接收一組 awaitables 並回傳列表。

`TaskGroup` 不是 `gather()` 的全面替代品；選擇取決於 failure propagation 與 task ownership。

## Timeout 與 Deadline

```python
import asyncio


async def load_profile(user_id: str) -> dict[str, object]:
    async with asyncio.timeout(5.0):
        return await query_profile(user_id)
```

規則：

- 使用整體 deadline，而不是讓每層各自擁有完整 timeout。
- timeout 後確認底層 operation 真的可取消；某些 thread/native call 仍會繼續執行。
- 不捕捉所有 `Exception` 後重試，否則可能吞掉程式錯誤。
- `asyncio.shield()` 只保護必須完成的短清理，不用來逃避取消。

## 取消安全

```python
import asyncio


async def consume(stream: AsyncStream) -> None:
    resource = await stream.open()
    try:
        async for item in resource:
            await process(item)
    except asyncio.CancelledError:
        await resource.abort()
        raise
    finally:
        await resource.aclose()
```

- 捕捉 `CancelledError` 後一定重新 `raise`，除非該函式有明確取消轉換契約。
- cleanup 本身要有 deadline，避免 shutdown 永久卡住。
- context manager 優先於分散的 open/close。
- 不建立無人持有 reference 的 fire-and-forget task。

## Bounded Concurrency

```python
import asyncio
from collections.abc import Awaitable, Callable, Sequence
from typing import TypeVar


T = TypeVar("T")
R = TypeVar("R")


async def bounded_map(
    func: Callable[[T], Awaitable[R]],
    items: Sequence[T],
    *,
    limit: int,
) -> list[R]:
    if limit < 1:
        raise ValueError("limit must be at least 1")

    semaphore = asyncio.Semaphore(limit)

    async def run(item: T) -> R:
        async with semaphore:
            return await func(item)

    async with asyncio.TaskGroup() as group:
        tasks = [group.create_task(run(item)) for item in items]
    return [task.result() for task in tasks]
```

對非常大的 input 不要一次建立全部 task；改用 bounded queue 或分批提交。

## Producer／Consumer 與背壓

每個 consumer 需要自己的停止訊號，且每次 `get()` 都必須對應一次 `task_done()`：

```python
import asyncio
from typing import Final


STOP: Final = object()


async def producer(
    queue: asyncio.Queue[object],
    *,
    worker_count: int,
) -> None:
    for item in range(100):
        await queue.put(item)
    for _ in range(worker_count):
        await queue.put(STOP)


async def consumer(
    queue: asyncio.Queue[object],
    worker_id: int,
) -> None:
    while True:
        item = await queue.get()
        try:
            if item is STOP:
                return
            await process_item(worker_id, int(item))
        finally:
            queue.task_done()


async def main() -> None:
    worker_count = 4
    queue: asyncio.Queue[object] = asyncio.Queue(maxsize=32)

    async with asyncio.TaskGroup() as group:
        group.create_task(producer(queue, worker_count=worker_count))
        for worker_id in range(worker_count):
            group.create_task(consumer(queue, worker_id))

    await queue.join()
```

不要讓 consumer 重新放回單一 sentinel；這會留下未完成項目或造成不穩定關閉。若 worker 可能動態增加，設計明確的 queue shutdown protocol。

## Blocking 與 CPU-bound 工作

### Blocking I/O

```python
result = await asyncio.to_thread(blocking_read, path)
```

- thread cancellation 通常只取消等待者，不能強制停止已執行的函式。
- 為 blocking function 提供自己的 timeout/cancellation token。
- 限制 default executor 大小，避免大量 thread。

### CPU-bound

- 優先 vectorized/native library 或演算法改善。
- 再考慮 `ProcessPoolExecutor`、專用 worker 或分散式 queue。
- 可選 free-threaded Python 時，仍需驗證 C extension、共享狀態與實際 scaling。
- 大型 payload 跨 process 傳輸可能抵銷平行收益。

## Retry

- 只重試 transient 且可安全重試的 operation。
- bounded exponential backoff + jitter。
- 將 retry budget 納入整體 deadline。
- cancellation 必須中斷 sleep 與下一次 retry。
- 不在多層同時重試，避免 retry storm。
- 對 rate limit 尊重 server hint。

## Graceful Shutdown

1. 停止接受新工作。
2. 設定 shutdown/cancellation event。
3. 等待 in-flight 工作至 deadline。
4. 取消剩餘 task。
5. 關閉 queue、client、pool、socket 與檔案。
6. 收集 task 結果，避免「Task exception was never retrieved」。
7. 輸出未完成工作與可重試資訊。

## 測試與除錯

- 使用 async test plugin 或 `asyncio.run()` 測 public async API。
- 對 sleep/clock 使用可控 abstraction，避免真實等待。
- 測 timeout、cancellation、consumer failure、producer failure 與 shutdown。
- 在測試結束檢查未完成 task。
- debug 模式可協助找 slow callback 與未 await coroutine。
- 壓力測試 queue depth、連線池與 file descriptor 上限。

## 交付標準

- 所有 child task 都有 owner，沒有無人等待的 fire-and-forget task。
- cancellation 會向上傳播，cleanup 具 deadline。
- 連線、操作與整體工作均有 timeout/deadline。
- task、queue、buffer、pool 與 retry 均有上限。
- producer/consumer 有正確的停止訊號與 `task_done()` 配對。
- blocking/CPU 工作不阻塞 event loop。
- shutdown 可重現且不留下 task、thread、socket 或資源。
- 已測 partial failure、timeout、cancel 與 slow consumer。

## 延伸閱讀

- [完整範例](references/examples.md)
- [速查表](references/cheatsheet.md)
- [常見陷阱](references/pitfalls.md)
- [asyncio documentation](https://docs.python.org/3/library/asyncio.html)

## 版本相容性

| Python | 建議 |
|---|---|
| 3.14 | 穩定維護基準；依實際 workload 評估 free-threaded |
| 3.11–3.13 | 完整使用 TaskGroup、ExceptionGroup、asyncio.timeout |
| 3.10 | 需使用相容替代方案；不可直接使用 TaskGroup |
| 3.15 preview | 僅提前相容測試，不作生產預設 |
