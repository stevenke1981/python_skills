---
name: py-perf
description: >
  Measure, diagnose, and improve Python performance with reproducible benchmarks, cProfile, Pyinstrument, py-spy, Scalene, Memray, tracemalloc, line profiling, allocation analysis, algorithmic changes, vectorization, caching, concurrency, and performance regression tests. Use for slow code, high memory, throughput or latency regressions, CPU or I/O bottlenecks, startup cost, and evaluating free-threaded Python or experimental JIT behavior.
compatibility: Agent Skills-compatible. Profilers and benchmark results depend on Python build, operating system, hardware, native extensions, and workload; record the complete environment.
metadata:
  author: stevenke1981
  version: "2.0.0"
  last-reviewed: "2026-07-30"
---

# Python 效能分析與最佳化

## 目標與邊界

用此 skill 找出可重現的瓶頸，採用最小且可驗證的改善，並防止效能回歸。

不要在沒有代表性 workload、correctness test 與 baseline 時進行猜測性微調。效能改善不能以單次執行、開發機體感或未說明環境的倍數宣稱。

## 執行流程

1. **定義效能目標**：延遲 percentile、吞吐、CPU、記憶體峰值、allocation、startup、I/O 或成本。
2. **建立正確性基準**：先確保輸出與行為可測；最佳化前後必須相同。
3. **建立代表性 workload**：資料大小、分布、並行、cache 狀態與冷／熱啟動符合實際使用。
4. **量測 baseline**：記錄 Python build、套件版本、OS、CPU、核心數、電源模式與命令。
5. **選擇 profiler**：先找出時間或記憶體熱點，再使用行級工具細查。
6. **一次修改一個瓶頸**：優先演算法、資料流與 I/O，再考慮低階微調。
7. **重新量測與比較**：重複樣本、觀察變異、確認沒有轉移瓶頸。
8. **建立 regression gate**：保存 benchmark、環境與可接受閾值。
9. **回報 trade-off**：可讀性、記憶體、精確度、延遲、相容性與維護成本。

## 工具選擇

| 問題 | 優先工具 | 用途 |
|---|---|---|
| 整體函式時間 | `cProfile`, Pyinstrument | 找出 cumulative/self time 熱點 |
| 不停止線上程序的取樣 | py-spy | attach 或產生 flame graph |
| CPU／記憶體／native 交界 | Scalene | 區分 Python/native/system 時間 |
| Python allocation 與 leak | tracemalloc, Memray | snapshot、allocation stack、peak memory |
| 單一函式逐行時間 | line_profiler | 已知熱點後細查 |
| 小型穩定 benchmark | `timeit`, pyperf | 重複量測與統計 |
| SQL／DataFrame | query plan、引擎 profiler | 不只看 Python call stack |
| Async／network | tracing、queue depth、pool stats | 找等待、背壓與 connection 問題 |

Profiler 會改變程式行為與時間分布。用取樣工具找大方向，再用 benchmark 驗證實際改善。

## Benchmark 基本規則

- 將 setup 與被測 operation 分離。
- 使用多次 process/run，而不是只跑一次。
- 記錄 warm-up、cold cache 與 steady-state 差異。
- 產生固定或有 seed 的資料，失敗時保存 seed。
- 量測真實輸入大小；microbenchmark 只回答局部問題。
- 避免同時跑大型下載、編譯、同步或省電模式。
- 比較相同 Python build、dependency 與環境設定。
- CI benchmark 使用寬鬆且有統計依據的 regression threshold，避免把噪音當失敗。

### 標準函式庫範例

```python
from statistics import median
from timeit import repeat


def normalize(values: list[str]) -> list[str]:
    return [value.strip().lower() for value in values]


def benchmark() -> float:
    values = [f" Item {index} " for index in range(10_000)]
    samples = repeat(
        stmt=lambda: normalize(values),
        repeat=7,
        number=100,
    )
    return median(samples)


if __name__ == "__main__":
    print(f"median seconds: {benchmark():.6f}")
```

這只能作本機比較。正式報告需保存所有樣本、環境與輸入描述。

## CPU Profiling

### cProfile

```bash
python -m cProfile -o profile.prof app.py
python -m pstats profile.prof
```

在 `pstats` 中查看 cumulative time、self time 與 call count。不要只最佳化呼叫次數最多的函式；先看總成本與業務重要性。

### Sampling Profiler

取樣 profiler 適合長時間程序、服務與低侵入調查：

```bash
py-spy record -o profile.svg -- python app.py
```

attach 線上 process 可能需要額外 OS 權限。先確認環境與授權，不在未知 production 主機任意操作。

## 記憶體與 Allocation

### tracemalloc snapshot

```python
import tracemalloc


def build_records(count: int) -> list[dict[str, int]]:
    return [{"id": index, "square": index * index} for index in range(count)]


tracemalloc.start()
before = tracemalloc.take_snapshot()
records = build_records(100_000)
after = tracemalloc.take_snapshot()

for stat in after.compare_to(before, "lineno")[:10]:
    print(stat)
```

注意：

- tracemalloc 主要追蹤 Python allocation，不代表 process RSS 的全部來源。
- native library、mmap、GPU 與 allocator fragmentation 需使用相應工具。
- leak 調查要比較多個時間點與穩定 workload，不只看一次高峰。
- 記憶體減少可能換來更多 CPU/I/O；一起量測。

## 最佳化優先順序

### 1. 演算法與資料結構

- 避免不必要的 O(n²) search/join。
- membership 使用 set/dict，而非重複掃描 list。
- 對已排序資料使用適合演算法。
- 大量資料採 streaming/chunking，不一次 materialize。
- 降低 serialization、copy 與跨 process 傳輸。

### 2. 減少工作量

- 儘早 filter，只選需要欄位。
- 合併重複 I/O，使用 batch。
- 重用 HTTP/DB client 與 connection pool。
- 避免重複 parse、compile、schema 建立與模型載入。
- cache 只用於可辨識 key、可控大小與可失效資料。

### 3. 使用最佳化實作

- NumPy/Polars/Arrow/native library 取代純 Python hot loop，前提是轉換成本合理。
- SQL 工作交給資料庫並檢查 query plan。
- 字串與二進位資料避免不必要 encode/decode/copy。
- 需要 native extension 時，先評估 wheel、ABI、除錯與維護成本。

### 4. 微最佳化

局部變數綁定、手動展開迴圈或難讀的 comprehension 通常不是第一步。只有 profiler 證明該位置主導成本，且 benchmark 顯示穩定收益時才採用。

## Cache

```python
from functools import lru_cache


@lru_cache(maxsize=512)
def parse_schema(schema_text: str) -> ParsedSchema:
    return compile_schema(schema_text)
```

使用 cache 前回答：

- key 是否完整且 hash 穩定？
- 值是否可能過期？
- 最大大小與 eviction 是什麼？
- 是否含敏感或 tenant-specific 資料？
- 多 process／多機器是否需要共享？
- cache miss storm 如何處理？

不要 cache 有副作用、依時間/權限隱含變動或記憶體無上限的函式。

## 並行與平行

| 工作型態 | 優先方向 |
|---|---|
| 大量 I/O 等待 | asyncio／有界 thread pool |
| CPU-bound 純 Python | process pool、演算法或 native implementation |
| 釋放 GIL 的 native code | thread pool 或 library 自身 parallelism |
| 大型共享資料 | 避免昂貴 process serialization，評估 shared memory/native engine |
| 多租戶服務 | 先處理 queue、backpressure 與資源隔離 |

### Free-threaded Python

Python 3.14 提供可選 free-threaded build，但仍需：

- 驗證 native extensions 與 thread safety。
- 比較一般 build、free-threaded、process pool 與 native library。
- 量測單執行緒 overhead 與多核心 scaling。
- 確認是否有 extension 在 runtime 重新啟用 GIL。
- 對共享 mutable state 做壓力與 race 測試。

### Experimental JIT

CPython JIT 仍應視為實驗選項：

- 不作生產預設。
- benchmark 記錄 build 與啟用方式。
- 觀察 warm-up、code shape 與 profiler 差異。
- 沒有實測時不宣稱加速。

## Async 與服務效能

- 區分 CPU time、wall time 與等待時間。
- 觀察 event-loop lag、queue depth、pool wait、timeout 與 retry。
- 無界 task/queue 可能短期提高吞吐、長期導致延遲與 OOM。
- client disconnect 時取消上游工作，避免浪費資源。
- 對 p50、p95、p99 分別量測，不以平均值掩蓋 tail latency。
- load test 要有授權、固定流量模型與安全上限。

## 效能回歸測試

- 保存 benchmark 名稱、版本、輸入與所有樣本。
- 將 correctness test 與 benchmark 分開。
- 在穩定 runner 上執行主要 benchmark，普通 PR CI 只跑小型 smoke benchmark。
- threshold 同時考慮絕對值與百分比，並允許合理噪音。
- regression 發生時先重新量測，再 bisect commit/dependency。
- 報告改善與退化的 trade-off，不只挑選最佳數字。

## 交付標準

- 效能目標、代表性 workload 與 baseline 已記錄。
- correctness 在最佳化前後一致。
- profiler 證據指向實際瓶頸，沒有猜測性重構。
- benchmark 有多次樣本、環境、warm-up 與變異資訊。
- 改善優先從演算法、I/O 與資料流著手。
- 記憶體、CPU、延遲與吞吐 trade-off 已說明。
- free-threaded/JIT 皆有 opt-in、相容性測試與 fallback。
- 已建立可重現的 regression benchmark 與合理閾值。

## 延伸閱讀

- [完整範例](references/examples.md)
- [速查表](references/cheatsheet.md)
- [常見陷阱](references/pitfalls.md)
- [Python profiling documentation](https://docs.python.org/3/library/profile.html)
- [Free-threaded Python HOWTO](https://docs.python.org/3/howto/free-threading-python.html)

## 版本相容性

| 環境 | 建議 |
|---|---|
| Python 3.14 | 穩定維護基準；free-threaded 可選，JIT 仍實驗性 |
| Python 3.10–3.13 | 支援；記錄不同 interpreter/build 的結果 |
| Native/GPU workloads | 使用對應 profiler，不只看 Python allocation |
| Preview Python | 只作獨立比較，不取代穩定 benchmark |
