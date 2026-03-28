---
name: py-perf
description: >
  Python performance optimization, profiling, benchmarking, and memory tuning.
  Trigger when user mentions profiling, cProfile, line_profiler, memory_profiler,
  Pyinstrument, timeit, optimization, bottleneck, slow code, memory leak.
  Also trigger when user asks about Cython, mypyc, Numba, JIT compilation,
  or free-threaded Python performance.
---

# Python 效能優化

## Quick Start（30 秒上手）

```python
from cProfile import Profile
from pstats import SortKey, Stats

def slow_func() -> list[int]:
    """找出 100 萬以內的質數"""
    return [n for n in range(2, 1_000_000)
            if all(n % d != 0 for d in range(2, int(n**0.5) + 1))]

with Profile() as pr:
    result = slow_func()
    Stats(pr).strip_dirs().sort_stats(SortKey.CUMULATIVE).print_stats(10)
```

一行指令 profiling：
```bash
python -m cProfile -s cumulative my_script.py
```

## 核心概念

### 1. 先量測，再優化

效能優化的黃金法則：**不要猜，要量測**。

```python
import timeit

# 基準測試：比較兩種實作
list_time = timeit.timeit("sum(range(10_000))", number=1000)
gen_time = timeit.timeit(
    "sum(x for x in range(10_000))", number=1000
)
print(f"list: {list_time:.4f}s  generator: {gen_time:.4f}s")
```

### 2. CPU Profiling — 確定性 vs 統計性

| 類型 | 工具 | 原理 | 優缺點 |
|------|------|------|--------|
| 確定性 | cProfile | 攔截所有函式呼叫 | 精確但有 overhead |
| 統計性 | Pyinstrument | 定時取樣 call stack | 低 overhead、樹狀報告 |
| 行級 | line_profiler | 逐行計時 | 超精細、高 overhead |

```python
# Pyinstrument — 統計性 profiler（推薦日常使用）
from pyinstrument import Profiler

with Profiler() as p:
    slow_func()

p.print()               # 終端樹狀報告
p.open_in_browser()     # 互動式 HTML 報告
```

### 3. 記憶體 Profiling

```python
# 方法 1：tracemalloc（標準函式庫）
import tracemalloc

tracemalloc.start()
data = [dict(x=i, y=i**2) for i in range(100_000)]
snapshot = tracemalloc.take_snapshot()

for stat in snapshot.statistics("lineno")[:5]:
    print(stat)
```

### 4. 資料結構選擇

| 操作 | list | deque | set | dict |
|------|------|-------|-----|------|
| append | O(1)* | O(1) | — | — |
| prepend | O(n) | O(1) | — | — |
| 查找 | O(n) | O(n) | O(1) | O(1) |
| 刪除 | O(n) | O(n) | O(1) | O(1) |

### 5. 常見加速手段

```python
# ❌ 慢：在迴圈中重複查找屬性
for item in items:
    result.append(item.lower())

# ✅ 快：本地變數綁定
_append = result.append
_lower = str.lower
for item in items:
    _append(_lower(item))
```

## 實戰 Patterns

### Pattern 1: Benchmark Decorator

**場景**：開發時快速比較函式效能。

```python
import functools
import time
from typing import Callable, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

def benchmark(func: Callable[P, R]) -> Callable[P, R]:
    """裝飾器：列印函式執行時間"""
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"{func.__name__}: {elapsed:.4f}s")
        return result
    return wrapper

@benchmark
def process_data(n: int) -> list[int]:
    return sorted(range(n, 0, -1))
```

### Pattern 2: `__slots__` 節省記憶體

**場景**：大量小物件（>10,000 個）。

```python
# 一般 class：每個實例有 __dict__（~64 bytes overhead）
class PointDict:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

# __slots__ class：無 __dict__（節省 ~40-50%）
class PointSlots:
    __slots__ = ("x", "y")
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

# 或用 dataclass + slots（Python 3.10+）
from dataclasses import dataclass

@dataclass(slots=True)
class PointData:
    x: float
    y: float
```

### Pattern 3: 字串拼接優化

**場景**：大量字串組合。

```python
# ❌ 慢：O(n²)
result = ""
for line in lines:
    result += line + "\n"

# ✅ 快：O(n)
result = "\n".join(lines) + "\n"

# ✅ 更快（寫入檔案時）
with open("output.txt", "w") as f:
    f.writelines(f"{line}\n" for line in lines)
```

### Pattern 4: LRU Cache 加速遞迴

**場景**：重複計算的純函式。

```python
from functools import lru_cache

@lru_cache(maxsize=256)
def fib(n: int) -> int:
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)

# 查看快取統計
print(fib.cache_info())
# CacheInfo(hits=98, misses=101, maxsize=256, currsize=101)
```

### Pattern 5: Generator 節省記憶體

**場景**：處理大資料集，不需一次載入全部。

```python
from collections.abc import Iterator
from pathlib import Path

def read_large_file(path: Path, chunk: int = 8192) -> Iterator[str]:
    """逐行讀取大檔案，不載入整個檔案到記憶體"""
    with open(path, encoding="utf-8") as f:
        while True:
            lines = f.readlines(chunk)
            if not lines:
                break
            yield from lines

# 用法：記憶體用量恆定
total = sum(1 for line in read_large_file(Path("huge.log"))
            if "ERROR" in line)
```

### Pattern 6: 並行加速 CPU-bound

**場景**：多核心平行計算。

```python
from concurrent.futures import ProcessPoolExecutor
from math import isqrt

def is_prime(n: int) -> bool:
    if n < 2:
        return False
    for d in range(2, isqrt(n) + 1):
        if n % d == 0:
            return False
    return True

def count_primes(numbers: list[int]) -> int:
    """利用多核平行判斷質數"""
    with ProcessPoolExecutor() as pool:
        results = pool.map(is_prime, numbers, chunksize=1000)
    return sum(results)
```

## 工具鏈推薦

| 工具 | 用途 | 安裝 | 備註 |
|------|------|------|------|
| cProfile | CPU 確定性 profiling | 標準函式庫 | 首選 |
| Pyinstrument | 統計性 profiling | `pip install pyinstrument` | 樹狀報告 |
| line_profiler | 行級 CPU profiling | `pip install line_profiler` | `@profile` 裝飾器 |
| memory_profiler | 行級記憶體 profiling | `pip install memory_profiler` | 需搭配 psutil |
| tracemalloc | 記憶體追蹤 | 標準函式庫 | 快照比較 |
| py-spy | 低 overhead 取樣 | `pip install py-spy` | 可 attach 執行中程序 |
| scalene | CPU+記憶體+GPU | `pip install scalene` | 全方位 |
| memray | 記憶體視覺化 | `pip install memray` | Bloomberg 出品 |

## 延伸閱讀

讀取 `references/` 目錄下的對應檔案：
- `references/examples.md` — 完整可運行範例
- `references/cheatsheet.md` — 速查表
- `references/pitfalls.md` — 常見錯誤與解法

## 版本相容性

| Python 版本 | 支援狀態 | 備註 |
|-------------|----------|------|
| 3.13+ | ✅ 完整支援 | free-threaded 模式下 profiling 可能不同 |
| 3.12 | ✅ | 支援 Linux `perf` profiler |
| 3.11 | ✅ | CPython 10-60% 加速 |
| 3.10 | ✅ | `dataclass(slots=True)` |
