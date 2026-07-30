# py-perf — 完整可運行範例

## 範例 1：cProfile + pstats 完整 Profiling 流程

```python
"""cProfile 完整分析流程：profiling → 儲存 → 讀取 → 報告"""
import cProfile
import pstats
from pathlib import Path
from pstats import SortKey


def build_matrix(size: int) -> list[list[int]]:
    """建立矩陣並計算元素值"""
    return [[i * j for j in range(size)] for i in range(size)]


def find_peaks(matrix: list[list[int]], threshold: int) -> list[tuple[int, int]]:
    """找出超過閾值的座標"""
    peaks: list[tuple[int, int]] = []
    for i, row in enumerate(matrix):
        for j, val in enumerate(row):
            if val > threshold:
                peaks.append((i, j))
    return peaks


def analyze(size: int = 500) -> int:
    """主分析函式"""
    matrix = build_matrix(size)
    threshold = (size * size) // 2
    peaks = find_peaks(matrix, threshold)
    return len(peaks)


def main() -> None:
    # 1. Profiling 並儲存結果
    output = Path("profile_data.prof")
    cProfile.run("analyze(500)", str(output))

    # 2. 讀取儲存的結果並分析
    stats = pstats.Stats(str(output))
    stats.strip_dirs()

    # 3. 按累計時間排序，顯示前 10 筆
    print("=== 按累計時間排序 ===")
    stats.sort_stats(SortKey.CUMULATIVE).print_stats(10)

    # 4. 按呼叫次數排序
    print("\n=== 按呼叫次數排序 ===")
    stats.sort_stats(SortKey.CALLS).print_stats(10)

    # 5. 顯示呼叫者關係
    print("\n=== 誰呼叫了 find_peaks？ ===")
    stats.print_callers("find_peaks")

    # 清理
    output.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
```

---

## 範例 2：Pyinstrument 樹狀分析 + HTML 報告

```python
"""Pyinstrument 統計性 profiling — 樹狀視覺化"""
# pip install pyinstrument
import json
from pathlib import Path

from pyinstrument import Profiler


def load_and_transform(data: list[dict[str, int]]) -> list[dict[str, int]]:
    """載入並轉換資料"""
    # 模擬資料轉換
    transformed: list[dict[str, int]] = []
    for item in data:
        new_item = {k: v * 2 for k, v in item.items()}
        transformed.append(new_item)
    return transformed


def aggregate(data: list[dict[str, int]]) -> dict[str, int]:
    """聚合統計"""
    totals: dict[str, int] = {}
    for item in data:
        for key, val in item.items():
            totals[key] = totals.get(key, 0) + val
    return totals


def pipeline(n: int = 50_000) -> dict[str, int]:
    """資料處理 Pipeline"""
    # 產生模擬資料
    raw = [{"a": i, "b": i * 2, "c": i * 3} for i in range(n)]
    transformed = load_and_transform(raw)
    result = aggregate(transformed)
    return result


def main() -> None:
    profiler = Profiler(interval=0.001)

    profiler.start()
    result = pipeline()
    profiler.stop()

    # 終端印出樹狀報告
    print(profiler.output_text(unicode=True, color=True))

    # 儲存 HTML 互動式報告
    html_path = Path("profile_report.html")
    html_path.write_text(profiler.output_html(), encoding="utf-8")
    print(f"HTML 報告已儲存: {html_path}")

    # JSON 格式（可程式化分析）
    json_data = json.loads(profiler.output(renderer="json"))
    print(f"根節點持續時間: {json_data['root_frame']['time']:.4f}s")


if __name__ == "__main__":
    main()
```

---

## 範例 3：tracemalloc 記憶體追蹤與快照比較

```python
"""tracemalloc 追蹤記憶體配置熱點 + 快照比較"""
import tracemalloc
from dataclasses import dataclass


@dataclass(slots=True)
class Record:
    name: str
    value: float


def create_dicts(n: int) -> list[dict[str, object]]:
    """用 dict 儲存資料"""
    return [{"name": f"item_{i}", "value": float(i)} for i in range(n)]


def create_dataclasses(n: int) -> list[Record]:
    """用 dataclass 儲存資料"""
    return [Record(name=f"item_{i}", value=float(i)) for i in range(n)]


def main() -> None:
    n = 100_000

    # 開始追蹤
    tracemalloc.start()

    # 快照 1：建立 dict 版本
    dicts = create_dicts(n)
    snapshot1 = tracemalloc.take_snapshot()

    # 釋放 dict，建立 dataclass 版本
    del dicts
    dataclasses = create_dataclasses(n)
    snapshot2 = tracemalloc.take_snapshot()

    # 顯示快照 1 的 Top 5 記憶體配置
    print("=== dict 版本 — Top 5 記憶體配置 ===")
    for stat in snapshot1.statistics("lineno")[:5]:
        print(f"  {stat}")

    # 比較兩個快照的差異
    print("\n=== 快照差異（snapshot2 vs snapshot1）===")
    diff = snapshot2.compare_to(snapshot1, "lineno")
    for stat in diff[:5]:
        print(f"  {stat}")

    # 目前記憶體用量
    current, peak = tracemalloc.get_traced_memory()
    print(f"\n目前記憶體: {current / 1024:.1f} KB")
    print(f"峰值記憶體: {peak / 1024:.1f} KB")

    tracemalloc.stop()
    _ = dataclasses  # 避免 unused 警告


if __name__ == "__main__":
    main()
```

---

## 範例 4：timeit 系統化基準測試

```python
"""timeit 系統化比較多種實作方案"""
import timeit
from typing import Any


def benchmark_implementations() -> None:
    """比較字串拼接的不同方法"""
    setup = "data = [str(i) for i in range(10_000)]"

    implementations: dict[str, str] = {
        "join": "''.join(data)",
        "f-string loop": "result = ''\nfor d in data:\n    result = f'{result}{d}'",
        "list + join": """
parts = []
for d in data:
    parts.append(d)
''.join(parts)
""",
        "io.StringIO": """
import io
buf = io.StringIO()
for d in data:
    buf.write(d)
buf.getvalue()
""",
    }

    print(f"{'方法':<20} {'時間 (ms)':>12} {'相對速度':>10}")
    print("-" * 45)

    results: dict[str, float] = {}
    for name, code in implementations.items():
        elapsed = timeit.timeit(code, setup=setup, number=100)
        results[name] = elapsed

    # 以最快的為基準
    fastest = min(results.values())
    for name, elapsed in sorted(results.items(), key=lambda x: x[1]):
        ms = elapsed * 1000 / 100  # 平均每次的毫秒
        ratio = elapsed / fastest
        marker = " ⚡" if ratio < 1.1 else ""
        print(f"{name:<20} {ms:>10.3f}ms {ratio:>8.1f}x{marker}")


def benchmark_lookups() -> None:
    """比較容器查找效能"""
    sizes = [100, 1_000, 10_000]
    containers: dict[str, str] = {
        "list": "target in data_list",
        "set": "target in data_set",
        "dict": "target in data_dict",
    }

    print("\n\n=== 容器查找效能（越小越好）===")
    for size in sizes:
        setup = (
            f"data_list = list(range({size}))\n"
            f"data_set = set(range({size}))\n"
            f"data_dict = dict.fromkeys(range({size}))\n"
            f"target = {size - 1}"
        )
        print(f"\n容器大小: {size:,}")
        for name, code in containers.items():
            elapsed = timeit.timeit(code, setup=setup, number=10_000)
            us = elapsed * 1_000_000 / 10_000
            print(f"  {name:<8}: {us:>8.2f} μs")


def main() -> None:
    print("=== 字串拼接效能比較 ===\n")
    benchmark_implementations()
    benchmark_lookups()


if __name__ == "__main__":
    main()
```

---

## 範例 5：ProcessPoolExecutor 多核加速 + 效能量測

```python
"""並行計算 vs 序列計算 — 效能比較"""
import time
from concurrent.futures import ProcessPoolExecutor
from math import isqrt


def is_prime(n: int) -> bool:
    """判斷質數"""
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    for d in range(5, isqrt(n) + 1, 6):
        if n % d == 0 or n % (d + 2) == 0:
            return False
    return True


def count_primes_serial(numbers: list[int]) -> int:
    """序列計算"""
    return sum(is_prime(n) for n in numbers)


def count_primes_parallel(numbers: list[int], workers: int = 4) -> int:
    """平行計算"""
    with ProcessPoolExecutor(max_workers=workers) as pool:
        results = pool.map(is_prime, numbers, chunksize=1_000)
    return sum(results)


def timed(label: str):
    """計時 context manager"""
    class Timer:
        def __init__(self, label: str) -> None:
            self.label = label
            self.elapsed = 0.0
        def __enter__(self):
            self._start = time.perf_counter()
            return self
        def __exit__(self, *_):
            self.elapsed = time.perf_counter() - self._start
            print(f"  {self.label}: {self.elapsed:.3f}s")
    return Timer(label)


def main() -> None:
    numbers = list(range(2, 200_001))
    print(f"在 {len(numbers):,} 個數中找質數\n")

    with timed("序列") as t_serial:
        count_s = count_primes_serial(numbers)

    with timed("平行 (4 workers)") as t_parallel:
        count_p = count_primes_parallel(numbers, workers=4)

    assert count_s == count_p, "結果不一致！"
    print(f"\n質數數量: {count_s:,}")

    speedup = t_serial.elapsed / t_parallel.elapsed if t_parallel.elapsed > 0 else 0
    print(f"加速比: {speedup:.2f}x")


if __name__ == "__main__":
    main()
```
