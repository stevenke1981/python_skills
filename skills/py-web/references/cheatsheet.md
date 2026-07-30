# py-web — 速查表

## FastAPI 基礎

### 安裝

```bash
pip install "fastapi[standard]"       # 含 uvicorn + swagger
pip install fastapi                   # 最小安裝
fastapi dev main.py                   # 開發模式（自動重載）
fastapi run main.py                   # 生產模式
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4  # 手動啟動
```

### 路由裝飾器

```python
@app.get("/path")          # GET
@app.post("/path")         # POST
@app.put("/path")          # PUT
@app.patch("/path")        # PATCH
@app.delete("/path")       # DELETE
@app.options("/path")      # OPTIONS
@app.head("/path")         # HEAD

# APIRouter 分模組
from fastapi import APIRouter
router = APIRouter(prefix="/api/v1", tags=["users"])

@router.get("/users")
async def list_users(): ...

app.include_router(router)
```

### 參數類型

| 類型 | 宣告方式 | 範例 |
|------|---------|------|
| Path | 函式參數 + 路徑 `{name}` | `def f(id: int)` |
| Query | 函式參數（未在路徑中） | `def f(skip: int = 0)` |
| Body | Pydantic Model 參數 | `def f(item: Item)` |
| Header | `Header()` | `def f(x_token: str = Header())` |
| Cookie | `Cookie()` | `def f(session: str = Cookie())` |
| Form | `Form()` | `def f(username: str = Form())` |
| File | `UploadFile` | `def f(file: UploadFile)` |

### 回應模型

```python
@app.get("/users/{id}", response_model=UserResponse)       # 過濾回應欄位
@app.post("/users/", status_code=201)                       # 自訂狀態碼
@app.get("/items/", response_model=list[ItemResponse])      # 列表回應
```

---

## Pydantic v2 速查

### 模型定義

```python
from pydantic import BaseModel, Field, field_validator, model_validator

class User(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=0, le=150)
    email: str | None = None
    tags: list[str] = []

    model_config = {
        "from_attributes": True,     # ORM 模式
        "str_strip_whitespace": True, # 自動去空白
        "json_schema_extra": {"examples": [{"name": "Alice", "age": 30}]},
    }
```

### 常用 Field 約束

| 約束 | 適用類型 | 說明 |
|------|---------|------|
| `min_length` / `max_length` | `str` | 字串長度 |
| `ge` / `gt` / `le` / `lt` | `int`, `float` | 數值範圍 |
| `pattern` | `str` | 正規表達式 |
| `default` | 全部 | 預設值 |
| `alias` | 全部 | JSON 欄位別名 |

### 序列化

```python
user.model_dump()                       # → dict
user.model_dump(exclude_unset=True)     # 只含明確設定的欄位
user.model_dump(exclude={"password"})   # 排除欄位
user.model_dump_json()                  # → JSON 字串
User.model_validate(data_dict)          # dict → Model
User.model_validate_json(json_string)   # JSON → Model
```

---

## SQLAlchemy 2.0 Async 速查

### 連線設定

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# 各資料庫 URL 格式
# PostgreSQL: "postgresql+asyncpg://user:pass@host:5432/db"
# MySQL:      "mysql+aiomysql://user:pass@host:3306/db"
# SQLite:     "sqlite+aiosqlite:///app.db"

engine = create_async_engine(url, pool_size=20, max_overflow=10, echo=False)
session_maker = async_sessionmaker(engine, expire_on_commit=False)
```

### ORM 模型（Mapped 語法）

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from datetime import datetime

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    posts: Mapped[list["Post"]] = relationship(back_populates="author")

class Post(Base):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    author: Mapped["User"] = relationship(back_populates="posts")
```

### 常用查詢

```python
from sqlalchemy import select, func

# 單筆查詢
result = await session.execute(select(User).where(User.id == 1))
user = result.scalar_one_or_none()

# 列表查詢 + 分頁
result = await session.execute(select(User).offset(0).limit(20))
users = result.scalars().all()

# 計數
result = await session.execute(select(func.count()).select_from(User))
count = result.scalar()

# JOIN
stmt = select(User, Post).join(Post, User.id == Post.author_id)
```

---

## HTTPX 速查

```python
import httpx

# 同步
resp = httpx.get("https://api.example.com/data")
resp = httpx.post(url, json={"key": "value"}, headers={"Authorization": "Bearer ..."})

# 非同步
async with httpx.AsyncClient(timeout=10.0, base_url="https://api.example.com") as c:
    resp = await c.get("/data")
    resp = await c.post("/data", json=payload)
    resp.raise_for_status()   # 非 2xx 時拋出異常
    data = resp.json()
```

---

## Middleware 常用清單

```python
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(CORSMiddleware, allow_origins=["https://mysite.com"])
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["mysite.com"])
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

---

## 狀態碼速查

| 碼 | 常數 | 用途 |
|----|------|------|
| 200 | `HTTP_200_OK` | 成功 |
| 201 | `HTTP_201_CREATED` | 建立成功 |
| 204 | `HTTP_204_NO_CONTENT` | 刪除成功 |
| 400 | `HTTP_400_BAD_REQUEST` | 客戶端錯誤 |
| 401 | `HTTP_401_UNAUTHORIZED` | 未認證 |
| 403 | `HTTP_403_FORBIDDEN` | 無權限 |
| 404 | `HTTP_404_NOT_FOUND` | 找不到 |
| 409 | `HTTP_409_CONFLICT` | 資源衝突 |
| 422 | `HTTP_422_UNPROCESSABLE_ENTITY` | 驗證失敗 |
| 429 | `HTTP_429_TOO_MANY_REQUESTS` | 頻率限制 |
| 500 | `HTTP_500_INTERNAL_SERVER_ERROR` | 伺服器錯誤 |

---

## 測試速查

```bash
pip install pytest httpx anyio pytest-anyio
```

```python
import pytest
from httpx import ASGITransport, AsyncClient

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.mark.anyio
async def test_read_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200

# 依賴覆蓋
from main import app, get_db
app.dependency_overrides[get_db] = lambda: mock_db_session
```
