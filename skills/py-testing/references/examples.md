# py-testing — 完整可運行範例

## 範例 1: Yield Fixture + 資源清理

```python
"""示範 yield fixture 的自動清理模式"""
import pytest
import sqlite3
from pathlib import Path


@pytest.fixture
def db_conn(tmp_path: Path):
    """建立測試用 SQLite 連線，測試結束自動清理"""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
    conn.commit()
    yield conn  # 測試函式會收到 conn
    # --- teardown ---
    conn.close()


def test_insert_and_query(db_conn: sqlite3.Connection):
    db_conn.execute("INSERT INTO users (name) VALUES (?)", ("Alice",))
    db_conn.commit()

    cursor = db_conn.execute("SELECT name FROM users")
    rows = cursor.fetchall()
    assert rows == [("Alice",)]


def test_empty_table(db_conn: sqlite3.Connection):
    """每個測試都拿到乾淨的 DB（function scope）"""
    cursor = db_conn.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    assert count == 0
```

---

## 範例 2: 多層 Parametrize + pytest.param

```python
"""示範 parametrize 的進階用法：堆疊、ID、xfail"""
import pytest


def parse_int(s: str, base: int = 10) -> int:
    """安全的整數解析"""
    return int(s.strip(), base)


# 基本 parametrize
@pytest.mark.parametrize("text, expected", [
    ("42", 42),
    ("  -7  ", -7),
    ("0", 0),
    pytest.param("abc", None, marks=pytest.mark.xfail(raises=ValueError)),  # 預期失敗
])
def test_parse_int_base10(text: str, expected: int | None):
    result = parse_int(text)
    assert result == expected


# 堆疊 parametrize — 產生組合
@pytest.mark.parametrize("text", ["ff", "FF", "  ff  "])
@pytest.mark.parametrize("base", [16])
def test_parse_int_hex(text: str, base: int):
    result = parse_int(text, base=base)
    assert result == 255


# 使用 ids 讓輸出更易讀
@pytest.mark.parametrize(
    "input_val, base, expected",
    [
        pytest.param("1010", 2, 10, id="binary-10"),
        pytest.param("77", 8, 63, id="octal-63"),
        pytest.param("ff", 16, 255, id="hex-255"),
    ],
)
def test_parse_int_various_bases(input_val: str, base: int, expected: int):
    assert parse_int(input_val, base) == expected
```

---

## 範例 3: monkeypatch + 環境變數 Mock

```python
"""示範 monkeypatch 取代真實環境依賴"""
import os
import pytest
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    db_host: str
    db_port: int
    debug: bool


def load_config() -> AppConfig:
    """從環境變數載入設定"""
    return AppConfig(
        db_host=os.environ.get("DB_HOST", "localhost"),
        db_port=int(os.environ.get("DB_PORT", "5432")),
        debug=os.environ.get("DEBUG", "false").lower() == "true",
    )


def test_load_config_defaults():
    """預設值測試（不設環境變數）"""
    config = load_config()
    assert config.db_host == "localhost"
    assert config.db_port == 5432
    assert config.debug is False


def test_load_config_custom(monkeypatch: pytest.MonkeyPatch):
    """monkeypatch 設定環境變數，測試結束自動還原"""
    monkeypatch.setenv("DB_HOST", "db.prod.internal")
    monkeypatch.setenv("DB_PORT", "3306")
    monkeypatch.setenv("DEBUG", "true")

    config = load_config()
    assert config.db_host == "db.prod.internal"
    assert config.db_port == 3306
    assert config.debug is True


def test_load_config_missing_port(monkeypatch: pytest.MonkeyPatch):
    """monkeypatch.delenv 確保環境變數不存在"""
    monkeypatch.delenv("DB_PORT", raising=False)
    config = load_config()
    assert config.db_port == 5432  # 使用預設值
```

---

## 範例 4: Hypothesis 屬性基底測試

```python
"""示範 Hypothesis 自動產生大量邊界測試資料"""
from hypothesis import given, settings, assume
from hypothesis import strategies as st


def clamp(value: int, lo: int, hi: int) -> int:
    """將 value 限制在 [lo, hi] 範圍"""
    if lo > hi:
        raise ValueError(f"lo ({lo}) > hi ({hi})")
    return max(lo, min(hi, value))


# 屬性 1: 回傳值必定在 [lo, hi] 範圍
@given(
    value=st.integers(min_value=-1000, max_value=1000),
    lo=st.integers(min_value=-500, max_value=0),
    hi=st.integers(min_value=0, max_value=500),
)
def test_clamp_within_bounds(value: int, lo: int, hi: int):
    assume(lo <= hi)  # 前提條件
    result = clamp(value, lo, hi)
    assert lo <= result <= hi


# 屬性 2: 已在範圍內的值不會改變
@given(
    lo=st.integers(min_value=-100, max_value=0),
    hi=st.integers(min_value=0, max_value=100),
)
def test_clamp_identity_in_range(lo: int, hi: int):
    assume(lo <= hi)
    for value in range(lo, hi + 1):
        assert clamp(value, lo, hi) == value


# 屬性 3: lo > hi 必須拋錯
@given(
    lo=st.integers(min_value=1, max_value=100),
    hi=st.integers(min_value=-100, max_value=0),
)
@settings(max_examples=50)
def test_clamp_invalid_range(lo: int, hi: int):
    assume(lo > hi)
    import pytest
    with pytest.raises(ValueError, match="lo .* > hi"):
        clamp(0, lo, hi)
```

---

## 範例 5: pytest-asyncio 非同步測試

```python
"""示範 pytest-asyncio 測試 async 函式與 fixture"""
import asyncio
import pytest


# 非同步 fixture
@pytest.fixture
async def async_data() -> list[int]:
    """模擬從非同步來源取得資料"""
    await asyncio.sleep(0.01)
    return [10, 20, 30]


# 被測的 async 函式
async def async_sum(values: list[int]) -> int:
    await asyncio.sleep(0.01)  # 模擬 IO
    return sum(values)


async def async_map(values: list[int], factor: int) -> list[int]:
    """非同步 map 運算"""
    await asyncio.sleep(0.01)
    return [v * factor for v in values]


# pytest-asyncio mode="auto" 時不需要 @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_async_sum(async_data: list[int]):
    result = await async_sum(async_data)
    assert result == 60


@pytest.mark.asyncio
async def test_async_map(async_data: list[int]):
    result = await async_map(async_data, 2)
    assert result == [20, 40, 60]


@pytest.mark.asyncio
async def test_concurrent_tasks():
    """使用 TaskGroup 並行執行多個 async 測試操作"""
    results: list[int] = []

    async with asyncio.TaskGroup() as tg:
        async def compute(n: int):
            await asyncio.sleep(0.01)
            results.append(n * n)

        for i in range(5):
            tg.create_task(compute(i))

    assert sorted(results) == [0, 1, 4, 9, 16]
```
