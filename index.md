# Python Skills Index

> 先依交付物選擇一個主要 skill，再按需要載入支援 skill。不要一次載入全部內容。

## 技能路由表

| Skill | 主要觸發情境 | 不應作為主要 skill 的情境 | 建議最低 Python |
|---|---|---|---:|
| [`py-modern`](py-modern/SKILL.md) | Python 版本升級、現代語法、typing、PEP、free-threaded | 單純打包或框架 API 問題 | 3.12 |
| [`py-async`](py-async/SKILL.md) | asyncio、TaskGroup、取消、逾時、Queue、並行 I/O | 一般同步 CLI 或 CPU benchmark | 3.11 |
| [`py-data`](py-data/SKILL.md) | DataFrame、ETL、CSV/Parquet、schema、資料品質 | 一般 API 路由或 GUI | 3.10 |
| [`py-testing`](py-testing/SKILL.md) | pytest、fixture、mock、property tests、coverage、flaky test | 實作產品功能本身 | 3.10 |
| [`py-packaging`](py-packaging/SKILL.md) | pyproject.toml、依賴、lock、wheel、sdist、PyPI、CI 發布 | 應用內部架構設計 | 3.10 |
| [`py-patterns`](py-patterns/SKILL.md) | Protocol、DI、Repository、Strategy、模組邊界 | 單一小函式或明確框架操作 | 3.10 |
| [`py-cli`](py-cli/SKILL.md) | 命令列工具、參數、子命令、exit code、Rich、Textual | 桌面視窗或 HTTP API | 3.10 |
| [`py-perf`](py-perf/SKILL.md) | profiling、benchmark、記憶體、瓶頸、效能回歸 | 尚未有可重現瓶頸時的猜測性優化 | 3.10 |
| [`py-ai`](py-ai/SKILL.md) | LLM、RAG、embedding、tool calling、本地模型、eval | 一般資料分析或無模型的 Web API | 3.10 |
| [`py-web`](py-web/SKILL.md) | FastAPI、Pydantic、SQLAlchemy、ASGI、認證、Web API | 自訂 TCP/UDP 協議 | 3.10 |
| [`py-gui`](py-gui/SKILL.md) | tkinter、CustomTkinter、PySide6、桌面事件迴圈、打包 | 純終端機工具 | 3.10 |
| [`py-network`](py-network/SKILL.md) | socket、TCP/UDP、TLS、WebSocket、DNS、協議、proxy | 一般 CRUD HTTP endpoint | 3.10 |

## 選擇順序

1. **先看最後交付物**：Web API、CLI、GUI、資料管線、AI 應用或網路協議。
2. **再看核心風險**：非同步、測試、效能、打包或架構。
3. **只選一個主要 skill**：主要 skill 負責工作流與交付標準。
4. **支援 skill 最多一至兩個**：避免規則衝突與上下文膨脹。
5. **細節按需讀取**：完整範例、速查表與陷阱位於各 skill 的 `references/`。

## 常見任務組合

### 生產級 Web API

- 主要：`py-web`
- 支援：`py-testing`, `py-packaging`
- 若有大量並行 I/O：再讀 `py-async`

### RAG 或 Tool-calling 服務

- 主要：`py-ai`
- 支援：`py-web`, `py-testing`
- 資料索引與品質：按需讀 `py-data`

### 大型 ETL / 分析管線

- 主要：`py-data`
- 支援：`py-testing`, `py-perf`
- 發布為套件或排程工具：按需讀 `py-packaging` 或 `py-cli`

### 即時連線或自訂協議

- 主要：`py-network`
- 支援：`py-async`, `py-testing`
- 若只是 FastAPI WebSocket endpoint，仍以 `py-web` 為主。

### 跨平台桌面應用

- 主要：`py-gui`
- 支援：`py-packaging`, `py-testing`
- 背景 I/O 很多時：按需讀 `py-async`

### 舊專案現代化

- 主要：`py-modern`
- 支援：`py-packaging`, `py-testing`
- 先保持行為不變，再逐步導入新語法與型別規則。

## 每個 Skill 的標準結構

```text
py-<name>/
├── SKILL.md
└── references/
    ├── examples.md
    ├── cheatsheet.md
    └── pitfalls.md
```

`SKILL.md` 應包含：

- 可辨識的 frontmatter
- 適用邊界
- `執行流程`
- 決策與實作規範
- 驗證方式
- `交付標準`
- `延伸閱讀`
- `版本相容性`

## 儲存庫層級檔案

| 檔案 | 用途 |
|---|---|
| [`AGENTS.md`](AGENTS.md) | 所有代理共用的執行與維護規範 |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | 新增、更新與 PR 流程 |
| [`skills-manifest.json`](skills-manifest.json) | 機器可讀的 skill 清單與版本政策 |
| [`evals/trigger-cases.json`](evals/trigger-cases.json) | 正向與負向觸發案例 |
| [`scripts/validate_skills.py`](scripts/validate_skills.py) | 無第三方依賴的結構驗證器 |
| [`.github/workflows/validate-skills.yml`](.github/workflows/validate-skills.yml) | CI 品質閘門 |

## 驗證

```bash
python scripts/validate_skills.py --strict
python -m unittest discover -s tests -v
python -m pip install -r requirements-dev.txt
for skill in py-*; do agentskills validate "$skill"; done
```

## 版本政策

- 穩定維護基準：Python 3.14。
- 實際產出必須遵守目標專案宣告的最低版本。
- Python 3.15 與其他預覽功能只作為 preview。
- 易變套件 API 不在索引中硬綁 patch 版本；使用時依鎖定檔及官方文件確認。
