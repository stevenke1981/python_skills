---
name: py-patterns
description: >
  Python design patterns, SOLID principles, and clean architecture guidance.
  Trigger when user mentions design patterns, SOLID, dependency injection,
  repository pattern, clean architecture, factory pattern, strategy pattern,
  observer pattern, singleton, decorator pattern, hexagonal architecture,
  ports and adapters, domain-driven design, inversion of control,
  abstract factory, or Pythonic patterns.
  Also trigger when user asks about structuring large Python projects,
  decoupling modules, or applying GoF patterns in Python.
---

# Python 設計模式與架構

## Quick Start（30 秒上手）

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

# Strategy Pattern — 用 Protocol 或 ABC 定義策略介面
class Compressor(ABC):
    @abstractmethod
    def compress(self, data: bytes) -> bytes: ...

class GzipCompressor(Compressor):
    def compress(self, data: bytes) -> bytes:
        import gzip
        return gzip.compress(data)

class NoopCompressor(Compressor):
    def compress(self, data: bytes) -> bytes:
        return data

@dataclass(frozen=True)
class FileProcessor:
    compressor: Compressor  # 依賴注入

    def process(self, data: bytes) -> bytes:
        return self.compressor.compress(data)

# 使用
processor = FileProcessor(compressor=GzipCompressor())
result = processor.process(b"hello world")
```

## 核心概念

### 1. SOLID 原則

| 原則 | 說明 | Python 實踐 |
|------|------|-------------|
| **S** — 單一職責 | 一個類別只有一個變更理由 | 拆分大模組、每個類別 < 200 行 |
| **O** — 開放封閉 | 對擴展開放、對修改封閉 | Protocol / ABC + 策略注入 |
| **L** — 里氏替換 | 子類別可完全替換父類別 | 遵守 ABC 契約、不強化前置條件 |
| **I** — 介面隔離 | 客戶端不依賴不需要的方法 | 小而專注的 Protocol |
| **D** — 依賴反轉 | 高層模組依賴抽象而非實作 | 建構子注入、Protocol 作型別提示 |

### 2. Protocol vs ABC

```python
from typing import Protocol, runtime_checkable

# Protocol — 結構子型態（鴨子型別 + 靜態檢查）
@runtime_checkable
class Repository(Protocol):
    def find_by_id(self, id: str) -> dict | None: ...
    def save(self, entity: dict) -> None: ...

# ABC — 名義子型態（強制繼承）
from abc import ABC, abstractmethod

class BaseRepository(ABC):
    @abstractmethod
    def find_by_id(self, id: str) -> dict | None: ...

    @abstractmethod
    def save(self, entity: dict) -> None: ...

    def exists(self, id: str) -> bool:
        """提供預設實現"""
        return self.find_by_id(id) is not None
```

**選擇指南**：
- 跨套件邊界 → Protocol（不強制繼承關係）
- 需要共享預設實現 → ABC
- 需要 `isinstance` 檢查 → `@runtime_checkable` Protocol 或 ABC

### 3. 依賴注入（DI）

```python
from dataclasses import dataclass, field
from typing import Protocol

class EmailSender(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...

class SMTPSender:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port

    def send(self, to: str, subject: str, body: str) -> None:
        print(f"SMTP → {to}: {subject}")

class ConsoleSender:
    def send(self, to: str, subject: str, body: str) -> None:
        print(f"[Console] {to}: {subject}\n{body}")

@dataclass
class NotificationService:
    sender: EmailSender  # 注入抽象，不是具體類別

    def notify_user(self, email: str, message: str) -> None:
        self.sender.send(email, "通知", message)

# 生產環境
service = NotificationService(sender=SMTPSender("smtp.example.com", 587))
# 測試環境
service = NotificationService(sender=ConsoleSender())
```

### 4. 不可變資料物件

```python
from dataclasses import dataclass, replace

@dataclass(frozen=True)
class Money:
    amount: int
    currency: str = "TWD"

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError(f"幣別不同: {self.currency} vs {other.currency}")
        return replace(self, amount=self.amount + other.amount)

price = Money(100, "TWD")
total = price.add(Money(50, "TWD"))  # Money(amount=150, currency='TWD')
# price 不被修改 — 不可變
```

### 5. 值物件與實體

```python
from dataclasses import dataclass, field
from uuid import UUID, uuid4

# 值物件 — 以值相等性判斷，不可變
@dataclass(frozen=True)
class Address:
    street: str
    city: str
    zip_code: str

# 實體 — 以 id 判斷相等性
@dataclass
class User:
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    address: Address | None = None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, User):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
```

## 實戰 Patterns

### Pattern 1: Repository（資料存取層）

**場景**：將資料存取邏輯與業務邏輯解耦。

```python
from typing import Protocol
from dataclasses import dataclass

@dataclass(frozen=True)
class Product:
    id: str
    name: str
    price: int

class ProductRepository(Protocol):
    def find_by_id(self, product_id: str) -> Product | None: ...
    def find_all(self) -> list[Product]: ...
    def save(self, product: Product) -> None: ...
    def delete(self, product_id: str) -> None: ...

class InMemoryProductRepo:
    """記憶體實現 — 用於測試"""
    def __init__(self) -> None:
        self._store: dict[str, Product] = {}

    def find_by_id(self, product_id: str) -> Product | None:
        return self._store.get(product_id)

    def find_all(self) -> list[Product]:
        return list(self._store.values())

    def save(self, product: Product) -> None:
        self._store[product.id] = product

    def delete(self, product_id: str) -> None:
        self._store.pop(product_id, None)
```

**注意**：Repository 只處理持久化邏輯，不包含業務規則。

### Pattern 2: Strategy（策略）

**場景**：根據不同條件選擇不同演算法。

```python
from typing import Protocol, Callable

class DiscountStrategy(Protocol):
    def calculate(self, price: int) -> int: ...

class NoDiscount:
    def calculate(self, price: int) -> int:
        return price

class PercentageDiscount:
    def __init__(self, percent: int) -> None:
        self._percent = percent

    def calculate(self, price: int) -> int:
        return price - (price * self._percent // 100)

# Pythonic 替代：直接用函式
type DiscountFn = Callable[[int], int]

def no_discount(price: int) -> int:
    return price

def make_percentage_discount(percent: int) -> DiscountFn:
    def _discount(price: int) -> int:
        return price - (price * percent // 100)
    return _discount
```

**注意**：Python 中簡單策略用函式和閉包更簡潔，複雜策略用類別。

### Pattern 3: Factory / Registry

**場景**：根據字串或 enum 動態建立物件。

```python
from typing import Protocol
from enum import StrEnum

class Serializer(Protocol):
    def serialize(self, data: dict) -> str: ...

class JsonSerializer:
    def serialize(self, data: dict) -> str:
        import json
        return json.dumps(data)

class YamlSerializer:
    def serialize(self, data: dict) -> str:
        import yaml
        return yaml.dump(data)

class Format(StrEnum):
    JSON = "json"
    YAML = "yaml"

# Registry Pattern — 用字典取代 if/elif 鏈
_REGISTRY: dict[Format, type[Serializer]] = {
    Format.JSON: JsonSerializer,
    Format.YAML: YamlSerializer,
}

def create_serializer(fmt: Format) -> Serializer:
    cls = _REGISTRY.get(fmt)
    if cls is None:
        raise ValueError(f"不支援的格式: {fmt}")
    return cls()
```

**注意**：Registry 用裝飾器自動註冊可更進一步降低耦合。

## 工具鏈推薦

| 工具 | 用途 | 安裝 | 備註 |
|------|------|------|------|
| `abc` | 抽象基底類別 | 標準庫 | 名義子型態 |
| `typing.Protocol` | 結構子型態 | 標準庫 | 3.8+ |
| `dataclasses` | 資料類別 | 標準庫 | frozen=True 做不可變 |
| `pydantic` | 資料驗證 | `pip install pydantic` | V2 以 Rust 核心 |
| `attrs` | 進階資料類別 | `pip install attrs` | validators, slots |
| `injector` | DI 容器 | `pip install injector` | 自動注入 |
| `dependency-injector` | DI 框架 | `pip install dependency-injector` | 支援 FastAPI |
| `returns` | 函數式模式 | `pip install returns` | Result, Maybe, IO |

## 延伸閱讀

讀取 `references/` 目錄下的對應檔案：
- `references/examples.md` — 完整可運行範例
- `references/cheatsheet.md` — 速查表
- `references/pitfalls.md` — 常見錯誤與解法

## 版本相容性

| Python 版本 | 支援狀態 | 備註 |
|-------------|----------|------|
| 3.13+ | ✅ 完整支援 | type alias 語法 |
| 3.12 | ✅ 完整支援 | PEP 695 type 語法 |
| 3.11 | ✅ | StrEnum, ExceptionGroup |
| 3.10 | ✅ | match-case, `X \| Y` union |
| 3.8–3.9 | ⚠️ 部分 | 需 `from __future__ import annotations` |
