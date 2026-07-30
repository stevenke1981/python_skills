# py-web — 完整範例程式碼集

## 範例 1：完整 CRUD API（FastAPI + SQLAlchemy Async）

```python
"""完整的 CRUD API 範例，包含資料庫操作、驗證、錯誤處理"""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# === 資料庫設定 ===
class Base(DeclarativeBase):
    pass


class TodoItem(Base):
    __tablename__ = "todos"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(index=True)
    completed: Mapped[bool] = mapped_column(default=False)


engine = create_async_engine("sqlite+aiosqlite:///todos.db")
session_maker = async_sessionmaker(engine, expire_on_commit=False)


# === Pydantic 模型 ===
class TodoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


class TodoUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    completed: bool | None = None


class TodoResponse(BaseModel):
    id: int
    title: str
    completed: bool
    model_config = {"from_attributes": True}


# === 依賴注入 ===
async def get_db():
    async with session_maker() as session:
        yield session


# === 應用程式 ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="Todo API", lifespan=lifespan)


@app.post("/todos/", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
async def create_todo(todo: TodoCreate, db: AsyncSession = Depends(get_db)):
    """建立新的 Todo 項目"""
    item = TodoItem(title=todo.title)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@app.get("/todos/", response_model=list[TodoResponse])
async def list_todos(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """列出所有 Todo 項目（分頁）"""
    result = await db.execute(select(TodoItem).offset(skip).limit(limit))
    return result.scalars().all()


@app.get("/todos/{todo_id}", response_model=TodoResponse)
async def get_todo(todo_id: int, db: AsyncSession = Depends(get_db)):
    """取得單一 Todo 項目"""
    result = await db.execute(select(TodoItem).where(TodoItem.id == todo_id))
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Todo 不存在")
    return item


@app.patch("/todos/{todo_id}", response_model=TodoResponse)
async def update_todo(
    todo_id: int, todo: TodoUpdate, db: AsyncSession = Depends(get_db)
):
    """更新 Todo 項目（部分更新）"""
    result = await db.execute(select(TodoItem).where(TodoItem.id == todo_id))
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Todo 不存在")

    update_data = todo.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    await db.commit()
    await db.refresh(item)
    return item


@app.delete("/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(todo_id: int, db: AsyncSession = Depends(get_db)):
    """刪除 Todo 項目"""
    result = await db.execute(select(TodoItem).where(TodoItem.id == todo_id))
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Todo 不存在")
    await db.delete(item)
    await db.commit()
```

---

## 範例 2：JWT 認證（OAuth2 + Password）

```python
"""JWT 認證範例：登入取得 token、保護路由"""
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel

# === 設定 ===
SECRET_KEY = "your-secret-key-from-env"  # 實際請用環境變數
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()


# === 模型 ===
class Token(BaseModel):
    access_token: str
    token_type: str


class UserInDB(BaseModel):
    username: str
    hashed_password: str


# === 工具函式 ===
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    """驗證 JWT token 並回傳使用者名稱"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="無法驗證憑證",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception
    return username


# === 路由 ===
@app.post("/token", response_model=Token)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """登入並取得 JWT Token"""
    # 實際應查資料庫驗證密碼
    if form_data.username != "demo" or form_data.password != "secret":
        raise HTTPException(status_code=400, detail="帳號或密碼錯誤")

    access_token = create_access_token(
        data={"sub": form_data.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(access_token=access_token, token_type="bearer")


@app.get("/protected/")
async def protected_route(username: Annotated[str, Depends(get_current_user)]):
    """需要登入才能存取的路由"""
    return {"message": f"歡迎, {username}！"}
```

---

## 範例 3：HTTPX 非同步 HTTP 客戶端

```python
"""HTTPX 範例：呼叫外部 API、stream 下載、重試"""
import asyncio

import httpx


async def basic_requests() -> None:
    """基本 GET / POST 請求"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        # GET 請求
        resp = await client.get("https://httpbin.org/get", params={"key": "value"})
        print(f"狀態碼: {resp.status_code}")
        print(f"JSON: {resp.json()}")

        # POST JSON
        resp = await client.post(
            "https://httpbin.org/post",
            json={"name": "Alice", "age": 30},
        )
        print(f"POST 結果: {resp.json()['json']}")


async def concurrent_requests() -> None:
    """並行發送多個請求"""
    urls = [
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/1",
    ]
    async with httpx.AsyncClient(timeout=5.0) as client:
        tasks = [client.get(url) for url in urls]
        responses = await asyncio.gather(*tasks)
        for resp in responses:
            print(f"  {resp.url} → {resp.status_code}")


async def stream_download(url: str, output_path: str) -> None:
    """串流下載大型檔案"""
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            with open(output_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    f.write(chunk)


if __name__ == "__main__":
    asyncio.run(basic_requests())
```

---

## 範例 4：pydantic-settings 環境設定管理

```python
"""集中管理應用程式設定：從 .env + 環境變數讀取"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """應用程式設定 — 自動從 .env 和環境變數載入"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # 資料庫
    database_url: str = Field(
        default="sqlite+aiosqlite:///app.db",
        description="資料庫連線字串",
    )

    # 認證
    secret_key: str = Field(..., description="JWT 簽署密鑰")
    access_token_expire_minutes: int = 30

    # CORS
    allowed_origins: list[str] = ["http://localhost:3000"]

    # 除錯
    debug: bool = False
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """快取設定，避免每次重新讀取 .env"""
    return Settings()


# 在 FastAPI 中使用
from fastapi import Depends, FastAPI

app = FastAPI()


@app.get("/info")
async def info(settings: Settings = Depends(get_settings)):
    return {
        "debug": settings.debug,
        "log_level": settings.log_level,
    }
```

---

## 範例 5：API 測試（pytest + httpx）

```python
"""使用 pytest + httpx 測試 FastAPI 應用"""
import pytest
from httpx import ASGITransport, AsyncClient

from main import app  # 假設主程式在 main.py


@pytest.fixture
async def client():
    """建立測試用的 async HTTP client"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_create_todo(client: AsyncClient):
    """測試建立 Todo"""
    response = await client.post("/todos/", json={"title": "寫測試"})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "寫測試"
    assert data["completed"] is False
    assert "id" in data


@pytest.mark.anyio
async def test_create_todo_validation_error(client: AsyncClient):
    """測試驗證錯誤：title 為空"""
    response = await client.post("/todos/", json={"title": ""})
    assert response.status_code == 422  # Unprocessable Entity


@pytest.mark.anyio
async def test_get_nonexistent_todo(client: AsyncClient):
    """測試 404：不存在的項目"""
    response = await client.get("/todos/99999")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_list_todos_pagination(client: AsyncClient):
    """測試分頁"""
    # 建立多筆資料
    for i in range(5):
        await client.post("/todos/", json={"title": f"項目 {i}"})

    # 取前 2 筆
    response = await client.get("/todos/", params={"limit": 2})
    assert response.status_code == 200
    assert len(response.json()) <= 2
```
