---
name: py-ai
description: >
  Design and implement Python AI applications with provider-neutral LLM clients, local models, structured outputs, RAG, embeddings, reranking, tool calling, agents, streaming, evaluation, observability, and GPU inference. Use when building or reviewing model-powered workflows that require security boundaries, prompt-injection defenses, cost controls, fallback behavior, or reliable production integration.
compatibility: Agent Skills-compatible. Model, SDK, framework, CUDA, and serving APIs change frequently; inspect the project's lockfile and provider documentation before coding.
metadata:
  author: stevenke1981
  version: "2.0.0"
  last-reviewed: "2026-07-30"
---

# Python AI／LLM 應用工程

## 目標與邊界

用此 skill 建立可測試、可替換供應商、具明確工具權限與輸出契約的 AI 應用。預設先用最少抽象完成工作；只有在需要複雜 orchestration、retrieval 或 tracing 時才導入框架。

若任務只是一般 DataFrame 處理，使用 `py-data`；若主要交付物是 HTTP API，以 `py-web` 為主、`py-ai` 為支援。

## 執行流程

1. **定義可驗收任務**：輸入、輸出 schema、品質門檻、延遲、成本、隱私與失敗模式。
2. **建立基準與 eval set**：先收集代表性、邊界與對抗案例，避免只靠主觀試聊。
3. **選擇最小架構**：單次呼叫優先直接 SDK；需要多步狀態、RAG 或工具編排時才使用框架。
4. **外部化模型設定**：provider、base URL、model、timeout、重試、token budget 與 sampling 由設定注入。
5. **限制信任邊界**：外部文件、網頁、使用者文字與模型輸出皆視為不可信資料。
6. **結構化與驗證輸出**：使用 schema 驗證；驗證失敗時有限次修復或明確失敗，不靜默猜測。
7. **限制工具副作用**：allowlist、參數驗證、最小權限、dry-run、人工確認與 audit log。
8. **加入觀測與回退**：記錄延遲、token、成本、retrieval、tool calls、錯誤類型與 fallback。
9. **以 eval 決定發布**：比較基準、回歸、風險與成本，不以單一 demo 成功作結論。

## 架構選擇

| 需求 | 優先方案 |
|---|---|
| 單一 prompt、structured output | 供應商官方 SDK + Pydantic |
| 多供應商切換 | 自製小型 Protocol/adapter；不要讓業務層綁定 SDK 類型 |
| 文件檢索與引用 | 明確的 ingest、chunk、retrieve、rerank、cite pipeline |
| 多步 agent 狀態 | 可持久化 state machine 或 workflow engine |
| 高吞吐本地服務 | 專用 inference server；應用透過穩定 API 呼叫 |
| 離線桌面工具 | llama.cpp、ONNX Runtime 或適合硬體的本地 runtime |
| 需要長期追蹤品質 | 固定 eval dataset、trace、版本化 prompt 與模型設定 |

不要只因熱門就導入 LangChain、LlamaIndex 或大型 agent framework。先確認它解決的是實際 orchestration 問題，而不是增加無法測試的抽象。

## Provider-neutral 邊界

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True, slots=True)
class Message:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class GenerationOptions:
    model: str
    timeout_seconds: float = 30.0
    max_output_tokens: int = 800


class ChatBackend(Protocol):
    async def generate(
        self,
        messages: Sequence[Message],
        options: GenerationOptions,
    ) -> str: ...
```

業務邏輯依賴 `ChatBackend`，供應商 adapter 負責：

- 認證與 base URL
- SDK message 格式轉換
- timeout、重試與 error mapping
- token/usage extraction
- streaming event 正規化
- structured output 能力差異

模型名稱不可硬編碼在 domain/service；從環境或設定檔注入，並在啟動時驗證是否存在。

## 結構化輸出

```python
from typing import Literal

from pydantic import BaseModel, Field, ValidationError


class Classification(BaseModel):
    label: Literal["billing", "technical", "other"]
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(max_length=500)


def parse_classification(raw_json: str) -> Classification:
    try:
        return Classification.model_validate_json(raw_json)
    except ValidationError as exc:
        raise ValueError("model returned invalid classification JSON") from exc
```

規則：

- schema 同時限制型別、長度、範圍與 enum。
- 不把「JSON 看起來正確」當作驗證。
- 修復重試必須有次數與成本上限。
- 需要精確數值、法律或財務決策時，模型只產生建議或候選，最終計算交給 deterministic code。

## RAG 工作流

### Ingestion

1. 保留來源 ID、版本、時間、權限與段落位置。
2. 先解析結構，再 chunk；不要只依固定字元數切割。
3. 對表格、程式碼、標題與 metadata 使用適合的策略。
4. 去除重複與不可索引內容，記錄 parse failures。
5. embedding 與 index 版本必須可重建。

### Retrieval

- 建立 keyword、vector 或 hybrid baseline。
- 先量測 recall，再決定是否加入 reranker。
- 依文件權限在 retrieval 前過濾，不能只在生成後遮蔽。
- 對查無證據的問題允許回答「資料不足」。
- 回答附來源 ID/片段位置；引用內容必須真的支持結論。

### Evaluation

至少量測：

- retrieval recall / precision
- citation correctness
- groundedness / unsupported claim rate
- answer usefulness
- latency、token 與每次查詢成本
- 權限隔離與 prompt-injection 對抗案例

## Tool Calling 與 Agent 安全

工具 schema 應窄化參數：

```python
from typing import Literal

from pydantic import BaseModel, Field


class FileAction(BaseModel):
    action: Literal["read", "list"]
    relative_path: str = Field(pattern=r"^[^\\/](?!.*\.\.).*$", max_length=240)
```

仍須在執行層重新驗證路徑；schema 不是完整 sandbox。

安全規則：

- 工具必須 allowlist，預設不可寫入、刪除、付款、寄信或部署。
- 高影響操作要求明確授權，必要時逐次確認。
- 工具輸出也可能包含 prompt injection，不得當成系統指令。
- 限制步數、執行時間、token、並行數與總成本。
- 記錄 tool name、經遮蔽的參數、結果、授權來源與錯誤。
- 對重試操作確認冪等性；避免 agent 重複建立或付款。

## Streaming 與並行

- 將供應商事件轉成自家穩定 event types。
- client disconnect 時取消上游生成與工具工作。
- 使用 bounded queue，避免慢 client 造成無限記憶體累積。
- 不把 token stream 當作已驗證的最終 structured output。
- 對 rate limit、timeout 與 transient error 使用有上限的退避；尊重服務端 retry hint。

## 本地模型與 GPU

導入本地推論前確認：

- 模型授權、權重格式與 tokenizer 相容性
- VRAM/RAM、context length、KV cache 與 batch 需求
- CUDA、ROCm、Metal 或 CPU runtime
- quantization 對品質與速度的影響
- cold start、模型下載、cache 路徑與磁碟空間
- GPU 不可用或 OOM 時的 CPU/遠端 fallback

本地模型仍需同樣的輸出驗證、工具授權、eval 與隱私規則。不要因為離線就假設輸入可信。

## 祕密與資料保護

- API key 只從 secret manager 或環境變數取得。
- log 與 trace 遮蔽 authorization header、cookie、token、個資與文件機密。
- 對第三方模型傳送資料前，明確知道 retention、training、region 與合規條件。
- 建立資料分類與 provider routing；敏感資料可限制在本地或核准服務。
- cache key 不包含裸機密，cache value 有存活時間與存取控制。

## 驗證方式

- 單元測試 adapter、parser、tool policy 與 retrieval filtering。
- 使用 fake backend 測試業務邏輯，不讓 CI 依賴付費 API。
- 建立少量 opt-in live tests 驗證供應商整合。
- 對固定 eval set 比較 prompt、model、retriever 與 reranker 版本。
- 對 timeout、rate limit、invalid JSON、tool failure、disconnect 與 OOM 注入故障。

## 交付標準

- model/provider 可由設定替換，業務層不綁定特定 SDK 類型。
- 輸出經 schema 驗證，修復與重試有上限。
- RAG 可追溯來源、權限與 index 版本，能拒答無證據問題。
- 工具有 allowlist、最小權限、參數重驗證與高風險確認。
- 已建立代表性 eval、回歸門檻、成本與延遲觀測。
- 祕密與敏感資料不出現在程式碼、錯誤訊息或 trace。
- 本地 GPU 與遠端 API 都有明確 fallback 與資源上限。

## 延伸閱讀

- [完整範例](references/examples.md)
- [速查表](references/cheatsheet.md)
- [常見陷阱](references/pitfalls.md)

## 版本相容性

| 環境 | 建議 |
|---|---|
| Python 3.14 | 穩定維護基準；先確認 ML/native wheels 與 GPU runtime |
| Python 3.10–3.13 | 支援；依專案鎖定版本選 SDK 與框架 API |
| 供應商 SDK | 視為易變依賴；以 lockfile、官方文件與 contract tests 驗證 |
| 本地 runtime | 模型格式、量化與硬體後端需獨立驗證 |
| 預覽模型/API | 只作 opt-in 實驗，必須有穩定 fallback |
