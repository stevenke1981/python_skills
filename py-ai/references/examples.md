# py-ai 完整範例

> 本文件補充 [`../SKILL.md`](../SKILL.md)。範例刻意把 provider/model 放在設定邊界，避免共用 skill 綁定會快速失效的模型名稱或 SDK。

## 範例 1：Provider-neutral Structured Output

安裝：

```bash
python -m pip install "pydantic>=2"
```

```python
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol, Sequence

from pydantic import BaseModel, Field, ValidationError
from typing_extensions import Literal


@dataclass(frozen=True, slots=True)
class Message:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True, slots=True)
class GenerationOptions:
    model: str
    timeout_seconds: float = 30.0
    max_output_tokens: int = 500


class ChatBackend(Protocol):
    async def generate(
        self,
        messages: Sequence[Message],
        options: GenerationOptions,
    ) -> str: ...


class TicketClassification(BaseModel):
    category: Literal["billing", "technical", "other"]
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str = Field(min_length=1, max_length=200)


class FakeBackend:
    """單元測試用；真實 adapter 只需實作同一 Protocol。"""

    async def generate(
        self,
        messages: Sequence[Message],
        options: GenerationOptions,
    ) -> str:
        del messages, options
        return (
            '{"category":"technical","confidence":0.94,'
            '"summary":"Application cannot connect to the server."}'
        )


async def classify_ticket(
    backend: ChatBackend,
    text: str,
    options: GenerationOptions,
) -> TicketClassification:
    messages = [
        Message(
            role="system",
            content=(
                "Classify the ticket. Return JSON matching the requested schema. "
                "Do not invent fields."
            ),
        ),
        Message(role="user", content=text),
    ]
    raw = await asyncio.wait_for(
        backend.generate(messages, options),
        timeout=options.timeout_seconds,
    )
    try:
        return TicketClassification.model_validate_json(raw)
    except ValidationError as exc:
        raise ValueError("backend returned invalid classification JSON") from exc


async def main() -> None:
    result = await classify_ticket(
        FakeBackend(),
        "The desktop client says connection refused.",
        GenerationOptions(model="test-model"),
    )
    print(result.model_dump())


if __name__ == "__main__":
    asyncio.run(main())
```

真實 provider adapter 應另外處理認證、base URL、timeout、retry、usage、streaming 與錯誤映射；application service 不需要改動。

---

## 範例 2：安全的 Tool Executor

模型只產生「工具請求草稿」，executor 再次驗證 canonical path 與權限。

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class FileToolRequest(BaseModel):
    action: Literal["read", "list"]
    relative_path: str = Field(min_length=1, max_length=240)


class FileToolExecutor:
    def __init__(self, root: Path, *, max_read_bytes: int = 64_000) -> None:
        self._root = root.resolve(strict=True)
        self._max_read_bytes = max_read_bytes

    def _resolve(self, relative_path: str) -> Path:
        candidate = (self._root / relative_path).resolve(strict=True)
        try:
            candidate.relative_to(self._root)
        except ValueError as exc:
            raise PermissionError("path escapes the allowed root") from exc
        return candidate

    def execute(self, request: FileToolRequest) -> dict[str, object]:
        path = self._resolve(request.relative_path)

        if request.action == "list":
            if not path.is_dir():
                raise NotADirectoryError(path)
            return {
                "entries": sorted(child.name for child in path.iterdir()),
            }

        if not path.is_file():
            raise FileNotFoundError(path)
        if path.stat().st_size > self._max_read_bytes:
            raise ValueError("file exceeds the configured read limit")
        return {"content": path.read_text(encoding="utf-8")}


def main() -> None:
    executor = FileToolExecutor(Path("."))
    raw_model_output = '{"action":"list","relative_path":"."}'
    request = FileToolRequest.model_validate_json(raw_model_output)
    print(json.dumps(executor.execute(request), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

仍需依應用加入 tenant/resource 授權、symlink policy、audit log、deadline 與人工確認。Schema 本身不是 sandbox。

---

## 範例 3：本地多語 Embedding 搜尋

安裝：

```bash
python -m pip install sentence-transformers numpy
```

```python
from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
from sentence_transformers import SentenceTransformer


@dataclass(frozen=True, slots=True)
class Document:
    source_id: str
    text: str


@dataclass(frozen=True, slots=True)
class SearchResult:
    source_id: str
    text: str
    score: float


def search(
    model: SentenceTransformer,
    documents: list[Document],
    query: str,
    *,
    top_k: int,
) -> list[SearchResult]:
    if top_k < 1:
        raise ValueError("top_k must be positive")

    texts = [document.text for document in documents]
    document_vectors = model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    query_vector = model.encode(
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True,
    )[0]

    scores = np.asarray(document_vectors) @ np.asarray(query_vector)
    order = np.argsort(scores)[::-1][:top_k]
    return [
        SearchResult(
            source_id=documents[index].source_id,
            text=documents[index].text,
            score=float(scores[index]),
        )
        for index in order
    ]


def main() -> None:
    model_id = os.environ.get(
        "EMBEDDING_MODEL",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    model = SentenceTransformer(model_id)
    documents = [
        Document("python", "Python 3.14 introduces deferred annotation evaluation."),
        Document("rag", "RAG combines retrieval evidence with generation."),
        Document("network", "TCP is a byte stream and needs message framing."),
    ]
    for result in search(model, documents, "如何用檢索改善生成？", top_k=2):
        print(f"{result.score:.3f} {result.source_id}: {result.text}")


if __name__ == "__main__":
    main()
```

生產環境應 pin 核准的 model revision，保存 embedding/index version，並用標註資料量測 retrieval quality；不要只看單一查詢。

---

## 範例 4：RAG Citation Eval Harness

此範例不依賴特定模型，專注於可重跑的評估資料格式。

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EvalCase:
    case_id: str
    question: str
    required_sources: frozenset[str]
    expected_phrase: str


@dataclass(frozen=True, slots=True)
class RagAnswer:
    text: str
    cited_sources: frozenset[str]


@dataclass(frozen=True, slots=True)
class EvalResult:
    case_id: str
    phrase_found: bool
    required_sources_present: bool

    @property
    def passed(self) -> bool:
        return self.phrase_found and self.required_sources_present


def evaluate(case: EvalCase, answer: RagAnswer) -> EvalResult:
    return EvalResult(
        case_id=case.case_id,
        phrase_found=case.expected_phrase.casefold() in answer.text.casefold(),
        required_sources_present=(
            case.required_sources <= answer.cited_sources
        ),
    )


def main() -> None:
    case = EvalCase(
        case_id="python-version",
        question="What is the stable baseline in this repository?",
        required_sources=frozenset({"AGENTS.md"}),
        expected_phrase="Python 3.14",
    )
    answer = RagAnswer(
        text="The repository uses Python 3.14 as its stable maintenance baseline.",
        cited_sources=frozenset({"AGENTS.md"}),
    )
    result = evaluate(case, answer)
    print(result)
    raise SystemExit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
```

實際 eval 還應加入 retrieval recall、citation span correctness、unsupported claims、權限隔離、latency 與 cost。

---

## 範例 5：本地 Transformers Runtime（模型由設定提供）

安裝方式依 CPU/GPU 平台選擇核准的 PyTorch／Transformers 套件。執行前設定：

```bash
export HF_MODEL_ID="your-approved-model-id"
export HF_TASK="text-classification"
# 正式環境另設定 pin 到 commit/tag 的 HF_REVISION
```

```python
from __future__ import annotations

import os

import torch
from transformers import pipeline


def build_pipeline():
    model_id = os.environ["HF_MODEL_ID"]
    task = os.environ.get("HF_TASK", "text-classification")
    revision = os.environ.get("HF_REVISION", "main")
    device = 0 if torch.cuda.is_available() else -1

    return pipeline(
        task=task,
        model=model_id,
        revision=revision,
        device=device,
        trust_remote_code=False,
    )


def main() -> None:
    inference = build_pipeline()
    print(inference("This deployment is reliable and easy to operate."))


if __name__ == "__main__":
    main()
```

正式部署應在 build/release 階段預先下載並驗證權重，記錄 license/hash/revision，測試 GPU OOM 與 CPU/remote fallback，不在每個 request 重新載入模型。

---

## 範例 6：有界 Async Batch

```python
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from typing import TypeVar


T = TypeVar("T")
R = TypeVar("R")


async def bounded_map(
    func: Callable[[T], Awaitable[R]],
    items: Sequence[T],
    *,
    concurrency: int,
    deadline_seconds: float,
) -> list[R]:
    if concurrency < 1:
        raise ValueError("concurrency must be positive")

    semaphore = asyncio.Semaphore(concurrency)

    async def run(item: T) -> R:
        async with semaphore:
            return await func(item)

    async with asyncio.timeout(deadline_seconds):
        async with asyncio.TaskGroup() as group:
            tasks = [group.create_task(run(item)) for item in items]
    return [task.result() for task in tasks]
```

大量 input 改用 bounded queue，避免先建立全部 task。Provider retry、rate limit 與 token/cost budget 仍需納入同一 deadline。
