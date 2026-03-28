# py-perf — 速查表

## cProfile 速查

### 命令列用法

```bash
# 執行並顯示分析結果
python -m cProfile script.py

# 排序方式：cumulative（預設推薦）
python -m cProfile -s cumtime script.py

# 儲存到檔案供 pstats 分析
python -m cProfile -o output.prof script.py
```

### 程式碼內用法

```python
import cProfile
import pstats
from pstats import SortKey

# 方法 1：直接分析字串
cProfile.run("main()")

# 方法 2：Profile 物件
profiler = cProfile.Profile()
profiler.enable()
# ... 要分析的程式碼 ...
profiler.disable()
profiler.print_stats(SortKey.CUMULATIVE)

# 方法 3：Context Manager（Python 3.12+ 推薦）
with cProfile.Profile() as pr:
    main()
pr.print_stats(SortKey.CUMULATIVE)
```

### pstats SortKey 排序鍵

| SortKey | 說明 | 常用場景 |
|---------|------|----------|
| `CUMULATIVE` | 累計時間（含子函式） | 找出最耗時的呼叫鏈 |
| `TIME` | 自身時間（不含子函式） | 找出真正的瓶頸函式 |
| `CALLS` | 呼叫次數 | 找出過度呼叫的函式 |
| `PCALLS` | 原始呼叫次數 | 排除遞迴影響 |
| `NAME` | 函式名 | 快速定位 |

### pstats 常用 API

```python
stats = pstats.Stats("output.prof")
stats.strip_dirs()                    # 移除路徑前綴
stats.sort_stats(SortKey.CUMULATIVE)  # 排序
stats.print_stats(20)                 # 前 20 筆
stats.print_callers("target_func")    # 誰呼叫了目標
stats.print_callees("target_func")    # 目標呼叫了誰
```

---

## timeit 速查

```python
import timeit

# 方法 1：字串式（推薦用於簡單表達式）
elapsed = timeit.timeit("sum(range(1000))", number=10_000)

# 方法 2：帶 setup
elapsed = timeit.timeit(
    stmt="target in data",
    setup="data = set(range(10000)); target = 9999",
    number=100_000,
)

# 方法 3：Timer 物件（可重複使用）
timer = timeit.Timer("sorted(data)", "import random; data = random.sample(range(10000), 10000)")
results = timer.repeat(repeat=5, number=100)
best = min(results)  # 取最小值（最少干擾）

# 命令列
# python -m timeit -n 1000 -r 5 "sum(range(10000))"
```

---

## Pyinstrument 速查

```python
from pyinstrument import Profiler

# 基本用法
profiler = Profiler(interval=0.001)
profiler.start()
# ... 程式碼 ...
profiler.stop()

# 輸出格式
print(profiler.output_text(unicode=True, color=True))  # 終端
profiler.output_html()                                   # HTML 字串
profiler.output(renderer="json")                         # JSON

# Context Manager 用法
with Profiler(interval=0.001) as profiler:
    main()
profiler.print()

# Django 中介軟體
# pip install pyinstrument
# MIDDLEWARE += ["pyinstrument.middleware.ProfilerMiddleware"]
# 訪問任何 URL 加上 ?profile 參數
```

```bash
# 命令列
pyinstrument script.py
pyinstrument -r html -o report.html script.py
```

---

## tracemalloc 速查

```python
import tracemalloc

# 開始追蹤（nframe=深度）
tracemalloc.start(nframe=10)

# 拍快照
snapshot = tracemalloc.take_snapshot()

# 按行號統計
for stat in snapshot.statistics("lineno")[:10]:
    print(stat)

# 按檔案統計
for stat in snapshot.statistics("filename")[:10]:
    print(stat)

# 比較兩個快照
diff = snapshot2.compare_to(snapshot1, "lineno")

# 取得當前 / 峰值記憶體
current, peak = tracemalloc.get_traced_memory()
print(f"Current: {current / 1024:.1f} KB, Peak: {peak / 1024:.1f} KB")

tracemalloc.stop()
```

---

## line_profiler 速查

```python
# pip install line_profiler

# 方法 1：裝飾器 + 命令列
# 在函式加上 @profile 裝飾器（不需要 import）
# kernprof -l -v script.py

# 方法 2：程式碼內
from line_profiler import LineProfiler

lp = LineProfiler()
lp.add_function(target_function)
lp_wrapper = lp(main)
lp_wrapper()
lp.print_stats()
```

---

## __slots__ 速查

```python
# 一般 class
class Point:
    __slots__ = ("x", "y")
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

# dataclass（Python 3.10+）
from dataclasses import dataclass

@dataclass(slots=True)
class Point:
    x: float
    y: float

# NamedTuple（天生不可變，無 __dict__）
from typing import NamedTuple

class Point(NamedTuple):
    x: float
    y: float
```

---

## 常用資料結構複雜度

| 操作 | list | deque | set | dict |
|------|------|-------|-----|------|
| 索引 `[i]` | O(1) | O(n) | — | O(1) |
| 搜尋 `in` | O(n) | O(n) | O(1) | O(1) |
| 附加尾端 | O(1)* | O(1) | O(1) | O(1) |
| 插入頭端 | O(n) | O(1) | — | — |
| 刪除指定值 | O(n) | O(n) | O(1) | O(1) |
| 排序 | O(n log n) | — | — | — |

> `*` = 平攤（amortized）

---

## py-spy 速查

```bash
# pip install py-spy

# 記錄到 SVG 火焰圖
py-spy record -o flame.svg -- python script.py

# 即時 top 畫面（類似 htop）
py-spy top -- python script.py

# 附加到已執行的 process
py-spy record -o flame.svg --pid 12345

# 顯示 GIL 使用情況
py-spy record --gil -- python script.py

# 指定取樣率（預設 100 Hz）
py-spy record --rate 200 -- python script.py
```

---

## 快速效能檢查清單

```
□ 先用 cProfile 找出熱點（80/20 法則）
□ 對熱點函式用 line_profiler 逐行分析
□ 記憶體問題用 tracemalloc 定位
□ 用 timeit 驗證優化效果（取 min 值）
□ 大量 `in` 查找 → 換 set/dict
□ 字串拼接 → ''.join()
□ 純計算密集 → ProcessPoolExecutor
□ I/O 密集 → asyncio / ThreadPoolExecutor
□ 確認 production 沒開 debug/profiling 工具
```
