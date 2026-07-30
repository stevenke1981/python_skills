# py-ai 速查表

> 本文件補充 [`../SKILL.md`](../SKILL.md)。SDK、模型名稱、價格與框架 API 變動快速；以專案 lockfile 與供應商官方文件為準。

## 最小架構

```text
UI / API
   ↓
Application service
   ↓
ChatBackend / EmbeddingBackend / ToolPolicy (Protocol)
   ↓
Provider adapter / local runtime / vector store
```

核心規則：

- model、provider、base URL、timeout 與 token budget 由設定注入。
- 業務層不 import 特定供應商 SDK type。
- 所有模型輸出視為不可信資料，先驗證再使用。
- 外部文件與工具輸出也可能含 prompt injection。
- 寫入、刪除、付款、寄信與部署需明確授權。

## 設定範例

```bash
export AI_PROVIDER="provider-name"
export AI_MODEL="provider-model-id"
export AI_BASE_URL="https://api.example.invalid/v1"
export AI_API_KEY="..."
export AI_TIMEOUT_SECONDS="30"
export AI_MAX_OUTPUT_TOKENS="800"
```

不要在 shell command、source code、trace 或錯誤訊息中回顯 key。正式環境優先使用 secret manager。

## Provider Adapter Checklist

- [ ] request message mapping
- [ ] model/base URL/config validation
- [ ] connect/read/write/pool timeout
- [ ] bounded retry + jitter
- [ ] usage/token extraction
- [ ] streaming event normalization
- [ ] structured output support/fallback
- [ ] provider error → stable application error
- [ ] cancellation/client disconnect
- [ ] log/trace redaction

## Structured Output

```python
from typing import Literal

from pydantic import BaseModel, Field


class Result(BaseModel):
    category: Literal["billing", "technical", "other"]
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str = Field(min_length=1, max_length=500)


result = Result.model_validate_json(raw_json)
```

檢查：

- enum、長度、範圍與 required field
- invalid JSON 的有限次修復
- schema version
- deterministic calculation 留給程式碼
- validation failure 不可靜默填值

## Prompt 結構

```text
SYSTEM
- 任務與角色
- 可使用的資料來源
- 禁止行為與安全邊界
- 輸出 schema
- 資料不足時如何回答

USER
- 使用者要求

CONTEXT (untrusted)
- 文件、檢索結果、工具輸出
- 明確標示來源與邊界
```

不要把 untrusted context 拼接成 system instruction。

## RAG Pipeline

```text
ingest
  → parse structure
  → attach source/version/permission metadata
  → chunk
  → embed/index
  → retrieve with permission filter
  → rerank (optional)
  → generate with citations
  → validate groundedness
```

### Ingestion Checklist

- [ ] source ID、版本、段落位置
- [ ] tenant／ACL metadata
- [ ] parse failure 統計
- [ ] duplicate/near-duplicate handling
- [ ] chunk strategy 依文件結構
- [ ] embedding/index version
- [ ] 可重建與可刪除

### Retrieval Checklist

- [ ] keyword/vector/hybrid baseline
- [ ] permission filter 在生成前執行
- [ ] top-k 由 eval 決定
- [ ] reranker 只在有增益時加入
- [ ] 查無證據允許拒答
- [ ] citation 真正支持結論

### Eval Metrics

| 層次 | 指標 |
|---|---|
| Retrieval | recall@k、precision@k、MRR、權限隔離 |
| Generation | groundedness、citation correctness、usefulness |
| Operation | latency、token、成本、timeout、error rate |
| Safety | injection success、secret leakage、tool authorization |

## Tool Calling

### Tool Schema

```python
from typing import Literal

from pydantic import BaseModel, Field


class ToolRequest(BaseModel):
    action: Literal["read", "list"]
    relative_path: str = Field(min_length=1, max_length=240)
```

### Executor Checklist

- [ ] allowlist tool names
- [ ] executor 重新驗證參數
- [ ] path/URL/tenant boundary
- [ ] timeout、step、token、cost limit
- [ ] idempotency／duplicate protection
- [ ] dry-run／human confirmation
- [ ] result size limit
- [ ] audit log with redaction
- [ ] tool output 仍視為 untrusted

## Streaming

```text
provider event
  → normalized internal event
  → bounded queue
  → client
```

- client disconnect 時取消上游工作。
- queue 有上限，slow client 有 drop/disconnect policy。
- partial token 不是已驗證的 structured result。
- 最終結果完成後再做 schema validation。

## Async Fan-out

```python
import asyncio


async def bounded_call(item: str, semaphore: asyncio.Semaphore) -> str:
    async with semaphore:
        return await backend.generate(item)


async def run_batch(items: list[str], limit: int = 5) -> list[str]:
    semaphore = asyncio.Semaphore(limit)
    async with asyncio.TaskGroup() as group:
        tasks = [
            group.create_task(bounded_call(item, semaphore))
            for item in items
        ]
    return [task.result() for task in tasks]
```

大量 input 不要一次建立所有 task；改用 bounded queue。retry budget 必須包含在整體 deadline。

## 本地模型

### 啟動前檢查

- [ ] model license
- [ ] tokenizer/model format
- [ ] VRAM/RAM 與 context length
- [ ] CUDA/ROCm/Metal/CPU backend
- [ ] quantization quality eval
- [ ] cold start 與 cache disk
- [ ] OOM/corrupt weights fallback
- [ ] concurrent request limit

### GPU 選擇

不要只寫 `device="cuda"` 就假設可用。啟動時偵測 backend、記錄實際裝置，並提供 CPU/remote fallback。

## 模型與供應商選擇

| 需求 | 評估項目 |
|---|---|
| 高品質推理 | task eval、tool/JSON reliability、latency、cost |
| 低成本大量分類 | small model accuracy、batch、cache、fallback |
| 多語言 RAG | embedding/retrieval eval、tokenization、reranker |
| 離線與隱私 | license、hardware、data residency、operations |
| 高吞吐服務 | continuous batching、KV cache、queue、autoscaling |
| 長上下文 | effective retrieval/attention quality，不只看宣告上限 |

不要在共用 skill 固定「最好」模型；以當前 eval 與官方支援決定。

## 成本控制

- token/input size 上限
- model routing 與 fallback
- prompt/context 去重
- embedding/index 增量更新
- cache 有 tenant/key/version 邊界
- per-request/per-user budget
- usage metric 與 anomaly alert
- live eval 與外部 API 測試 opt-in

價格不可硬編碼為長期事實；從核准設定或當前官方資料取得。

## Observability

記錄：

- request/trace ID
- provider/model/config version
- prompt template version
- retrieval source IDs（依隱私遮蔽）
- tool name、授權來源與結果狀態
- input/output token 或等效 usage
- latency、retry、timeout、fallback
- schema validation／safety failure

不要記錄完整秘密、敏感文件、authorization header 或不必要的 prompt/body。

## 測試矩陣

| 測試 | 使用方式 |
|---|---|
| Unit | fake backend、parser、policy、routing |
| Contract | adapter request/response mapping |
| Eval | 固定 dataset 比較模型/prompt/retriever |
| Adversarial | prompt injection、tool escalation、secret leakage |
| Failure | timeout、rate limit、invalid JSON、OOM、disconnect |
| Live | opt-in、有限成本、核准帳號與環境 |

## 發布前 Checklist

- [ ] model/provider 可由設定替換
- [ ] schema validation 與有限修復
- [ ] tool allowlist、最小權限與確認
- [ ] RAG ACL、citation 與拒答
- [ ] eval dataset、基準與 regression threshold
- [ ] timeout、retry、queue、step、token、cost limit
- [ ] secret/data retention/region policy
- [ ] tracing、redaction、fallback 與 rollback
