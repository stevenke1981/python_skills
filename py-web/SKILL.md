---
name: py-web
description: >
  Modern Python web development patterns with FastAPI, Pydantic v2, SQLAlchemy 2.0,
  Starlette, ASGI, and async-first architecture.
  Trigger when user mentions FastAPI, web API, REST API, Pydantic model, endpoint,
  middleware, dependency injection, ASGI, CORS, WebSocket, Starlette, Litestar,
  SQLModel, httpx, or async web server.
  Also trigger when user asks about building web services, API design, request
  validation, response serialization, or deploying Python web apps.
---

# Python Web 開發（FastAPI + Pydantic v2 + SQLAlchemy 2.0）

## Quick Start（30 秒上手）

```python
# pip install "fastapi[standard]"
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Item(BaseModel):
    name: str
    price: float
    in_stock: bool = True


@app.get("/")
async def root():
    return {"message": "Hello, World!"}


@app.post("/items/", response_model=Item)
async def create_item(item: Item):
    return item


# 啟動：fastapi dev main.py
# 文件：http://127.0.0.1:8000/docs
```

## 核心概念

### 1. 路由與路徑參數

FastAPI 使用 Python type hints 自動驗證和文件化 API。

```python
from fastapi import FastAPI, Path, Query

app = FastAPI()


@app.get("/users/{user_id}")
async def get_user(
    user_id: int = Path(..., ge=1, description="使用者 ID"),
    include_email: bool = Query(False, description="是否回傳 email"),
):
    return {"user_id": user_id, "include_email": include_email}
```

### 2. Pydantic v2 模型與驗證

Pydantic v2 的核心由 Rust 撰寫，驗證速度比 v1 快 5-50 倍。

```python
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator


class UserCreate(BaseModel):
    """建立使用者的請求 body"""
    username: str = Field(..., min_length=3, max_length=30)
    email: str = Field(..., pattern=r"^[\w.-]+@[\w.-]+\.\w+$")
    age: int = Field(..., ge=0, le=150)

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError("使用者名稱只能包含英數字")
        return v.lower()


class UserResponse(BaseModel):
    """回傳給前端的使用者資料"""
    id: int
    username: str
    created_at: datetime

    model_config = {"from_attributes": True}  # ORM 模式
```

### 3. 依賴注入（Dependency Injection）

FastAPI 內建的 DI 系統，可管理資料庫連線、認證、設定等。

```python
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI()


async def get_db() -> AsyncSession:
    """依賴：提供資料庫 session"""
    async with async_session_maker() as session:
        yield session  # yield 確保結束時自動關閉


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """依賴：驗證 JWT 並取得目前使用者"""
    user = await verify_token(token, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user


# 使用 Annotated 簡化重複的依賴宣告
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@app.get("/me")
async def read_me(user: CurrentUser):
    return user
```

### 4. Middleware 與 CORS

```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time

app = FastAPI()

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://example.com"],  # 不要用 ["*"] 在生產環境
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


# 自訂 middleware：計算請求處理時間
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    return response
```

### 5. SQLAlchemy 2.0 Async + SQLModel

```python
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(unique=True, index=True)
    email: Mapped[str] = mapped_column(unique=True)


# Async engine
engine = create_async_engine("sqlite+aiosqlite:///app.db", echo=True)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
```

## 實戰 Patterns

### Pattern 1: Repository Pattern（資料存取抽象）

**場景**：將 SQLAlchemy 查詢封裝成獨立的 Repository，業務邏輯不直接碰 ORM。

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self._session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, username: str, email: str) -> User:
        user = User(username=username, email=email)
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user
```

### Pattern 2: 結構化錯誤回應

**場景**：統一 API 錯誤格式，前端容易處理。

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: str
    detail: str
    status_code: int


class AppError(Exception):
    def __init__(self, error: str, detail: str, status_code: int = 400):
        self.error = error
        self.detail = detail
        self.status_code = status_code


app = FastAPI()


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.error,
            detail=exc.detail,
            status_code=exc.status_code,
        ).model_dump(),
    )
```

### Pattern 3: WebSocket 即時通訊

**場景**：聊天室、即時通知、資料推送。

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()
active_connections: list[WebSocket] = []


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # 廣播給所有連線
            for conn in active_connections:
                await conn.send_text(f"訊息: {data}")
    except WebSocketDisconnect:
        active_connections.remove(websocket)
```

### Pattern 4: 背景任務與 Lifespan

**場景**：應用啟動時初始化資源、關閉時清理。

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動時：建立資料庫表、連線池
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # 關閉時：清理資源
    await engine.dispose()


app = FastAPI(lifespan=lifespan)


@app.post("/notify/")
async def send_notification(
    email: str,
    background_tasks: BackgroundTasks,
):
    background_tasks.add_task(send_email, email)
    return {"message": "通知已排入佇列"}
```

## 工具鏈推薦

| 工具 | 用途 | 安裝 | 備註 |
|------|------|------|------|
| FastAPI | Web 框架 | `pip install "fastapi[standard]"` | 內附 Uvicorn + Swagger UI |
| Pydantic v2 | 資料驗證 | `pip install pydantic` | Rust 核心，極快 |
| SQLAlchemy 2.0 | ORM / SQL | `pip install sqlalchemy[asyncio]` | 支援 async |
| HTTPX | HTTP 客戶端 | `pip install httpx` | async + sync 雙模式 |
| Uvicorn | ASGI Server | `pip install uvicorn[standard]` | 含 uvloop |
| Alembic | DB Migration | `pip install alembic` | SQLAlchemy 官方遷移工具 |
| pydantic-settings | 環境設定 | `pip install pydantic-settings` | .env + 環境變數管理 |
| pytest + httpx | API 測試 | `pip install pytest httpx` | TestClient 替代方案 |

## 延伸閱讀

讀取 `references/` 目錄下的對應檔案：
- `references/examples.md` — 完整可運行範例
- `references/cheatsheet.md` — 速查表
- `references/pitfalls.md` — 常見錯誤與解法

## 版本相容性

| Python 版本 | 支援狀態 | 備註 |
|-------------|----------|------|
| 3.13+ | ✅ 完整支援 | FastAPI 0.115+ |
| 3.12 | ✅ 完整支援 | 推薦版本 |
| 3.11 | ✅ 完整支援 | |
| 3.10 | ✅ 支援 | Pydantic v2 最低要求 3.9 |
| 3.9 | ⚠️ 維護中 | 需用 `from __future__ import annotations` |
