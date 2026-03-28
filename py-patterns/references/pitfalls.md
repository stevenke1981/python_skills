# py-patterns — 常見陷阱與解法

## 陷阱 1：God Class 上帝類別

**症狀**：一個類別負責 10+ 種不相關功能，超過 500 行。

```python
# ❌ God Class — 什麼都做
class AppManager:
    def create_user(self, ...): ...
    def send_email(self, ...): ...
    def process_payment(self, ...): ...
    def generate_report(self, ...): ...
    def upload_to_s3(self, ...): ...

# ✅ 拆分為專責類別
class UserService:
    def create(self, ...): ...

class EmailService:
    def send(self, ...): ...

class PaymentService:
    def process(self, ...): ...
```

**判斷標準**：如果一個類別有超過 2 個「改動理由」，就該拆分。

---

## 陷阱 2：過度使用設計模式

**症狀**：為了「架構漂亮」引入 Factory、Builder、Proxy... 但實際只有一種實作。

```python
# ❌ 過度設計 — 只有一種 Parser 卻用 Factory
class ParserFactory:
    @staticmethod
    def create(fmt: str) -> Parser:
        if fmt == "json":
            return JsonParser()
        raise ValueError(f"Unknown: {fmt}")

# ✅ 直接用就好，等到有第二種再抽象
parser = JsonParser()
data = parser.parse(raw_text)
```

**原則**：YAGNI（You Ain't Gonna Need It）— 等到真正需要多型的時候再引入模式。

---

## 陷阱 3：Protocol 與 ABC 混用

**症狀**：同一個介面既用 Protocol 又繼承 ABC，造成型別檢查器混淆。

```python
# ❌ 混用 — mypy 可能報錯或行為不一致
from abc import ABC, abstractmethod
from typing import Protocol

class Fetchable(Protocol):
    def fetch(self) -> str: ...

class BaseFetcher(ABC):
    @abstractmethod
    def fetch(self) -> str: ...

class MyFetcher(BaseFetcher):  # 繼承 ABC
    def fetch(self) -> str:
        return "data"

def process(f: Fetchable) -> str:  # 接口是 Protocol
    return f.fetch()

# ✅ 二選一：Protocol 或 ABC，不要混用
class Fetchable(Protocol):
    def fetch(self) -> str: ...

class HttpFetcher:  # 不需要繼承任何東西
    def fetch(self) -> str:
        return "data"

def process(f: Fetchable) -> str:
    return f.fetch()  # 結構化子型別自動匹配
```

---

## 陷阱 4：Dataclass 可變預設值

**症狀**：使用 `list` 或 `dict` 作為預設值，所有實例共享同一個物件。

```python
# ❌ 致命錯誤 — 所有實例共享同一個 list
@dataclass
class Config:
    items: list[str] = []  # Python 會報 ValueError!
    # 但如果用 class variable 方式寫不會報錯卻是 bug

# ✅ 使用 field(default_factory=...)
from dataclasses import dataclass, field

@dataclass
class Config:
    items: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
```

**說明**：Python dataclass 會對可變預設值直接報 `ValueError`，但在普通 class 中可變預設值是常見的隱性 bug。養成使用 `field(default_factory=...)` 的習慣。

---

## 陷阱 5：Singleton 反模式

**症狀**：用 `__new__` 或 metaclass 實作 Singleton，測試時無法替換。

```python
# ❌ 典型 Singleton — 全域狀態，測試困難
class DatabaseConnection:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

# ✅ Python 慣用做法 — 模組層級實例 + DI
# db.py
_connection: DatabaseConnection | None = None

def get_connection() -> DatabaseConnection:
    global _connection
    if _connection is None:
        _connection = DatabaseConnection(url=os.environ["DB_URL"])
    return _connection

# service.py — 可透過建構子注入測試用替身
@dataclass
class UserService:
    db: DatabaseConnection  # 注入，不是自己去拿
```

**替代方案**：模組本身就是 Python 的 Singleton（import 一次後快取）。需要控制生命週期時用 factory function。

---

## 陷阱 6：繼承層數過深

**症狀**：5 層以上的繼承鏈，每修改一層就波及全部。

```python
# ❌ 繼承地獄
class BaseHandler:           ...
class AuthHandler:           ...  # extends BaseHandler
class LoggingAuthHandler:    ...  # extends AuthHandler
class CachedLoggingAuth:     ...  # extends LoggingAuthHandler
class RateLimitedCachedLog:  ...  # extends CachedLoggingAuth

# ✅ 組合取代繼承 — 用 Decorator / Wrapper 疊加功能
@dataclass
class Handler:
    auth: Authenticator
    logger: Logger
    cache: Cache
    rate_limiter: RateLimiter

    def handle(self, request: Request) -> Response:
        self.rate_limiter.check(request)
        self.auth.verify(request)
        if cached := self.cache.get(request.key):
            return cached
        response = self._process(request)
        self.cache.set(request.key, response)
        self.logger.log(request, response)
        return response
```

**經驗法則**：繼承深度 ≤ 2 層。超過就改用組合（Composition）。

---

## 陷阱 7：Leaky Abstraction 漏洞抽象

**症狀**：Repository 介面暴露了底層實作的細節（如 SQL、ORM session）。

```python
# ❌ 漏洞抽象 — 呼叫者必須知道 SQLAlchemy 細節
class UserRepository(Protocol):
    def find_by_query(self, session: Session, query: str) -> list[User]: ...

# ✅ 乾淨的抽象 — 隱藏實作細節
class UserRepository(Protocol):
    def find_by_email(self, email: str) -> User | None: ...
    def find_active(self) -> list[User]: ...
    def save(self, user: User) -> None: ...

# 具體實作內部管理自己的 session
class SqlUserRepo:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def find_by_email(self, email: str) -> User | None:
        with self._session_factory() as session:
            return session.query(UserModel).filter_by(email=email).first()
```

---

## 陷阱 8：DI Container 上癮

**症狀**：引入 Dependency Injector / injector 等框架，但專案只有 5 個 service。

```python
# ❌ 過度使用 DI Container — container 設定比業務碼還多
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    db = providers.Singleton(Database, url=config.db_url)
    user_repo = providers.Factory(UserRepo, db=db)
    user_service = providers.Factory(UserService, repo=user_repo)
    # ... 20 more providers for a small CRUD app

# ✅ 小型專案直接用 factory function 組裝
def create_app() -> App:
    db = Database(url=os.environ["DB_URL"])
    user_repo = UserRepo(db=db)
    user_service = UserService(repo=user_repo)
    return App(user_service=user_service)
```

**門檻判斷**：
- < 10 個 service → 手動組裝 factory function
- 10–30 個 service → 簡單的 registry dict
- 30+ 個 service → 考慮 DI Container 框架
