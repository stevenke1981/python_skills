# py-testing — 常見陷阱與解法

## 陷阱 1: Fixture Scope 不匹配導致狀態洩漏

**問題**：`module` scope fixture 回傳 mutable 物件，不同測試互相污染。

```python
# ❌ 錯誤：module scope + mutable list
@pytest.fixture(scope="module")
def shared_list() -> list[int]:
    return []

def test_append(shared_list):
    shared_list.append(1)
    assert shared_list == [1]

def test_should_be_empty(shared_list):
    # ❌ 失敗！shared_list 已經是 [1]
    assert shared_list == []
```

```python
# ✅ 正確：function scope（預設）或回傳不可變物件
@pytest.fixture
def fresh_list() -> list[int]:
    return []

def test_append(fresh_list):
    fresh_list.append(1)
    assert fresh_list == [1]

def test_is_empty(fresh_list):
    assert fresh_list == []  # ✅ 每次都是空的
```

---

## 陷阱 2: patch 路徑錯誤

**問題**：`patch` 要 patch「使用方」的 namespace，不是「定義方」。

```python
# src/service.py
from src.client import http_get

def get_data():
    return http_get("/api/data")

# ❌ 錯誤：patch 定義方
@patch("src.client.http_get")  # 定義方的路徑
def test_wrong(mock_get):
    mock_get.return_value = {"ok": True}
    result = get_data()
    assert result == {"ok": True}  # ⚠️ 可能不生效
```

```python
# ✅ 正確：patch 使用方（import 後的 reference）
@patch("src.service.http_get")  # service.py 裡的 reference
def test_correct(mock_get):
    mock_get.return_value = {"ok": True}
    result = get_data()
    assert result == {"ok": True}  # ✅ 正確 mock
```

---

## 陷阱 3: parametrize 共用 mutable 預設值

**問題**：parametrize 的 list/dict 引數在測試間共享。

```python
# ❌ 危險：mutable 物件作為 parametrize 引數
@pytest.mark.parametrize("data", [
    [1, 2, 3],  # ⚠️ 這個 list 可能被修改
])
def test_mutate(data):
    data.append(4)
    assert len(data) == 4
    # 如果 pytest 重用相同物件，下次測試 data 就是 [1,2,3,4]
```

```python
# ✅ 安全：在測試內部複製，或使用 tuple
@pytest.mark.parametrize("data", [
    (1, 2, 3),  # tuple 不可變
])
def test_safe(data):
    work = list(data)  # 複製一份來操作
    work.append(4)
    assert len(work) == 4
```

---

## 陷阱 4: async fixture 搭配錯誤 scope

**問題**：`pytest-asyncio` 的 async fixture 與 session scope 混用會出問題。

```python
# ❌ 可能有問題：async + session scope
@pytest.fixture(scope="session")
async def db_pool():
    pool = await create_pool()
    yield pool
    await pool.close()
    # ⚠️ 不同 event loop 會導致錯誤
```

```python
# ✅ 建議：async fixture 使用 function 或 module scope
@pytest.fixture(scope="module")
async def db_pool():
    pool = await create_pool()
    yield pool
    await pool.close()

# 或者使用同步 fixture + event_loop
@pytest.fixture(scope="session")
def db_pool(event_loop):
    pool = event_loop.run_until_complete(create_pool())
    yield pool
    event_loop.run_until_complete(pool.close())
```

---

## 陷阱 5: conftest.py 放錯位置

**問題**：conftest.py 必須放在 `tests/` 或其子目錄才會被自動載入。

```
# ❌ 錯誤結構
project/
├── conftest.py        # 放在專案根目錄
├── src/
│   └── app.py
└── tests/
    └── test_app.py    # 不一定能讀到根目錄的 conftest！
```

```
# ✅ 正確結構
project/
├── src/
│   └── app.py
└── tests/
    ├── conftest.py    # ← 放在 tests/ 目錄
    └── test_app.py
```

---

## 陷阱 6: monkeypatch 與 import 時機衝突

**問題**：若模組在 import 時就讀取了環境變數，monkeypatch 來不及生效。

```python
# src/config.py
import os
API_URL = os.environ.get("API_URL", "https://default.api")  # ← import 時就決定了

# ❌ monkeypatch 無效
def test_config(monkeypatch):
    monkeypatch.setenv("API_URL", "https://test.api")
    from src.config import API_URL  # ⚠️ 已經 cached
    assert API_URL == "https://test.api"  # 失敗！
```

```python
# ✅ 解法 1: 改為函式呼叫（延遲求值）
# src/config.py
import os
def get_api_url() -> str:
    return os.environ.get("API_URL", "https://default.api")

# ✅ 解法 2: reload 模組
def test_config(monkeypatch):
    monkeypatch.setenv("API_URL", "https://test.api")
    import importlib
    import src.config
    importlib.reload(src.config)
    assert src.config.API_URL == "https://test.api"
```

---

## 陷阱 7: Coverage 數字高但測試品質低

**問題**：高覆蓋率≠高品質，很多測試只驗證「不報錯」但沒驗證行為。

```python
# ❌ 無效測試：只確保不拋例外
def test_process():
    result = process_data([1, 2, 3])
    assert result is not None  # 這告訴我們什麼？
```

```python
# ✅ 有效測試：驗證具體行為
def test_process_sums_values():
    result = process_data([1, 2, 3])
    assert result.total == 6
    assert result.count == 3
    assert result.average == pytest.approx(2.0)

def test_process_empty_raises():
    with pytest.raises(ValueError, match="empty"):
        process_data([])
```

**建議**：搭配 `mutmut`（突變測試）驗證測試品質：
```bash
mutmut run --paths-to-mutate=src/
mutmut results
```

---

## 陷阱 8: 測試間順序依賴

**問題**：測試隱式依賴執行順序，單獨跑或平行跑就失敗。

```python
# ❌ 隱式依賴：test_b 依賴 test_a 修改的全域狀態
_cache = {}

def test_a():
    _cache["key"] = "value"

def test_b():
    assert _cache["key"] == "value"  # ⚠️ 單獨跑會 KeyError
```

```python
# ✅ 用 fixture 隔離
@pytest.fixture
def cache() -> dict:
    return {}

def test_a(cache):
    cache["key"] = "value"
    assert cache["key"] == "value"

def test_b(cache):
    assert cache == {}  # 確保隔離

# ✅ 驗證：加上 pytest-randomly 隨機化測試順序
# pip install pytest-randomly
# pytest -p randomly
```
