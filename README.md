# Python Skills

面向 Codex、ChatGPT 與其他相容 AI 編碼代理的 **12 組 Python 工程技能**。每組提供任務選擇、執行流程、安全邊界、交付標準，以及按需載入的範例與除錯參考。這是 skills-only 套件，不是 Python runtime，也不包含 MCP server。

## 開始使用

安裝腳本只需要 **Python 3.10+ 標準函式庫**，不需 API key，不下載 Python 套件。腳本修改的是「執行腳本的環境」，不會將本機檔案自動同步到 ChatGPT 網頁或其他 VM。

本次整合主線為 `main`，原 `master` 保留。Clone 時明確指定分支，避免取得尚未整合 plugin 的舊預設分支：

```bash
git clone --branch main --single-branch https://github.com/stevenke1981/python_skills.git
cd python_skills
python scripts/install_codex.py --mode skills --scope user --dry-run
python scripts/install_codex.py --mode skills --scope user
```

Windows PowerShell（`python` 不存在時可改用 `py -3`）：

```powershell
.\scripts\install_codex.ps1 --mode skills --scope user --dry-run
.\scripts\install_codex.ps1 --mode skills --scope user
```

重新開啟 Codex session 以探索 skills。在支援本機 Marketplace 的環境，使用 plugin 模式：

```bash
python scripts/install_codex.py --mode plugin --scope user
```

此命令建立本機 plugin 與 marketplace entry；仍需在支援的 Plugins 介面選擇 **Python Engineering Skills** 並安裝。它不會變更模型、sandbox 或核准規則。

## 更新與保護既有檔案

重新執行安裝命令可更新未修改的安裝。安裝器先驗證來源、manifest、路徑與共用設定，再暫存全部內容，最後替換目標；可捕捉的 I/O 錯誤會觸發回復。

每個安裝目錄包含 `.python-skills-install.json` 雜湊紀錄。**舊版沒有紀錄，或內容曾被手動修改時，預設停止而不是覆蓋。** 請先自行備份，再明確使用 `--force`；`--force` 不會繞過 symlink、junction 或路徑越界檢查。

```bash
# 僅在已備份、確定要覆蓋舊版或本機修改後執行
python scripts/install_codex.py --mode skills --scope user --force

# 解除安裝；模式及範圍需與安裝時一致
python scripts/uninstall_codex.py --mode skills --scope user --dry-run
python scripts/uninstall_codex.py --mode skills --scope user
```

其他 skills、其他 marketplace entries 與 `config.toml` 不會被移除。完整範圍、復原與限制請看 [CODEX_PLUGIN.md](CODEX_PLUGIN.md)。

## 技能列表

| Skill | 主要任務 | 建議最低 Python |
|---|---|---|
| [py-modern](skills/py-modern/SKILL.md) | 現代語法、升級、型別與 free-threaded Python | 3.12 |
| [py-async](skills/py-async/SKILL.md) | asyncio、取消、逾時、背壓 | 3.11 |
| [py-data](skills/py-data/SKILL.md) | pandas、Polars、Arrow、DuckDB、ETL | 3.10 |
| [py-testing](skills/py-testing/SKILL.md) | 測試策略、故障注入、產物驗收 | 3.10 |
| [py-packaging](skills/py-packaging/SKILL.md) | pyproject.toml、依賴、ZIP、wheel、發布 | 3.10 |
| [py-patterns](skills/py-patterns/SKILL.md) | Protocol、依賴注入與架構 | 3.10 |
| [py-cli](skills/py-cli/SKILL.md) | argparse、Typer、Click、Rich、CLI UX | 3.10 |
| [py-perf](skills/py-perf/SKILL.md) | profiling、benchmark、效能回歸 | 3.10 |
| [py-ai](skills/py-ai/SKILL.md) | LLM、RAG、tool calling、eval | 3.10 |
| [py-web](skills/py-web/SKILL.md) | FastAPI、Pydantic、SQLAlchemy、API 安全 | 3.10 |
| [py-gui](skills/py-gui/SKILL.md) | tkinter、PySide6、桌面架構與打包 | 3.10 |
| [py-network](skills/py-network/SKILL.md) | TCP/UDP、TLS、WebSocket、重試 | 3.10 |

先依最後交付物選一個主要 skill，再按需加入一至兩個支援 skill；只在需要時讀取 `references/`。例如 API 以 `py-web` 為主，搭配 `py-testing` 與 `py-packaging`。

## 下載版與原始碼版

GitHub Actions 的 **Validate and Package Codex Plugin** 成功後，提供 `python-engineering-skills` artifact，內含可解壓安裝的 ZIP 及 `.sha256`。ZIP 內已包含解除安裝所需的 `skills-manifest.json` 與共用工具，不依賴原始碼 checkout。

Linux 可用 `sha256sum -c <ZIP檔名>.sha256`；PowerShell 使用 `Get-FileHash <ZIP檔名> -Algorithm SHA256` 比對雜湊。Checksum 用來檢查傳輸完整性，不是數位簽章。

開發、完整驗證與重新打包需使用 Git 原始碼版。安裝用 ZIP 刻意不包含測試、CI 或根目錄維護副本。

## 維護與品質閘門（Git 原始碼版）

修改前閱讀 `AGENTS.md` 與 `CONTRIBUTING.md`。`index.md` 提供路由索引；`skills-manifest.json` 與 `evals/trigger-cases.json` 維護機器清單及觸發案例。

根目錄 `py-*` 是唯一維護來源，`skills/` 是安裝鏡像，請勿分別手動修改。同步器拒絕空來源、不完整來源及不安全路徑；內容相同的檔案不會重新複製。

```bash
python scripts/sync_plugin_skills.py
python scripts/sync_plugin_skills.py --check
python scripts/validate_skills.py --strict
python scripts/validate_plugin.py
python -m unittest discover -s tests -v
python -m compileall -q scripts tests
python scripts/package_plugin.py
```

Agent Skills 參考驗證器需另安裝 `requirements-dev.txt`，CI 會執行。離線標準函式庫測試不需安裝該依賴。

CI 覆蓋 `main`、`master` 與 `agent/**`：安裝工具在 Ubuntu、Windows、macOS × Python 3.10/3.14 執行回歸測試，另以 Python 3.11/3.14 執行上游 Agent Skills 驗證。ZIP 只在跨平台矩陣成功後建立。

## 相容性與限制

Python 3.14 是技能內容維護基準，安裝工具最低版本為 3.10；實際產生的程式仍需遵守目標專案最低版本。預覽功能不可自動當成正式環境基準。

回復機制不是跨多路徑的單一原子交易，也不保證斷電復原；請勿同時執行多個安裝、同步或移除程序。`--force` 成功後不保留歷史備份。官方格式與套件 API 仍應以目標版本文件確認。
