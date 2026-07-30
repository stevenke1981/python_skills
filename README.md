# Python Skills

面向 ChatGPT、Codex 與其他 AI 編碼代理的 Python 技能包，遵循 Agent Skills 目錄與 `SKILL.md` 格式。內容涵蓋語言、非同步、資料、測試、打包、架構、CLI、效能、AI、Web、GUI 與網路程式設計。

本專案同時是一個可安裝的 **skills-only Codex plugin**：

- Plugin manifest：`.codex-plugin/plugin.json`
- Marketplace：`.agents/plugins/marketplace.json`
- Plugin skills：`skills/`
- 完整安裝說明：[`CODEX_PLUGIN.md`](CODEX_PLUGIN.md)

## Codex / ChatGPT 快速安裝

加入 GitHub Marketplace：

```bash
codex plugin marketplace add stevenke1981/python_skills
codex plugin marketplace list
```

從已下載的儲存庫安裝到使用者 Marketplace：

```bash
python scripts/install_codex.py --mode plugin --scope user
```

直接安裝 skills 到 Codex VM：

```bash
python scripts/install_codex.py --mode skills --scope user
```

Windows PowerShell：

```powershell
.\scripts\install_codex.ps1 --mode plugin --scope user
```

重新執行安裝命令會先取代這個外掛或同名 skills 的舊版本，但會保留使用者其他 Marketplace 外掛與 skills。

本專案不是單純的 Python 教學筆記。每個 skill 都提供：

- 可被代理辨識的觸發描述
- 任務導向的執行流程與決策指南
- 安全、相容性與品質閘門
- 按需載入的完整範例、速查表與常見陷阱
- 可由 CI、外掛驗證器與 Agent Skills 參考工具驗證的結構

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

只使用標準函式庫的技能與外掛驗證器：

```bash
python scripts/validate_skills.py --strict
python scripts/sync_plugin_skills.py --check
python scripts/validate_plugin.py
python -m unittest discover -s tests -v
```

建立可發布 ZIP：

```bash
python scripts/package_plugin.py
```

再使用 Agent Skills 參考驗證器：

```bash
python -m pip install -r requirements-dev.txt
for skill in py-*; do agentskills validate "$skill"; done
```

Windows PowerShell：

```powershell
python scripts/validate_skills.py --strict
python scripts/sync_plugin_skills.py --check
python scripts/validate_plugin.py
python -m unittest discover -s tests -v
python -m pip install -r requirements-dev.txt
Get-ChildItem -Directory py-* | ForEach-Object { agentskills validate $_.FullName }
```

## 使用方式

1. 由代理或 Plugin Marketplace 依 `description` 選擇主要 skill。
2. 載入該 skill 的 `SKILL.md`。
3. 只有需要完整程式碼、速查或除錯時，再讀取 `references/`。
4. 同一任務通常只需要一個主要 skill，加上一至兩個支援 skill。

範例：

- 建立 FastAPI 服務：`py-web` 為主，搭配 `py-testing` 與 `py-packaging`。
- 建立 RAG API：`py-ai` 為主，搭配 `py-web`、`py-data` 與 `py-testing`。
- 現代化舊專案：`py-modern` 為主，搭配 `py-packaging` 與 `py-testing`。
- 建立即時網路服務：`py-network` 為主，搭配 `py-async` 與 `py-testing`。

## 目錄結構

```text
python_skills/
├── .codex-plugin/
│   └── plugin.json                 # Codex / ChatGPT plugin manifest
├── .agents/plugins/
│   └── marketplace.json            # 本機與 GitHub Marketplace 清單
├── .github/workflows/
│   ├── validate-skills.yml
│   └── package-plugin.yml          # 驗證並產生 ZIP artifact
├── AGENTS.md                       # 跨代理維護與執行規範
├── CODEX_PLUGIN.md                 # 安裝、更新、移除與發布說明
├── CONTRIBUTING.md
├── README.md
├── index.md                        # skill 路由索引
├── skills-manifest.json            # 機器可讀清單
├── evals/
│   └── trigger-cases.json
├── scripts/
│   ├── install_codex.py
│   ├── install_codex.ps1
│   ├── install_codex.sh
│   ├── package_plugin.py
│   ├── sync_plugin_skills.py
│   ├── uninstall_codex.py
│   ├── validate_plugin.py
│   └── validate_skills.py
├── tests/
│   ├── test_validate_plugin.py
│   └── test_validate_skills.py
├── skills/                         # 安裝用鏡像，由 py-* 同步產生
│   └── py-*/
│       ├── SKILL.md
│       └── references/
└── py-*/                           # 唯一維護來源
    ├── SKILL.md
    └── references/
        ├── examples.md
        ├── cheatsheet.md
        └── pitfalls.md
```

## 版本政策

- 穩定維護基準為 Python 3.14。
- 安裝器、同步器與外掛驗證器維持 Python 3.10+ 標準函式庫相容。
- 各 skill 的最低版本不同，實際實作必須先遵守目標專案的 `requires-python` 與 CI 矩陣。
- Python 3.15 與套件預覽功能只可作為 preview 選項，不作為預設生產方案。
- 套件 API、支援版本與安全建議會變動；更新時應以官方文件或上游發行說明為準。

## 維護

根目錄 `py-*` 是技能唯一維護來源。修改後執行：

```bash
python scripts/sync_plugin_skills.py
python scripts/validate_skills.py --strict
python scripts/validate_plugin.py
python -m unittest discover -s tests -v
```

修改前先讀取 [`AGENTS.md`](AGENTS.md)，新增或更新 skill 請依 [`CONTRIBUTING.md`](CONTRIBUTING.md) 執行。CI 會檢查 frontmatter、目錄名稱、必要章節、相對連結、參考檔、manifest、觸發案例、外掛鏡像與 ZIP 打包。
