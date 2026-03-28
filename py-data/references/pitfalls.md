# py-data 常見陷阱與解法

## 陷阱 1：pandas SettingWithCopyWarning / ChainedAssignment

**問題**：鏈式索引修改可能作用在副本上，不會改到原始 DataFrame。

```python
# ❌ 危險！可能修改副本
df[df["age"] > 30]["score"] = 100

# ❌ 同理
subset = df[df["active"]]
subset["label"] = "VIP"   # 可能不反映到 df
```

**解法**：

```python
# ✅ pandas 2.x 啟用 Copy-on-Write（推薦）
pd.options.mode.copy_on_write = True

# ✅ 使用 .loc 一次定位
df.loc[df["age"] > 30, "score"] = 100
```

---

## 陷阱 2：pandas inplace=True 不是真正的「就地」

**問題**：`inplace=True` 仍會建立新物件再賦值回去，效能沒有提升，且 pandas 官方計畫棄用。

```python
# ❌ 不推薦
df.drop(columns=["tmp"], inplace=True)
df.fillna(0, inplace=True)
```

**解法**：

```python
# ✅ 重新賦值（語意更清楚）
df = df.drop(columns=["tmp"])
df = df.fillna(0)
```

---

## 陷阱 3：Polars 嚴格型別 vs pandas 隱式轉型

**問題**：Polars 不允許隱式型別轉換，混合型別的欄會直接報錯。

```python
# ❌ Polars 會報 ComputeError
pl.DataFrame({"val": [1, "two", 3]})
```

**解法**：

```python
# ✅ 確保型別一致
pl.DataFrame({"val": [1, 2, 3]})

# 需要混合型別時明確用 Object 或 String
pl.DataFrame({"val": ["1", "two", "3"]})
```

---

## 陷阱 4：Polars Lazy 忘記 .collect()

**問題**：`scan_*` 系列回傳的是 `LazyFrame`，不會觸發運算，直到呼叫 `.collect()`。

```python
# ❌ lf 是 LazyFrame，print 只會看到查詢計畫
lf = pl.scan_csv("data.csv").filter(pl.col("x") > 0)
print(lf)           # 不是結果！
print(len(lf))      # LazyFrame 沒有 len()
```

**解法**：

```python
# ✅ 顯式觸發
df = lf.collect()
print(df)

# 或只取前 N 筆預覽
print(lf.head(5).collect())
```

---

## 陷阱 5：read_csv 大檔記憶體爆炸

**問題**：一次讀入超大 CSV（> 可用記憶體）會 OOM。

```python
# ❌ 10GB CSV 一次全載
df = pd.read_csv("huge.csv")
```

**解法**：

```python
# ✅ 方法 1：分塊讀取
chunks = pd.read_csv("huge.csv", chunksize=100_000)
for chunk in chunks:
    process(chunk)

# ✅ 方法 2：DuckDB 直接查（不載入記憶體）
import duckdb
result = duckdb.sql("SELECT col, SUM(val) FROM 'huge.csv' GROUP BY col").df()

# ✅ 方法 3：Polars streaming
result = (
    pl.scan_csv("huge.csv")
    .group_by("col")
    .agg(pl.col("val").sum())
    .collect(streaming=True)
)
```

---

## 陷阱 6：GroupBy 之後 apply 效能極差

**問題**：`groupby().apply()` 會對每個 group 呼叫 Python 函式，極慢。

```python
# ❌ 非常慢
df.groupby("cat").apply(lambda g: g["val"].sum() / g["cnt"].sum())
```

**解法**：

```python
# ✅ 使用內建聚合
df.groupby("cat").agg(
    weighted_avg=("val", "sum")
)

# ✅ 若需自訂邏輯，用 Polars expressions
pl_df.group_by("cat").agg(
    (pl.col("val").sum() / pl.col("cnt").sum()).alias("weighted_avg")
)
```

---

## 陷阱 7：Arrow 型別不匹配導致資料遺失

**問題**：pandas Nullable dtype 與 NumPy dtype 混用，轉型時 NA 被無聲丟棄。

```python
import pandas as pd
import numpy as np

# ❌ 混合 nullable 與 numpy
s = pd.array([1, pd.NA, 3], dtype="Int64")   # 大寫 I → Nullable
arr = s.to_numpy()          # NA 變成 nan，型別變 float64
arr = s.to_numpy(na_value=0)  # 明確指定才安全
```

**解法**：

```python
# ✅ 全面用 Arrow 後端就不會有混合問題
df = pd.read_csv("f.csv", dtype_backend="pyarrow")

# ✅ 轉 numpy 時明確處理
arr = df["col"].to_numpy(dtype="float64", na_value=np.nan)
```

---

## 陷阱 8：merge/join 鍵值型別不一致

**問題**：兩個 DataFrame 的 join key 型別不同（一個 int、一個 str），merge 結果為空。

```python
# ❌ 靜默回傳空 DataFrame
left = pd.DataFrame({"id": [1, 2], "v": [10, 20]})
right = pd.DataFrame({"id": ["1", "2"], "v": [100, 200]})
pd.merge(left, right, on="id")  # 空！因為 int ≠ str
```

**解法**：

```python
# ✅ 合併前統一型別
right["id"] = right["id"].astype(int)
result = pd.merge(left, right, on="id")

# ✅ Polars 會直接報錯（更安全）
# pl.DataFrame left.join(right, on="id")  → SchemaError
```
