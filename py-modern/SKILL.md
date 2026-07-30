---
name: py-modern
description: >
  Modernize Python projects and choose version-appropriate language features. Use for Python 3.12, 3.13, or 3.14 upgrades, PEP 695 generics, typing improvements, deferred annotations, template strings, free-threaded CPython, experimental JIT evaluation, deprecation cleanup, and migration from legacy syntax while preserving compatibility.
compatibility: Agent Skills-compatible. Inspect the target project's requires-python and CI matrix before using version-specific syntax.
metadata:
  author: stevenke1981
  version: "2.0.0"
  last-reviewed: "2026-07-30"
---

# Python 現代化與版本遷移

## 目標與邊界

用此 skill 升級 Python 版本、導入現代語法、改善 typing，並在不破壞既有行為的前提下移除過時寫法。

不要因為某功能存在於最新版 Python，就直接套用到最低版本較舊的專案。若任務主要是依賴、wheel、PyPI 或鎖定檔，改以 `py-packaging` 為主。

## 執行流程

1. **盤點版本契約**：讀取 `pyproject.toml`、`.python-version`、Dockerfile、CI matrix、type checker 與部署環境。
2. **建立行為基準**：先執行測試；缺少測試時，為公開 API、序列化格式與 CLI 行為補 characterization tests。
3. **選擇最低語法版本**：以實際 `requires-python` 為準，不以開發機版本為準。
4. **分批遷移**：先處理 deprecation 與相容性，再導入新語法，最後才評估 free-threaded 或 JIT。
5. **執行靜態與動態驗證**：至少執行 compile、lint、type check、test 與目標版本矩陣。
6. **記錄破壞性變更**：列出升級前置條件、回復方式與仍未驗證的第三方套件。

## 版本決策指南

| 功能 | 起始版本 | 使用原則 |
|---|---:|---|
| `match` / `case` | 3.10 | 僅在結構化模式比 `if/elif` 更清楚時使用 |
| `TaskGroup`, `ExceptionGroup` | 3.11 | 非同步工作優先讀 `py-async` |
| PEP 695 型別參數與 `type` alias | 3.12 | 套件若仍支援 3.11，不可直接採用 |
| PEP 701 f-string 文法 | 3.12 | 保持可讀性，不把複雜邏輯塞入 f-string |
| `typing.override` | 3.12 | 建議搭配 pyright 或 mypy 驗證 |
| `TypeIs`, `ReadOnly`, TypeVar defaults | 3.13 | 確認 type checker 已支援 |
| deferred annotations 新語意 | 3.14 | 升級時測試 runtime annotation introspection |
| template strings（t-strings） | 3.14 | 需要安全插值處理時才採用，不能把它當自動防注入 |
| multiple interpreters 標準 API | 3.14 | 先驗證 extension 與共享狀態相容性 |
| free-threaded CPython | 3.14 正式支援但仍為可選 build | 僅在依賴相容且 benchmark 證明有益時採用 |
| CPython JIT | 3.14 仍屬實驗性 | 不作為生產預設，也不宣稱必然加速 |

Python 3.15 預覽功能只能放在實驗分支或明確 opt-in，不得成為預設交付基準。

## 現代型別語法

### Python 3.12+ 泛型

```python
from collections.abc import Iterable


type Result[T] = tuple[T | None, Exception | None]


def first[T](items: Iterable[T]) -> T:
    for item in items:
        return item
    raise ValueError("items must not be empty")
```

若套件仍支援 Python 3.11，改用 `TypeVar` 與傳統 alias，不要在執行時用條件分支包住無法解析的新語法；舊直譯器會在載入檔案前就發生 `SyntaxError`。

### `override` 驗證繼承契約

```python
from typing import override


class BaseExporter:
    def export(self, value: object) -> str:
        raise NotImplementedError


class JsonExporter(BaseExporter):
    @override
    def export(self, value: object) -> str:
        import json

        return json.dumps(value, ensure_ascii=False)
```

## Python 3.14 遷移注意事項

### Deferred annotations

- 搜尋 `__annotations__`、`typing.get_type_hints()`、dataclass、Pydantic、ORM 與自製 decorator 的 runtime introspection。
- 不要假設 annotation 在函式定義當下已求值。
- 對 forward reference、區域名稱、decorator 執行順序與 import cycle 補測試。
- 升級前先更新依賴，再移除不再需要的 workaround。

### Free-threaded 執行環境

先辨識 build 與 runtime 狀態：

```python
import sys
import sysconfig


built_without_gil = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))
runtime_gil_enabled = (
    sys._is_gil_enabled() if hasattr(sys, "_is_gil_enabled") else True
)

print({
    "free_threaded_build": built_without_gil,
    "gil_enabled_now": runtime_gil_enabled,
})
```

導入前必須：

1. 確認 C extension、NumPy、資料庫 driver 與 native library 支援狀態。
2. 執行 thread sanitizer 或壓力測試可涵蓋的共享狀態。
3. 比較一般 build、free-threaded build、process pool 與 async I/O。
4. 若 extension 會重新啟用 GIL，清楚記錄並保留 fallback。

### Experimental JIT

- 只在可重現 benchmark 中測試。
- 同時記錄 interpreter build、環境變數、warm-up、輸入資料與 profiler 限制。
- 不把單一 microbenchmark 結果外推到整個應用。
- 生產部署預設保持關閉，除非專案已有明確驗證與回復方案。

## 遷移策略

### 應用程式

- 可一次提高最低 Python 版本，但先驗證作業系統、容器與部署平台。
- 鎖定依賴並建立完整回歸測試。
- 用 feature flag 隔離風險較高的新 runtime 功能。

### 可發布套件

- 先決定真正需要支援的最低版本。
- 使用 CI matrix 驗證每個宣告版本。
- 新語法必須與 wheel/sdist 的 `Requires-Python` 一致。
- 若要同時支援舊版，避免讓舊版 parser 看見新語法。

## 驗證命令

依專案工具調整：

```bash
python -m compileall src tests
ruff check .
ruff format --check .
pyright
pytest -q
```

多版本測試可使用 tox、nox、uv 或 CI matrix；不得只在目前 shell 的 Python 上驗證。

## 交付標準

- 明確列出升級前後的最低 Python 版本。
- 新語法與 `Requires-Python`、CI matrix 一致。
- runtime annotation、序列化與公開 API 行為已有回歸測試。
- free-threaded 或 JIT 方案附 benchmark、依賴相容性與 fallback。
- 沒有用未量測的倍數宣稱效能改善。
- 預覽功能均為 opt-in，且不影響穩定路徑。

## 延伸閱讀

- [完整範例](references/examples.md)
- [速查表](references/cheatsheet.md)
- [常見陷阱](references/pitfalls.md)
- [Python 3.14 What's New](https://docs.python.org/3/whatsnew/3.14.html)
- [Free-threaded Python HOWTO](https://docs.python.org/3/howto/free-threading-python.html)

## 版本相容性

| Python | 此 skill 的建議 |
|---|---|
| 3.14 | 穩定維護基準；free-threaded 可選，JIT 仍為實驗性 |
| 3.13 | 支援；free-threaded 屬較早階段，需更保守驗證 |
| 3.12 | 支援 PEP 695、PEP 701 與 `override` |
| 3.10–3.11 | 可協助遷移，但不得使用 3.12+ parser 語法 |
| 3.15 preview | 僅實驗與提前相容性測試，不作為生產基準 |
