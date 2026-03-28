---
name: py-modern
description: >
  Python 3.12+ and 3.13+ modern syntax, features, and best practices.
  Trigger when user mentions match-case, structural pattern matching,
  type hints, PEP 695, type parameter syntax, f-string improvements,
  GIL-free, free-threaded Python, PEP 701, modern Python syntax,
  Python 3.12 new features, Python 3.13 new features, type alias,
  TypeVar new syntax, walrus operator, exception groups.
  Also trigger when user asks about upgrading to Python 3.12+,
  migrating legacy code to modern Python, or writing idiomatic
  modern Python.
---

# Python 3.12+ / 3.13+ 現代語法與特性

## Quick Start（30 秒上手）

```python
# Python 3.12+ 新型態參數語法（PEP 695）
type Point = tuple[float, float]

def first[T](items: list[T]) -> T:
    """回傳列表中的第一個元素"""
    return items[0]

class Stack[T]:
    """泛型堆疊"""
    def __init__(self) -> None:
        self._items: list[T] = []

    def push(self, item: T) -> None:
        self._items.append(item)

    def pop(self) -> T:
        return self._items.pop()

stack = Stack[int]()
stack.push(42)
print(first([1, 2, 3]))  # 1
```

## 核心概念

### 1. PEP 695 — 型別參數語法（Python 3.12+）

取代冗長的 `TypeVar` 宣告，新語法更簡潔，且 variance 自動推斷。

```python
# 舊方式（3.11 以前）
from typing import TypeVar, Generic
_T = TypeVar("_T")
class Container(Generic[_T]):
    def get(self) -> _T: ...

# 新方式（3.12+）——無需匯入 TypeVar 或 Generic
class Container[T]:
    def get(self) -> T: ...

# 泛型函式
def max_item[T: (int, float, str)](items: list[T]) -> T:
    return max(items)

# 泛型型別別名
type ListOrSet[T] = list[T] | set[T]
```

### 2. PEP 701 — f-string 完整解放（Python 3.12+）

f-string 現在是正式文法的一部分，解除所有舊限制。

```python
# 可在 f-string 內使用相同引號
songs = ["Eden", "Alkaline"]
print(f"Playlist: {", ".join(songs)}")

# 多行表達式 + 註解
result = f"Total: {
    sum([1, 2, 3])  # 這裡可以放註解
}"

# 反斜線與 Unicode 跳脫
print(f"Songs:\n{"\n".join(songs)}")
print(f"Heart: {"\N{BLACK HEART SUIT}"}")
```

### 3. Structural Pattern Matching（Python 3.10+，持續進化）

match-case 是 Python 的模式比對語法，類似其他語言的 switch-case 但更強大。

```python
from dataclasses import dataclass

@dataclass
class Point:
    x: float
    y: float

def describe(obj: object) -> str:
    """使用 match-case 做結構化模式比對"""
    match obj:
        case Point(x=0, y=0):
            return "原點"
        case Point(x, y) if x == y:
            return f"對角線上 ({x}, {y})"
        case Point(x, y):
            return f"點 ({x}, {y})"
        case [*items] if len(items) > 3:
            return f"長序列，共 {len(items)} 項"
        case {"action": "buy", "item": str(name)}:
            return f"購買 {name}"
        case _:
            return "未知"
```

### 4. Free-threaded Python / GIL-free（Python 3.13+，實驗性）

Python 3.13 引入實驗性的 free-threaded 模式（PEP 703），允許真正的多執行緒並行。

```python
import sys
import threading

# 檢查是否為 free-threaded 版本
if hasattr(sys, "_is_gil_enabled"):
    print(f"GIL 啟用: {sys._is_gil_enabled()}")

# 在 free-threaded 模式下，多執行緒可真正平行執行
def cpu_work(n: int) -> int:
    """CPU 密集任務"""
    return sum(i * i for i in range(n))

threads: list[threading.Thread] = []
for _ in range(4):
    t = threading.Thread(target=cpu_work, args=(10_000_000,))
    threads.append(t)
    t.start()
for t in threads:
    t.join()
```

### 5. typing 模組新增特性

```python
from typing import TypeIs, ReadOnly, TypedDict, override, deprecated
from warnings import deprecated as warn_deprecated

# PEP 742: TypeIs（3.13+）——更直覺的型別窄化
def is_str_list(val: list[object]) -> TypeIs[list[str]]:
    return all(isinstance(x, str) for x in val)

# PEP 705: ReadOnly TypedDict（3.13+）
class Config(TypedDict):
    name: str
    debug: ReadOnly[bool]  # 型別檢查器會禁止修改

# PEP 698: @override 裝飾器（3.12+）
class Base:
    def method(self) -> None: ...

class Child(Base):
    @override
    def method(self) -> None:  # 若父類別無此方法會報錯
        ...

# PEP 702: @deprecated（3.13+）
@warn_deprecated("使用 new_func() 代替")
def old_func() -> None: ...
```

## 實戰 Patterns

### Pattern 1: 用新語法重寫泛型容器

**場景**：需要定義型別安全的泛型容器
**程式碼**：

```python
from collections.abc import Iterator

class Registry[K, V]:
    """型別安全的註冊表"""
    def __init__(self) -> None:
        self._store: dict[K, V] = {}

    def register(self, key: K, value: V) -> None:
        self._store[key] = value

    def get(self, key: K) -> V | None:
        return self._store.get(key)

    def __iter__(self) -> Iterator[tuple[K, V]]:
        yield from self._store.items()

# 使用
reg = Registry[str, int]()
reg.register("age", 30)
```

**注意**：PEP 695 語法不能與傳統 `TypeVar` 混用。

### Pattern 2: copy.replace() 不可變更新（3.13+）

**場景**：建立不可變物件的修改副本
**程式碼**：

```python
from copy import replace
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    host: str = "localhost"
    port: int = 8080
    debug: bool = False

# 建立修改副本，原物件不變
base = Settings()
dev = replace(base, debug=True, port=3000)
print(dev)  # Settings(host='localhost', port=3000, debug=True)
```

**注意**：自定義類別需實作 `__replace__()` 方法。

### Pattern 3: TypeVar 預設值（3.13+）

**場景**：泛型參數需要預設型別

```python
from typing import TypeVar

# PEP 696: TypeVar 支援預設值（3.13+）
T = TypeVar("T", default=int)

class Container[T = int]:
    def __init__(self, value: T) -> None:
        self.value = value

c1 = Container(42)      # Container[int]
c2 = Container("hello") # Container[str]
```

## 工具鏈推薦

| 工具 | 用途 | 安裝 | 備註 |
|------|------|------|------|
| ruff | Linter + Formatter | `pip install ruff` | 取代 black + isort + flake8 |
| mypy | 靜態型別檢查 | `pip install mypy` | 支援所有新語法 |
| pyright | 型別檢查 (LSP) | `pip install pyright` | 由 Microsoft 維護，速度快 |
| basedpyright | 增強版 pyright | `pip install basedpyright` | 更嚴格的檢查 |
| uv | 套件管理器 | `pip install uv` | 極速套件安裝與虛擬環境 |

## 延伸閱讀

讀取 `references/` 目錄下的對應檔案：
- `references/examples.md` — 完整可運行範例
- `references/cheatsheet.md` — 速查表
- `references/pitfalls.md` — 常見錯誤與解法

## 版本相容性

| Python 版本 | 支援狀態 | 備註 |
|-------------|----------|------|
| 3.13+ | ✅ 完整支援 | free-threaded, TypeIs, ReadOnly, TypeVar defaults, JIT |
| 3.12 | ✅ 完整支援 | PEP 695 型別參數語法, PEP 701 f-string, @override |
| 3.11 | ⚠️ 部分 | ExceptionGroup, match-case (3.10+), 無新型別語法 |
| 3.10 | ⚠️ 基礎 | match-case, `X | Y` union 語法 |
