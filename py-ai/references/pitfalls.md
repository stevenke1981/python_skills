# py-ai — 常見陷阱與解法

## 陷阱 1：API Key 寫死在程式碼中

**問題**：API Key 直接寫在 Python 檔案裡，推上 Git 後洩漏。

```python
# ❌ 千萬不要這樣做
llm = ChatOpenAI(api_key="sk-abc123...")
```

**解法**：使用環境變數，永遠不把 Key 寫在程式碼中。

```python
import os

# ✅ 從環境變數讀取
api_key = os.environ["OPENAI_API_KEY"]
llm = ChatOpenAI(api_key=api_key)

# ✅ 更好：LangChain 自動讀取環境變數
# 只要設定了 OPENAI_API_KEY，不需要傳 api_key 參數
llm = ChatOpenAI(model="gpt-4o-mini")

# ✅ .env + python-dotenv（開發用）
# pip install python-dotenv
from dotenv import load_dotenv
load_dotenv()  # 讀取 .env 檔
```

---

## 陷阱 2：RAG Chunk 大小不當

**問題**：chunk 太大導致噪音多、太小導致上下文不足。

```python
# ❌ chunk_size 太大 — 檢索到的資料雜訊多
splitter = RecursiveCharacterTextSplitter(chunk_size=5000)

# ❌ chunk_size 太小 — 語意不完整
splitter = RecursiveCharacterTextSplitter(chunk_size=50)
```

**解法**：根據資料類型調整 chunk 大小，加入 overlap 保持語意連續。

```python
# ✅ 一般文件：300-800 字元，20% overlap
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
    separators=["\n\n", "\n", "。", "，", " "],
)

# ✅ 程式碼：用語言感知的 splitter
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter.from_language(
    language=Language.PYTHON,
    chunk_size=1000,
    chunk_overlap=200,
)
```

---

## 陷阱 3：忽略 Embedding 模型與查詢語言的匹配

**問題**：文件是中文，但用英文 Embedding 模型，檢索品質大幅下降。

```python
# ❌ 用純英文模型嵌入中文文件
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
# 此模型主要針對英文訓練
```

**解法**：選擇支援目標語言的 Embedding 模型。

```python
# ✅ 多語言模型
# OpenAI text-embedding-3 系列天然支援多語言
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# ✅ 開源多語言模型
embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-m3",  # 多語言、多功能
)
```

---

## 陷阱 4：沒有處理 LLM 幻覺（Hallucination）

**問題**：RAG 系統回傳看似正確但實際上是 LLM 編造的答案。

```python
# ❌ 沒有驗證 LLM 回答是否基於檢索到的上下文
response = query_engine.query("公司的年營收是多少？")
# LLM 可能編造數字
```

**解法**：加入參考來源、設定 prompt 限制、使用 faithfulness 評估。

```python
# ✅ Prompt 明確限制
prompt = """根據以下上下文回答問題。
規則：
1. 只根據上下文中的資訊回答
2. 如果上下文未提及，回答「資料中未提及」
3. 引用具體的來源段落

上下文：{context}
問題：{question}
"""

# ✅ 回傳時附帶來源
response = query_engine.query("年營收是多少？")
for node in response.source_nodes:
    print(f"  來源: {node.node.get_content()[:100]}")
    print(f"  相似度: {node.score:.3f}")
```

---

## 陷阱 5：Transformers 模型載入太慢

**問題**：每次啟動都重新下載/載入模型，浪費時間和頻寬。

```python
# ❌ 每次都從 Hub 載入
pipe = pipeline("sentiment-analysis")  # 每次啟動都要下載
```

**解法**：預先下載到本地，重複使用快取。

```python
# ✅ 方法 1：指定快取目錄
import os
os.environ["HF_HOME"] = "/path/to/model_cache"

# ✅ 方法 2：先下載後載入
from transformers import AutoTokenizer, AutoModel

model_name = "distilbert-base-uncased"
local_dir = "./models/distilbert"

# 首次：下載並儲存
tokenizer = AutoTokenizer.from_pretrained(model_name)
tokenizer.save_pretrained(local_dir)

# 之後：從本地載入（秒級啟動）
tokenizer = AutoTokenizer.from_pretrained(local_dir)
```

---

## 陷阱 6：沒有設定 Temperature 和 Token 上限

**問題**：使用預設 temperature=1.0，每次回答差異大且可能冗長。

```python
# ❌ 預設參數 — 回答不穩定且可能超出預算
llm = ChatOpenAI()
```

**解法**：根據任務特性設定適當參數。

```python
# ✅ 事實性回答 → 低 temperature
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,      # 穩定可重現
    max_tokens=500,     # 控制回答長度和成本
)

# ✅ 創意生成 → 較高 temperature
llm_creative = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.8,
    max_tokens=2000,
)

# 常見 temperature 設定
# 0.0 — 資料擷取、分類、程式碼生成
# 0.3 — RAG 問答、摘要
# 0.7 — 一般對話
# 1.0 — 創意寫作、腦力激盪
```

---

## 陷阱 7：同步呼叫阻塞 — 沒用 Async

**問題**：多個 LLM 請求序列執行，白白浪費等待 I/O 的時間。

```python
# ❌ 序列呼叫 3 次 API — 總時間 = t1 + t2 + t3
results = []
for q in questions:
    r = llm.invoke(q)
    results.append(r)
```

**解法**：使用 async 並行呼叫。

```python
import asyncio
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")

# ✅ 並行呼叫 — 總時間 ≈ max(t1, t2, t3)
async def batch_query(questions: list[str]) -> list:
    tasks = [llm.ainvoke(q) for q in questions]
    return await asyncio.gather(*tasks)

results = asyncio.run(batch_query(questions))

# ✅ LangChain 內建 batch 方法
results = llm.batch(questions, config={"max_concurrency": 5})
```

---

## 陷阱 8：忽略 Token 計費 — 成本失控

**問題**：開發階段大量呼叫 GPT-4 級別的模型，帳單爆表。

**解法**：開發用便宜模型，生產再切換；監控 token 使用量。

```python
import os

# ✅ 環境區分模型
model = os.environ.get("LLM_MODEL", "gpt-4o-mini")  # 開發預設便宜模型
llm = ChatOpenAI(model=model)

# ✅ 使用 callback 追蹤 token 使用量
from langchain_community.callbacks import get_openai_callback

with get_openai_callback() as cb:
    response = llm.invoke("你好")
    print(f"Tokens: {cb.total_tokens}")
    print(f"Cost: ${cb.total_cost:.4f}")

# ✅ 成本估算表（2024 美金/1M tokens）
# gpt-4o:        input $2.50 / output $10.00
# gpt-4o-mini:   input $0.15 / output $0.60
# claude-sonnet: input $3.00 / output $15.00
# claude-haiku:  input $0.25 / output $1.25
```
