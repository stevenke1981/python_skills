# py-testing — 速查表

## pytest CLI 常用指令

| 指令 | 說明 |
|------|------|
| `pytest` | 執行所有測試 |
| `pytest -v` | 詳細輸出 |
| `pytest -x` | 第一個失敗即停止 |
| `pytest --lf` | 只跑上次失敗的測試 |
| `pytest --ff` | 上次失敗的優先跑 |
| `pytest -k "keyword"` | 按名稱篩選 |
| `pytest -m slow` | 按 mark 篩選 |
| `pytest -n auto` | 平行執行（需 xdist） |
| `pytest --co` | 只列出要跑的測試（不執行） |
| `pytest -s` | 顯示 print() 輸出 |
| `pytest --tb=short` | 簡短 traceback |
| `pytest --durations=10` | 顯示最慢的 10 個測試 |

## Fixture Scope 速查

```python
@pytest.fixture(scope="function")   # 預設，每個測試重建
@pytest.fixture(scope="class")       # 每個 class 一次
@pytest.fixture(scope="module")      # 每個 .py 檔一次
@pytest.fixture(scope="package")     # 每個套件一次
@pytest.fixture(scope="session")     # 整個 session 一次
```

## Fixture 模式

```python
# 1. yield teardown（推薦）
@pytest.fixture
def resource():
    r = create_resource()
    yield r
    r.cleanup()

# 2. Factory fixture
@pytest.fixture
def make_item():
    def _make(**kwargs) -> Item:
        return Item(**kwargs)
    return _make

# 3. Autouse（自動套用，不需參數）
@pytest.fixture(autouse=True)
def reset_state():
    State.clear()
    yield
    State.clear()

# 4. Parametrized fixture
@pytest.fixture(params=["sqlite", "postgres"])
def db_engine(request):
    return create_engine(request.param)
```

## assert 模式

```python
# 基本斷言
assert result == expected
assert value is None
assert item in collection
assert len(items) == 3

# 近似比較
assert result == pytest.approx(3.14, abs=0.01)

# 例外
with pytest.raises(ValueError, match="invalid"):
    do_something()

# 警告
with pytest.warns(DeprecationWarning):
    old_function()

# 巢狀 dict 比較（pytest 會清楚顯示差異）
assert {"a": 1, "b": [2, 3]} == {"a": 1, "b": [2, 4]}
```

## Mark 裝飾器

```python
@pytest.mark.skip(reason="尚未實作")
@pytest.mark.skipif(sys.platform == "win32", reason="Linux only")
@pytest.mark.xfail(reason="已知 bug", raises=ValueError)
@pytest.mark.slow                    # 自訂 mark（需在 pyproject.toml 註冊）
@pytest.mark.parametrize(...)
@pytest.mark.asyncio                 # pytest-asyncio
@pytest.mark.usefixtures("db_conn")  # 類別級使用 fixture
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
```

## Monkeypatch 速查

```python
def test_with_monkeypatch(monkeypatch):
    # 設定環境變數
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.delenv("SECRET", raising=False)

    # 替換屬性
    monkeypatch.setattr("module.Class.method", lambda self: "mocked")
    monkeypatch.setattr(obj, "attr", new_value)

    # 替換 dict 項目
    monkeypatch.setitem(config, "key", "value")
    monkeypatch.delitem(config, "key", raising=False)

    # 修改 sys.path
    monkeypatch.syspath_prepend("/custom/path")

    # 切換工作目錄
    monkeypatch.chdir(tmp_path)
```

## unittest.mock 速查

```python
from unittest.mock import patch, MagicMock, AsyncMock, call

# patch 裝飾器
@patch("module.function")
def test_it(mock_fn):
    mock_fn.return_value = 42

# patch context manager
with patch("module.Class") as MockCls:
    MockCls.return_value.method.return_value = "ok"

# MagicMock 驗證
mock.assert_called_once()
mock.assert_called_with(1, key="val")
mock.assert_has_calls([call(1), call(2)])
assert mock.call_count == 3

# side_effect
mock.side_effect = [1, 2, ValueError("boom")]
mock.side_effect = lambda x: x * 2

# AsyncMock（Python 3.8+）
@patch("module.async_fn", new_callable=AsyncMock)
async def test_async(mock_fn):
    mock_fn.return_value = {"ok": True}
```

## Coverage 指令

```bash
# 基本覆蓋率
pytest --cov=src --cov-report=term-missing

# HTML 報告
pytest --cov=src --cov-report=html

# 設定最低門檻
pytest --cov=src --cov-fail-under=80

# 只看特定檔案
pytest --cov=src/module.py

# 產出 XML（CI 用）
pytest --cov=src --cov-report=xml
```

## conftest.py 分層

```
tests/
├── conftest.py          # session fixtures（DB、cache）
├── unit/
│   ├── conftest.py      # unit fixtures（mocks）
│   └── test_*.py
├── integration/
│   ├── conftest.py      # integration fixtures（HTTP client）
│   └── test_*.py
└── e2e/
    └── test_*.py
```

## Hypothesis 策略速查

```python
from hypothesis import strategies as st

st.integers()                          # 任意整數
st.integers(min_value=0, max_value=100)
st.floats(allow_nan=False)
st.text(min_size=1, max_size=50)
st.booleans()
st.none()
st.lists(st.integers(), max_size=20)
st.tuples(st.text(), st.integers())
st.dictionaries(st.text(), st.integers())
st.one_of(st.none(), st.integers())    # Union type
st.sampled_from(["a", "b", "c"])       # 從列表取
st.builds(MyClass, name=st.text())     # 建構物件
st.from_type(MyDataclass)              # 自動從 type hints 產生

# 組合
st.fixed_dictionaries({
    "name": st.text(min_size=1),
    "age": st.integers(min_value=0, max_value=150),
})
```

## pyproject.toml 完整設定範本

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra -q --strict-markers --strict-config"
markers = [
    "slow: 需要較長執行時間",
    "integration: 整合測試",
    "e2e: 端到端測試",
]
filterwarnings = [
    "error",
    "ignore::DeprecationWarning:third_party_lib",
]

[tool.coverage.run]
source = ["src"]
branch = true

[tool.coverage.report]
fail_under = 80
show_missing = true
exclude_lines = [
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.",
    "@overload",
    "raise NotImplementedError",
]
```
