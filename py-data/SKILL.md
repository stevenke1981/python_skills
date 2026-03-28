---
name: py-data
description: >
  Data processing and analysis with pandas, Polars, NumPy, and data pipeline patterns.
  Trigger when user mentions pandas, polars, numpy, dataframe, data pipeline,
  ETL, data wrangling, data cleaning, data transformation, CSV processing,
  parquet, arrow, columnar data, lazy evaluation, groupby, aggregation.
  Also trigger when user asks about data analysis, time series processing,
  or choosing between pandas and polars.
---

# 資料處理與分析

## Quick Start（30 秒上手）

```python
import polars as pl

# 讀取 CSV → 篩選 → 聚合 → 輸出
result = (
    pl.scan_csv("sales.csv")           # 延遲讀取
    .filter(pl.col("amount") > 100)    # 篩選
    .group_by("category")              # 分組
    .agg(
        pl.col("amount").sum().alias("total"),
        pl.len().alias("count"),
    )
    .sort("total", descending=True)
    .collect()                         # 觸發執行
)
print(result)
```

## 核心概念

### 1. pandas 2.x — Arrow 後端與 Copy-on-Write

pandas 2.x 引入 PyArrow 後端，大幅改善記憶體效率與型別支援：

```python
import pandas as pd

# 使用 Arrow 後端（更省記憶體、支援更多型別）
df = pd.read_csv("data.csv", dtype_backend="pyarrow")

# Copy-on-Write（pandas 3.0 預設啟用）
pd.options.mode.copy_on_write = True
df2 = df[["col_a", "col_b"]]  # 不立即複製，修改時才複製
df2["col_a"] = 0               # 此時才觸發複製
```

### 2. Polars — 延遲執行與表達式 API

Polars 的延遲模式允許查詢最佳化：

```python
import polars as pl

# Lazy API：建立查詢計畫，最後才執行
lazy_df = (
    pl.scan_parquet("events/*.parquet")
    .with_columns(
        pl.col("timestamp").dt.year().alias("year"),
        (pl.col("price") * pl.col("quantity")).alias("revenue"),
    )
    .filter(pl.col("year") >= 2024)
    .group_by("product_id")
    .agg(pl.col("revenue").sum())
)

# 查看查詢計畫
print(lazy_df.explain())

# 執行查詢
result = lazy_df.collect()
```

### 3. NumPy — 向量化運算基礎

NumPy 提供高效的陣列運算，是整個資料生態系的基礎：

```python
import numpy as np

# 向量化 vs 迴圈：快 10-100 倍
data: np.ndarray = np.random.randn(1_000_000)
# ✅ 好：向量化
result = np.where(data > 0, data * 2, data * 0.5)
# ❌ 差：Python 迴圈
# result = [x * 2 if x > 0 else x * 0.5 for x in data]
```

### 4. Apache Arrow — 跨框架資料交換

Arrow 是零複製資料交換的標準格式：

```python
import pyarrow as pa
import pyarrow.parquet as pq
import polars as pl
import pandas as pd

# Arrow Table 作為中間格式
arrow_table: pa.Table = pq.read_table("data.parquet")

# 零複製轉換
polars_df: pl.DataFrame = pl.from_arrow(arrow_table)
pandas_df: pd.DataFrame = arrow_table.to_pandas()
```

### 5. 資料管線模式（ETL Pipeline）

結構化的資料處理管線：

```python
from pathlib import Path
import polars as pl

def extract(source: Path) -> pl.LazyFrame:
    """擷取：讀取原始資料"""
    return pl.scan_parquet(source)

def transform(lf: pl.LazyFrame) -> pl.LazyFrame:
    """轉換：清洗與加工"""
    return (
        lf.drop_nulls(subset=["user_id"])
        .with_columns(
            pl.col("email").str.to_lowercase().alias("email_clean"),
            pl.col("created_at").cast(pl.Date).alias("date"),
        )
        .filter(pl.col("status") == "active")
    )

def load(lf: pl.LazyFrame, dest: Path) -> None:
    """載入：寫出結果"""
    lf.collect().write_parquet(dest)

# 執行管線
raw = extract(Path("raw/users.parquet"))
cleaned = transform(raw)
load(cleaned, Path("processed/active_users.parquet"))
```

## 實戰 Patterns

### Pattern 1: pandas 與 Polars 的選擇策略

**場景**：決定使用哪個框架

| 情境 | 建議 | 原因 |
|------|------|------|
| 快速原型、Jupyter 探索 | pandas | 生態系廣、文件豐富 |
| 大型資料（> 1GB） | Polars | 延遲執行、記憶體效率高 |
| 多執行緒環境 | Polars | 無 GIL 限制、原生平行化 |
| 既有 pandas 程式碼 | pandas（Arrow 後端） | 低遷移成本 |
| ETL 管線 | Polars lazy | 查詢最佳化、streaming 支援 |

### Pattern 2: 分塊處理大型檔案

**場景**：記憶體無法一次載入整個資料集

```python
import polars as pl

# Polars streaming（自動分塊）
result = (
    pl.scan_csv("huge_file.csv")
    .filter(pl.col("status") == "completed")
    .group_by("region")
    .agg(pl.col("amount").sum())
    .collect(streaming=True)  # 啟用 streaming 引擎
)
```

### Pattern 3: 時間序列重採樣

**場景**：將高頻交易資料降頻為日/週/月匯總

```python
import polars as pl

trades = pl.scan_parquet("trades.parquet")
daily_summary = (
    trades
    .sort("timestamp")
    .group_by_dynamic("timestamp", every="1d")
    .agg(
        pl.col("price").first().alias("open"),
        pl.col("price").max().alias("high"),
        pl.col("price").min().alias("low"),
        pl.col("price").last().alias("close"),
        pl.col("volume").sum().alias("volume"),
    )
    .collect()
)
```

### Pattern 4: 多來源資料合併

**場景**：合併不同格式的資料來源

```python
import polars as pl

# 讀取不同格式
users = pl.read_csv("users.csv")
orders = pl.read_parquet("orders.parquet")
products = pl.read_json("products.json")

# 多表 join
result = (
    orders
    .join(users, on="user_id", how="left")
    .join(products, on="product_id", how="left")
    .with_columns(
        (pl.col("price") * pl.col("quantity")).alias("total"),
    )
    .group_by("user_name")
    .agg(
        pl.col("total").sum().alias("total_spent"),
        pl.col("order_id").n_unique().alias("order_count"),
    )
)
```

## 工具鏈推薦

| 工具 | 用途 | 安裝 | 備註 |
|------|------|------|------|
| polars | 高效能 DataFrame | `pip install polars` | Rust 核心，原生平行化 |
| pandas | 經典 DataFrame | `pip install pandas[pyarrow]` | 2.x+ 建議用 Arrow 後端 |
| numpy | 數值陣列運算 | `pip install numpy` | 向量化運算基礎 |
| pyarrow | Arrow 格式 / Parquet IO | `pip install pyarrow` | 跨框架資料交換 |
| duckdb | 記憶體內 SQL 分析 | `pip install duckdb` | 可直接查詢 Parquet/CSV |
| connectorx | 高速資料庫讀取 | `pip install connectorx` | 搭配 Polars 最佳化 |
| great_expectations | 資料品質驗證 | `pip install great_expectations` | 資料管線必備 |
| narwhals | 跨框架相容 API | `pip install narwhals` | 寫一次支援 pandas + Polars |

## 延伸閱讀

讀取 `references/` 目錄下的對應檔案：
- `references/examples.md` — 完整可運行範例
- `references/cheatsheet.md` — 速查表
- `references/pitfalls.md` — 常見錯誤與解法

## 版本相容性

| Python 版本 | 支援狀態 | 備註 |
|-------------|----------|------|
| 3.13+ | ✅ 完整支援 | pandas 2.2+ / Polars 1.x |
| 3.12 | ✅ 完整支援 | 推薦版本 |
| 3.11 | ✅ | pandas 2.x / Polars 0.20+ |
| 3.10 | ✅ | pandas 2.x 最低需求 |
| 3.9 | ⚠️ 部分 | Polars 1.x 已不支援 |
