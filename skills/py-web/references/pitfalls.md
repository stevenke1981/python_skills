# py-web — 常見陷阱與解法

## 陷阱 1：在 async endpoint 中呼叫同步阻塞操作

**問題**：在 `async def` 函式中直接呼叫 `time.sleep()`、同步 DB 查詢等，會阻塞整個事件迴圈。

```python
import time
from fastapi import FastAPI

app = FastAPI()

# ❌ 阻塞型操作在 async 函式中 — 整個 server 卡住
@app.get("/slow")
async def slow_endpoint():
    time.sleep(5)  # 阻塞事件迴圈！
    return {"message": "done"}
```

**解法**：改用 sync `def`（FastAPI 會自動放到 threadpool）或用 async 版本。

```python
import asyncio

# ✅ 方法 1：用 def（FastAPI 自動排到 threadpool）
@app.get("/slow")
def slow_endpoint():
    time.sleep(5)  # OK — FastAPI 幫你跑在 thread 裡
    return {"message": "done"}

# ✅ 方法 2：用 async 版本
@app.get("/slow")
async def slow_endpoint():
    await asyncio.sleep(5)
    return {"message": "done"}

# ✅ 方法 3：手動放到 threadpool
@app.get("/slow")
async def slow_endpoint():
    result = await asyncio.to_thread(blocking_function)
    return {"result": result}
```

---

## 陷阱 2：CORS 設定過於寬鬆

**問題**：`allow_origins=["*"]` 在生產環境允許任何網域呼叫 API。

```python
# ❌ 生產環境不應允許所有來源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**解法**：明確列出允許的來源。

```python
import os

# ✅ 從環境變數讀取允許的來源
allowed_origins = os.environ.get(
    "CORS_ORIGINS", "http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=True,
)
```

---

## 陷阱 3：沒有用 response_model 過濾回應欄位

**問題**：直接回傳 ORM 對象，可能洩漏 `hashed_password` 等敏感欄位。

```python
# ❌ 直接回傳 ORM 對象 — hashed_password 也會被序列化
@app.get("/users/{id}")
async def get_user(id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, id)
    return user  # 包含 hashed_password！
```

**解法**：用 `response_model` 選擇性公開欄位。

```python
class UserPublic(BaseModel):
    id: int
    username: str
    created_at: datetime
    model_config = {"from_attributes": True}

# ✅ 只回傳安全的欄位
@app.get("/users/{id}", response_model=UserPublic)
async def get_user(id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, id)
    if not user:
        raise HTTPException(status_code=404)
    return user
```

---

## 陷阱 4：Pydantic model_dump(exclude_unset=True) 與 PATCH 混淆

**問題**：PUT 和 PATCH 混用，不知道哪些欄位是使用者「故意設為 None」，哪些是「沒傳」。

```python
class TodoUpdate(BaseModel):
    title: str | None = None
    completed: bool | None = None

# ❌ 無法區分「沒傳 title」和「傳了 title=None」
@app.patch("/todos/{id}")
async def update_todo(id: int, data: TodoUpdate, db = Depends(get_db)):
    item = await db.get(TodoItem, id)
    for key, value in data.model_dump().items():
        setattr(item, key, value)  # None 也會覆蓋！
```

**解法**：使用 `exclude_unset=True` 只更新有明確傳送的欄位。

```python
# ✅ 只更新使用者實際傳送的欄位
@app.patch("/todos/{id}")
async def update_todo(id: int, data: TodoUpdate, db = Depends(get_db)):
    item = await db.get(TodoItem, id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)
    await db.commit()
    return item
```

---

## 陷阱 5：忘記處理 SQLAlchemy Session 的生命週期

**問題**：共用同一個 session 或沒正確關閉，導致連線洩漏。

```python
# ❌ 全域 session — 多 request 互相干擾
session = async_sessionmaker(engine)()

@app.get("/users")
async def list_users():
    result = await session.execute(select(User))  # 跨 request 共用！
    return result.scalars().all()
```

**解法**：每個 request 一個 session，用 `yield` 依賴自動管理。

```python
# ✅ 每個 request 獨立 session，自動關閉
async def get_db():
    async with session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

@app.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    return result.scalars().all()
```

---

## 陷阱 6：422 錯誤訊息對前端不友善

**問題**：Pydantic 驗證錯誤的預設格式對前端開發者不直覺。

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "username"],
      "msg": "String should have at least 3 characters",
      "input": "ab"
    }
  ]
}
```

**解法**：自訂 ValidationError handler，轉換成更友善的格式。

```python
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    errors = {}
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        errors[field] = error["msg"]

    return JSONResponse(
        status_code=422,
        content={"errors": errors, "message": "驗證失敗"},
    )
# 輸出: {"errors": {"username": "String should have at least 3 characters"}, "message": "驗證失敗"}
```

---

## 陷阱 7：沒有設定 Request Body 大小限制

**問題**：惡意使用者上傳超大 body 導致記憶體耗盡。

```python
# ❌ 完全沒有大小限制
@app.post("/upload/")
async def upload(file: UploadFile):
    content = await file.read()  # 10GB 檔案直接讀到記憶體！
```

**解法**：限制檔案大小，使用串流讀取。

```python
from fastapi import UploadFile, HTTPException

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

@app.post("/upload/")
async def upload(file: UploadFile):
    # ✅ 檢查 Content-Length（如果有的話）
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="檔案太大")

    # ✅ 串流讀取，邊讀邊檢查大小
    total_size = 0
    chunks: list[bytes] = []
    while chunk := await file.read(8192):
        total_size += len(chunk)
        if total_size > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="檔案超過 10MB 限制")
        chunks.append(chunk)
    content = b"".join(chunks)
    return {"size": len(content)}
```

---

## 陷阱 8：生產環境暴露 Swagger 文件

**問題**：`/docs` 和 `/redoc` 在生產環境暴露 API 結構給攻擊者。

```python
# ❌ 預設所有環境都開啟 Swagger
app = FastAPI()  # /docs 和 /redoc 永遠可存取
```

**解法**：生產環境關閉自動文件。

```python
import os

# ✅ 根據環境決定是否開啟文件
is_production = os.environ.get("ENV") == "production"

app = FastAPI(
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json",
)
```
