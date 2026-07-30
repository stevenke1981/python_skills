---
name: py-data
description: >
  Build and review reliable Python data workflows with pandas 3, Polars, NumPy, Arrow, DuckDB, CSV, Parquet, and ETL patterns. Use for DataFrame transformations, schema design, null handling, joins, aggregations, time series, lazy or streaming execution, large-file processing, migration from pandas 2, and data quality validation.
compatibility: Agent Skills-compatible. Library APIs are version-sensitive; inspect the project's lockfile before choosing pandas, Polars, Arrow, or DuckDB syntax.
metadata:
  author: stevenke1981
  version: "2.0.0"
  last-reviewed: "2026-07-30"
---

# Python 資料處理與分析

## 目標與邊界

用此 skill 建立可重現、可驗證、具明確 schema 的資料處理流程。重點不是把程式縮成最短 method chain，而是讓輸入、轉換、品質檢查與輸出契約可追蹤。

若任務主要是模型推論或 RAG，改以 `py-ai` 為主；若主要問題是效能瓶頸，先完成正確性後再搭配 `py-perf`。

## 執行流程

1. **定義資料契約**：列出欄位、型別、null 規則、主鍵、時區、單位與允許值。
2. **盤點資料規模與來源**：檔案格式、壓縮、分割方式、資料庫、記憶體限制與更新頻率。
3. **選擇引擎**：依既有生態、查詢型態、資料量與部署環境選 pandas、Polars、DuckDB、Arrow 或 NumPy。
4. **先做小樣本驗證**：用代表性資料確認 schema、join cardinality、排序與時間語意。
5. **建立 lazy/streaming 管線**：能延遲執行就避免中途 materialize；只選取需要欄位並儘早過濾。
6. **加入資料品質閘門**：驗證列數、主鍵、null、重複、範圍、類別值與 reconciliation。
7. **輸出可重現結果**：固定 schema、排序需求、分割策略、壓縮與 metadata。

## 引擎選擇指南

| 情境 | 優先考慮 | 原因 |
|---|---|---|
| 互動分析、既有生態、廣泛第三方整合 | pandas | API 與生態成熟 |
| 表格式 ETL、平行查詢、lazy pipeline | Polars | expression API 與查詢最佳化 |
| 直接查詢 CSV/Parquet、多表 SQL | DuckDB | 嵌入式分析 SQL 與 predicate pushdown |
| 跨語言交換、columnar memory | Arrow | 明確 schema 與低複製交換 |
| 純數值陣列、線性代數 | NumPy | 通用數值核心 |

不要只用固定檔案大小門檻選工具。先量測資料寬度、字串比例、group/join 型態、記憶體峰值與部署限制。

## Schema-first Polars 管線

```python
from pathlib import Path

import polars as pl


REQUIRED_COLUMNS = {"user_id", "amount", "status"}


def build_report(source: Path) -> pl.DataFrame:
    lazy = pl.scan_parquet(source)
    available = set(lazy.collect_schema().names())
    missing = REQUIRED_COLUMNS - available
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")

    result = (
        lazy.select("user_id", "amount", "status")
        .filter(pl.col("status") == "completed")
        .with_columns(
            pl.col("amount").cast(pl.Float64, strict=True),
            pl.col("user_id").cast(pl.String, strict=True),
        )
        .group_by("user_id")
        .agg(
            pl.col("amount").sum().alias("total_amount"),
            pl.len().alias("order_count"),
        )
        .sort("total_amount", descending=True)
        .collect(engine="streaming")
    )

    if result["user_id"].null_count() != 0:
        raise ValueError("user_id must not contain null values")
    return result
```

現行 Polars 使用 `collect(engine="streaming")` 選擇 streaming engine；不要沿用已過時的 `collect(streaming=True)` 範例。若查詢不支援 streaming，必須觀察 fallback 與實際記憶體使用。

## pandas 3 遷移規則

pandas 3 的重要行為變化需要明確測試：

- Copy-on-Write 已成為預設且唯一模式。
- chained assignment 不再是可靠更新方式；使用單一步驟 `.loc[...] = ...`。
- 字串欄位預設推斷為專用 `str` dtype，而不是一律 `object`。
- datetime/timedelta 的推斷解析度可能不再固定為 nanoseconds。
- 從 pandas 2 升級時，先升到最新 2.x 並清除 deprecation warnings，再進入 3.x。

```python
import pandas as pd


def normalize_users(df: pd.DataFrame) -> pd.DataFrame:
    required = {"email", "active"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")

    result = df.loc[:, ["email", "active"]].copy()
    result.loc[:, "email"] = result["email"].astype("str").str.strip().str.lower()
    result.loc[:, "active"] = result["active"].astype("boolean")
    return result
```

不要依賴 `dtype == object` 判斷文字欄位；使用 pandas type predicates 或明確 schema。

## Join 與聚合安全規則

- 在 join 前驗證 key 的 uniqueness、null 與 dtype。
- 明確知道期望 cardinality：one-to-one、one-to-many 或 many-to-many。
- join 後比較列數與關鍵總額，防止意外笛卡兒積。
- 金額使用適當 decimal/整數最小單位，不以 binary float 表示需要精確結算的值。
- group/rolling 前先定義排序、時區與 window 邊界。
- 對缺值是「未知」「不適用」還是「零」作明確區分。

pandas 可使用 `merge(..., validate="one_to_one")` 等驗證；其他引擎則在 join 前後自行建立不變量。

## 大型資料與輸出

- 只讀取必要欄位並儘早 filter。
- 優先 Parquet/Arrow 等具 schema 的 columnar 格式。
- 寫出大量資料時使用 sink/partition，而不是先全部 collect 到記憶體。
- partition key 避免過高 cardinality 與大量小檔案。
- 輸出前固定欄位順序、dtype、時區、排序需求與壓縮設定。
- 若結果需可重跑，記錄來源版本、參數、程式版本與產出時間。

## 資料品質檢查

至少依風險加入：

```python
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class QualityResult:
    rows: int
    duplicate_ids: int
    null_emails: int


def inspect_users(df: pd.DataFrame) -> QualityResult:
    return QualityResult(
        rows=len(df),
        duplicate_ids=int(df["user_id"].duplicated().sum()),
        null_emails=int(df["email"].isna().sum()),
    )
```

將檢查結果寫入 log、測試報告或資料品質系統；不要只 `print()` 後忽略失敗。

## 驗證方式

- 以小型 fixture 驗證每個轉換。
- 加入空資料、全 null、重複 key、極端值、時區切換與錯誤 schema。
- 對重要聚合執行來源與結果 reconciliation。
- 用 property-based tests 驗證不變量。
- 用實際大小資料量測 peak memory、spill、I/O 與執行計畫。

## 交付標準

- 輸入與輸出 schema、null、key、時區與單位已記錄。
- join cardinality 與列數變化可解釋。
- pandas 3 的 CoW、string dtype 與 datetime 行為已有遷移測試。
- Polars streaming 使用現行 `engine` API，且確認是否 fallback。
- 大型資料不會因不必要 materialization 造成不可控記憶體峰值。
- 產出具可重現參數與資料品質結果。

## 延伸閱讀

- [完整範例](references/examples.md)
- [速查表](references/cheatsheet.md)
- [常見陷阱](references/pitfalls.md)
- [pandas 3.0 release notes](https://pandas.pydata.org/docs/whatsnew/v3.0.0.html)
- [Polars LazyFrame API](https://docs.pola.rs/api/python/stable/reference/lazyframe/)

## 版本相容性

| 環境 | 建議 |
|---|---|
| Python 3.14 | 穩定維護基準；先確認各 native dependency wheel |
| Python 3.10–3.13 | 支援；依鎖定版本選 pandas、Polars 與 Arrow API |
| pandas 3.x | 使用 CoW 新語意、`str` dtype 與新 datetime 解析度 |
| pandas 2.x | 遷移期間清除 warnings，避免 chained assignment |
| Polars 現行穩定版 | 使用 `engine="streaming"`，以官方 API 為準 |
