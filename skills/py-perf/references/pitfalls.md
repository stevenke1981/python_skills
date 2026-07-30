# py-perf — 常見陷阱與解法

## 陷阱 1：過早優化

**問題**：還沒 profiling 就直覺式優化，浪費時間在非瓶頸上。

```python
# ❌ 直覺式「優化」— 可能根本不是瓶頸
# 花 3 小時手寫 C extension 優化某個函式
# 結果它只佔總執行時間 0.1%
```

**解法**：永遠先 profiling，遵循 80/20 法則。

```python
# ✅ 先量測再行動
import cProfile
from pstats import SortKey

with cProfile.Profile() as pr:
    main()

pr.print_stats(SortKey.CUMULATIVE)
# 先看 cumtime 最大的函式，那才是真正的瓶頸
```

---

## 陷阱 2：在 Debug 模式下做效能測試

**問題**：開著 debug 工具（profiler / debugger / assert）測效能，結果嚴重失真。

```python
# ❌ cProfile 本身有 overhead —— 不要用它來測精確時間
with cProfile.Profile() as pr:
    elapsed = timeit.timeit(func, number=1000)
    # elapsed 會比真實慢 2-10 倍
```

**解法**：分開使用工具 —— profiling 找熱點，timeit 測精確時間。

```python
# ✅ 分別使用
# Step 1: cProfile 找出瓶頸函式
# Step 2: timeit 測量該函式的精確效能
elapsed = timeit.timeit(lambda: bottleneck_func(data), number=1000)

# 注意：timeit 已自動停用 GC，不需要額外處理
```

---

## 陷阱 3：GIL 誤解 — 多執行緒不等於多核加速

**問題**：CPU 密集任務用 `ThreadPoolExecutor`，期望線性加速，結果反而更慢。

```python
# ❌ CPU 密集任務用多執行緒 — GIL 導致沒有加速
from concurrent.futures import ThreadPoolExecutor

def cpu_bound(n: int) -> int:
    return sum(i * i for i in range(n))

# 在 CPython 中，這比單執行緒更慢（GIL 爭搶 + context switch）
with ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(cpu_bound, [10_000_000] * 4))
```

**解法**：CPU 密集用 `ProcessPoolExecutor`（或等 Python 3.13 free-threaded）。

```python
# ✅ CPU 密集 → ProcessPoolExecutor
from concurrent.futures import ProcessPoolExecutor

with ProcessPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(cpu_bound, [10_000_000] * 4))

# I/O 密集 → ThreadPoolExecutor 或 asyncio
# CPU 密集 → ProcessPoolExecutor
# CPU 密集 + Python 3.13t → 可試 ThreadPoolExecutor
```

---

## 陷阱 4：`lru_cache` 快取可變物件

**問題**：`lru_cache` 只看引數 hash，如果回傳可變物件，外部修改會污染快取。

```python
from functools import lru_cache

# ❌ 回傳 list（可變），呼叫者可能修改它
@lru_cache(maxsize=128)
def get_defaults() -> list[str]:
    return ["a", "b", "c"]

result = get_defaults()
result.append("HACKED")     # 污染了快取！
print(get_defaults())        # ['a', 'b', 'c', 'HACKED'] 😱
```

**解法**：回傳不可變物件，或在回傳前複製。

```python
# ✅ 方法 1：回傳 tuple（不可變）
@lru_cache(maxsize=128)
def get_defaults() -> tuple[str, ...]:
    return ("a", "b", "c")

# ✅ 方法 2：快取內部，回傳複製
@lru_cache(maxsize=128)
def _get_defaults_cached() -> tuple[str, ...]:
    return ("a", "b", "c")

def get_defaults() -> list[str]:
    return list(_get_defaults_cached())
```

---

## 陷阱 5：memory_profiler 導致生產性能問題

**問題**：忘記移除 `@profile` 裝飾器就部署到 production。

```python
# ❌ 留在 production 的 @profile 裝飾器
# 如果 memory_profiler 沒安裝會直接報錯
# 如果有安裝則 overhead 非常大
@profile  # <-- 忘記移除
def process_data(data: list[int]) -> int:
    return sum(x * x for x in data)
```

**解法**：使用 `line_profiler` / `memory_profiler` 時，用 `kernprof` 命令列注入，不要在程式碼中 `import`。

```python
# ✅ 方法 1：透過 kernprof 命令列注入（推薦）
# 程式碼不需要 import 任何 profiling 套件
# 執行: kernprof -l -v script.py

# ✅ 方法 2：用 conditional import
import os
if os.environ.get("PROFILING"):
    from memory_profiler import profile
else:
    from typing import TypeVar, Callable
    F = TypeVar("F", bound=Callable)
    def profile(func: F) -> F:  # type: ignore[misc]
        return func
```

---

## 陷阱 6：timeit 取「平均」而非「最小值」

**問題**：用 `timeit.timeit()` 的結果除以 `number` 當效能指標，受系統噪音影響大。

```python
# ❌ 只跑一次取平均
elapsed = timeit.timeit(stmt, number=1000)
avg = elapsed / 1000  # 包含了 GC、OS 排程等噪音
```

**解法**：用 `repeat()` 多次取 `min()`，最小值最接近真實效能。

```python
# ✅ 多次重複，取最小值
timer = timeit.Timer(stmt, setup)
results = timer.repeat(repeat=5, number=1000)
best = min(results) / 1000

# 說明：min 是最不受 GC/OS 干擾的結果
# Python 官方文檔也推薦這種方式
```

---

## 陷阱 7：字串格式化在緊迴圈中的隱藏成本

**問題**：在高頻迴圈中使用 logging/f-string 格式化，即使 log level 不輸出也會計算。

```python
import logging

logger = logging.getLogger(__name__)

# ❌ 即使 DEBUG 被停用，f-string 仍然會執行格式化
for item in huge_dataset:  # 100 萬次迴圈
    logger.debug(f"Processing {item!r} with value {compute_repr(item)}")
    # compute_repr() 每次都會被呼叫！
```

**解法**：用 `%` 風格延遲格式化，或先檢查 log level。

```python
# ✅ 方法 1：% 風格 — logging 內部只在需要時才格式化
logger.debug("Processing %r with value %s", item, compute_repr(item))
# 注意：compute_repr 仍然會被呼叫，但字串格式化被跳過

# ✅ 方法 2：先檢查 level（完全避免計算）
if logger.isEnabledFor(logging.DEBUG):
    logger.debug("Processing %r with value %s", item, compute_repr(item))
```

---

## 陷阱 8：Profiling 結果不可重現

**問題**：每次 profiling 結果差異大，無法判斷優化是否有效。

**原因**：
- 背景程序干擾（瀏覽器、IDE、防毒）
- CPU boost/throttle（筆電省電模式）
- GC 運行時機不一致
- 冷快取 vs 熱快取

**解法**：

```python
import gc
import time

# 1. 暖機 — 先跑幾次讓 CPU/快取穩定
for _ in range(3):
    func(data)

# 2. 停用 GC 減少噪音
gc.disable()
try:
    start = time.perf_counter()
    for _ in range(100):
        func(data)
    elapsed = time.perf_counter() - start
finally:
    gc.enable()

# 3. 確保環境一致
# - 關閉不必要的背景程式
# - 使用桌機或固定 CPU 頻率
# - 同一台機器比較結果
# - 跑多次取 min
```
