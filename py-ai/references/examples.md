# py-ai — 完整可運行範例

## 範例 1：LangChain RAG Pipeline（端到端）

```python
"""LangChain RAG：載入文件 → 切割 → 嵌入 → 向量庫 → 查詢"""
# pip install langchain langchain-openai langchain-community chromadb
import os
from pathlib import Path

from langchain_community.document_loaders import TextLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma


def build_rag_chain(docs_dir: str = "docs"):
    """建立完整 RAG Chain"""
    # 1. 載入所有 .txt 文件
    documents = []
    for txt_file in Path(docs_dir).glob("*.txt"):
        loader = TextLoader(str(txt_file), encoding="utf-8")
        documents.extend(loader.load())

    if not documents:
        raise FileNotFoundError(f"{docs_dir}/ 中沒有 .txt 檔案")

    # 2. 文件切割
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", "。", "，", " "],
    )
    chunks = splitter.split_documents(documents)
    print(f"切割成 {len(chunks)} 個 chunks")

    # 3. 建立向量庫
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = Chroma.from_documents(chunks, embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    # 4. 建立 RAG Chain
    prompt = ChatPromptTemplate.from_template(
        "根據以下上下文回答問題。如果上下文中沒有相關資訊，請說「資料中未提及」。\n\n"
        "上下文：\n{context}\n\n"
        "問題：{question}\n\n"
        "回答："
    )
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain


def main() -> None:
    # 確保有文件目錄（示範用）
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)
    sample = docs_dir / "sample.txt"
    if not sample.exists():
        sample.write_text(
            "Python 3.12 於 2023 年 10 月發布。\n"
            "主要新特性包括 PEP 695 type alias 語法和改進的錯誤訊息。\n"
            "Python 3.13 加入了實驗性的 free-threaded 模式。\n",
            encoding="utf-8",
        )

    chain = build_rag_chain(str(docs_dir))

    questions = [
        "Python 3.12 有什麼新特性？",
        "free-threaded 模式是哪個版本加入的？",
    ]
    for q in questions:
        print(f"\nQ: {q}")
        answer = chain.invoke(q)
        print(f"A: {answer}")


if __name__ == "__main__":
    main()
```

---

## 範例 2：LlamaIndex Agent with Tools

```python
"""LlamaIndex Agent — 使用工具回答問題"""
# pip install llama-index llama-index-llms-openai
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.openai import OpenAI


def calculate_bmi(weight_kg: float, height_m: float) -> str:
    """計算 BMI 值"""
    bmi = weight_kg / (height_m ** 2)
    if bmi < 18.5:
        category = "過輕"
    elif bmi < 24:
        category = "正常"
    elif bmi < 27:
        category = "過重"
    else:
        category = "肥胖"
    return f"BMI = {bmi:.1f}，分類為「{category}」"


def search_nutrition(food: str) -> str:
    """查詢食物營養資訊（模擬）"""
    nutrition_db: dict[str, str] = {
        "雞胸肉": "每 100g：蛋白質 31g、脂肪 3.6g、熱量 165 kcal",
        "白飯": "每 100g：碳水 28g、蛋白質 2.7g、熱量 130 kcal",
        "蘋果": "每 100g：碳水 14g、纖維 2.4g、熱量 52 kcal",
    }
    return nutrition_db.get(food, f"找不到「{food}」的營養資訊")


def main() -> None:
    # 建立工具
    bmi_tool = FunctionTool.from_defaults(fn=calculate_bmi)
    nutrition_tool = FunctionTool.from_defaults(fn=search_nutrition)

    # 建立 ReAct Agent
    llm = OpenAI(model="gpt-4o-mini", temperature=0)
    agent = ReActAgent.from_tools(
        tools=[bmi_tool, nutrition_tool],
        llm=llm,
        verbose=True,  # 顯示思考過程
    )

    # 對話
    response = agent.chat("我身高 175cm 體重 70kg，BMI 是多少？")
    print(f"\n最終回答: {response}")

    response = agent.chat("推薦我一道高蛋白食物，查一下雞胸肉的營養")
    print(f"\n最終回答: {response}")


if __name__ == "__main__":
    main()
```

---

## 範例 3：Transformers 本地推論（分類 + 生成）

```python
"""Transformers Pipeline — 無需 API Key 的本地推論"""
# pip install transformers torch sentencepiece
from transformers import pipeline


def sentiment_analysis() -> None:
    """情感分析"""
    classifier = pipeline(
        "sentiment-analysis",
        model="distilbert-base-uncased-finetuned-sst-2-english",
    )
    texts = [
        "I love this new Python feature!",
        "The documentation is confusing and outdated.",
        "It works, but nothing special.",
    ]
    results = classifier(texts)
    for text, result in zip(texts, results):
        print(f"  {result['label']:>8} ({result['score']:.3f}): {text}")


def text_generation() -> None:
    """文字生成"""
    generator = pipeline(
        "text-generation",
        model="gpt2",
        max_new_tokens=50,
        do_sample=True,
        temperature=0.7,
    )
    prompt = "The future of artificial intelligence is"
    outputs = generator(prompt, num_return_sequences=2)
    for i, output in enumerate(outputs):
        print(f"  [{i+1}] {output['generated_text']}")


def question_answering() -> None:
    """閱讀理解"""
    qa = pipeline(
        "question-answering",
        model="distilbert-base-cased-distilled-squad",
    )
    context = (
        "Python was created by Guido van Rossum and first released in 1991. "
        "It emphasizes code readability with significant indentation. "
        "Python 3.12 introduced type parameter syntax and improved error messages."
    )
    questions = [
        "Who created Python?",
        "When was Python first released?",
        "What did Python 3.12 introduce?",
    ]
    for q in questions:
        answer = qa(question=q, context=context)
        print(f"  Q: {q}")
        print(f"  A: {answer['answer']} (confidence: {answer['score']:.3f})")


def main() -> None:
    print("=== 情感分析 ===")
    sentiment_analysis()

    print("\n=== 文字生成 ===")
    text_generation()

    print("\n=== 閱讀理解 ===")
    question_answering()


if __name__ == "__main__":
    main()
```

---

## 範例 4：Embedding + Cosine Similarity 語意搜尋

```python
"""手動實作語意搜尋 — 不依賴向量資料庫"""
# pip install langchain-openai numpy
import numpy as np
from langchain_openai import OpenAIEmbeddings


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """計算兩個向量的 cosine similarity"""
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    return float(dot / norm) if norm > 0 else 0.0


def semantic_search(
    query: str,
    corpus: list[str],
    embeddings_model: OpenAIEmbeddings,
    top_k: int = 3,
) -> list[tuple[str, float]]:
    """語意搜尋：回傳最相關的文件"""
    # 一次嵌入所有文件 + query
    all_texts = corpus + [query]
    all_vectors = embeddings_model.embed_documents(all_texts)

    query_vec = np.array(all_vectors[-1])
    corpus_vecs = [np.array(v) for v in all_vectors[:-1]]

    # 計算相似度並排序
    scores = [
        (text, cosine_similarity(query_vec, vec))
        for text, vec in zip(corpus, corpus_vecs)
    ]
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_k]


def main() -> None:
    corpus = [
        "Python 是一種通用程式語言，強調可讀性",
        "機器學習是人工智慧的一個子領域",
        "Docker 容器化技術讓應用部署更一致",
        "RAG 結合了檢索與生成來回答問題",
        "PostgreSQL 是強大的開源關聯式資料庫",
        "FastAPI 是高效能的 Python Web 框架",
        "向量搜尋使用嵌入空間中的距離來尋找相似文件",
    ]

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    queries = ["如何建立 AI 應用？", "資料庫技術"]
    for query in queries:
        print(f"\n查詢: {query}")
        results = semantic_search(query, corpus, embeddings, top_k=3)
        for text, score in results:
            print(f"  [{score:.3f}] {text}")


if __name__ == "__main__":
    main()
```

---

## 範例 5：ONNX Runtime 高效推論

```python
"""ONNX Runtime 推論 — 比 PyTorch 更快的部署選項"""
# pip install onnxruntime optimum[onnxruntime] transformers
from pathlib import Path

from optimum.onnxruntime import ORTModelForSequenceClassification
from transformers import AutoTokenizer, pipeline


def export_and_inference() -> None:
    """匯出模型到 ONNX 並進行推論"""
    model_name = "distilbert-base-uncased-finetuned-sst-2-english"
    onnx_dir = Path("onnx_model")

    # 載入 ONNX 模型（首次會自動匯出）
    model = ORTModelForSequenceClassification.from_pretrained(
        model_name,
        export=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    # 儲存到本地
    model.save_pretrained(onnx_dir)
    tokenizer.save_pretrained(onnx_dir)

    # 使用 pipeline 推論
    onnx_pipeline = pipeline(
        "sentiment-analysis",
        model=model,
        tokenizer=tokenizer,
    )

    texts = [
        "ONNX Runtime makes inference much faster!",
        "I don't like slow model loading times.",
    ]
    results = onnx_pipeline(texts)
    for text, result in zip(texts, results):
        print(f"  {result['label']} ({result['score']:.3f}): {text}")


def main() -> None:
    print("=== ONNX Runtime 推論 ===")
    export_and_inference()


if __name__ == "__main__":
    main()
```
