# py-patterns — 速查表

## SOLID 原則速查

| 原則 | 關鍵字 | Python 做法 | 反面教材 |
|------|--------|-------------|---------|
| **S** 單一職責 | 一個類別一個理由改 | 每 class < 200 行，拆 service/repo | God class 什麼都做 |
| **O** 開放封閉 | 擴充不改既有碼 | Protocol + registry | `if type == "X"` 串 |
| **L** 里氏替換 | 子型別可替換父型別 | 遵守 Protocol 簽名 | 子類 raise NotImplementedError |
| **I** 介面隔離 | 不強迫實作用不到的 | 多個小 Protocol | 一個巨大 ABC |
| **D** 依賴反轉 | 依賴抽象不依賴具體 | 建構子注入 Protocol | 直接 import 具體類別 |

## Protocol vs ABC 決策表

| 情境 | 選擇 | 原因 |
|------|------|------|
| 跨套件/跨團隊介面 | `Protocol` | 結構化子型別（structural），不需 import |
| 需要預設實作 / 模板方法 | `ABC` | 可定義 concrete method + abstract method |
| 第三方類別適配 | `Protocol` | 不需修改第三方原始碼 |
| 框架 plugin 合約 | `ABC` | 強制子類顯式繼承，IDE 提示更完整 |
| 純 type checker 用途 | `Protocol` | runtime_checkable 可選 |
| 需要 `isinstance()` 檢查 | `ABC`（天生支援）或 `Protocol` + `@runtime_checkable` | |

## 常見 GoF 模式 Python 版

### Creational

| 模式 | Python 慣用替代 | 範例 |
|------|-----------------|------|
| Singleton | 模組層級實例 | `_instance = MyService()` 在模組直接建立 |
| Factory Method | `dict[str, Callable]` registry | `FACTORIES = {"csv": CsvParser, "json": JsonParser}` |
| Builder | `@dataclass` + 鏈式方法 | `Builder().with_x(1).with_y(2).build()` |
| Prototype | `copy.deepcopy()` / `dataclass.replace()` | `new_obj = replace(old, name="new")` |

### Structural

| 模式 | Python 慣用替代 | 範例 |
|------|-----------------|------|
| Adapter | Protocol + wrapper class | `class LegacyAdapter: def fetch(self): return self.old.get_data()` |
| Decorator | 函式裝飾器 `@` 或 wrapper class | `@retry(3)` / `LoggingFetcher(inner)` |
| Facade | 模組層級函式 | `def send_email(to, body): ...` 包裝 SMTP 細節 |
| Proxy | `__getattr__` 委派 | LazyProxy 延遲載入 |

### Behavioral

| 模式 | Python 慣用替代 | 範例 |
|------|-----------------|------|
| Strategy | 函式參數 / Protocol | `def sort(data, *, key=None)` |
| Observer | Callback list / Event bus | `bus.subscribe(EventType, handler)` |
| Command | `Callable` + 閉包 | `commands: list[Callable]` |
| Template Method | ABC + hook methods | `class Pipeline(ABC): @abstractmethod def transform()` |
| Iterator | `__iter__` / `__next__` / generator | `yield from items` |
| State | Enum + match-case | `match state: case State.ACTIVE: ...` |

## Dependency Injection 模式

```python
# 1. 建構子注入（最推薦）
@dataclass
class OrderService:
    repo: OrderRepository       # Protocol 型別
    notifier: Notifier          # Protocol 型別

# 2. 工廠函式組裝（Application Root）
def create_order_service() -> OrderService:
    return OrderService(
        repo=PostgresOrderRepo(db_url=os.environ["DB_URL"]),
        notifier=EmailNotifier(smtp_host="..."),
    )
```

## Dataclass 選項速查

```python
from dataclasses import dataclass, field, replace

@dataclass                      # 可變，自動 __init__, __repr__, __eq__
@dataclass(frozen=True)         # 不可變（hashable），適合值物件
@dataclass(slots=True)          # 省記憶體，Python 3.10+
@dataclass(kw_only=True)        # 全部參數 keyword-only，Python 3.10+

# field() 選項
age: int = field(default=0)
items: list = field(default_factory=list)  # 可變預設值必用 factory
_cache: dict = field(default_factory=dict, repr=False, compare=False)

# 不可變更新
new_obj = replace(old_obj, name="new_name")
```

## Protocol 定義模板

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Readable(Protocol):
    def read(self, n: int = -1) -> bytes: ...

class Closable(Protocol):
    def close(self) -> None: ...

# 組合多個小 Protocol
class ReadableClosable(Readable, Closable, Protocol): ...
```

## Repository Pattern 模板

```python
from typing import Protocol, TypeVar, Generic
from uuid import UUID

T = TypeVar("T")

class Repository(Protocol[T]):
    def find_by_id(self, id: UUID) -> T | None: ...
    def find_all(self) -> list[T]: ...
    def save(self, entity: T) -> None: ...
    def delete(self, id: UUID) -> None: ...
```

## Descriptor Protocol

```python
class Validated:
    """資料描述器 — 自動驗證欄位值"""
    def __init__(self, min_val: int, max_val: int) -> None:
        self.min_val = min_val
        self.max_val = max_val

    def __set_name__(self, owner: type, name: str) -> None:
        self.attr_name = f"_{name}"

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self.attr_name, self.min_val)

    def __set__(self, obj, value: int) -> None:
        if not self.min_val <= value <= self.max_val:
            raise ValueError(f"{value} 不在 [{self.min_val}, {self.max_val}] 範圍")
        setattr(obj, self.attr_name, value)
```

## 常用工具比較

| 工具 | 值物件 | 驗證 | JSON | 效能 |
|------|--------|------|------|------|
| `dataclasses` | ✅ frozen | ❌ 需手寫 | ❌ 需手寫 | ⭐⭐⭐ 最快 |
| `pydantic` | ✅ frozen | ✅ 內建 | ✅ 內建 | ⭐⭐ C 擴展 |
| `attrs` | ✅ frozen | ✅ validators | ❌ 需 cattrs | ⭐⭐⭐ 快 |
| `NamedTuple` | ✅ 天生不可變 | ❌ | ❌ | ⭐⭐⭐ |
