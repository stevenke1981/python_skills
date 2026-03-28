# Python Skills Index

> AI 編碼助理專用的 Python 技能包索引。每個 skill 包含 SKILL.md 主文件與 references/ 參考資料。

## 技能列表

| Skill ID | 主題 | 說明 | Python 版本 |
|----------|------|------|-------------|
| [py-modern](py-modern/SKILL.md) | 現代語法與特性 | Python 3.12+/3.13+ 新語法：match-case、PEP 695 generics、PEP 701 f-string、type hints 改進、free-threaded Python | 3.12+ |
| [py-async](py-async/SKILL.md) | 非同步程式設計 | asyncio、TaskGroup 結構化並行、async generators、aiohttp、Semaphore、Queue | 3.11+ |
| [py-data](py-data/SKILL.md) | 資料處理與分析 | pandas 2.x Arrow/CoW、Polars lazy、NumPy、DuckDB、narwhals 跨 DataFrame 抽象層 | 3.10+ |
| [py-testing](py-testing/SKILL.md) | 測試與品質保證 | pytest fixtures/parametrize/mocking、hypothesis property-based testing、coverage、async testing | 3.10+ |
| [py-packaging](py-packaging/SKILL.md) | 打包與發布 | pyproject.toml PEP 621、uv 工作流、ruff linting、build backends、Trusted Publisher 發布 | 3.8+ |
| [py-patterns](py-patterns/SKILL.md) | 設計模式與架構 | SOLID 原則、Protocol vs ABC、DI、immutable data、Repository/Strategy/Factory 模式 | 3.10+ |
| [py-cli](py-cli/SKILL.md) | CLI 工具開發 | Typer type-driven 設計、subcommands、Rich Console 美化、interactive Prompt、Textual TUI | 3.10+ |
| [py-perf](py-perf/SKILL.md) | 效能優化 | cProfile/Pyinstrument/line_profiler 分析、tracemalloc 記憶體、資料結構選擇、最佳化模式 | 3.10+ |
| [py-ai](py-ai/SKILL.md) | AI/ML 整合 | RAG pipeline、embeddings、agents/tool calling、prompt engineering、LangChain/LlamaIndex/Transformers | 3.10+ |
| [py-web](py-web/SKILL.md) | Web 開發 | FastAPI routing/DI、Pydantic v2 驗證、SQLAlchemy 2.0 async ORM、HTTPX、JWT 認證 | 3.9+ |
| [py-gui](py-gui/SKILL.md) | GUI 桌面應用 | tkinter/ttk、CustomTkinter 現代 UI、PySide6/PyQt6 Qt 綁定、事件迴圈、多執行緒 | 3.10+ |
| [py-network](py-network/SKILL.md) | 網路程式設計 | socket TCP/UDP、asyncio streams、HTTP httpx/aiohttp、WebSocket、SSL/TLS、DNS | 3.10+ |

## 目錄結構

```
python-skills/
├── index.md                    ← 本檔案
├── claude.md                   ← Agent 規範文件
├── py-modern/
│   ├── SKILL.md
│   └── references/
│       ├── examples.md
│       ├── cheatsheet.md
│       └── pitfalls.md
├── py-async/
│   ├── SKILL.md
│   └── references/
│       ├── examples.md
│       ├── cheatsheet.md
│       └── pitfalls.md
├── py-data/
│   ├── SKILL.md
│   └── references/
│       ├── examples.md
│       ├── cheatsheet.md
│       └── pitfalls.md
├── py-testing/
│   ├── SKILL.md
│   └── references/
│       ├── examples.md
│       ├── cheatsheet.md
│       └── pitfalls.md
├── py-packaging/
│   ├── SKILL.md
│   └── references/
│       ├── examples.md
│       ├── cheatsheet.md
│       └── pitfalls.md
├── py-patterns/
│   ├── SKILL.md
│   └── references/
│       ├── examples.md
│       ├── cheatsheet.md
│       └── pitfalls.md
├── py-cli/
│   ├── SKILL.md
│   └── references/
│       ├── examples.md
│       ├── cheatsheet.md
│       └── pitfalls.md
├── py-perf/
│   ├── SKILL.md
│   └── references/
│       ├── examples.md
│       ├── cheatsheet.md
│       └── pitfalls.md
├── py-ai/
│   ├── SKILL.md
│   └── references/
│       ├── examples.md
│       ├── cheatsheet.md
│       └── pitfalls.md
├── py-web/
│   ├── SKILL.md
│   └── references/
│       ├── examples.md
│       ├── cheatsheet.md
│       └── pitfalls.md
├── py-gui/
│   ├── SKILL.md
│   └── references/
│       ├── examples.md
│       ├── cheatsheet.md
│       └── pitfalls.md
└── py-network/
    ├── SKILL.md
    └── references/
        ├── examples.md
        ├── cheatsheet.md
        └── pitfalls.md
```

## 使用方式

每個 skill 的 `SKILL.md` 包含：
- **Quick Start** — 30 秒上手最小範例
- **核心概念** — 3-5 個核心概念，搭配程式碼片段
- **實戰 Patterns** — 場景驅動的模式與注意事項
- **工具鏈推薦** — 相關工具的安裝與用途
- **版本相容性** — Python 版本支援表

`references/` 目錄包含：
- `examples.md` — 完整可運行的範例程式碼
- `cheatsheet.md` — 速查表
- `pitfalls.md` — 常見錯誤與解法

## 產出規格

- 所有程式碼使用 Python 3.12+ 語法
- 必須包含 type hints
- 註解使用繁體中文，變數名使用英文
- 使用 ruff 格式化風格
- SKILL.md 不超過 400 行
