# py-data 速查表

## pandas 常用操作

### IO 讀寫
```python
# 讀取（推薦 Arrow 後端）
df = pd.read_csv("f.csv", dtype_backend="pyarrow")
df = pd.read_parquet("f.parquet")
df = pd.read_excel("f.xlsx", engine="openpyxl")
df = pd.read_json("f.json")

# 寫出
df.to_parquet("out.parquet", engine="pyarrow")
df.to_csv("out.csv", index=False)
```

### 選取與過濾
```python
df["col"]                      # 單欄 → Series
df[["a", "b"]]                 # 多欄 → DataFrame
df.loc[mask, "col"]            # 條件 + 欄名
df.iloc[0:5, 0:3]             # 位置索引
df.query("age > 30 and city == 'Taipei'")  # 字串查詢
```

### 聚合與分組
```python
df.groupby("key").agg(
    total=("value", "sum"),
    avg=("value", "mean"),
    cnt=("id", "nunique"),
)
df.pivot_table(values="v", index="a", columns="b", aggfunc="sum")
```

### 合併
```python
pd.merge(left, right, on="key", how="left")                    # Join
pd.concat([df1, df2], ignore_index=True)                        # 垂直合併
left.merge(right, left_on="a", right_on="b", how="inner")     # 不同欄名
```

### 缺值處理
```python
df.isna().sum()                    # 缺值計數
df.fillna({"col": 0})             # 填補
df.dropna(subset=["a", "b"])      # 移除
df.interpolate(method="linear")   # 插值
```

---

## Polars 常用操作

### 讀寫
```python
df = pl.read_parquet("f.parquet")
lf = pl.scan_parquet("f.parquet")    # Lazy（推薦）
lf = pl.scan_csv("f.csv")
df.write_parquet("out.parquet")
```

### 基本語法
```python
# select：選欄
df.select("a", "b", pl.col("c").sum())

# filter：過濾列
df.filter(pl.col("age") > 30)

# with_columns：新增/修改欄
df.with_columns(
    (pl.col("a") + pl.col("b")).alias("ab_sum"),
    pl.col("name").str.to_uppercase(),
)

# group_by + agg
df.group_by("key").agg(
    pl.col("value").sum(),
    pl.col("value").mean().alias("avg"),
    pl.len().alias("count"),
)
```

### Lazy API 模式
```python
result = (
    pl.scan_parquet("data/*.parquet")
    .filter(pl.col("status") == "active")
    .group_by("category")
    .agg(pl.col("amount").sum())
    .sort("amount", descending=True)
    .collect()      # 觸發計算
)
```

### 合併
```python
df1.join(df2, on="key", how="left")
pl.concat([df1, df2])                  # 垂直
pl.concat([df1, df2], how="horizontal") # 水平
```

### 視窗函式
```python
df.with_columns(
    pl.col("v").sum().over("group").alias("group_sum"),
    pl.col("v").rank().over("group").alias("rank"),
    pl.col("v").shift(1).over("group").alias("prev"),
)
```

---

## NumPy 速查

```python
a = np.array([1, 2, 3])
b = np.arange(0, 10, 0.5)   # 等差
c = np.linspace(0, 1, 100)  # 線性空間
d = np.zeros((3, 4))        # 全零矩陣

# 向量化運算（避免 for 迴圈）
result = np.where(a > 2, a * 10, a)  # 條件替換
np.einsum("ij,jk->ik", A, B)        # Einstein 求和
```

---

## 框架互轉

```python
# pandas → Polars
pl_df = pl.from_pandas(pd_df)

# Polars → pandas
pd_df = pl_df.to_pandas()

# Arrow Table 中介（零拷貝）
import pyarrow as pa
arrow_table = pa.Table.from_pandas(pd_df)
pl_df = pl.from_arrow(arrow_table)
pd_df = arrow_table.to_pandas()

# DuckDB ↔ DataFrame
import duckdb
duckdb.sql("SELECT * FROM pd_df WHERE x > 1").pl()  # → Polars
duckdb.sql("SELECT * FROM pl_df LIMIT 10").df()      # → pandas
```

---

## 效能調校快記

| 場景 | 建議 |
|------|------|
| 大 CSV | `pl.scan_csv()` lazy 或 `pd.read_csv(chunksize=)` |
| 多 Parquet | `pl.scan_parquet("dir/*.parquet")` glob |
| GroupBy 慢 | Polars 原生快 2-5x；pandas 可用 `.pipe()` 減少中間物件 |
| 記憶體不足 | `duckdb.sql()` 直接查詢檔案、Polars streaming |
| 型別推斷開銷 | 指定 `dtypes` / `schema` 避免自動推斷 |
| Arrow 後端 | `pd.read_csv(dtype_backend="pyarrow")` 省 50%+ 記憶體 |
