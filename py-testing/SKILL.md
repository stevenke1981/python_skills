---
name: py-testing
description: >
  Python testing and quality assurance with pytest ecosystem.
  Trigger when user mentions pytest, unit test, integration test,
  test fixtures, parametrize, test coverage, mocking, hypothesis,
  property-based testing, mutation testing, conftest, TDD, test-driven.
  Also trigger when user asks about testing best practices,
  test architecture, or how to write reliable Python tests.
---

# Python 測試與品質保證

## Quick Start（30 秒上手）

```python
# test_calculator.py
import pytest

def add(a: int, b: int) -> int:
    return a + b

# 基本測試
def test_add_positive():
    assert add(2, 3) == 5

# 參數化：一次跑多組輸入
@pytest.mark.parametrize("a, b, expected", [
    (1, 2, 3),
    (-1, 1, 0),
    (0, 0, 0),
])
def test_add_parametrize(a: int, b: int, expected: int):
    assert add(a, b) == expected
```

```bash
# 執行
pytest test_calculator.py -v
```

## 核心概念

### 1. Fixtures — 測試的骨架

Fixtures 提供可重用的前置設定與清理邏輯，透過依賴注入自動傳入測試函式。

```python
import pytest
from pathlib import Path

@pytest.fixture
def sample_data() -> dict[str, list[int]]:
    """提供測試用範例資料"""
    return {"values": [1, 2, 3, 4, 5], "empty": []}

@pytest.fixture
def tmp_config(tmp_path: Path) -> Path:
    """建立暫時設定檔（pytest 內建 tmp_path）"""
    config = tmp_path / "config.toml"
    config.write_text('[app]\ndebug = true\n')
    return config

def test_data_sum(sample_data: dict[str, list[int]]):
    assert sum(sample_data["values"]) == 15

def test_config_exists(tmp_config: Path):
    assert tmp_config.exists()
    assert "debug" in tmp_config.read_text()
```

**Fixture Scope**：控制生命週期

| Scope | 說明 | 典型用途 |
|-------|------|----------|
| `function` | 每個測試函式（預設） | 資料隔離 |
| `class` | 每個測試類別 | 類別級共用資源 |
| `module` | 每個 .py 檔 | DB 連線 |
| `session` | 整個測試 session | 全域設定 |

### 2. Parametrize — 資料驅動測試

用 `@pytest.mark.parametrize` 將多組測試資料解耦出來。

```python
import pytest

def is_palindrome(s: str) -> bool:
    cleaned = s.lower().replace(" ", "")
    return cleaned == cleaned[::-1]

@pytest.mark.parametrize("text, expected", [
    ("racecar", True),
    ("hello", False),
    ("A man a plan a canal Panama", True),
    ("", True),
], ids=["simple", "not_palindrome", "sentence", "empty"])
def test_palindrome(text: str, expected: bool):
    assert is_palindrome(text) == expected
```

### 3. Mocking — 隔離外部依賴

```python
from unittest.mock import patch, MagicMock
import pytest

# 被測函式
def fetch_user(user_id: int) -> dict:
    import httpx
    resp = httpx.get(f"https://api.example.com/users/{user_id}")
    resp.raise_for_status()
    return resp.json()

def test_fetch_user():
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 1, "name": "Alice"}
    mock_response.raise_for_status.return_value = None

    with patch("httpx.get", return_value=mock_response) as mock_get:
        result = fetch_user(1)
        assert result["name"] == "Alice"
        mock_get.assert_called_once_with("https://api.example.com/users/1")
```

### 4. Hypothesis — 屬性基底測試

讓 Hypothesis 自動產生大量隨機測試資料，發現手動想不到的邊界情況。

```python
from hypothesis import given, strategies as st

def encode_decode(s: str) -> str:
    return s.encode("utf-8").decode("utf-8")

@given(st.text())
def test_encode_decode_roundtrip(s: str):
    """編碼再解碼必定還原"""
    assert encode_decode(s) == s

@given(st.lists(st.integers(), min_size=1))
def test_sorted_is_ordered(lst: list[int]):
    result = sorted(lst)
    for i in range(len(result) - 1):
        assert result[i] <= result[i + 1]
```

### 5. Coverage — 測試覆蓋率

```bash
# 安裝
pip install pytest-cov

# 執行並產出覆蓋率報告
pytest --cov=src --cov-report=term-missing --cov-fail-under=80

# HTML 報告
pytest --cov=src --cov-report=html
```

**pyproject.toml 設定**：

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra -q --strict-markers"
markers = [
    "slow: 執行時間較長的測試",
    "integration: 整合測試",
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
]
```

## 實戰 Patterns

### Pattern 1: conftest.py 分層組織

**場景**：大型專案需要不同層級的共用 fixtures。

```
tests/
├── conftest.py              # session-level fixtures（DB 連線等）
├── unit/
│   ├── conftest.py          # unit test 共用 fixtures
│   └── test_models.py
├── integration/
│   ├── conftest.py          # integration fixtures（HTTP client 等）
│   └── test_api.py
└── e2e/
    └── test_flows.py
```

```python
# tests/conftest.py
import pytest

@pytest.fixture(scope="session")
def db_url() -> str:
    return "sqlite:///test.db"

# tests/unit/conftest.py
import pytest

@pytest.fixture
def mock_repo():
    """單元測試用的 mock repository"""
    from unittest.mock import MagicMock
    return MagicMock()
```

### Pattern 2: Factory Fixtures

**場景**：需要在單一測試中建立多個不同參數的物件。

```python
import pytest
from dataclasses import dataclass

@dataclass(frozen=True)
class User:
    name: str
    age: int
    active: bool = True

@pytest.fixture
def make_user():
    """工廠 fixture — 每次呼叫建立新 User"""
    created: list[User] = []

    def _make(name: str = "Test", age: int = 25, active: bool = True) -> User:
        user = User(name=name, age=age, active=active)
        created.append(user)
        return user

    yield _make
    # teardown: 清理（若有 DB 則刪除記錄）

def test_multiple_users(make_user):
    admin = make_user("Admin", 30)
    guest = make_user("Guest", 18, active=False)
    assert admin.active is True
    assert guest.active is False
```

### Pattern 3: 非同步測試 (pytest-asyncio)

**場景**：測試 async 函式。

```python
import pytest
import asyncio

async def async_fetch(url: str) -> str:
    await asyncio.sleep(0.01)  # 模擬 IO
    return f"response from {url}"

@pytest.mark.asyncio
async def test_async_fetch():
    result = await async_fetch("https://example.com")
    assert "example.com" in result
```

**pyproject.toml**：
```toml
[tool.pytest-asyncio]
mode = "auto"  # 自動偵測 async 測試，不需每個都加 mark
```

### Pattern 4: Snapshot / Approval Testing

**場景**：驗證輸出結構（JSON、HTML、報表）不意外改變。

```python
# 需安裝 pytest-snapshot 或 syrupy
import pytest

def generate_report(data: list[int]) -> dict:
    return {
        "count": len(data),
        "sum": sum(data),
        "mean": sum(data) / len(data) if data else 0,
    }

def test_report_snapshot(snapshot):
    result = generate_report([10, 20, 30])
    assert result == snapshot
    # 首次執行：pytest --snapshot-update 產生基準
    # 後續執行：自動比對
```

## 工具鏈推薦

| 工具 | 用途 | 安裝 | 備註 |
|------|------|------|------|
| pytest | 測試框架核心 | `pip install pytest` | 必備 |
| pytest-cov | 覆蓋率 | `pip install pytest-cov` | 搭配 coverage.py |
| pytest-asyncio | async 測試 | `pip install pytest-asyncio` | auto mode 推薦 |
| pytest-xdist | 平行執行 | `pip install pytest-xdist` | `pytest -n auto` |
| hypothesis | 屬性基底測試 | `pip install hypothesis` | 自動產生測試資料 |
| pytest-mock | mock 輔助 | `pip install pytest-mock` | 提供 `mocker` fixture |
| syrupy | Snapshot 測試 | `pip install syrupy` | 取代 pytest-snapshot |
| mutmut | 突變測試 | `pip install mutmut` | 驗證測試品質 |
| factory-boy | 工廠模式 | `pip install factory-boy` | Django/SQLAlchemy 整合 |
| freezegun | 時間凍結 | `pip install freezegun` | 測試時間相關邏輯 |

## 延伸閱讀

讀取 `references/` 目錄下的對應檔案：
- `references/examples.md` — 完整可運行範例
- `references/cheatsheet.md` — 速查表
- `references/pitfalls.md` — 常見錯誤與解法

## 版本相容性

| Python 版本 | 支援狀態 | 備註 |
|-------------|----------|------|
| 3.13+ | ✅ 完整支援 | pytest 8.x |
| 3.12 | ✅ 完整支援 | |
| 3.11 | ✅ | |
| 3.10 | ✅ | pytest 8.x 最低要求 |
| 3.9 | ⚠️ | pytest 8.x 仍支援但將淘汰 |
