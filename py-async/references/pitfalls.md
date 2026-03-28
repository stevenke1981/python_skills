# py-async 常見陷阱與解法

## 陷阱 1：忘記 await

**錯誤**：呼叫 coroutine 但沒有 `await`，回傳的是 coroutine object 而非結果。

```python
# ❌ 錯誤：沒有 await
async def main() -> None:
    result = fetch_data()  # 回傳 coroutine object，不會執行！
    print(result)  # <coroutine object fetch_data at 0x...>

# ✅ 正確：使用 await
async def main() -> None:
    result = await fetch_data()
    print(result)  # 實際結果
```

**診斷**：啟用 `asyncio.run(main(), debug=True)` 會在 coroutine 未被 await 時發出 RuntimeWarning。

---

## 陷阱 2：在 async 函式中使用阻塞呼叫

**錯誤**：在 coroutine 中呼叫 `time.sleep()`、同步 HTTP、或同步檔案 IO，會阻塞整個 event loop。

```python
import time

# ❌ 錯誤：阻塞 event loop
async def bad_handler() -> str:
    time.sleep(5)  # 整個 event loop 被凍結 5 秒！
    return "done"

# ✅ 正確：使用 asyncio.sleep 或 to_thread
import asyncio

async def good_handler() -> str:
    await asyncio.sleep(5)  # 讓出控制權
    return "done"

async def good_handler_v2() -> str:
    result = await asyncio.to_thread(blocking_sync_function)
    return result
```

---

## 陷阱 3：gather 不會自動取消其他任務

```python
import asyncio

# ❌ 問題：task2 失敗時 task1 和 task3 繼續跑（資源浪費）
async def main() -> None:
    try:
        results = await asyncio.gather(task1(), task2(), task3())
    except Exception:
        pass  # task1, task3 可能仍在背景執行

# ✅ 解法：使用 TaskGroup（3.11+）自動取消
async def main() -> None:
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(task1())
            tg.create_task(task2())  # 失敗時自動取消 task1, task3
            tg.create_task(task3())
    except* Exception as eg:
        for e in eg.exceptions:
            print(f"錯誤: {e}")
```

---

## 陷阱 4：建立 Task 但不保留引用

**錯誤**：`create_task()` 回傳的 Task 如果沒有被引用，可能被 GC 回收。

```python
# ❌ 錯誤：Task 可能被垃圾回收
async def main() -> None:
    asyncio.create_task(background_work())  # 無引用！
    # Task 可能在 background_work 完成前被 GC

# ✅ 正確：保持 Task 引用
async def main() -> None:
    background_tasks: set[asyncio.Task[None]] = set()
    task = asyncio.create_task(background_work())
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
```

---

## 陷阱 5：Semaphore 建立在 async 函式外部

**錯誤**：在模組級別建立 `asyncio.Semaphore`（Python 3.10+ 會警告）。

```python
# ❌ 錯誤：模組級別建立（可能綁定到錯誤的 event loop）
sem = asyncio.Semaphore(10)

async def handler() -> None:
    async with sem:  # DeprecationWarning 或 RuntimeError
        pass

# ✅ 正確：在 async 函式內部或 class 的 async init 中建立
async def main() -> None:
    sem = asyncio.Semaphore(10)
    async with asyncio.TaskGroup() as tg:
        for i in range(20):
            tg.create_task(handler_with_sem(sem, i))

async def handler_with_sem(sem: asyncio.Semaphore, task_id: int) -> None:
    async with sem:
        await asyncio.sleep(0.1)
```

---

## 陷阱 6：except* 與普通 except 混用

```python
# ❌ 錯誤：不能在同一個 try 中混用 except 和 except*
try:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(work())
except ValueError:        # 不能同時用！
    pass
except* TypeError:        # SyntaxError
    pass

# ✅ 正確：只用 except* 處理 ExceptionGroup
try:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(work())
except* ValueError as eg:
    for e in eg.exceptions:
        print(e)
except* TypeError as eg:
    for e in eg.exceptions:
        print(e)
```

---

## 陷阱 7：asyncio.run() 巢狀呼叫

```python
# ❌ 錯誤：在已有 event loop 的環境中再呼叫 asyncio.run()
async def inner() -> str:
    return "hello"

async def outer() -> None:
    result = asyncio.run(inner())  # RuntimeError: event loop already running!

# ✅ 正確：直接 await
async def outer() -> None:
    result = await inner()

# ✅ 或使用 create_task
async def outer() -> None:
    task = asyncio.create_task(inner())
    result = await task
```

---

## 陷阱 8：忽略 CancelledError 導致取消失效

```python
# ❌ 錯誤：捕獲所有 Exception 會吞掉 CancelledError（3.9+ 改為 BaseException）
async def bad_worker() -> None:
    while True:
        try:
            await asyncio.sleep(1)
        except Exception:  # 3.8 以前會捕獲 CancelledError
            pass  # 取消永遠不生效！

# ✅ 正確：明確處理 CancelledError 或不要捕獲 BaseException
async def good_worker() -> None:
    while True:
        try:
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            print("正在清理...")
            raise  # 必須重新拋出！
        except Exception:
            print("處理其他錯誤")
```

**注意**：Python 3.9+ 中 `CancelledError` 繼承 `BaseException` 而非 `Exception`，降低了意外捕獲的風險，但仍需注意 `except BaseException` 的使用。
