# py-patterns — 完整範例

## 範例 1：Clean Architecture 分層結構

```python
"""
Clean Architecture — 領域層、應用層、基礎設施層
三層各自獨立，依賴方向從外向內
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID, uuid4

# ===== 領域層（Domain）— 純業務邏輯，無外部依賴 =====

@dataclass(frozen=True)
class OrderItem:
    """訂單項目（值物件）"""
    product_id: str
    quantity: int
    unit_price: int

    @property
    def subtotal(self) -> int:
        return self.quantity * self.unit_price

@dataclass
class Order:
    """訂單（實體）"""
    id: UUID = field(default_factory=uuid4)
    customer_id: str = ""
    items: list[OrderItem] = field(default_factory=list)
    status: str = "pending"

    @property
    def total(self) -> int:
        return sum(item.subtotal for item in self.items)

    def add_item(self, item: OrderItem) -> None:
        if self.status != "pending":
            raise ValueError("只能在 pending 狀態加入項目")
        self.items = [*self.items, item]  # 不可變式更新

    def confirm(self) -> None:
        if not self.items:
            raise ValueError("空訂單不能確認")
        self.status = "confirmed"

# ===== 應用層（Application）— 用例編排 =====

class OrderRepository(Protocol):
    def save(self, order: Order) -> None: ...
    def find_by_id(self, order_id: UUID) -> Order | None: ...

class EventPublisher(Protocol):
    def publish(self, event: str, payload: dict) -> None: ...

@dataclass
class CreateOrderUseCase:
    """建立訂單用例"""
    repo: OrderRepository
    events: EventPublisher

    def execute(self, customer_id: str, items: list[dict]) -> Order:
        order = Order(customer_id=customer_id)
        for item_data in items:
            order.add_item(OrderItem(**item_data))
        order.confirm()
        self.repo.save(order)
        self.events.publish("order.created", {"order_id": str(order.id)})
        return order

# ===== 基礎設施層（Infrastructure）— 具體實現 =====

class InMemoryOrderRepo:
    def __init__(self) -> None:
        self._store: dict[UUID, Order] = {}

    def save(self, order: Order) -> None:
        self._store[order.id] = order

    def find_by_id(self, order_id: UUID) -> Order | None:
        return self._store.get(order_id)

class ConsoleEventPublisher:
    def publish(self, event: str, payload: dict) -> None:
        print(f"[Event] {event}: {payload}")

# ===== 組裝與執行 =====
if __name__ == "__main__":
    use_case = CreateOrderUseCase(
        repo=InMemoryOrderRepo(),
        events=ConsoleEventPublisher(),
    )
    order = use_case.execute("customer-001", [
        {"product_id": "P1", "quantity": 2, "unit_price": 100},
        {"product_id": "P2", "quantity": 1, "unit_price": 250},
    ])
    print(f"訂單 {order.id} 總額: {order.total}")
```

---

## 範例 2：Observer + Event System

```python
"""
事件驅動系統 — 發布/訂閱模式
使用 callable 作為 handler，避免複雜的 Observer 類別
"""
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable

# 事件型別定義
@dataclass(frozen=True)
class UserRegistered:
    user_id: str
    email: str

@dataclass(frozen=True)
class OrderPlaced:
    order_id: str
    total: int

# 事件型別用 type alias
type Event = UserRegistered | OrderPlaced
type Handler = Callable[[Any], None]

class EventBus:
    """簡單的同步事件匯流排"""

    def __init__(self) -> None:
        self._handlers: dict[type, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, event: Event) -> None:
        for handler in self._handlers.get(type(event), []):
            handler(event)

    def subscriber(self, event_type: type) -> Callable[[Handler], Handler]:
        """裝飾器版訂閱"""
        def decorator(handler: Handler) -> Handler:
            self.subscribe(event_type, handler)
            return handler
        return decorator

# 使用
bus = EventBus()

@bus.subscriber(UserRegistered)
def send_welcome_email(event: UserRegistered) -> None:
    print(f"寄送歡迎信到 {event.email}")

@bus.subscriber(UserRegistered)
def init_user_profile(event: UserRegistered) -> None:
    print(f"初始化使用者 {event.user_id} 的個人檔案")

@bus.subscriber(OrderPlaced)
def notify_warehouse(event: OrderPlaced) -> None:
    print(f"通知倉庫出貨: 訂單 {event.order_id}")

if __name__ == "__main__":
    bus.publish(UserRegistered(user_id="U001", email="alice@example.com"))
    bus.publish(OrderPlaced(order_id="ORD-100", total=450))
```

---

## 範例 3：Decorator Pattern（包裝器鏈）

```python
"""
裝飾器模式 — 用組合取代繼承
動態添加功能（日誌、快取、重試）
"""
from typing import Protocol
from dataclasses import dataclass
from functools import lru_cache
import time

class DataFetcher(Protocol):
    def fetch(self, key: str) -> str: ...

class RealFetcher:
    """真正的資料取得邏輯"""
    def fetch(self, key: str) -> str:
        time.sleep(0.1)  # 模擬 I/O
        return f"data-for-{key}"

@dataclass
class LoggingFetcher:
    """加入日誌的包裝器"""
    inner: DataFetcher

    def fetch(self, key: str) -> str:
        print(f"[LOG] 開始取得: {key}")
        result = self.inner.fetch(key)
        print(f"[LOG] 完成取得: {key}")
        return result

@dataclass
class CachingFetcher:
    """加入快取的包裝器"""
    inner: DataFetcher

    def __post_init__(self) -> None:
        self._cache: dict[str, str] = {}

    def fetch(self, key: str) -> str:
        if key not in self._cache:
            self._cache[key] = self.inner.fetch(key)
        return self._cache[key]

@dataclass
class RetryFetcher:
    """加入重試的包裝器"""
    inner: DataFetcher
    max_retries: int = 3

    def fetch(self, key: str) -> str:
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                return self.inner.fetch(key)
            except Exception as e:
                last_error = e
                print(f"[RETRY] 第 {attempt + 1} 次失敗: {e}")
        raise RuntimeError(f"重試 {self.max_retries} 次後失敗") from last_error

# 組合：像套娃一樣層層包裝
if __name__ == "__main__":
    fetcher: DataFetcher = LoggingFetcher(
        inner=CachingFetcher(
            inner=RetryFetcher(
                inner=RealFetcher()
            )
        )
    )
    print(fetcher.fetch("user-42"))
    print(fetcher.fetch("user-42"))  # 第二次命中快取
```

---

## 範例 4：Result 模式（無例外錯誤處理）

```python
"""
Result 模式 — 用型別安全的 Result 取代例外
適合預期中的業務錯誤（非程式 bug）
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")

@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T

    def is_ok(self) -> bool:
        return True

    def unwrap(self) -> T:
        return self.value

@dataclass(frozen=True)
class Err:
    message: str
    code: str = "UNKNOWN"

    def is_ok(self) -> bool:
        return False

    def unwrap(self) -> None:
        raise RuntimeError(f"Unwrap on Err: {self.code} — {self.message}")

type Result[T] = Ok[T] | Err

# 使用 Result 的業務邏輯
def parse_age(value: str) -> Result[int]:
    """解析年齡字串，回傳 Ok 或 Err"""
    try:
        age = int(value)
    except ValueError:
        return Err(f"'{value}' 不是有效數字", code="INVALID_FORMAT")

    if age < 0 or age > 150:
        return Err(f"年齡 {age} 超出合理範圍", code="OUT_OF_RANGE")

    return Ok(age)

def validate_registration(name: str, age_str: str) -> Result[dict]:
    """組合多個 Result 驗證"""
    if not name.strip():
        return Err("姓名不能為空", code="EMPTY_NAME")

    age_result = parse_age(age_str)
    if not age_result.is_ok():
        return age_result  # type: ignore[return-value]

    return Ok({"name": name.strip(), "age": age_result.unwrap()})

if __name__ == "__main__":
    # 成功案例
    match validate_registration("Alice", "25"):
        case Ok(value):
            print(f"註冊成功: {value}")
        case Err(message=msg, code=code):
            print(f"錯誤 [{code}]: {msg}")

    # 失敗案例
    match validate_registration("Bob", "abc"):
        case Ok(value):
            print(f"註冊成功: {value}")
        case Err(message=msg, code=code):
            print(f"錯誤 [{code}]: {msg}")
```

---

## 範例 5：Plugin / Registry 自動發現

```python
"""
Plugin Registry — 裝飾器自動註冊 + 動態發現
適合 CLI 子命令、序列化格式、資料匯入匯出等
"""
from typing import Protocol, ClassVar
from dataclasses import dataclass

class Exporter(Protocol):
    format_name: ClassVar[str]
    def export(self, data: list[dict]) -> str: ...

# 全域 registry
_EXPORTERS: dict[str, type[Exporter]] = {}

def register_exporter(cls: type[Exporter]) -> type[Exporter]:
    """裝飾器：自動將 Exporter 註冊到 registry"""
    _EXPORTERS[cls.format_name] = cls
    return cls

@register_exporter
class CsvExporter:
    format_name = "csv"

    def export(self, data: list[dict]) -> str:
        if not data:
            return ""
        headers = list(data[0].keys())
        lines = [",".join(headers)]
        for row in data:
            lines.append(",".join(str(row.get(h, "")) for h in headers))
        return "\n".join(lines)

@register_exporter
class JsonExporter:
    format_name = "json"

    def export(self, data: list[dict]) -> str:
        import json
        return json.dumps(data, ensure_ascii=False, indent=2)

@register_exporter
class MarkdownExporter:
    format_name = "markdown"

    def export(self, data: list[dict]) -> str:
        if not data:
            return ""
        headers = list(data[0].keys())
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ]
        for row in data:
            lines.append("| " + " | ".join(str(row.get(h, "")) for h in headers) + " |")
        return "\n".join(lines)

# 工廠函式
def get_exporter(format_name: str) -> Exporter:
    cls = _EXPORTERS.get(format_name)
    if cls is None:
        available = ", ".join(sorted(_EXPORTERS.keys()))
        raise ValueError(f"不支援的格式: {format_name}（可用: {available}）")
    return cls()

def list_exporters() -> list[str]:
    return sorted(_EXPORTERS.keys())

if __name__ == "__main__":
    sample_data = [
        {"name": "Alice", "age": 30, "city": "Taipei"},
        {"name": "Bob", "age": 25, "city": "Tokyo"},
    ]

    print(f"可用格式: {list_exporters()}")
    for fmt in list_exporters():
        exporter = get_exporter(fmt)
        print(f"\n=== {fmt.upper()} ===")
        print(exporter.export(sample_data))
```
