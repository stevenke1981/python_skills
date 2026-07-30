---
name: py-patterns
description: >
  Design and refactor maintainable Python architecture with Protocol, dataclasses, composition, dependency injection, Strategy, Factory, Adapter, Repository, Unit of Work, state machines, domain services, events, and clean module boundaries. Use when coupling, testability, extension points, transactions, or growing codebases require an explicit design rather than a framework-specific patch.
compatibility: Agent Skills-compatible. Apply patterns only when they solve observed variation, coupling, lifecycle, or testing problems.
metadata:
  author: stevenke1981
  version: "2.0.0"
  last-reviewed: "2026-07-30"
---

# Python 設計模式與架構邊界

## 目標與邊界

用此 skill 將業務規則、I/O、framework 與第三方服務分離，使系統可測試、可替換且容易理解。

預設從函式、模組與 composition 開始。只有在存在真實變化點、生命週期、transaction 或依賴反轉需求時才引入 pattern。小型程式不需要為了「架構完整」建立大量抽象類別。

## 執行流程

1. **描述痛點**：耦合、重複條件、難以測試、跨層 transaction、第三方 API 漂移或狀態混亂。
2. **畫出依賴方向**：domain 應依賴什麼抽象，I/O/framework 實作位於哪一層。
3. **找出變化軸**：策略、provider、storage、format、workflow state 或 side effect。
4. **先建立最小 seam**：函式參數、Protocol 或小型 adapter，避免一次重寫全專案。
5. **把 lifecycle 放在組合根**：client、pool、repository 與 service 在 app startup/command handler 組裝。
6. **定義 transaction 與錯誤邊界**：commit/rollback 由 use case 管理，不讓 repository 偷偷決定。
7. **用測試驗證替換性**：domain 使用 fake/in-memory implementation，adapter 有 contract test。
8. **移除無價值抽象**：若只有一個實作且沒有測試/邊界需求，保留簡單設計。

## Pattern 選擇指南

| 問題 | 優先解法 | 何時不要用 |
|---|---|---|
| 多種演算法可替換 | Strategy / callable | 只有一個簡單分支 |
| 第三方 API 汙染 domain | Adapter | wrapper 只是逐字轉呼叫且無邊界價值 |
| 建立物件需要條件與依賴 | Factory | 直接 constructor 已清楚 |
| 需要依賴反轉與 fake | Protocol + DI | 建立大型 service locator |
| domain 查詢與 persistence 隔離 | Repository | 對 ORM 每個 CRUD 再包一層無語意介面 |
| 多 repository 同一 transaction | Unit of Work | 每次操作都是獨立、無 transaction 關係 |
| 明確狀態轉移 | State machine | 幾個無狀態 boolean 就足夠 |
| 跨模組副作用通知 | Domain event | 同一函式直接呼叫已清楚 |
| 複雜建立流程 | Builder | dataclass constructor 或 factory 足夠 |

## Protocol 與依賴注入

Protocol 適合描述呼叫端真正需要的最小能力：

```python
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ChargeResult:
    transaction_id: str
    approved: bool


class PaymentGateway(Protocol):
    def charge(
        self,
        *,
        customer_id: str,
        amount: Decimal,
        idempotency_key: str,
    ) -> ChargeResult: ...


class AuditSink(Protocol):
    def record(self, event: str, payload: dict[str, object]) -> None: ...


@dataclass(slots=True)
class CheckoutService:
    payments: PaymentGateway
    audit: AuditSink

    def checkout(
        self,
        customer_id: str,
        amount: Decimal,
        idempotency_key: str,
    ) -> ChargeResult:
        if amount <= 0:
            raise ValueError("amount must be positive")

        result = self.payments.charge(
            customer_id=customer_id,
            amount=amount,
            idempotency_key=idempotency_key,
        )
        self.audit.record(
            "checkout.completed",
            {
                "customer_id": customer_id,
                "transaction_id": result.transaction_id,
                "approved": result.approved,
            },
        )
        return result
```

規則：

- constructor injection 優先於全域 singleton/service locator。
- Protocol 由使用端定義，不必鏡像第三方 SDK 的整個介面。
- domain type 不回傳 framework response、ORM session 或 SDK model。
- optional dependency 應有清楚預設與錯誤，不在任意位置偷偷 lookup。

## Strategy

若策略只需要一個操作，可直接使用 callable：

```python
from collections.abc import Callable
from decimal import Decimal


type PricingRule = Callable[[Decimal], Decimal]


def apply_pricing(subtotal: Decimal, rule: PricingRule) -> Decimal:
    total = rule(subtotal)
    if total < 0:
        raise ValueError("pricing rule returned a negative total")
    return total
```

只有在策略需要多個方法、狀態或 lifecycle 時才升級為 class/Protocol。

## Adapter 與 Anti-corruption Layer

第三方 client 放在 infrastructure 層：

- 將供應商 request/response 映射為 domain type。
- 將 SDK exception 轉成穩定的 application error。
- 集中 timeout、retry、認證、rate limit 與觀測。
- 不讓供應商 model/type 穿透所有層。
- adapter contract test 使用錄製 fixture 或受控 sandbox，不在 domain unit test 呼叫網路。

## Repository

Repository 應表達 domain 語意：

```python
from typing import Protocol


class OrderRepository(Protocol):
    def get_open_for_customer(self, customer_id: str) -> list[Order]: ...
    def add(self, order: Order) -> None: ...
```

避免建立無限泛型的 `BaseRepository[T]`，只提供 `get/list/create/update/delete`，卻把所有查詢細節洩漏到 service。

Repository 規則：

- 不在每個方法內自行 commit。
- 查詢回傳 domain/read model，而非任意 ORM session。
- eager/lazy loading 策略在 adapter 內可測。
- 對複雜報表可直接使用 query service，不必硬塞入 aggregate repository。

## Unit of Work 與 Transaction

```python
from types import TracebackType
from typing import Protocol, Self


class UnitOfWork(Protocol):
    orders: OrderRepository

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...
    def rollback(self) -> None: ...
```

- use case 決定 transaction boundary。
- 成功才 commit；失敗 rollback。
- 外部網路副作用與 DB transaction 不可假裝成單一 ACID transaction。
- 需要可靠跨系統事件時使用 outbox/inbox、idempotency 與重試策略。

## State Machine

當流程具有明確狀態與禁止轉移時，集中定義：

- state enum
- allowed transitions
- transition command
- guard conditions
- emitted events
- persistence/versioning

不要讓多個 boolean 組合產生無法解釋的狀態，例如 `is_paid=True` 同時 `is_cancelled=True` 卻沒有規則。

## Domain Event

適合在一個 use case 完成後觸發其他模組：

- event 使用不可變資料。
- event name/version 穩定。
- handler 失敗政策清楚：同步失敗、outbox retry 或 dead letter。
- consumer 具 idempotency。
- 不把 event bus 當成隱藏 control flow；重要鏈路要可追蹤。

## 組合根

所有 concrete implementation 在程式入口組裝：

```python

def build_checkout_service(settings: Settings) -> CheckoutService:
    gateway = HttpPaymentGateway(
        base_url=settings.payment_url,
        api_key=settings.payment_api_key,
        timeout_seconds=settings.timeout_seconds,
    )
    audit = StructuredAuditLogger()
    return CheckoutService(payments=gateway, audit=audit)
```

避免在 domain/service 內讀環境變數、建立 HTTP client 或 import framework global。

## 常見反模式

- 每個 class 都有 interface，但只有一個無差異實作。
- `Manager`, `Helper`, `Utils` 收納無關責任。
- 以 inheritance 共用程式碼，造成脆弱 base class。
- repository 自行 commit，破壞跨 repository transaction。
- service locator 隱藏依賴。
- domain object import FastAPI、SQLAlchemy session 或 SDK response。
- event 驅動卻沒有 trace、idempotency 與失敗政策。
- pattern 數量成為品質指標。

## 測試策略

- domain service 使用 in-memory fake 或小型 stub。
- Protocol implementation 共用 contract tests。
- repository adapter 使用真實 database integration test。
- Unit of Work 測 commit、rollback 與 exception path。
- state machine 使用 table/property tests 驗證所有 allowed/forbidden transition。
- outbox/event handler 測 idempotency、retry 與 duplicate delivery。
- 組合根做 smoke test，確保依賴可建立與關閉。

## 交付標準

- 每個抽象都對應真實變化點、邊界或測試需求。
- domain 不依賴 framework、ORM session 或第三方 SDK type。
- 依賴由 constructor/參數注入，組合集中在入口。
- transaction boundary 由 use case 管理，repository 不偷 commit。
- 外部副作用有 adapter、timeout、error mapping 與 contract test。
- state/event 流程具明確規則、觀測、idempotency 與失敗政策。
- 沒有為單一簡單實作建立不必要 pattern 層。

## 延伸閱讀

- [完整範例](references/examples.md)
- [速查表](references/cheatsheet.md)
- [常見陷阱](references/pitfalls.md)

## 版本相容性

| Python | 建議 |
|---|---|
| 3.14 | 穩定維護基準 |
| 3.12–3.13 | 可使用 PEP 695 type alias；確認 type checker |
| 3.10–3.11 | 使用 `TypeAlias`/`TypeVar` 等相容語法 |
| Preview Python | 架構原則不變，新 typing 語法僅 opt-in |
