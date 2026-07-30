---
name: py-web
description: >
  Build and review production Python web services with FastAPI, Starlette, Pydantic, SQLAlchemy, ASGI, HTTP clients, REST APIs, WebSocket, authentication, authorization, transactions, lifespan resources, middleware, CORS, idempotency, rate limits, observability, and deployment. Use for API design, request or response validation, database boundaries, async service failures, security hardening, and web integration tests.
compatibility: Agent Skills-compatible. FastAPI, Pydantic, SQLAlchemy, ASGI server, and authentication APIs are version-sensitive; inspect the project's lockfile before coding.
metadata:
  author: stevenke1981
  version: "2.0.0"
  last-reviewed: "2026-07-30"
---

# Python Web／API 工程

## 目標與邊界

用此 skill 建立輸入經驗證、權限清楚、transaction 安全、資源可關閉且可觀測的 Web 服務。

若任務主要是自訂 TCP/UDP 協議，使用 `py-network`；若主要是 LLM/RAG orchestration，以 `py-ai` 為主、`py-web` 負責 API 邊界。

## 執行流程

1. **定義 API 契約**：method、path、request/response schema、status、錯誤、auth、idempotency 與版本策略。
2. **盤點信任邊界**：browser、mobile、service-to-service、proxy、tenant、上傳檔案與外部 URL。
3. **分離層次**：route 解析 HTTP，service 執行 use case，repository/adapter 處理 I/O。
4. **設計 transaction**：每個 use case 的 commit/rollback 邊界清楚，不讓 repository 自行 commit。
5. **建立 lifecycle resource**：DB engine、HTTP client、cache、model 與 worker 在 lifespan 建立／關閉。
6. **加入安全控制**：認證、授權、CORS allowlist、CSRF/SSRF、rate limit、body limit 與秘密管理。
7. **處理故障**：timeout、取消、retry、duplicate request、partial failure 與 graceful shutdown。
8. **測試與觀測**：unit、integration、contract、trace、metrics、structured logs 與 deployment smoke test。

## 分層與依賴方向

```text
HTTP route / schema
        ↓
application service / use case
        ↓
domain rules + ports (Protocol)
        ↓
DB repository / HTTP adapter / queue implementation
```

規則：

- route 不直接寫複雜 SQL 或建立第三方 client。
- domain/service 不回傳 `Response`、ORM session 或 SDK model。
- request schema 與 response schema 分離，避免意外回傳秘密欄位。
- dependency injection 只負責組裝，不把 framework context 傳遍所有層。
- sync library 不可在 async route 直接阻塞 event loop。

## 路由與 Schema

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Protocol

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    email: str = Field(max_length=320)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str


@dataclass(frozen=True, slots=True)
class CreatedUser:
    id: int
    username: str
    email: str


class UserService(Protocol):
    async def create_user(self, payload: UserCreate) -> CreatedUser: ...


def get_user_service() -> UserService:
    raise NotImplementedError("provide the application service")


router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserOut:
    try:
        user = await service.create_user(payload)
    except DuplicateUsernameError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "username_exists", "message": str(exc)},
        ) from exc
    return UserOut.model_validate(user)
```

範例中的 `DuplicateUsernameError` 與 dependency provider 應由專案定義。重點是 route 只做 HTTP mapping，錯誤格式與 status 穩定。

## Request／Response 規則

- 對字串長度、collection 數量、數值範圍、enum 與格式設定上限。
- email、URL、金額等可使用專用 type，但仍要驗證業務規則。
- request model 不直接作 ORM model。
- response model 明確列出允許欄位，避免 password hash、token、internal notes 洩漏。
- partial update 使用明確「未提供」語意，不把 null 與缺省混淆。
- 大型 upload 採 streaming、大小限制、content sniffing、隔離暫存與惡意檔案掃描策略。
- error response 具穩定 code、message、correlation ID；不回傳 stack trace 或 SQL。

## Database Session 與 Transaction

### Session lifecycle

- 每個 request/use case 使用獨立 session。
- engine/session factory 在 application lifespan 建立。
- session dependency 只負責提供與關閉，不自動 commit 所有操作。
- read-only、write transaction 與 isolation level 依需求設定。
- 不跨 background task 或 WebSocket lifetime 重用 request session。

### Unit of Work

```python
from __future__ import annotations

from typing import Protocol, Self


class UnitOfWork(Protocol):
    users: UserRepository

    async def __aenter__(self) -> Self: ...
    async def __aexit__(self, exc_type, exc, traceback) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


class CreateUserService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def create_user(self, payload: UserCreate) -> CreatedUser:
        async with self._uow_factory() as uow:
            if await uow.users.username_exists(payload.username):
                raise DuplicateUsernameError(payload.username)
            user = await uow.users.add(payload)
            await uow.commit()
            return CreatedUser(
                id=user.id,
                username=user.username,
                email=user.email,
            )
```

規則：

- repository 不在每個 method 內 `commit()`。
- unique constraint 仍是最後防線；先查後寫不能消除 race condition。
- 將資料庫 integrity error 映射為穩定 application error。
- 需要 DB + message 的可靠一致性時使用 outbox，而不是假裝跨系統 ACID。
- retry transaction 前確認 operation idempotency 與 isolation 語意。

## Lifespan 與共享 Client

```python
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    timeout = httpx.Timeout(connect=5.0, read=20.0, write=20.0, pool=5.0)
    limits = httpx.Limits(max_connections=100, max_keepalive_connections=20)

    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        app.state.http_client = client
        yield


app = FastAPI(lifespan=lifespan)
```

- 重用 HTTP client/connection pool，不在每個 route 新建。
- 啟動時不執行不可控的大型 migration、模型下載或無 timeout 網路工作。
- readiness 在必要依賴可服務後才成功；liveness 不依賴所有下游服務。
- shutdown 停止接受新工作、等待 deadline、取消剩餘 task、關閉 pool。

## Authentication 與 Authorization

認證回答「你是誰」，授權回答「你可以對這個資源做什麼」。

- token 驗證 issuer、audience、signature、expiry、not-before 與演算法 allowlist。
- 不信任 token header 指定的任意 key URL。
- authorization 在 resource/tenant 層檢查，不只看角色名稱。
- 防止 IDOR/BOLA：查詢必須同時限制 resource ID 與 caller scope。
- refresh/revocation/session policy 明確。
- password 使用專用 password hashing library 與合適參數，不自行設計加密。
- service-to-service 使用短期 credential、mTLS 或核准機制，避免共享長期 token。
- log 遮蔽 bearer token、cookie、API key 與個資。

## CORS、CSRF 與 Browser

- CORS 不是認證機制。
- production 使用明確 origin allowlist；credentials 模式不能隨意搭配 wildcard。
- cookie-based auth 需評估 CSRF token、SameSite、Secure、HttpOnly 與 origin/referrer policy。
- 對 state-changing request 使用正確 method，不以 GET 執行寫入。
- security header 依部署代理與前端架構設定。
- proxy 後方的 scheme/client IP 只信任明確配置的 proxy chain。

## SSRF 與外部 HTTP

若 API 接收 URL 或 callback：

- 限制 scheme、hostname、port 與用途。
- DNS resolve 後檢查 loopback、private、link-local、metadata 與禁止網段。
- redirect 後重新驗證。
- 限制 response 大小、content type、timeout 與下載時間。
- 不把內部 error/body 原樣回傳給 caller。
- 對 webhook callback 使用簽章、idempotency 與 allowlist（適用時）。

## Idempotency、Retry 與 Rate Limit

- 建立／付款／寄信等非冪等操作使用 idempotency key 與 server-side result storage。
- client retry 只針對 transient failure，並納入整體 deadline。
- 不在 proxy、client、service、DB 每一層都無限制重試。
- rate limit 應依 caller、tenant、resource cost 與 burst 設計，不只依 IP。
- 超限回傳穩定錯誤與合理 retry hint。
- background job enqueue 前後處理 duplicate delivery 與 at-least-once 語意。

## WebSocket

- 建立 connection manager，而不是 module-level global list。
- 每個 connection 有 bounded send queue、message size、idle timeout 與 auth expiry。
- browser client 驗證 Origin。
- slow consumer 有 drop/disconnect/backpressure 策略。
- 廣播使用有界並行，個別失敗不阻塞全部連線。
- shutdown 傳送 close frame，在 deadline 後取消。
- 多 process 部署需外部 pub/sub，不假設記憶體 list 能跨 worker。

## Background Tasks

FastAPI `BackgroundTasks` 適合短、低風險、同 process 的工作。以下情況使用持久化 queue/worker：

- 工作時間長
- 需要 retry、排程、進度與 durable delivery
- 不能因 Web process 重啟而遺失
- CPU/GPU 密集
- 有獨立擴縮與資源需求

將 request body 中必要資料複製成不可變 job payload；不要把 request/session 物件傳給背景 worker。

## Observability

至少記錄：

- request ID / trace ID
- route template（不要用包含 ID 的 raw path 當 metric label）
- status、latency、request/response size
- DB query/pool wait、external call、retry、timeout
- authenticated subject/tenant 的安全識別（依隱私規則）
- exception class 與 stable error code

避免高 cardinality metric label 與敏感 log。health endpoint 不回傳 secret、connection string 或完整 dependency error。

## 測試策略

- domain/service 使用 fake repository、clock 與 external adapter。
- route 測 request validation、response schema、status 與 error mapping。
- DB integration 使用真實 engine，測 migration、constraint、rollback 與 concurrency race。
- auth 測過期、錯誤 issuer/audience、跨 tenant 與資源授權。
- HTTP adapter 測 timeout、retry、redirect、SSRF 與 response limit。
- WebSocket 測 auth、Origin、message limit、slow client 與 disconnect。
- lifespan 測 client/pool 建立與關閉。
- deployment smoke test 經過實際 ASGI server/reverse proxy。

常用檢查：

```bash
pytest -q
ruff check .
pyright
```

API contract 可另輸出 OpenAPI 並做 breaking-change 檢查，但生成 schema 不能取代實際 integration test。

## 部署

- container 以 non-root 執行，filesystem 權限最小化。
- secret 由平台注入，不 bake 入 image。
- 設定 worker 數、thread、connection pool 與 DB pool 的總和，避免每個 worker 都放大資源。
- 在 reverse proxy 與 app 同時設定 body、header、timeout 與 keepalive 上限。
- migration 使用獨立 release step，不讓每個 worker 競爭執行。
- graceful shutdown deadline 與 orchestrator termination grace period 一致。
- rollback 需考慮 database schema forward/backward compatibility。

## 交付標準

- API request、response、status、error、auth 與 idempotency 契約已定義。
- route、service、domain 與 I/O adapter 邊界清楚。
- session 每 request/use case 隔離，transaction 由 service/UoW 管理。
- engine、HTTP client、cache 等共享資源由 lifespan 建立與關閉。
- 認證、資源授權、tenant 隔離、CORS/CSRF/SSRF 已依風險處理。
- timeout、retry、rate limit、body/queue/connection limit 均有上限。
- background work 的 durability 與 duplicate 語意已明確。
- structured logs、metrics、traces 與 health checks 不洩漏敏感資料。
- migration、integration、WebSocket、shutdown 與部署 smoke test 已覆蓋。

## 延伸閱讀

- [完整範例](references/examples.md)
- [速查表](references/cheatsheet.md)
- [常見陷阱](references/pitfalls.md)
- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy asyncio documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)

## 版本相容性

| 環境 | 建議 |
|---|---|
| Python 3.14 | 穩定維護基準；確認 ASGI/native dependency wheels |
| Python 3.10–3.13 | 支援；依鎖定版本使用 FastAPI/Pydantic/SQLAlchemy API |
| FastAPI/Pydantic/SQLAlchemy | 視為易變整合面，升級時執行 schema、migration 與 contract tests |
| Multi-worker deployment | 外部 state/pub-sub；不要依賴 process-local global state |
| Preview Python/framework | 只作 opt-in compatibility job，不作唯一 production baseline |
