---
name: py-testing
description: >
  Design, implement, and repair Python test suites with pytest, fixtures, parametrization, mocks, fakes, property-based testing, async tests, integration tests, contract tests, coverage, flaky-test diagnosis, and CI quality gates. Use when adding tests, reviewing test architecture, reproducing bugs, validating migrations, or making Python behavior deterministic and regression-safe.
compatibility: Agent Skills-compatible. pytest 9 supports Python 3.10+; inspect the project's pinned pytest and plugin versions before using newer APIs.
metadata:
  author: stevenke1981
  version: "2.0.1"
  last-reviewed: "2026-09-07"
---

# Python 測試工程

## 目標與邊界

用此 skill 建立快速、穩定、能說明行為契約的測試。測試重點是防止有意義的回歸，不是追求單一 coverage 百分比或對每一行實作做鏡像斷言。

若任務主要是實作功能，仍以對應領域 skill 為主，`py-testing` 負責測試策略與品質閘門。

## 執行流程

1. **先重現問題或行為**：建立最小失敗案例，記錄輸入、環境與期望。
2. **辨識測試層級**：unit、component、integration、contract、end-to-end 或 performance。
3. **選擇穩定邊界**：優先測 public behavior；只有必要時才測內部細節。
4. **控制非決定性**：時間、亂數、網路、檔案、環境變數、locale、timezone 與並行。
5. **建立代表性案例**：正常、邊界、錯誤、空值、極端值、權限與故障注入。安裝器另測真正封裝產物、Unicode 路徑、dry-run 零寫入，以及部分寫入失敗後的回復。
6. **執行最小到完整套件**：先單一測試，再目錄，最後完整 CI matrix。
7. **檢查測試品質**：避免過度 mock、共享狀態、順序依賴與無條件重跑。
8. **回報驗證範圍**：列出執行命令、通過結果、未覆蓋環境與已知限制。

## 測試層級

| 層級 | 驗證內容 | 典型特性 |
|---|---|---|
| Unit | 純函式、domain rule、parser | 快、隔離、數量多 |
| Component | 一個模組或 service + fake boundary | 驗證協作但仍可控 |
| Integration | DB、filesystem、message broker、HTTP adapter | 真實依賴與 lifecycle |
| Contract | client/server、schema、provider adapter | 防止介面漂移 |
| End-to-end | 完整使用者流程 | 數量少、成本高 |
| Property-based | 不變量與廣泛輸入空間 | 找到人工案例之外的錯誤 |
| Performance | 延遲、吞吐、記憶體回歸 | 需穩定環境與統計方法 |

不要把所有測試都做成 E2E，也不要用 mock 讓 integration test 失去整合意義。

## pytest 基本設定

```toml
[tool.pytest.ini_options]
addopts = ["-ra", "--strict-config", "--strict-markers"]
testpaths = ["tests"]
xfail_strict = true
markers = [
  "integration: requires real infrastructure or service fixtures",
  "slow: intentionally slower validation",
]
```

`strict` 模式可提早發現拼錯 marker 或設定。CI 不應依賴開發者本機自動載入的未知 plugin。

## 清楚的行為測試

```python
import pytest


def calculate_discount(total: int, rate: float) -> int:
    if total < 0:
        raise ValueError("total must be non-negative")
    if not 0.0 <= rate <= 1.0:
        raise ValueError("rate must be between 0 and 1")
    return round(total * rate)


@pytest.mark.parametrize(
    ("total", "rate", "expected"),
    [
        (1_000, 0.1, 100),
        (0, 0.5, 0),
        (999, 0.0, 0),
    ],
)
def test_calculate_discount(
    total: int,
    rate: float,
    expected: int,
) -> None:
    assert calculate_discount(total, rate) == expected


@pytest.mark.parametrize(
    ("total", "rate"),
    [(-1, 0.1), (100, -0.1), (100, 1.1)],
)
def test_calculate_discount_rejects_invalid_input(
    total: int,
    rate: float,
) -> None:
    with pytest.raises(ValueError):
        calculate_discount(total, rate)
```

斷言 observable outcome、exception type 與必要訊息，不要對每一步內部呼叫順序做脆弱斷言。

## Fixture 設計

- fixture 只負責建立可重用測試資源，不隱藏主要 Arrange 行為。
- scope 越大，共享狀態與順序依賴風險越高。
- resource fixture 使用 `yield` 確保 teardown。
- factory fixture 適合產生多種資料，但要有明確型別。
- 使用 `tmp_path`、`monkeypatch` 與 framework 提供的 lifecycle fixture。
- 不在 import time 建立資料庫、client 或 event loop。

```python
from collections.abc import Callable
from dataclasses import dataclass

import pytest


@dataclass(frozen=True, slots=True)
class User:
    name: str
    active: bool


@pytest.fixture
def user_factory() -> Callable[..., User]:
    def make_user(
        *,
        name: str = "Alice",
        active: bool = True,
    ) -> User:
        return User(name=name, active=active)

    return make_user
```

## Mock、Fake 與 Stub

### 優先順序

1. 純值與真實 domain object
2. 小型 in-memory fake
3. local test server / containerized dependency
4. mock 外部邊界

規則：

- patch 使用物件被查找的位置，不是原始定義位置。
- mock clock、random、HTTP transport、email sender 等 boundary。
- 不 mock 被測函式自己的核心邏輯。
- 對重要 adapter 增加 contract test，防止 fake 與真實服務漂移。
- 使用 autospec/spec_set 可降低不存在屬性的假通過，但仍不能取代 integration test。

## 時間、亂數與環境

- 將 clock 與 random generator 注入，而不是到處呼叫全域函式。
- 測試固定 timezone 與 locale，並加入 DST/日期邊界案例。
- 使用 seeded randomness，但失敗時輸出 seed。
- 每個測試自行設定環境變數並復原。
- 不依賴目前工作目錄、使用者家目錄或測試執行順序。

## Async 測試

- 使用與專案相容的 async pytest plugin 或測試 runner。
- 每個測試結束檢查未完成 task、未關閉 client 與 resource warning。
- 不用真實 `sleep()` 等待背景工作；使用 event、queue 或可控 clock。
- 測 cancellation、timeout、partial failure、slow consumer 與 graceful shutdown。
- 對 client disconnect 驗證上游工作真的取消。

```python
import asyncio

import pytest


@pytest.mark.asyncio
async def test_worker_honors_cancellation() -> None:
    started = asyncio.Event()

    async def worker() -> None:
        started.set()
        await asyncio.Future()

    task = asyncio.create_task(worker())
    await started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
```

plugin marker/mode 依鎖定版本設定，不要複製不相容的網路範例。

## Property-based Testing

適合：

- parser/serializer round trip
- 排序、去重與集合不變量
- 金額、日期與區間邊界
- protocol frame 與 malformed input
- schema migration

範例不變量：

- encode 後 decode 等於原始資料。
- normalize 執行兩次等於一次。
- filter 不會增加列數。
- 聚合後總額與來源 reconciliation 一致。

保留 framework 回報的最小反例，並在修復後加入 regression case。

## Integration 與 Contract Tests

- 使用 ephemeral database/schema、temporary directory 或受控 container。
- migration 從空資料庫與前一正式版本都要測。
- HTTP 測 status、headers、schema、auth、timeout 與 retry，而不只 body happy path。
- provider adapter 對 request/response mapping 建立 contract fixtures。
- 測試資料不得包含真實 token、個資或生產快照中的機密。
- live external test 應 opt-in，且有成本與速率限制。

## Flaky Test 處理

不要直接加入 rerun 後忽略。

1. 收集失敗 seed、順序、worker、OS、Python、時區與資源資訊。
2. 單獨重跑並使用隨機順序重現。
3. 檢查共享狀態、固定 port、真實時間、thread/task leak 與 eventual consistency。
4. 修正同步條件或隔離資源。
5. 若必須 quarantine，設定 owner、原因與到期日。

## Coverage 與品質閘門

- 使用 branch coverage，但不要只追求單一百分比。
- 高風險 path、錯誤處理與權限邊界比簡單 getter 更重要。
- 新 bug 必須先有失敗 regression test。
- 可對核心純邏輯使用 mutation testing 評估斷言強度。
- 慢測試分類並定期執行，不要永久從 CI 消失。

常用命令：

```bash
pytest -q
pytest tests/unit -q
pytest -m "not slow" -q
pytest --cov=src --cov-branch --cov-report=term-missing
```

## 交付標準

- 測試驗證 public behavior 與重要不變量，不鏡像實作細節。
- 時間、亂數、網路、檔案與環境等非決定性已受控。
- fixture 有清楚 scope、型別與 teardown。
- mock 限於 boundary，重要 adapter 有 integration/contract test。
- async 測試涵蓋取消、逾時與資源關閉。
- flaky test 有根因處理，不以無限 rerun 掩蓋。
- CI 命令、marker、coverage 與支援 Python matrix 已記錄。
- 測試失敗能提供可重現的輸入與環境資訊。

## 延伸閱讀

- [完整範例](references/examples.md)
- [速查表](references/cheatsheet.md)
- [常見陷阱](references/pitfalls.md)
- [pytest documentation](https://docs.pytest.org/en/stable/)

## 版本相容性

| 環境 | 建議 |
|---|---|
| Python 3.14 | 穩定維護基準；確認 coverage、async 與 native plugin |
| Python 3.10–3.13 | 支援；依 pytest/plugin lockfile 選 API |
| pytest 9.x | Python 3.10+；升級時檢查 collection 與 plugin 相容性 |
| 舊 pytest | 先讀 changelog/deprecations，不直接套用 9.x 設定 |
| Preview Python | 只作 compatibility job，不取代穩定 CI |
