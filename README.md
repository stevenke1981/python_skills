# Python Skills

面向 AI 編碼代理的 Python 技能包，遵循 Agent Skills 目錄與 `SKILL.md` 格式。內容涵蓋語言、非同步、資料、測試、打包、架構、CLI、效能、AI、Web、GUI 與網路程式設計。

本專案不是單純的 Python 教學筆記。每個 skill 都提供：

- 可被代理辨識的觸發描述
- 任務導向的執行流程與決策指南
- 安全、相容性與品質閘門
- 按需載入的完整範例、速查表與常見陷阱
- 可由 CI 與 Agent Skills 參考工具驗證的結構

## 技能列表

| Skill | 主要用途 | 建議最低 Python |
|---|---|---:|
| [`py-modern`](py-modern/SKILL.md) | 現代語法、版本升級、型別系統、free-threaded Python | 3.12 |
| [`py-async`](py-async/SKILL.md) | asyncio、結構化並行、取消、逾時、背壓 | 3.11 |
| [`py-data`](py-data/SKILL.md) | pandas、Polars、Arrow、DuckDB、ETL 與資料品質 | 3.10 |
| [`py-testing`](py-testing/SKILL.md) | pytest、測試架構、property-based、coverage | 3.10 |
| [`py-packaging`](py-packaging/SKILL.md) | pyproject.toml、uv、build、wheel、PyPI 發布 | 3.10 |
| [`py-patterns`](py-patterns/SKILL.md) | Protocol、依賴注入、設計模式、架構邊界 | 3.10 |
| [`py-cli`](py-cli/SKILL.md) | argparse、Typer、Click、Rich、Textual 與 CLI UX | 3.10 |
| [`py-perf`](py-perf/SKILL.md) | profiling、benchmark、記憶體與效能回歸 | 3.10 |
| [`py-ai`](py-ai/SKILL.md) | LLM、RAG、tool calling、本地模型、eval 與防護 | 3.10 |
| [`py-web`](py-web/SKILL.md) | FastAPI、Pydantic、SQLAlchemy、ASGI 與 API 安全 | 3.10 |
| [`py-gui`](py-gui/SKILL.md) | tkinter、CustomTkinter、PySide6、桌面架構與打包 | 3.10 |
| [`py-network`](py-network/SKILL.md) | TCP/UDP、TLS、WebSocket、協議、重試與背壓 | 3.10 |

完整的選用方式與交叉搭配請看 [`index.md`](index.md)。

## 快速驗證

只使用標準函式庫的專案驗證器：

```bash
python scripts/validate_skills.py --strict
python -m unittest discover -s tests -v
```

再使用 Agent Skills 參考驗證器：

```bash
python -m pip install -r requirements-dev.txt
for skill in py-*; do agentskills validate "$skill"; done
```

Windows PowerShell：

```powershell
python scripts/validate_skills.py --strict
python -m unittest discover -s tests -v
python -m pip install -r requirements-dev.txt
Get-ChildItem -Directory py-* | ForEach-Object { agentskills validate $_.FullName }
```

## 使用方式

1. 依所使用代理的文件，將需要的 `py-*` 目錄複製或連結到它的 skills 目錄。
2. 讓代理先從 `description` 選擇一個主要 skill。
3. 載入該 skill 的 `SKILL.md`。
4. 只有需要完整程式碼、速查或除錯時，再讀取 `references/`。
5. 同一任務通常只需要一個主要 skill，加上一至兩個支援 skill。

範例：

- 建立 FastAPI 服務：`py-web` 為主，搭配 `py-testing` 與 `py-packaging`。
- 建立 RAG API：`py-ai` 為主，搭配 `py-web`、`py-data` 與 `py-testing`。
- 現代化舊專案：`py-modern` 為主，搭配 `py-packaging` 與 `py-testing`。
- 建立即時網路服務：`py-network` 為主，搭配 `py-async` 與 `py-testing`。

## 目錄結構

```text
python_skills/
├── AGENTS.md                     # 跨代理維護與執行規範
├── CONTRIBUTING.md               # 貢獻流程
├── README.md
├── index.md                      # skill 路由索引
├── skills-manifest.json          # 機器可讀清單
├── evals/
│   └── trigger-cases.json        # 正向與負向觸發案例
├── scripts/
│   └── validate_skills.py        # 無第三方依賴的驗證器
├── tests/
│   └── test_validate_skills.py
├── .github/workflows/
│   └── validate-skills.yml
└── py-*/
    ├── SKILL.md
    └── references/
        ├── examples.md
        ├── cheatsheet.md
        └── pitfalls.md
```

## 版本政策

- 穩定維護基準為 Python 3.14。
- 各 skill 的最低版本不同，實際實作必須先遵守目標專案的 `requires-python` 與 CI 矩陣。
- Python 3.15 與套件預覽功能只可作為 preview 選項，不作為預設生產方案。
- 套件 API、支援版本與安全建議會變動；更新時應以官方文件或上游發行說明為準。

## 維護

修改前先讀取 [`AGENTS.md`](AGENTS.md)，新增或更新 skill 請依 [`CONTRIBUTING.md`](CONTRIBUTING.md) 執行。CI 會檢查 frontmatter、目錄名稱、必要章節、相對連結、參考檔、manifest 與觸發案例。
