# py-ai — 速查表

## LangChain 速查

### 安裝

```bash
# 核心
pip install langchain langchain-core

# LLM Provider（按需安裝）
pip install langchain-openai       # OpenAI / Azure OpenAI
pip install langchain-anthropic    # Claude
pip install langchain-google-genai # Gemini

# 向量庫
pip install langchain-chroma       # ChromaDB
pip install langchain-community    # 社群整合
```

### LLM 呼叫

```python
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

# OpenAI
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Anthropic
llm = ChatAnthropic(model="claude-sonnet-4-6")

# 同步呼叫
response = llm.invoke("你好")

# 串流
for chunk in llm.stream("說一個故事"):
    print(chunk.content, end="")

# 非同步
response = await llm.ainvoke("你好")
```

### Chain（LCEL 語法）

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

prompt = ChatPromptTemplate.from_template("翻譯成{lang}: {text}")
chain = prompt | llm | StrOutputParser()
result = chain.invoke({"lang": "英文", "text": "你好世界"})
```

### Agent

```python
from langchain.agents import create_agent

agent = create_agent(
    model="gpt-4o-mini",
    tools=[my_tool],
    system_prompt="...",
)
result = agent.invoke({"messages": [{"role": "user", "content": "..."}]})
```

### Structured Output

```python
from pydantic import BaseModel

class Output(BaseModel):
    name: str
    score: float

structured_llm = llm.with_structured_output(Output)
result = structured_llm.invoke("...")  # 回傳 Output 物件
```

---

## LlamaIndex 速查

### 安裝

```bash
pip install llama-index                   # 核心
pip install llama-index-llms-openai       # OpenAI LLM
pip install llama-index-embeddings-openai # OpenAI Embeddings
pip install llama-index-vector-stores-chroma  # ChromaDB
```

### 5 行 RAG

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

documents = SimpleDirectoryReader("data").load_data()
index = VectorStoreIndex.from_documents(documents)
engine = index.as_query_engine()
response = engine.query("問題")
```

### ReAct Agent

```python
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool

tool = FunctionTool.from_defaults(fn=my_func)
agent = ReActAgent.from_tools([tool], llm=llm, verbose=True)
response = agent.chat("問題")
```

### 自訂 Retriever 參數

```python
engine = index.as_query_engine(
    similarity_top_k=5,          # 檢索前 5 筆
    response_mode="tree_summarize",  # 摘要模式
)
```

---

## Transformers 速查

### Pipeline 快速推論

```python
from transformers import pipeline

# 情感分析
classifier = pipeline("sentiment-analysis")
classifier("I love Python!")

# 文字生成
generator = pipeline("text-generation", model="gpt2")
generator("The future is", max_new_tokens=50)

# 問答
qa = pipeline("question-answering")
qa(question="Who?", context="...")

# 摘要
summarizer = pipeline("summarization")
summarizer(long_text, max_length=100)

# 翻譯
translator = pipeline("translation_en_to_fr")
translator("Hello world")
```

### 可用的 Pipeline 任務

| 任務 | pipeline() 參數 | 說明 |
|------|-----------------|------|
| 情感分析 | `"sentiment-analysis"` | 正面/負面分類 |
| 文字生成 | `"text-generation"` | 自回歸生成 |
| 閱讀理解 | `"question-answering"` | 基於段落回答 |
| 文字摘要 | `"summarization"` | 長文摘要 |
| 翻譯 | `"translation_xx_to_yy"` | 語言翻譯 |
| 填空 | `"fill-mask"` | 遮罩語言模型 |
| NER | `"ner"` | 命名實體辨識 |
| 零樣本分類 | `"zero-shot-classification"` | 無需訓練的分類 |

### GPU 設定

```python
# 自動選擇 GPU
pipe = pipeline("text-generation", model="gpt2", device="cuda")

# 指定 GPU 編號
pipe = pipeline("text-generation", model="gpt2", device="cuda:0")

# 多 GPU（模型平行）
from transformers import AutoModelForCausalLM
model = AutoModelForCausalLM.from_pretrained("meta-llama/...", device_map="auto")
```

---

## Embedding 模型選擇

| 模型 | 維度 | 特點 | 安裝 |
|------|------|------|------|
| text-embedding-3-small | 1536 | OpenAI、CP 值最高 | langchain-openai |
| text-embedding-3-large | 3072 | OpenAI、最高品質 | langchain-openai |
| all-MiniLM-L6-v2 | 384 | 免費本地、快速 | sentence-transformers |
| bge-large-en-v1.5 | 1024 | 開源、高品質 | sentence-transformers |
| nomic-embed-text | 768 | 開源、長上下文 | Ollama / HF |

---

## 向量資料庫選擇

| 資料庫 | 類型 | 適用場景 | Python 套件 |
|--------|------|----------|-------------|
| ChromaDB | 嵌入式 | 原型開發、小規模 | `chromadb` |
| FAISS | 嵌入式 | 高效能本地搜尋 | `faiss-cpu` / `faiss-gpu` |
| Pinecone | 雲端 | 生產級、全託管 | `pinecone-client` |
| Weaviate | 自架/雲端 | 多模態、GraphQL | `weaviate-client` |
| Qdrant | 自架/雲端 | Rust 核心、高效能 | `qdrant-client` |
| pgvector | PostgreSQL | 已有 PG 的專案 | `pgvector` |

---

## 環境變數設定

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# LangSmith（觀測）
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY="lsv2_..."

# Hugging Face
export HF_TOKEN="hf_..."

# Azure OpenAI
export AZURE_OPENAI_API_KEY="..."
export AZURE_OPENAI_ENDPOINT="https://xxx.openai.azure.com/"
```

---

## 快速決策指南

```
需要 RAG？
├── 快速原型 → LlamaIndex（5 行 RAG）
├── 複雜 Chain → LangChain LCEL
└── 生產級檢索 → LlamaIndex + Reranker

需要 Agent？
├── 簡單工具呼叫 → LangChain create_agent
├── 多步驟推理 → LlamaIndex ReActAgent
└── 複雜工作流 → LangGraph

本地推論？
├── 分類/NER → Transformers pipeline
├── 聊天機器人 → Ollama + llama.cpp
└── 高吞吐服務 → vLLM

模型選擇？
├── 最強能力 → GPT-4o / Claude Opus
├── CP 值最高 → GPT-4o-mini / Claude Haiku
└── 離線/隱私 → Llama 3 / Mistral / Phi
```
