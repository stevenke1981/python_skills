---
name: py-ai
description: >
  Python AI/ML integration patterns and frameworks.
  Trigger when user mentions LangChain, LlamaIndex, RAG, retrieval augmented generation,
  embeddings, vector store, LLM integration, model serving, ONNX, transformers,
  Hugging Face, agents, tool calling, prompt engineering, semantic search.
  Also trigger when user asks about building AI applications in Python,
  LLM-powered apps, AI pipelines, or context-augmented generation.
---

# Python AI/ML 整合

## Quick Start（30 秒上手）

使用 LangChain 建立最簡單的 LLM 應用：

```python
# pip install langchain langchain-openai
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# 環境變數設定 API Key（不要寫死在程式碼中）
llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=os.environ["OPENAI_API_KEY"],
)
response = llm.invoke([HumanMessage(content="用一句話解釋 RAG")])
print(response.content)
```

---

## 核心概念

### 1. RAG（Retrieval-Augmented Generation）

RAG 是目前最主流的 LLM 應用模式：將外部資料檢索與 LLM 生成結合，解決 LLM 知識過期和幻覺問題。

```python
# LlamaIndex 5 行 RAG
# pip install llama-index
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

documents = SimpleDirectoryReader("data").load_data()
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine()
response = query_engine.query("文件中提到的主要結論是什麼？")
print(response)
```

**核心流程**：載入資料 → 切割（chunking）→ Embedding → 存入向量庫 → 查詢時檢索 → 送入 LLM 生成

### 2. Embeddings 與向量搜尋

Embedding 將文字轉換為高維向量，讓語意相近的文字在向量空間中距離相近。

```python
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vectors = embeddings.embed_documents([
    "Python 是一種程式語言",
    "蟒蛇是一種大型蛇類",
])
# vectors[0] 和 vectors[1] 的語意不同，cosine similarity 低
```

### 3. Agent 與 Tool Calling

Agent 是 LLM 驅動的智慧助理，能根據使用者需求自動選擇並呼叫工具。

```python
from langchain.agents import create_agent

def search_database(query: str) -> str:
    """搜尋資料庫中的相關記錄"""
    # 實際應用中連接資料庫
    return f"找到 3 筆與 '{query}' 相關的記錄"

agent = create_agent(
    model="gpt-4o-mini",
    tools=[search_database],
    system_prompt="你是一個資料查詢助手",
)
result = agent.invoke(
    {"messages": [{"role": "user", "content": "查詢最近的訂單"}]}
)
```

### 4. Prompt Engineering

Prompt 設計直接影響 LLM 輸出品質。結構化 prompt 比自由文字效果更好。

```python
from langchain_core.prompts import ChatPromptTemplate

# 結構化 Prompt Template
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是 {domain} 領域的專家。請用 {style} 的方式回答。"),
    ("human", "{question}"),
])

chain = prompt | llm
response = chain.invoke({
    "domain": "資料工程",
    "style": "簡潔技術",
    "question": "什麼是 ETL？",
})
```

### 5. 模型服務與部署

從本地推論到 API 服務，Python 生態系提供多種部署選項。

| 方案 | 適用場景 | 特點 |
|------|----------|------|
| Hugging Face Transformers | 本地推論 / fine-tuning | 最大模型生態系 |
| ONNX Runtime | 跨平台推論 | 高效能、輕量部署 |
| vLLM | LLM 服務化 | PagedAttention、高吞吐 |
| Ollama | 本地 LLM | 簡單易用、離線運行 |
| TGI + TEI | 推論 + Embedding 服務 | Docker 部署、生產級 |

---

## 實戰 Patterns

### Pattern 1：RAG Pipeline with Reranking

**場景**：基本 RAG 檢索品質不夠時，加入 Reranker 提升精準度。

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.postprocessor import SentenceTransformerRerank

# 載入與索引
documents = SimpleDirectoryReader("data").load_data()
index = VectorStoreIndex.from_documents(documents)

# 加入 Reranker — 先粗篩多一點，再精排
reranker = SentenceTransformerRerank(
    model="cross-encoder/ms-marco-MiniLM-L-2-v2",
    top_n=3,  # 最終保留 3 筆
)
query_engine = index.as_query_engine(
    similarity_top_k=10,  # 先粗篩 10 筆
    node_postprocessors=[reranker],
)
response = query_engine.query("最重要的技術決策是什麼？")
```

**注意**：Reranker 是 cross-encoder，比 bi-encoder 慢但更精準；先用 bi-encoder 縮小範圍再 rerank。

### Pattern 2：Structured Output（結構化輸出）

**場景**：需要 LLM 回傳可程式化處理的結構化資料。

```python
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

class MovieReview(BaseModel):
    """電影評論結構化輸出"""
    title: str = Field(description="電影名稱")
    rating: float = Field(ge=0, le=10, description="評分 0-10")
    sentiment: str = Field(description="正面/負面/中性")
    summary: str = Field(description="一句話摘要")

llm = ChatOpenAI(model="gpt-4o-mini")
structured_llm = llm.with_structured_output(MovieReview)
review = structured_llm.invoke("評論電影《乘風破浪》好看嗎？")
# review.title, review.rating, review.sentiment 都是型別安全的
```

**注意**：不是所有模型都支援 structured output；Pydantic v2 的 Field 驗證會在 parse 時自動執行。

### Pattern 3：Streaming + Async 即時回應

**場景**：需要逐 token 輸出給使用者，改善 UX。

```python
import asyncio
from langchain_openai import ChatOpenAI

async def stream_response(question: str) -> None:
    llm = ChatOpenAI(model="gpt-4o-mini", streaming=True)
    async for chunk in llm.astream(question):
        print(chunk.content, end="", flush=True)
    print()

asyncio.run(stream_response("說明 Python 的 GIL"))
```

### Pattern 4：本地模型推論（Transformers Pipeline）

**場景**：不想依賴外部 API，在本地運行模型。

```python
# pip install transformers torch
from transformers import pipeline

# 情感分析（自動下載模型）
classifier = pipeline("sentiment-analysis")
results = classifier([
    "This product is amazing!",
    "Terrible experience, waste of money.",
])
for r in results:
    print(f"{r['label']}: {r['score']:.3f}")
# POSITIVE: 0.999
# NEGATIVE: 0.998
```

**注意**：首次執行會下載模型到 `~/.cache/huggingface/`；可用 `device="cuda"` 啟用 GPU。

---

## 工具鏈推薦

| 工具 | 用途 | 安裝 | 備註 |
|------|------|------|------|
| LangChain | LLM 應用框架 | `pip install langchain` | Agent + Chain 模式 |
| LlamaIndex | RAG 框架 | `pip install llama-index` | 資料索引與查詢引擎 |
| Transformers | 模型推論/訓練 | `pip install transformers` | Hugging Face 生態核心 |
| ONNX Runtime | 跨平台推論 | `pip install onnxruntime` | 高效能推論引擎 |
| ChromaDB | 向量資料庫 | `pip install chromadb` | 輕量嵌入式向量庫 |
| Pydantic | 結構化輸出 | `pip install pydantic` | LLM 輸出驗證 |
| vLLM | LLM 服務化 | `pip install vllm` | 高吞吐 OpenAI 兼容 API |
| LangSmith | 觀測與除錯 | 雲端服務 | Trace / Eval / Monitor |

---

## 延伸閱讀

讀取 `references/` 目錄下的對應檔案：
- `references/examples.md` — 完整可運行範例
- `references/cheatsheet.md` — 速查表
- `references/pitfalls.md` — 常見錯誤與解法

---

## 版本相容性

| Python 版本 | 支援狀態 | 備註 |
|-------------|----------|------|
| 3.13+ | ✅ 完整支援 | LangChain/LlamaIndex 最新版本支援 |
| 3.12 | ✅ 完整支援 | 推薦版本 |
| 3.11 | ✅ 支援 | Transformers/PyTorch 廣泛測試 |
| 3.10 | ⚠️ 部分 | 部分套件不再測試新功能 |
