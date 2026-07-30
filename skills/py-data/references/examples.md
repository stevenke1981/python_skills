# py-data 完整範例集

## 範例 1：Polars Lazy Pipeline — 電商銷售分析

```python
"""從 Parquet 檔讀取銷售資料，做清洗、聚合、排序後輸出"""
import polars as pl
from pathlib import Path

def analyze_sales(source: Path) -> pl.DataFrame:
    """分析銷售資料的完整 lazy pipeline"""
    return (
        pl.scan_parquet(source)
        # 清洗：去除無效記錄
        .filter(
            pl.col("order_id").is_not_null()
            & (pl.col("quantity") > 0)
            & (pl.col("unit_price") > 0)
        )
        # 計算欄位
        .with_columns(
            (pl.col("unit_price") * pl.col("quantity")).alias("revenue"),
            pl.col("order_date").cast(pl.Date),
            pl.col("category").str.to_lowercase().str.strip_chars(),
        )
        # 按類別聚合
        .group_by("category")
        .agg(
            pl.col("revenue").sum().alias("total_revenue"),
            pl.col("revenue").mean().round(2).alias("avg_order_value"),
            pl.col("order_id").n_unique().alias("unique_orders"),
            pl.col("quantity").sum().alias("total_units"),
        )
        .sort("total_revenue", descending=True)
        .collect()
    )

# 使用範例（需有對應的 Parquet 檔案）
# result = analyze_sales(Path("data/sales.parquet"))
# print(result)
```

## 範例 2：pandas Arrow 後端 — 資料清洗管線

```python
"""使用 pandas 2.x Arrow 後端做資料清洗"""
import pandas as pd
import numpy as np

def clean_user_data(csv_path: str) -> pd.DataFrame:
    """清洗使用者資料：型別轉換、缺值處理、格式標準化"""
    # 使用 Arrow 後端讀取（更省記憶體、更好的 NA 處理）
    df = pd.read_csv(
        csv_path,
        dtype_backend="pyarrow",
        parse_dates=["created_at", "last_login"],
    )

    # Copy-on-Write 安全操作
    pd.options.mode.copy_on_write = True

    cleaned = (
        df
        # 移除完全重複的列
        .drop_duplicates(subset=["email"])
        # 標準化 email
        .assign(
            email=lambda x: x["email"].str.lower().str.strip(),
            age=lambda x: x["age"].clip(lower=0, upper=120),
            name=lambda x: x["name"].str.title(),
        )
        # 移除無效 email
        .loc[lambda x: x["email"].str.contains(r"^[\w.+-]+@[\w-]+\.[\w.]+$", regex=True, na=False)]
        # 填補缺值
        .fillna({"age": df["age"].median(), "country": "Unknown"})
        .reset_index(drop=True)
    )
    return cleaned

# 使用範例
# result = clean_user_data("users.csv")
# print(result.info())
```

## 範例 3：DuckDB — 直接查詢檔案

```python
"""使用 DuckDB 進行記憶體內 SQL 查詢，直接讀取 Parquet/CSV"""
import duckdb

def sql_analytics(parquet_path: str) -> None:
    """用 SQL 分析 Parquet 資料"""
    con = duckdb.connect()

    # 直接查詢 Parquet 檔（無需先載入 DataFrame）
    result = con.sql(f"""
        SELECT
            region,
            product_category,
            COUNT(*) AS order_count,
            SUM(amount) AS total_amount,
            AVG(amount) AS avg_amount,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY amount) AS median_amount
        FROM read_parquet('{parquet_path}')
        WHERE order_date >= '2024-01-01'
        GROUP BY region, product_category
        HAVING COUNT(*) >= 10
        ORDER BY total_amount DESC
        LIMIT 20
    """)

    print(result.show())

    # DuckDB 也能直接轉為 Polars/pandas
    # polars_df = result.pl()
    # pandas_df = result.df()
    con.close()

# 使用範例
# sql_analytics("data/orders.parquet")
```

## 範例 4：Polars 視窗函式與複雜聚合

```python
"""示範 window function 與 rolling 計算"""
import polars as pl
import datetime as dt

def calculate_metrics(df: pl.DataFrame) -> pl.DataFrame:
    """計算每個使用者的相對指標與移動平均"""
    return df.with_columns(
        # 每個使用者的排名（group 內排序）
        pl.col("score")
        .rank(descending=True)
        .over("user_id")
        .alias("rank_in_user"),

        # 組內百分比
        (pl.col("score") / pl.col("score").sum().over("category") * 100)
        .round(2)
        .alias("pct_of_category"),

        # 7 天移動平均（需先排序）
        pl.col("score")
        .rolling_mean(window_size=7)
        .over("user_id")
        .alias("score_ma7"),

        # 與前一筆的差異
        (pl.col("score") - pl.col("score").shift(1).over("user_id"))
        .alias("score_diff"),
    )

# 建立測試資料
sample = pl.DataFrame({
    "user_id": ["A"] * 10 + ["B"] * 10,
    "category": (["X", "Y"] * 5) * 2,
    "date": [dt.date(2024, 1, i + 1) for i in range(10)] * 2,
    "score": [10, 15, 12, 18, 20, 14, 16, 22, 19, 25,
              8, 11, 9, 14, 17, 13, 10, 19, 15, 21],
}).sort("user_id", "date")

result = calculate_metrics(sample)
print(result)
```

## 範例 5：跨框架資料交換（narwhals）

```python
"""使用 narwhals 撰寫框架無關的資料處理函式"""
import narwhals as nw
from narwhals.typing import IntoFrame, Frame

@nw.narwhalify
def add_bmi(df: Frame) -> Frame:
    """計算 BMI — 同時支援 pandas 和 Polars"""
    return df.with_columns(
        bmi=(nw.col("weight") / (nw.col("height") ** 2)).round(2)
    )

# 用 pandas
import pandas as pd
pdf = pd.DataFrame({"weight": [70.0, 85.0], "height": [1.75, 1.80]})
print(add_bmi(pdf))

# 用 Polars（同一函式）
import polars as pl
plf = pl.DataFrame({"weight": [70.0, 85.0], "height": [1.75, 1.80]})
print(add_bmi(plf))
```
