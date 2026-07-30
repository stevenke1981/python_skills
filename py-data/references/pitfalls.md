# py-data 常見陷阱與解法

> 本文件補充 [`../SKILL.md`](../SKILL.md)。範例以 pandas 3 與現行 Polars API 為主；實際專案仍以 lockfile 與官方文件為準。

## 陷阱 1：pandas Chained Assignment

**問題**：鏈式索引無法可靠表達「修改原始 DataFrame」。pandas 3 的 Copy-on-Write 已是預設且唯一模式，鏈式賦值不應作為更新方式。

```python
# ❌ 不可靠
users[users["active"]]["label"] = "VIP"
```

**解法**：用單一步驟 `.loc` 明確定位。

```python
users.loc[users["active"], "label"] = "VIP"
```

若只想修改 subset，先明確 `.copy()`，不要期待它回寫原始資料。

---

## 陷阱 2：把 `inplace=True` 當成記憶體最佳化

**問題**：`inplace=True` 不保證零複製或較省記憶體，還會讓 method chaining 與測試變得較難。不同 operation 的實作也不相同。

```python
# 語意容易分散
frame.drop(columns=["temporary"], inplace=True)
frame.fillna(0, inplace=True)
```

**解法**：優先使用清楚的資料流與重新賦值，再用 profiler 判斷記憶體。

```python
frame = frame.drop(columns=["temporary"]).fillna(0)
```

---

## 陷阱 3：依賴 `object` 判斷文字欄位

**問題**：pandas 3 預設可推斷專用 `str` dtype；`dtype == object` 不再是可靠的文字判斷。

**解法**：使用明確 schema、`astype("str")` 或 pandas type predicates。

```python
from pandas.api.types import is_string_dtype

if not is_string_dtype(frame["name"]):
    raise TypeError("name must be a string column")
```

---

## 陷阱 4：Polars 混合型別與靜默 cast 假設

**問題**：同一欄混合數字與文字會造成 schema 推斷或 cast 問題。

```python
# ❌ 不清楚的欄位契約
values = pl.DataFrame({"value": [1, "two", 3]})
```

**解法**：在 ingestion 邊界指定 schema 或先正規化。

```python
values = pl.DataFrame(
    {"value": ["1", "two", "3"]},
    schema={"value": pl.String},
)
```

對不允許失敗的轉型使用 `strict=True`，不要讓錯誤值無聲變成 null。

---

## 陷阱 5：LazyFrame 忘記執行或過早 `collect()`

`scan_*` 回傳 `LazyFrame`；忘記 `collect()` 不會得到結果，但太早 `collect()` 又會失去查詢最佳化與 streaming 機會。

```python
lazy = pl.scan_parquet("events/*.parquet")

# ✅ 在 lazy pipeline 中先 select/filter/aggregate
result = (
    lazy.select("user_id", "amount", "status")
    .filter(pl.col("status") == "completed")
    .group_by("user_id")
    .agg(pl.col("amount").sum())
    .collect(engine="streaming")
)
```

現行 API 使用 `engine="streaming"`；不要沿用已過時的 `collect(streaming=True)`。

---

## 陷阱 6：把 streaming 當成「一定不會 OOM」

**問題**：並非所有 operation 都能完整 streaming；sort、某些 join 或 UDF 可能需要 materialization 或 fallback。

**解法**：

- 查看 query plan。
- 儘早 filter/select。
- 寫大量輸出時使用 sink/partition。
- 以實際資料量量測 peak RSS 與 spill。
- 對 fallback 設定資源與告警。

```python
query = pl.scan_csv("huge.csv").group_by("region").agg(pl.col("amount").sum())
print(query.explain())
result = query.collect(engine="streaming")
```

---

## 陷阱 7：`groupby.apply()` 把工作拉回 Python

**問題**：每個 group 執行 Python callback 通常阻礙向量化與引擎最佳化。

```python
# ❌ 可由內建聚合完成時，不要先用 apply
result = frame.groupby("category").apply(custom_sum)
```

**解法**：先嘗試內建 aggregation/expression。

```python
result = frame.groupby("category", as_index=False).agg(
    value_sum=("value", "sum"),
    count=("value", "size"),
)
```

若業務邏輯確實需要 UDF，先建立 correctness test，再量測成本。

---

## 陷阱 8：Join key 型別或 cardinality 不一致

**問題**：一邊是整數、一邊是字串，或 one-to-one 實際變成 many-to-many，會產生錯誤、空結果或列數爆炸。

**解法**：

```python
left["id"] = left["id"].astype("string")
right["id"] = right["id"].astype("string")

result = left.merge(
    right,
    on="id",
    how="left",
    validate="one_to_one",
)
```

Join 前後比較：

- key null／duplicate
- dtype
- 輸入與輸出列數
- 關鍵金額或數量 reconciliation

---

## 陷阱 9：把 null、空字串與零視為同一件事

```python
# ❌ 可能把「未知」誤當成 0
frame["amount"] = frame["amount"].fillna(0)
```

先定義：

- null：未知／缺失
- 空字串：存在但沒有文字，或無效資料
- 零：已知數值為 0
- 不適用：可能需要獨立欄位或狀態

清洗規則必須能追溯，並保留被修正／拒絕資料的統計。

---

## 陷阱 10：時間欄位沒有時區與解析度契約

**問題**：naive datetime、DST、不同單位與 pandas 3 的解析度變化會造成排序、join 或窗口錯誤。

**解法**：

- ingestion 時驗證格式與 timezone。
- 儲存時明確使用 UTC 或已定義區域。
- 顯示時才轉換使用者時區。
- 不假設所有 datetime 都是 nanoseconds。
- 測 DST 切換、月底、閏年與跨時區資料。

---

## 陷阱 11：Arrow／NumPy 轉換忽略 null 與 copy

轉換前先確認 dtype、null 與是否真的 zero-copy。某些轉換會配置新 buffer 或將 nullable integer 轉為 float。

```python
array = frame["amount"].to_numpy(
    dtype="float64",
    na_value=float("nan"),
)
```

不要只看 API 名稱中的 Arrow/zero-copy；用 memory profiler 與實際 schema 驗證。

---

## 陷阱 12：輸出檔不可重現

常見原因：

- 欄位或列順序未定義
- partition 產生大量小檔案
- 未記錄來源版本與參數
- dtype/時區隨推斷改變
- 直接覆寫正式檔案，失敗後留下半成品

**解法**：固定 schema 與必要排序，寫入暫存位置，驗證後 atomic publish，並保存資料版本、程式版本與品質結果。
